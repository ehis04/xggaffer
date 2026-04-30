from __future__ import annotations

import unicodedata

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.clubs.models import (
    Club,
    ClubPlayer,
    ClubPlayerInjury,
    ClubSeasonResult,
    Fixture,
)
from apps.livefootball.models import CompetitionFixture, TeamDirectoryEntry
from apps.playerdata.models import ClubSeasonEnrichment, PlayerSeasonEnrichment
from apps.players.models import ExternalProvider, Player, PlayerExternalIdentity


def _normalise_club_name(value: str) -> str:
    if not value:
        return ""

    normalised = unicodedata.normalize("NFKD", value)
    ascii_only = normalised.encode("ascii", "ignore").decode("ascii")
    tokens = "".join(ch if ch.isalnum() else " " for ch in ascii_only.lower()).split()
    return " ".join(tokens)


def _normalise_person_name(value: str) -> str:
    if not value:
        return ""

    normalised = unicodedata.normalize("NFKD", value)
    ascii_only = normalised.encode("ascii", "ignore").decode("ascii")
    tokens = "".join(ch if ch.isalnum() else " " for ch in ascii_only.lower()).split()
    return " ".join(tokens)


def _current_playerdata_season_label() -> str:
    today = timezone.now().date()
    return str(today.year if today.month >= 7 else today.year - 1)


class Command(BaseCommand):
    help = (
        "Backfill existing real-club-copy user clubs with snapshot data from "
        "their referenced system club (players, injuries, latest understat summary, "
        "recent results, upcoming fixtures)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--club-id",
            action="append",
            type=int,
            dest="club_ids",
            help="Restrict to one or more club IDs (repeat flag for multiple).",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            default=False,
            help="Persist changes. Without this flag, runs in dry-run mode.",
        )

    def handle(self, *args, **options):
        commit = options["commit"]
        club_ids = options.get("club_ids") or []

        if club_ids:
            queryset = Club.objects.filter(
                id__in=club_ids,
                is_trashed=False,
            ).order_by("id")
        else:
            queryset = Club.objects.filter(
                club_type=Club.ClubType.USER_FICTIONAL,
                fictional_basis=Club.FictionalBasis.REAL_CLUB_COPY,
                is_trashed=False,
            ).order_by("id")

        clubs = list(queryset)

        if not clubs:
            self.stdout.write(self.style.WARNING("No target clubs found."))
            return

        mode = "COMMIT" if commit else "DRY-RUN"
        self.stdout.write(f"Running real-club-copy snapshot backfill in {mode} mode")

        stats = {
            "clubs_scanned": 0,
            "clubs_backfilled": 0,
            "clubs_skipped_no_source": 0,
            "players_created": 0,
            "injuries_created": 0,
            "enrichments_created": 0,
            "results_created": 0,
            "fixtures_created": 0,
        }

        for club in clubs:
            stats["clubs_scanned"] += 1

            source_name = (club.source_real_club_name or club.name or "").strip()
            source_club = self._find_source_system_club(source_name)
            if source_club is None:
                stats["clubs_skipped_no_source"] += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"[{club.id}] {club.name}: no system source found for '{source_name}'"
                    )
                )
                continue

            delta = self._build_backfill_plan(club=club, source_club=source_club)
            has_changes = any(value > 0 for value in delta.values())

            if not has_changes:
                self.stdout.write(f"[{club.id}] {club.name}: already hydrated, no changes")
                continue

            if commit:
                with transaction.atomic():
                    applied = self._apply_backfill(club=club, source_club=source_club, plan=delta)
            else:
                applied = delta

            stats["clubs_backfilled"] += 1
            stats["players_created"] += applied["players_created"]
            stats["injuries_created"] += applied["injuries_created"]
            stats["enrichments_created"] += applied["enrichments_created"]
            stats["results_created"] += applied["results_created"]
            stats["fixtures_created"] += applied["fixtures_created"]

            self.stdout.write(
                (
                    f"[{club.id}] {club.name}: players={applied['players_created']}, "
                    f"injuries={applied['injuries_created']}, enrichments={applied['enrichments_created']}, "
                    f"results={applied['results_created']}, fixtures={applied['fixtures_created']}"
                )
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Backfill summary"))
        self.stdout.write(f"  clubs_scanned: {stats['clubs_scanned']}")
        self.stdout.write(f"  clubs_backfilled: {stats['clubs_backfilled']}")
        self.stdout.write(f"  clubs_skipped_no_source: {stats['clubs_skipped_no_source']}")
        self.stdout.write(f"  players_created: {stats['players_created']}")
        self.stdout.write(f"  injuries_created: {stats['injuries_created']}")
        self.stdout.write(f"  enrichments_created: {stats['enrichments_created']}")
        self.stdout.write(f"  results_created: {stats['results_created']}")
        self.stdout.write(f"  fixtures_created: {stats['fixtures_created']}")

        if not commit:
            self.stdout.write(self.style.WARNING("Dry-run only. Re-run with --commit to persist."))

    def _find_source_system_club(self, source_name: str):
        source_key = _normalise_club_name(source_name)
        if not source_key:
            return None

        candidates = list(
            Club.objects.filter(club_type=Club.ClubType.SYSTEM_PROFESSIONAL)
            .only("id", "name")
            .order_by("id")
        )

        exact_match = next(
            (club for club in candidates if _normalise_club_name(club.name) == source_key),
            None,
        )
        if exact_match is not None:
            return exact_match

        startswith_match = next(
            (
                club
                for club in candidates
                if _normalise_club_name(club.name).startswith(source_key)
                or source_key.startswith(_normalise_club_name(club.name))
            ),
            None,
        )
        if startswith_match is not None:
            return startswith_match

        return next(
            (
                club
                for club in candidates
                if source_key in _normalise_club_name(club.name)
                or _normalise_club_name(club.name) in source_key
            ),
            None,
        )

    def _build_backfill_plan(self, *, club: Club, source_club: Club):
        has_players = club.club_players.filter(is_active=True).exists()
        has_injuries = ClubPlayerInjury.objects.filter(
            club_player__club=club,
            is_current=True,
        ).exists()
        has_understat = club.season_enrichments.filter(provider=ExternalProvider.UNDERSTAT).exists()
        has_results = club.season_results.exists()
        has_upcoming_fixtures = club.fixtures.filter(match_datetime__gte=timezone.now()).exists()

        plan = {
            "create_players": not has_players,
            "create_injuries": not has_injuries,
            "create_enrichment": not has_understat,
            "create_results": not has_results,
            "create_fixtures": not has_upcoming_fixtures,
        }

        if not plan["create_players"]:
            plan["create_injuries"] = plan["create_injuries"] and bool(
                ClubPlayerInjury.objects.filter(
                    club_player__club=source_club,
                    is_current=True,
                ).exists()
            )

        livefootball_fixtures = self._get_livefootball_fixtures_for_source(source_club)
        livefootball_results_count = livefootball_fixtures.filter(status="FINISHED").count()
        livefootball_upcoming_count = livefootball_fixtures.filter(
            Q(status__in=["TIMED", "SCHEDULED"]),
            kickoff_at__gte=timezone.now(),
        ).count()

        source_players_count = source_club.club_players.filter(is_active=True).count()
        source_injuries_count = ClubPlayerInjury.objects.filter(
            club_player__club=source_club,
            is_current=True,
        ).count()
        source_results_count = source_club.season_results.count() or livefootball_results_count
        source_fixtures_count = (
            source_club.fixtures.filter(match_datetime__gte=timezone.now()).count()
            or livefootball_upcoming_count
        )
        source_understat_count = source_club.season_enrichments.filter(
            provider=ExternalProvider.UNDERSTAT,
        ).count()
        source_lf_table_row = self._get_livefootball_table_row_for_source(source_club)
        has_enrichment_source = source_understat_count > 0 or source_lf_table_row is not None

        return {
            "players_created": source_players_count if plan["create_players"] else 0,
            "injuries_created": source_injuries_count if plan["create_injuries"] else 0,
            "enrichments_created": 1 if plan["create_enrichment"] and has_enrichment_source else 0,
            "results_created": min(source_results_count, 38) if plan["create_results"] else 0,
            "fixtures_created": min(source_fixtures_count, 30) if plan["create_fixtures"] else 0,
            "_flags": plan,
        }

    def _player_profile_provider_set(self, player: Player | None, season_label: str) -> set[str]:
        if player is None:
            return set()

        return set(
            PlayerSeasonEnrichment.objects.filter(
                player=player,
                season_label=season_label,
                provider__in=[
                    ExternalProvider.UNDERSTAT,
                    ExternalProvider.SOFASCORE,
                ],
            ).values_list("provider", flat=True).distinct()
        )

    def _club_player_name_keys(self, club_player: ClubPlayer) -> set[str]:
        keys = {
            _normalise_person_name(club_player.display_name),
            _normalise_person_name(
                f"{club_player.first_name} {club_player.last_name}".strip()
            ),
        }

        if club_player.player_id:
            keys.update({
                _normalise_person_name(club_player.player.display_name),
                _normalise_person_name(club_player.player.full_name),
            })

        keys.discard("")
        return keys

    def _matching_current_profile_club_players(
        self,
        *,
        source_club: Club,
        source_player: ClubPlayer,
        season_label: str,
    ):
        target_keys = self._club_player_name_keys(source_player)
        if not target_keys:
            return []

        enriched_club_players = (
            source_club.club_players
            .filter(
                player__season_enrichments__season_label=season_label,
                player__season_enrichments__provider__in=[
                    ExternalProvider.UNDERSTAT,
                    ExternalProvider.SOFASCORE,
                ],
            )
            .select_related("player")
            .distinct()
        )

        return [
            candidate
            for candidate in enriched_club_players
            if candidate.player_id
            and target_keys & self._club_player_name_keys(candidate)
        ]

    def _copy_missing_current_profile_data(
        self,
        *,
        target_player: Player,
        candidates: list[ClubPlayer],
        season_label: str,
    ) -> None:
        candidate_player_ids = {
            candidate.player_id
            for candidate in candidates
            if candidate.player_id and candidate.player_id != target_player.id
        }
        if not candidate_player_ids:
            return

        profile_providers = [
            ExternalProvider.UNDERSTAT,
            ExternalProvider.SOFASCORE,
        ]

        existing_providers = set(
            PlayerSeasonEnrichment.objects.filter(
                player=target_player,
                season_label=season_label,
                provider__in=profile_providers,
            ).values_list("provider", flat=True).distinct()
        )

        enrichments = (
            PlayerSeasonEnrichment.objects
            .filter(
                player_id__in=candidate_player_ids,
                season_label=season_label,
                provider__in=profile_providers,
            )
            .order_by("provider", "-matches_played", "-minutes_played", "-updated_at", "-id")
        )

        for enrichment in enrichments:
            if enrichment.provider in existing_providers:
                continue

            PlayerSeasonEnrichment.objects.update_or_create(
                player=target_player,
                provider=enrichment.provider,
                season_label=enrichment.season_label,
                competition_code=enrichment.competition_code,
                external_team_id=enrichment.external_team_id,
                defaults={
                    "club": enrichment.club,
                    "competition_name": enrichment.competition_name,
                    "external_player_id": enrichment.external_player_id,
                    "matches_played": enrichment.matches_played,
                    "minutes_played": enrichment.minutes_played,
                    "goals": enrichment.goals,
                    "assists": enrichment.assists,
                    "shots": enrichment.shots,
                    "xg": enrichment.xg,
                    "xa": enrichment.xa,
                    "npg": enrichment.npg,
                    "npxg": enrichment.npxg,
                    "xg_chain": enrichment.xg_chain,
                    "xg_buildup": enrichment.xg_buildup,
                    "yellow_cards": enrichment.yellow_cards,
                    "red_cards": enrichment.red_cards,
                    "key_passes": enrichment.key_passes,
                    "last_synced_at": enrichment.last_synced_at,
                    "metadata": enrichment.metadata,
                    "raw_snapshot": enrichment.raw_snapshot,
                },
            )
            existing_providers.add(enrichment.provider)

        existing_identity_providers = set(
            PlayerExternalIdentity.objects.filter(
                player=target_player,
                provider__in=profile_providers,
            ).values_list("provider", flat=True).distinct()
        )
        identities = (
            PlayerExternalIdentity.objects
            .filter(
                player_id__in=candidate_player_ids,
                provider__in=profile_providers,
            )
            .order_by("provider", "-is_primary", "-last_synced_at", "-updated_at", "-id")
        )
        for identity in identities:
            if identity.provider in existing_identity_providers:
                continue
            identity.player = target_player
            identity.last_synced_at = identity.last_synced_at or timezone.now()
            identity.save(update_fields=["player", "last_synced_at", "updated_at"])
            existing_identity_providers.add(identity.provider)

    def _resolve_profile_player_for_copy(
        self,
        *,
        source_club: Club,
        source_player: ClubPlayer,
    ) -> Player | None:
        target_keys = self._club_player_name_keys(source_player)
        if not target_keys:
            return source_player.player

        season_label = _current_playerdata_season_label()
        provider_order = {
            ExternalProvider.UNDERSTAT: 2,
            ExternalProvider.SOFASCORE: 1,
        }
        matching_candidates = self._matching_current_profile_club_players(
            source_club=source_club,
            source_player=source_player,
            season_label=season_label,
        )

        if source_player.player_id:
            self._copy_missing_current_profile_data(
                target_player=source_player.player,
                candidates=matching_candidates,
                season_label=season_label,
            )
            return source_player.player

        candidates: list[tuple[tuple[int, int, int, int], Player]] = []

        for candidate in matching_candidates:
            providers = self._player_profile_provider_set(candidate.player, season_label)
            if not providers:
                continue

            candidates.append((
                (
                    len(providers),
                    sum(provider_order.get(provider, 0) for provider in providers),
                    int(candidate.is_active),
                    -candidate.id,
                ),
                candidate.player,
            ))

        if not candidates:
            return source_player.player

        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _apply_backfill(self, *, club: Club, source_club: Club, plan: dict):
        flags = plan["_flags"]
        owner_membership = club.memberships.filter(
            role=club.memberships.model.Role.OWNER,
            is_active=True,
        ).select_related("user").first()
        owner = owner_membership.user if owner_membership else club.creator
        created_counts = {
            "players_created": 0,
            "injuries_created": 0,
            "enrichments_created": 0,
            "results_created": 0,
            "fixtures_created": 0,
        }

        source_to_new_player_ids = {}

        if flags["create_players"]:
            used_numbers = set(
                club.club_players.exclude(squad_number__isnull=True)
                .values_list("squad_number", flat=True)
            )

            source_players = source_club.club_players.filter(is_active=True).select_related("player")
            for source_player in source_players:
                linked_player = self._resolve_profile_player_for_copy(
                    source_club=source_club,
                    source_player=source_player,
                )

                if linked_player is None:
                    linked_player = Player(
                        first_name=source_player.first_name,
                        last_name=source_player.last_name,
                        display_name=source_player.display_name,
                        primary_position=source_player.primary_position,
                        preferred_foot=source_player.preferred_foot,
                        date_of_birth=source_player.date_of_birth,
                        height_cm=source_player.height_cm,
                    )

                    if hasattr(linked_player, "secondary_positions"):
                        linked_player.secondary_positions = (
                            [source_player.secondary_position]
                            if source_player.secondary_position else []
                        )

                    if hasattr(linked_player, "photo"):
                        linked_player.photo = source_player.photo

                    linked_player.save()

                squad_number = source_player.squad_number
                if squad_number in used_numbers:
                    squad_number = None
                if squad_number is not None:
                    used_numbers.add(squad_number)

                new_player = ClubPlayer.objects.create(
                    club=club,
                    player=linked_player,
                    user=None,
                    first_name=source_player.first_name,
                    last_name=source_player.last_name,
                    display_name=source_player.display_name,
                    squad_number=squad_number,
                    primary_position=source_player.primary_position,
                    secondary_position=source_player.secondary_position,
                    preferred_foot=source_player.preferred_foot,
                    date_of_birth=source_player.date_of_birth,
                    height_cm=source_player.height_cm,
                    photo=source_player.photo,
                    is_active=source_player.is_active,
                    is_public=False,
                    created_by=owner,
                )
                source_to_new_player_ids[source_player.id] = new_player.id
                created_counts["players_created"] += 1

        if flags["create_injuries"]:
            if not source_to_new_player_ids:
                source_players = source_club.club_players.filter(is_active=True).values(
                    "id",
                    "player_id",
                    "first_name",
                    "last_name",
                    "display_name",
                )
                target_players = club.club_players.filter(is_active=True).values(
                    "id",
                    "player_id",
                    "first_name",
                    "last_name",
                    "display_name",
                )

                source_by_player_id = {
                    row["player_id"]: row["id"]
                    for row in source_players
                    if row["player_id"]
                }
                target_by_player_id = {
                    row["player_id"]: row["id"]
                    for row in target_players
                    if row["player_id"]
                }

                for player_id, source_player_id in source_by_player_id.items():
                    target_player_id = target_by_player_id.get(player_id)
                    if target_player_id:
                        source_to_new_player_ids[source_player_id] = target_player_id

                if not source_to_new_player_ids:
                    source_by_name = {
                        _normalise_person_name(
                            (row.get("display_name") or "")
                            or f"{row.get('first_name', '')} {row.get('last_name', '')}"
                        ): row["id"]
                        for row in source_players
                    }
                    target_by_name = {
                        _normalise_person_name(
                            (row.get("display_name") or "")
                            or f"{row.get('first_name', '')} {row.get('last_name', '')}"
                        ): row["id"]
                        for row in target_players
                    }

                    for name_key, source_player_id in source_by_name.items():
                        target_player_id = target_by_name.get(name_key)
                        if name_key and target_player_id:
                            source_to_new_player_ids[source_player_id] = target_player_id

            source_injuries = ClubPlayerInjury.objects.filter(
                club_player__club=source_club,
                is_current=True,
            ).select_related("club_player")

            for injury in source_injuries:
                target_player_id = source_to_new_player_ids.get(injury.club_player_id)
                if not target_player_id:
                    continue

                if ClubPlayerInjury.objects.filter(
                    club_player_id=target_player_id,
                    is_current=True,
                ).exists():
                    continue

                ClubPlayerInjury.objects.create(
                    club_player_id=target_player_id,
                    injury_type=injury.injury_type,
                    severity=injury.severity,
                    availability_status=injury.availability_status,
                    injured_at=injury.injured_at,
                    estimated_return=injury.estimated_return,
                    notes=injury.notes,
                    is_current=True,
                    recorded_by=owner,
                )
                created_counts["injuries_created"] += 1

        if flags["create_enrichment"]:
            latest_understat = source_club.season_enrichments.filter(
                provider=ExternalProvider.UNDERSTAT,
            ).order_by("-season_label", "-updated_at", "-id").first()

            if latest_understat is not None:
                ClubSeasonEnrichment.objects.update_or_create(
                    club=club,
                    provider=latest_understat.provider,
                    season_label=latest_understat.season_label,
                    competition_code=latest_understat.competition_code,
                    defaults={
                        "competition_name": latest_understat.competition_name,
                        "external_team_id": latest_understat.external_team_id,
                        "matches_played": latest_understat.matches_played,
                        "wins": latest_understat.wins,
                        "draws": latest_understat.draws,
                        "losses": latest_understat.losses,
                        "goals_for": latest_understat.goals_for,
                        "goals_against": latest_understat.goals_against,
                        "xg": latest_understat.xg,
                        "xga": latest_understat.xga,
                        "npxg": latest_understat.npxg,
                        "ppda": latest_understat.ppda,
                        "last_synced_at": latest_understat.last_synced_at,
                        "metadata": latest_understat.metadata,
                        "raw_snapshot": latest_understat.raw_snapshot,
                    },
                )
                created_counts["enrichments_created"] += 1
            else:
                # Fallback: derive from livefootball competition table row
                table_row = self._get_livefootball_table_row_for_source(source_club)
                if table_row is not None:
                    snapshot = table_row.snapshot
                    competition = snapshot.competition
                    team = table_row.team
                    _, created = ClubSeasonEnrichment.objects.update_or_create(
                        club=club,
                        provider=team.provider if team else ExternalProvider.FOOTBALL_DATA,
                        season_label=snapshot.season_label,
                        competition_code=competition.code or '',
                        defaults={
                            "competition_name": competition.name,
                            "matches_played": table_row.played,
                            "wins": table_row.won,
                            "draws": table_row.drawn,
                            "losses": table_row.lost,
                            "goals_for": table_row.goals_for,
                            "goals_against": table_row.goals_against,
                        },
                    )
                    created_counts["enrichments_created"] += 1

        if flags["create_results"]:
            source_team = self._get_livefootball_team_entry(source_club)
            recent_results = list(source_club.season_results.order_by("-match_date", "-created_at")[:38])
            if recent_results:
                for result in recent_results:
                    ClubSeasonResult.objects.create(
                        club=club,
                        opponent_name=result.opponent_name,
                        venue=result.venue,
                        competition=result.competition,
                        match_date=result.match_date,
                        goals_for=result.goals_for,
                        goals_against=result.goals_against,
                        fixture=None,
                        notes=result.notes,
                        created_by=owner,
                    )
                    created_counts["results_created"] += 1
            else:
                for match in self._get_livefootball_fixtures_for_source(source_club).filter(
                    status="FINISHED"
                ).order_by("-kickoff_at", "-id")[:38]:
                    venue, opponent_name, goals_for, goals_against = self._map_livefootball_fixture(
                        source_team=source_team,
                        match=match,
                    )
                    if opponent_name is None or match.kickoff_at is None:
                        continue

                    ClubSeasonResult.objects.create(
                        club=club,
                        opponent_name=opponent_name,
                        venue=venue,
                        competition=match.competition.name,
                        match_date=match.kickoff_at.date(),
                        goals_for=goals_for or 0,
                        goals_against=goals_against or 0,
                        fixture=None,
                        notes="Imported from livefootball fixture history.",
                        created_by=owner,
                    )
                    created_counts["results_created"] += 1

        if flags["create_fixtures"]:
            source_team = self._get_livefootball_team_entry(source_club)
            upcoming_fixtures = list(
                source_club.fixtures.filter(
                    match_datetime__gte=timezone.now(),
                ).order_by("match_datetime", "id")[:30]
            )

            if upcoming_fixtures:
                for fixture in upcoming_fixtures:
                    Fixture.objects.create(
                        club=club,
                        opponent_name=fixture.opponent_name,
                        venue=fixture.venue,
                        competition=fixture.competition,
                        match_datetime=fixture.match_datetime,
                        location=fixture.location,
                        fixture_status=fixture.fixture_status,
                        source_type=Fixture.SourceType.MANUAL,
                        external_fixture_id="",
                        created_by=owner,
                    )
                    created_counts["fixtures_created"] += 1
            else:
                for match in self._get_livefootball_fixtures_for_source(source_club).filter(
                    Q(status__in=["TIMED", "SCHEDULED"]),
                    kickoff_at__gte=timezone.now(),
                ).order_by("kickoff_at", "id")[:30]:
                    venue, opponent_name, _, _ = self._map_livefootball_fixture(
                        source_team=source_team,
                        match=match,
                    )
                    if opponent_name is None or match.kickoff_at is None:
                        continue

                    Fixture.objects.create(
                        club=club,
                        opponent_name=opponent_name,
                        venue=venue,
                        competition=match.competition.name,
                        match_datetime=match.kickoff_at,
                        location="",
                        fixture_status=Fixture.FixtureStatus.SCHEDULED,
                        source_type=Fixture.SourceType.MANUAL,
                        external_fixture_id="",
                        created_by=owner,
                    )
                    created_counts["fixtures_created"] += 1

        return created_counts

    def _get_livefootball_team_entry(self, source_club: Club):
        source_key = _normalise_club_name(source_club.name)
        candidates = list(
            TeamDirectoryEntry.objects.select_related("competition")
            .order_by("-season_label", "-id")
        )
        return next(
            (team for team in candidates if _normalise_club_name(team.name) == source_key),
            None,
        )

    def _get_livefootball_table_row_for_source(self, source_club: Club):
        team = self._get_livefootball_team_entry(source_club)
        if team is None:
            return None
        from apps.livefootball.models import CompetitionTableRow
        return (
            CompetitionTableRow.objects
            .filter(team=team)
            .select_related("snapshot", "snapshot__competition", "team")
            .order_by("-snapshot__season_label", "-snapshot__synced_at", "-id")
            .first()
        )

    def _get_livefootball_fixtures_for_source(self, source_club: Club):
        team = self._get_livefootball_team_entry(source_club)
        if team is None:
            return CompetitionFixture.objects.none()

        return CompetitionFixture.objects.filter(
            Q(home_team=team) | Q(away_team=team)
        ).select_related("competition", "home_team", "away_team")

    def _map_livefootball_fixture(self, *, source_team: TeamDirectoryEntry | None, match: CompetitionFixture):
        if source_team is not None and match.home_team_id == source_team.id:
            return (
                ClubSeasonResult.Venue.HOME,
                match.away_team_name,
                match.home_score,
                match.away_score,
            )

        if source_team is not None and match.away_team_id == source_team.id:
            return (
                ClubSeasonResult.Venue.AWAY,
                match.home_team_name,
                match.away_score,
                match.home_score,
            )

        return (None, None, None, None)
