"""
Management command to seed one professional club per top-5 European league,
populate their current squads from football-data.org, then back-fill
Understat player-season enrichment records for 2014/15 – current season.

Usage
-----
    # Full run (all clubs, all seasons)
    python manage.py seed_pro_clubs

    # Wipe existing seeded clubs and start fresh
    python manage.py seed_pro_clubs --reset

    # Only run a specific club (by slug key)
    python manage.py seed_pro_clubs --club man_utd

    # Only sync specific seasons
    python manage.py seed_pro_clubs --seasons 2023 2024

    # Skip the Understat back-fill (squad sync only)
    python manage.py seed_pro_clubs --skip-understat

    # Skip the squad sync (Understat back-fill only, clubs must already exist)
    python manage.py seed_pro_clubs --skip-squad-sync

Football-data.org team IDs are hardcoded below. They are stable IDs from the
v4 API. Understat team slugs are the URL path segments used on understat.com.
"""

from __future__ import annotations

import csv
import time
import unicodedata
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.clubs.models import Club, ClubExternalIdentity, ClubPlayer
from apps.playerdata.models import PlayerSeasonEnrichment
from apps.players.models import ExternalProvider, Player, PlayerExternalIdentity
from services.providers.football_data.sync import sync_club_team_squad
from services.providers.understat.client import UnderstatClient
from services.providers.understat.sync import (
    sync_understat_club_players_season,
    sync_understat_club_season,
)

User = get_user_model()

# ──────────────────────────────────────────────────────────────────────────────
# Club catalogue
# ──────────────────────────────────────────────────────────────────────────────

PRO_CLUBS: list[dict] = [
    {
        "slug": "man_utd",
        "name": "Manchester United FC",
        "description": (
            "One of the most decorated clubs in English football history, "
            "Manchester United have won 20 First Division/Premier League titles "
            "and three UEFA Champions League trophies."
        ),
        "city": "Manchester",
        "country": "GB",
        "division": "Premier League",
        # football-data.org v4 team ID  (https://www.football-data.org/v4/teams/66)
        "football_data_team_id": "66",
        # Understat URL slug  (https://understat.com/team/Manchester_United)
        "understat_team_slug": "Manchester_United",
        # Understat competition code used in their API
        "understat_competition_code": "EPL",
    },
    {
        "slug": "real_madrid",
        "name": "Real Madrid CF",
        "description": (
            "The most successful club in UEFA Champions League history, "
            "Real Madrid have won 15 European Cups and a record 35 La Liga titles."
        ),
        "city": "Madrid",
        "country": "ES",
        "division": "La Liga",
        "football_data_team_id": "86",
        "understat_team_slug": "Real_Madrid",
        "understat_competition_code": "La_liga",
    },
    {
        "slug": "bayern",
        "name": "FC Bayern München",
        "description": (
            "Germany's most dominant club, Bayern Munich have won the Bundesliga "
            "over 30 times and claimed the UEFA Champions League six times."
        ),
        "city": "Munich",
        "country": "DE",
        "division": "Bundesliga",
        "football_data_team_id": "5",
        "understat_team_slug": "Bayern_Munich",
        "understat_competition_code": "Bundesliga",
    },
    {
        "slug": "juventus",
        "name": "Juventus FC",
        "description": (
            "Italy's most successful club, Juventus have won 36 Serie A titles "
            "and reached the UEFA Champions League final three times in the modern era."
        ),
        "city": "Turin",
        "country": "IT",
        "division": "Serie A",
        "football_data_team_id": "109",
        "understat_team_slug": "Juventus",
        "understat_competition_code": "Serie_A",
    },
    {
        "slug": "psg",
        "name": "Paris Saint-Germain FC",
        "description": (
            "France's dominant force, PSG have won 11 Ligue 1 titles since their "
            "2011 takeover and reached the UEFA Champions League final in 2020."
        ),
        "city": "Paris",
        "country": "FR",
        "division": "Ligue 1",
        "football_data_team_id": "524",
        "understat_team_slug": "Paris_Saint_Germain",
        "understat_competition_code": "Ligue_1",
    },
]

# Season labels Understat uses — just the start year of the season.
# 2014 = 2014/15, 2024 = 2024/25 (current, may be partial).
ALL_SEASONS = [str(y) for y in range(2014, 2025)]

# Short delay between Understat calls to avoid hammering their server.
UNDERSTAT_CALL_DELAY_SECONDS = 1.5

# Root of the pre-processed player CSV files.
# Layout: DATA_PLAYERS_DIR / {season_year} / players_sofascore_{league}_{year}_canonical.csv
DATA_PLAYERS_DIR = settings.BASE_DIR.parent / "data" / "processed" / "players"

# Maps our internal understat_competition_code → Sofascore team name as it appears in the CSVs.
SOFASCORE_TEAM_NAMES: dict[str, str] = {
    "EPL": "Manchester United",
    "La_liga": "Real Madrid",
    "Bundesliga": "FC Bayern München",
    "Serie_A": "Juventus",
    "Ligue_1": "Paris Saint-Germain",
}

# Maps understat_competition_code → the league token used in CSV filenames.
# (CSV files use title-case La_Liga, not Understat's La_liga.)
SOFASCORE_CSV_LEAGUE: dict[str, str] = {
    "EPL": "EPL",
    "La_liga": "La_Liga",
    "Bundesliga": "Bundesliga",
    "Serie_A": "Serie_A",
    "Ligue_1": "Ligue_1",
}


# ──────────────────────────────────────────────────────────────────────────────
# Command
# ──────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = (
        "Seed one professional club per top-5 league with squad data from "
        "football-data.org and historical player/team enrichment from Understat "
        "(seasons 2014/15 – 2024/25)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            default=False,
            help="Delete existing system-seeded pro clubs and recreate from scratch.",
        )
        parser.add_argument(
            "--club",
            dest="clubs",
            action="append",
            metavar="SLUG",
            default=None,
            help=(
                "Only process this club slug (can be repeated). "
                "Slugs: man_utd, real_madrid, bayern, juventus, psg"
            ),
        )
        parser.add_argument(
            "--seasons",
            nargs="+",
            metavar="YEAR",
            default=None,
            help=(
                "Understat season labels to sync (start year). "
                "Defaults to 2014–2024. Example: --seasons 2023 2024"
            ),
        )
        parser.add_argument(
            "--skip-understat",
            action="store_true",
            default=False,
            help="Skip Understat back-fill. Only create clubs and sync squads.",
        )
        parser.add_argument(
            "--skip-squad-sync",
            action="store_true",
            default=False,
            help=(
                "Skip football-data squad sync. Only run Understat back-fill. "
                "Clubs must already exist."
            ),
        )
        parser.add_argument(
            "--skip-sofascore",
            action="store_true",
            default=False,
            help="Skip Sofascore CSV enrichment back-fill.",
        )

    # ── main entry ─────────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        reset = options["reset"]
        club_slugs = options["clubs"]
        seasons = options["seasons"] or ALL_SEASONS
        skip_understat = options["skip_understat"]
        skip_squad_sync = options["skip_squad_sync"]
        skip_sofascore = options["skip_sofascore"]

        # Validate season labels
        for s in seasons:
            try:
                year = int(s)
                if not (2003 <= year <= 2030):
                    raise ValueError
            except ValueError:
                raise CommandError(
                    f"Invalid season label '{s}'. Use a 4-digit start year, e.g. 2024."
                )

        # Filter clubs if --club was specified
        clubs_to_seed = PRO_CLUBS
        if club_slugs:
            known = {c["slug"] for c in PRO_CLUBS}
            unknown = set(club_slugs) - known
            if unknown:
                raise CommandError(
                    f"Unknown club slug(s): {', '.join(sorted(unknown))}. "
                    f"Valid slugs: {', '.join(sorted(known))}"
                )
            clubs_to_seed = [c for c in PRO_CLUBS if c["slug"] in club_slugs]

        system_user = self._get_or_create_system_user()

        if reset:
            self._reset_clubs(system_user, clubs_to_seed)

        total_clubs = len(clubs_to_seed)
        for idx, club_config in enumerate(clubs_to_seed, start=1):
            self.stdout.write("")
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"[{idx}/{total_clubs}] {club_config['name']}"
                )
            )
            try:
                self._seed_club(
                    system_user=system_user,
                    club_config=club_config,
                    seasons=seasons,
                    skip_squad_sync=skip_squad_sync,
                    skip_understat=skip_understat,
                    skip_sofascore=skip_sofascore,
                )
            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(f"  ERROR seeding {club_config['name']}: {exc}")
                )
                # Continue with remaining clubs rather than aborting.

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("seed_pro_clubs complete."))

    # ── per-club logic ─────────────────────────────────────────────────────────

    def _seed_club(self, *, system_user, club_config, seasons, skip_squad_sync, skip_understat, skip_sofascore):
        club = self._get_or_create_club(system_user, club_config)

        if not skip_squad_sync:
            self._sync_squad(club, club_config)

        if not skip_understat:
            self._ensure_understat_identity(club, club_config)
            self._sync_understat_seasons(club, club_config, seasons)

        if not skip_sofascore:
            self._sync_sofascore_csv_seasons(club, club_config, seasons)

    def _get_or_create_club(self, system_user, club_config):
        club, created = Club.objects.get_or_create(
            name=club_config["name"],
            creator=system_user,
            defaults={
                "description": club_config["description"],
                "city": club_config["city"],
                "country": club_config["country"],
                "division": club_config.get("division", ""),
                "club_type": Club.ClubType.SYSTEM_PROFESSIONAL,
                "visibility": Club.Visibility.PUBLIC,
                "directory_visibility": Club.DirectoryVisibility.LISTED,
                "join_policy": Club.JoinPolicy.INVITE_ONLY,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"  Created club: {club.name} (id={club.id})"))
            # Make the system user an owner so they can manage the club.
            from apps.clubs.models import ClubMembership
            ClubMembership.objects.get_or_create(
                club=club,
                user=system_user,
                defaults={
                    "role": ClubMembership.Role.OWNER,
                    "is_active": True,
                    "joined_at": timezone.now(),
                },
            )
        else:
            self.stdout.write(f"  Club already exists: {club.name} (id={club.id})")

        return club

    def _sync_squad(self, club, club_config):
        football_data_id = club_config["football_data_team_id"]
        self.stdout.write(
            f"  Syncing squad from football-data.org (team_id={football_data_id})…"
        )
        try:
            result = sync_club_team_squad(
                club=club,
                external_team_id=football_data_id,
                provider="football_data",
            )
            meta = result["summary"].get("metadata", {})
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Squad sync done — "
                    f"players_created={meta.get('players_created', 0)}, "
                    f"players_updated={meta.get('players_updated', 0)}, "
                    f"club_players_created={meta.get('club_players_created', 0)}"
                )
            )
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"  Squad sync failed: {exc}"))
            raise

    def _ensure_understat_identity(self, club, club_config):
        """Create or confirm the ClubExternalIdentity for Understat."""
        slug = club_config["understat_team_slug"]
        identity, created = ClubExternalIdentity.objects.get_or_create(
            provider=ExternalProvider.UNDERSTAT,
            external_id=slug,
            defaults={
                "club": club,
                "provider_display_name": club_config["name"],
                "competition_context": club_config.get("understat_competition_code", ""),
                "is_primary": True,
                "last_synced_at": timezone.now(),
            },
        )

        if not created and identity.club_id != club.id:
            # Edge case: slug already mapped to a different club — update it.
            identity.club = club
            identity.save(update_fields=["club", "updated_at"])
            self.stdout.write(
                self.style.WARNING(
                    f"  Re-pointed Understat identity '{slug}' to club {club.id}"
                )
            )
        elif created:
            self.stdout.write(
                f"  Created Understat club identity: slug='{slug}'"
            )

    def _sync_understat_seasons(self, club, club_config, seasons):
        competition_code = club_config["understat_competition_code"]
        slug = club_config["understat_team_slug"]
        total = len(seasons)

        self.stdout.write(
            f"  Back-filling Understat data: {total} season(s), "
            f"competition={competition_code}, team={slug}"
        )

        understat_client = UnderstatClient()

        for i, season_label in enumerate(seasons, start=1):
            season_display = f"{season_label}/{int(season_label) + 1}"
            self.stdout.write(f"    [{i}/{total}] Season {season_display}…")

            errors: list[str] = []

            # ── Step 1: fetch raw Understat team page once ────────────────────
            try:
                raw_payload = understat_client.get_team_season_payload(slug, season_label)
                time.sleep(UNDERSTAT_CALL_DELAY_SECONDS)
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"      ⚠  Could not fetch Understat team page: {exc}"))
                continue

            # ── Step 2: pre-create Player/ClubPlayer records for anyone not
            #            yet in the DB so the enrichment sync can match by ID ──
            pre_created, pre_linked = self._ensure_historical_players(
                club=club,
                raw_players=raw_payload.get("players") or [],
                season_label=season_label,
            )
            if pre_created or pre_linked:
                self.stdout.write(
                    f"      pre-created={pre_created} players, "
                    f"linked-existing={pre_linked} identities"
                )

            # ── Step 3: team-level enrichment (xG, xGA, PPDA, etc.) ──────────
            try:
                team_result = sync_understat_club_season(
                    club=club,
                    season_label=season_label,
                    competition_code=competition_code,
                    external_team_id=slug,
                )
                team_meta = team_result["summary"].get("metadata", {})
                team_status = "ok" if team_meta.get("enrichment_created") or team_meta.get("enrichment_updated") else "updated"
            except Exception as exc:
                team_status = "err"
                errors.append(f"team enrichment: {exc}")

            time.sleep(UNDERSTAT_CALL_DELAY_SECONDS)

            # ── Step 4: per-player enrichment (goals, assists, xG, xA…) ──────
            try:
                player_result = sync_understat_club_players_season(
                    club=club,
                    season_label=season_label,
                    competition_code=competition_code,
                    external_team_id=slug,
                )
                p_meta = player_result["summary"].get("metadata", {})
                player_status = (
                    f"matched={p_meta.get('players_matched', 0)}, "
                    f"unmatched={p_meta.get('players_unmatched', 0)}, "
                    f"enrichments_created={p_meta.get('player_season_enrichments_created', 0)}"
                )
            except Exception as exc:
                player_status = "err"
                errors.append(f"player enrichments: {exc}")

            time.sleep(UNDERSTAT_CALL_DELAY_SECONDS)

            self.stdout.write(
                f"      team={team_status} | players={player_status}"
            )

            if errors:
                for err in errors:
                    self.stdout.write(self.style.WARNING(f"      ⚠  {err}"))

    # ── Sofascore CSV enrichment ───────────────────────────────────────────────

    def _sync_sofascore_csv_seasons(self, club: Club, club_config: dict, seasons: list[str]) -> None:
        """
        Back-fill PlayerSeasonEnrichment records from pre-processed Sofascore
        CSV files at data/processed/players/{season}/players_sofascore_{league}_{season}_canonical.csv

        Matching strategy per player row:
          1. PlayerExternalIdentity(provider=SOFASCORE, external_id=source_player_id)
          2. Name normalisation against ClubPlayer records for this club
          3. Skip if unresolvable.
        """
        competition_code = club_config["understat_competition_code"]
        sofascore_team_name = SOFASCORE_TEAM_NAMES.get(competition_code)
        if not sofascore_team_name:
            self.stdout.write(
                self.style.WARNING(
                    f"  No Sofascore team name mapping for competition={competition_code}, skipping."
                )
            )
            return

        total = len(seasons)
        self.stdout.write(
            f"  Back-filling Sofascore CSV data: {total} season(s), team='{sofascore_team_name}'"
        )

        csv_league = SOFASCORE_CSV_LEAGUE.get(competition_code, competition_code)

        for i, season_label in enumerate(seasons, start=1):
            csv_path = DATA_PLAYERS_DIR / season_label / f"players_sofascore_{csv_league}_{season_label}_canonical.csv"
            season_display = f"{season_label}/{int(season_label) + 1}"

            if not csv_path.exists():
                self.stdout.write(f"    [{i}/{total}] Season {season_display} — CSV not found, skipping")
                continue

            created, skipped = self._import_sofascore_season_csv(
                club=club,
                csv_path=csv_path,
                season_label=season_label,
                competition_code=competition_code,
                sofascore_team_name=sofascore_team_name,
            )
            self.stdout.write(
                f"    [{i}/{total}] Season {season_display} — "
                f"created={created}, skipped={skipped}"
            )

    def _import_sofascore_season_csv(
        self,
        *,
        club: Club,
        csv_path: Path,
        season_label: str,
        competition_code: str,
        sofascore_team_name: str,
    ) -> tuple[int, int]:
        created = 0
        skipped = 0

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("team", "").strip() != sofascore_team_name:
                    continue
                if row.get("source", "").strip() != "sofascore":
                    continue

                source_player_id = str(row.get("source_player_id") or "").strip()
                raw_name = str(row.get("name") or "").strip()
                if not raw_name:
                    skipped += 1
                    continue

                try:
                    with transaction.atomic():
                        player = self._resolve_sofascore_player(
                            club=club,
                            source_player_id=source_player_id,
                            raw_name=raw_name,
                        )
                        if player is None:
                            skipped += 1
                            continue

                        # Ensure Sofascore external identity exists.
                        if source_player_id:
                            PlayerExternalIdentity.objects.get_or_create(
                                provider=ExternalProvider.SOFASCORE,
                                external_id=source_player_id,
                                defaults={
                                    "player": player,
                                    "external_team_id": "",
                                    "provider_display_name": raw_name,
                                    "is_primary": False,
                                    "last_synced_at": timezone.now(),
                                },
                            )

                        _, was_created = PlayerSeasonEnrichment.objects.get_or_create(
                            player=player,
                            provider=ExternalProvider.SOFASCORE,
                            season_label=season_label,
                            competition_code=competition_code,
                            external_team_id=source_player_id or "",
                            defaults=self._build_sofascore_enrichment_defaults(club, row),
                        )
                        if was_created:
                            created += 1
                        else:
                            skipped += 1

                except Exception:
                    skipped += 1

        return created, skipped

    def _resolve_sofascore_player(
        self,
        *,
        club: Club,
        source_player_id: str,
        raw_name: str,
    ) -> Player | None:
        # 1. Already has a Sofascore identity.
        if source_player_id:
            identity = (
                PlayerExternalIdentity.objects
                .select_related("player")
                .filter(provider=ExternalProvider.SOFASCORE, external_id=source_player_id)
                .first()
            )
            if identity:
                return identity.player

        # 2. Name match against ClubPlayer records for this club.
        normalised = self._normalise_name(raw_name)
        if not normalised:
            return None

        for cp in ClubPlayer.objects.filter(club=club).select_related("player"):
            possible = {
                self._normalise_name(cp.display_name),
                self._normalise_name(f"{cp.first_name} {cp.last_name}"),
                self._normalise_name(cp.player.full_name if hasattr(cp.player, 'full_name') else ""),
                self._normalise_name(cp.player.display_name),
            }
            possible.discard("")
            if normalised in possible:
                return cp.player

        return None

    @staticmethod
    def _build_sofascore_enrichment_defaults(club: Club, row: dict) -> dict:
        def _int(key: str) -> int:
            try:
                v = row.get(key)
                return int(float(v)) if v not in (None, "", "nan") else 0
            except (ValueError, TypeError):
                return 0

        def _dec(key: str):
            try:
                v = row.get(key)
                if v in (None, "", "nan"):
                    return None
                return float(v)
            except (ValueError, TypeError):
                return None

        metadata: dict = {}
        for field in (
            "rating", "tackles_won", "tackles_attempted", "interceptions",
            "recoveries", "clearances", "blocked_shots", "aerial_duels_won",
            "aerial_duels_total", "ground_duels_won", "ground_duels_total",
            "duels_won", "duels_total", "was_fouled", "fouls_committed",
            "successful_dribbles", "accurate_passes", "total_passes",
            "accurate_crosses", "total_crosses",
        ):
            v = _dec(field)
            if v is not None:
                metadata[field] = v

        return {
            "club": club,
            "matches_played": _int("appearances") or _int("games"),
            "minutes_played": _int("minutes_played") or _int("minutes"),
            "goals": _int("goals"),
            "assists": _int("assists"),
            "shots": _int("shots"),
            "xg": _dec("xg"),
            "xa": _dec("xa"),
            "npg": _dec("npg"),
            "npxg": _dec("npxg"),
            "xg_chain": _dec("xg_chain"),
            "xg_buildup": _dec("xg_buildup"),
            "yellow_cards": _int("yellow_cards"),
            "red_cards": _int("red_cards"),
            "key_passes": _int("key_passes"),
            "last_synced_at": timezone.now(),
            "metadata": metadata,
        }

    def _ensure_historical_players(
        self,
        *,
        club: Club,
        raw_players: list[dict],
        season_label: str,
    ) -> tuple[int, int]:
        """
        For each player Understat returns for this team/season, ensure a
        canonical Player + PlayerExternalIdentity(understat) exists in the DB
        and that a ClubPlayer record links them to this club.

        This runs BEFORE sync_understat_club_players_season so the enrichment
        sync can always match by Understat player ID rather than relying on
        fragile name matching.

        Returns (pre_created, pre_linked):
          pre_created  — new Player + ClubPlayer records created from scratch
          pre_linked   — existing Players given a new understat identity/ClubPlayer link
        """
        pre_created = 0
        pre_linked = 0

        for raw in raw_players:
            external_player_id = str(raw.get("id") or "").strip()
            raw_name = (
                raw.get("player_name")
                or raw.get("player")
                or raw.get("name")
                or ""
            ).strip()

            if not external_player_id or not raw_name:
                continue

            try:
                with transaction.atomic():
                    # 1. Already has an Understat identity → ensure ClubPlayer link exists.
                    existing_identity = (
                        PlayerExternalIdentity.objects
                        .select_related("player")
                        .filter(provider=ExternalProvider.UNDERSTAT, external_id=external_player_id)
                        .first()
                    )

                    if existing_identity:
                        player = existing_identity.player
                        self._ensure_club_player_link(club, player, raw)
                        pre_linked += 1
                        continue

                    # 2. No Understat identity yet — try to find a canonical Player by name.
                    player = self._find_player_by_name(raw_name)

                    if player is None:
                        # 3. Nobody matched — create a new canonical Player from Understat data.
                        player = self._create_player_from_understat(raw)
                        pre_created += 1
                    else:
                        pre_linked += 1

                    # Attach Understat identity to the (new or found) Player.
                    PlayerExternalIdentity.objects.get_or_create(
                        provider=ExternalProvider.UNDERSTAT,
                        external_id=external_player_id,
                        defaults={
                            "player": player,
                            "external_team_id": "",
                            "provider_display_name": raw_name,
                            "is_primary": False,
                            "last_synced_at": timezone.now(),
                        },
                    )

                    self._ensure_club_player_link(club, player, raw)

            except Exception:
                # Non-fatal — log and move on so one bad player doesn't abort the season.
                pass

        return pre_created, pre_linked

    def _find_player_by_name(self, raw_name: str) -> Player | None:
        """
        Try to find an existing canonical Player whose full_name or display_name
        normalises to the same value as raw_name.
        """
        normalised_target = self._normalise_name(raw_name)
        if not normalised_target:
            return None

        # Search only among players whose normalised full_name starts with the
        # same first token — avoids a full-table scan.
        first_token = normalised_target.split()[0]

        candidates = Player.objects.filter(
            last_name__icontains=first_token.split()[-1] if first_token else ""
        ).select_related()[:200]

        for player in candidates:
            possible = {
                self._normalise_name(player.full_name),
                self._normalise_name(player.display_name),
            }
            possible.discard("")
            if normalised_target in possible:
                return player

        return None

    @transaction.atomic
    def _create_player_from_understat(self, raw: dict) -> Player:
        """Create a minimal canonical Player record from raw Understat data."""
        raw_name = (
            raw.get("player_name") or raw.get("player") or raw.get("name") or ""
        ).strip()

        parts = raw_name.split()
        first_name = parts[0] if parts else ""
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        return Player.objects.create(
            first_name=first_name,
            last_name=last_name,
            display_name=raw_name,
            is_active=False,  # Not a verified/active player record.
            is_verified=False,
        )

    def _ensure_club_player_link(self, club: Club, player: Player, raw: dict) -> None:
        """
        Make sure a ClubPlayer record exists linking this Player to this Club.
        Creates an inactive/historical record if one doesn't already exist.
        """
        if ClubPlayer.objects.filter(club=club, player=player).exists():
            return

        raw_name = (
            raw.get("player_name") or raw.get("player") or raw.get("name") or ""
        ).strip()
        parts = raw_name.split()

        ClubPlayer.objects.create(
            club=club,
            player=player,
            first_name=player.first_name or (parts[0] if parts else ""),
            last_name=player.last_name or (" ".join(parts[1:]) if len(parts) > 1 else ""),
            display_name=player.display_name or raw_name,
            is_active=False,
            is_public=True,
        )

    @staticmethod
    def _normalise_name(value: str | None) -> str:
        """Mirrors UnderstatSyncService._normalise_name for consistent matching."""
        if not value:
            return ""
        # Strip accents so "Martínez" == "Martinez" etc.
        nfkd = unicodedata.normalize("NFKD", value)
        ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
        return " ".join(ascii_str.strip().casefold().split())

    # ── helpers ────────────────────────────────────────────────────────────────

    def _get_or_create_system_user(self):
        user, created = User.objects.get_or_create(
            email="system@ifoot.app",
            defaults={
                "first_name": "iFoot",
                "last_name": "System",
                "is_staff": True,
                "is_active": True,
            },
        )
        if created:
            user.set_unusable_password()
            user.save()
            self.stdout.write(self.style.SUCCESS("Created system user: system@ifoot.app"))
        return user

    def _reset_clubs(self, system_user, clubs_to_seed):
        names = [c["name"] for c in clubs_to_seed]
        deleted_count, _ = Club.objects.filter(
            name__in=names,
            creator=system_user,
        ).delete()
        if deleted_count:
            self.stdout.write(
                self.style.WARNING(
                    f"--reset: deleted {deleted_count} existing seeded club record(s)."
                )
            )
        else:
            self.stdout.write("--reset: no existing seeded clubs found.")
