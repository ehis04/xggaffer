import re
import unicodedata
from datetime import date

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.clubs.models import ClubExternalIdentity, ClubPlayer
from apps.livefootball.models import (
    Competition,
    CompetitionFixture,
    CompetitionTableRow,
    CompetitionTableSnapshot,
    CompetitionTopScorer,
    PlayerDirectoryEntry,
    TeamDirectoryEntry,
)
from apps.livefootball.services.exceptions import TeamMappingNotFoundError
from apps.livefootball.services.team_bridge import (
    resolve_understat_team_name,
    resolve_understat_team_name_for_entry,
)
from apps.players.models import (
    Player,
    PlayerExternalIdentity,
    ProviderSyncJob,
    ProviderSyncStatus,
)

from .client import FootballDataClient
from .exceptions import FootballDataAuthenticationError
from .normalisers import (
    normalize_competition,
    normalize_competition_matches_payload,
    normalize_competition_scorers_payload,
    normalize_competition_table,
    normalize_competition_team,
    normalize_competition_teams_payload,
    normalize_competitions_payload,
    normalize_squad_player,
    normalize_team,
    normalize_team_directory_entry,
    normalize_team_players_payload,
)
from services.providers.understat.client import UnderstatClient


def _season_str(season) -> str:
    return str(season) if season is not None else ""


class FootballDataSyncService:
    def __init__(self, client=None):
        self.client = client or FootballDataClient()
        self._understat_client = None

    def link_club_to_provider_team(
        self,
        club,
        external_team_id,
        provider="football_data",
        provider_display_name="",
        triggered_by=None,
    ):
        job = self._start_sync_job(
            provider=provider,
            resource_type="team_link",
            resource_external_id=str(external_team_id),
            triggered_by=triggered_by,
            metadata={"club_id": club.id},
        )

        try:
            team_payload = self.client.get_team(external_team_id)
            team_data = normalize_team(team_payload)

            if provider_display_name:
                team_data["provider_display_name"] = provider_display_name

            identity, created, updated = self._upsert_club_external_identity(
                club=club,
                team_data=team_data,
                provider=provider,
            )

            summary = {
                "status": ProviderSyncStatus.SUCCESS,
                "records_processed": 1,
                "records_created": 1 if created else 0,
                "records_updated": 1 if updated else 0,
                "error_count": 0,
                "raw_error_summary": "",
                "metadata": {
                    "club_id": club.id,
                    "club_external_identity_id": identity.id,
                    "provider_team_id": team_data["external_id"],
                },
            }

            self._finish_sync_job_success(job, summary)

            return {
                "job": job,
                "club_external_identity": identity,
                "summary": summary,
            }
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    def sync_club_team_squad(
        self,
        club,
        external_team_id=None,
        provider="football_data",
        triggered_by=None,
    ):
        resolved_external_team_id = external_team_id or self._resolve_club_external_team_id(
            club=club,
            provider=provider,
        )

        job = self._start_sync_job(
            provider=provider,
            resource_type="team_squad",
            resource_external_id=str(resolved_external_team_id),
            triggered_by=triggered_by,
            metadata={"club_id": club.id},
        )

        try:
            team_payload = self.client.get_team(resolved_external_team_id)
            team_data = normalize_team(team_payload)

            club_identity, club_identity_created, club_identity_updated = (
                self._upsert_club_external_identity(
                    club=club,
                    team_data=team_data,
                    provider=provider,
                )
            )

            squad_payload = team_payload.get("squad") or []

            summary = {
                "status": ProviderSyncStatus.SUCCESS,
                "records_processed": 0,
                "records_created": 1 if club_identity_created else 0,
                "records_updated": 1 if club_identity_updated else 0,
                "error_count": 0,
                "raw_error_summary": "",
                "metadata": {
                    "club_id": club.id,
                    "club_external_identity_id": club_identity.id,
                    "provider_team_id": team_data["external_id"],
                    "players_created": 0,
                    "players_updated": 0,
                    "player_external_identities_created": 0,
                    "player_external_identities_updated": 0,
                    "club_players_created": 0,
                    "club_players_updated": 0,
                    "club_players_deactivated": 0,
                },
            }

            errors = []
            seen_player_ids: set[int] = set()

            for raw_player in squad_payload:
                summary["records_processed"] += 1

                try:
                    player_data = normalize_squad_player(
                        raw_player,
                        external_team_id=team_data["external_id"],
                    )

                    with transaction.atomic():
                        player, player_created, player_updated = (
                            self._resolve_or_create_player_from_provider(
                                player_data=player_data,
                                provider=provider,
                            )
                        )

                        _, identity_created, identity_updated = (
                            self._upsert_player_external_identity(
                                player=player,
                                player_data=player_data,
                                provider=provider,
                            )
                        )

                        _, club_player_created, club_player_updated = (
                            self._ensure_club_player_for_player(
                                club=club,
                                player=player,
                                player_data=player_data,
                                triggered_by=triggered_by,
                            )
                        )

                    seen_player_ids.add(player.id)

                    if player_created:
                        summary["records_created"] += 1
                        summary["metadata"]["players_created"] += 1
                    elif player_updated:
                        summary["records_updated"] += 1
                        summary["metadata"]["players_updated"] += 1

                    if identity_created:
                        summary["records_created"] += 1
                        summary["metadata"]["player_external_identities_created"] += 1
                    elif identity_updated:
                        summary["records_updated"] += 1
                        summary["metadata"]["player_external_identities_updated"] += 1

                    if club_player_created:
                        summary["records_created"] += 1
                        summary["metadata"]["club_players_created"] += 1
                    elif club_player_updated:
                        summary["records_updated"] += 1
                        summary["metadata"]["club_players_updated"] += 1

                except Exception as exc:
                    summary["error_count"] += 1
                    errors.append(self._format_player_error(raw_player, exc))

            # Deactivate ClubPlayer records for players no longer in the squad.
            # Only do this when the API returned a non-empty squad so a partial
            # response doesn't silently wipe the whole roster.
            if seen_player_ids:
                departed_count = ClubPlayer.objects.filter(
                    club=club,
                    is_active=True,
                    player__isnull=False,
                ).exclude(
                    player_id__in=seen_player_ids,
                ).update(
                    is_active=False,
                    updated_at=timezone.now(),
                )
                if departed_count:
                    summary["records_updated"] += departed_count
                    summary["metadata"]["club_players_deactivated"] += departed_count

            if errors:
                summary["status"] = ProviderSyncStatus.PARTIAL
                summary["raw_error_summary"] = "\n".join(errors)

            self._finish_sync_job_success(job, summary)

            return {
                "job": job,
                "club_external_identity": club_identity,
                "summary": summary,
            }
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    def sync_provider_team(
        self,
        team_external_id,
        provider="football_data",
        triggered_by=None,
    ):
        job = self._start_sync_job(
            provider=provider,
            resource_type="team",
            resource_external_id=str(team_external_id),
            triggered_by=triggered_by,
        )

        try:
            team_payload = self.client.get_team(team_external_id)
            team_data = normalize_team(team_payload)
            squad_payload = team_payload.get("squad") or []

            linked_identity = ClubExternalIdentity.objects.select_related("club").filter(
                provider=provider,
                external_id=str(team_data["external_id"]),
            ).first()

            summary = {
                "status": ProviderSyncStatus.SUCCESS,
                "records_processed": 0,
                "records_created": 0,
                "records_updated": 0,
                "error_count": 0,
                "raw_error_summary": "",
                "metadata": {
                    "provider_team_id": team_data["external_id"],
                    "mapped_club_id": linked_identity.club_id if linked_identity else None,
                    "players_created": 0,
                    "players_updated": 0,
                    "player_external_identities_created": 0,
                    "player_external_identities_updated": 0,
                    "club_players_created": 0,
                    "club_players_updated": 0,
                },
            }

            errors = []

            if linked_identity:
                _, _, club_identity_updated = self._upsert_club_external_identity(
                    club=linked_identity.club,
                    team_data=team_data,
                    provider=provider,
                )
                if club_identity_updated:
                    summary["records_updated"] += 1

            for raw_player in squad_payload:
                summary["records_processed"] += 1

                try:
                    player_data = normalize_squad_player(
                        raw_player,
                        external_team_id=team_data["external_id"],
                    )

                    with transaction.atomic():
                        player, player_created, player_updated = (
                            self._resolve_or_create_player_from_provider(
                                player_data=player_data,
                                provider=provider,
                            )
                        )

                        _, identity_created, identity_updated = (
                            self._upsert_player_external_identity(
                                player=player,
                                player_data=player_data,
                                provider=provider,
                            )
                        )

                        club_player_created = False
                        club_player_updated = False

                        if linked_identity:
                            _, club_player_created, club_player_updated = (
                                self._ensure_club_player_for_player(
                                    club=linked_identity.club,
                                    player=player,
                                    player_data=player_data,
                                    triggered_by=triggered_by,
                                )
                            )

                    if player_created:
                        summary["records_created"] += 1
                        summary["metadata"]["players_created"] += 1
                    elif player_updated:
                        summary["records_updated"] += 1
                        summary["metadata"]["players_updated"] += 1

                    if identity_created:
                        summary["records_created"] += 1
                        summary["metadata"]["player_external_identities_created"] += 1
                    elif identity_updated:
                        summary["records_updated"] += 1
                        summary["metadata"]["player_external_identities_updated"] += 1

                    if club_player_created:
                        summary["records_created"] += 1
                        summary["metadata"]["club_players_created"] += 1
                    elif club_player_updated:
                        summary["records_updated"] += 1
                        summary["metadata"]["club_players_updated"] += 1

                except Exception as exc:
                    summary["error_count"] += 1
                    errors.append(self._format_player_error(raw_player, exc))

            if errors:
                summary["status"] = ProviderSyncStatus.PARTIAL
                summary["raw_error_summary"] = "\n".join(errors)

            self._finish_sync_job_success(job, summary)

            return {
                "job": job,
                "summary": summary,
            }
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    def sync_competitions(
        self,
        areas=None,
        provider="football_data",
        triggered_by=None,
    ):
        job = self._start_sync_job(
            provider=provider,
            resource_type="competitions",
            resource_external_id="all",
            triggered_by=triggered_by,
            metadata={"areas": list(areas) if isinstance(areas, (list, tuple, set)) else areas},
        )

        try:
            payload = self.client.get_competitions(areas=areas)
            competitions_data = normalize_competitions_payload(payload)

            summary = {
                "status": ProviderSyncStatus.SUCCESS,
                "records_processed": 0,
                "records_created": 0,
                "records_updated": 0,
                "error_count": 0,
                "raw_error_summary": "",
                "metadata": {
                    "areas": list(areas) if isinstance(areas, (list, tuple, set)) else areas,
                    "competition_ids": [],
                },
            }

            errors = []

            for competition_data in competitions_data:
                summary["records_processed"] += 1

                try:
                    competition, created, updated = self._upsert_competition(
                        competition_data=competition_data,
                        provider=provider,
                    )

                    summary["metadata"]["competition_ids"].append(competition.id)

                    if created:
                        summary["records_created"] += 1
                    elif updated:
                        summary["records_updated"] += 1

                except Exception as exc:
                    summary["error_count"] += 1
                    errors.append(
                        f"competition:{competition_data.get('external_id', 'unknown')} {exc}"
                    )

            if errors:
                summary["status"] = ProviderSyncStatus.PARTIAL
                summary["raw_error_summary"] = "\n".join(errors)

            self._finish_sync_job_success(job, summary)

            return {
                "job": job,
                "summary": summary,
            }
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    def sync_competition_teams(
        self,
        competition_external_id,
        season=None,
        provider="football_data",
        triggered_by=None,
    ):
        job = self._start_sync_job(
            provider=provider,
            resource_type="competition_teams",
            resource_external_id=str(competition_external_id),
            triggered_by=triggered_by,
            metadata={"season": _season_str(season)},
        )

        try:
            competition = self._ensure_competition_record(
                competition_external_id=competition_external_id,
                provider=provider,
            )

            payload = self.client.get_competition_teams(competition_external_id, season=season)
            teams_payload = payload.get("teams") or []
            teams_data = normalize_competition_teams_payload(
                payload,
                competition_external_id=competition.external_id,
                season_label=_season_str(season),
            )

            summary = {
                "status": ProviderSyncStatus.SUCCESS,
                "records_processed": 0,
                "records_created": 0,
                "records_updated": 0,
                "error_count": 0,
                "raw_error_summary": "",
                "metadata": {
                    "competition_external_id": str(competition_external_id),
                    "competition_id": competition.id,
                    "season_label": teams_data[0]["season_label"] if teams_data else (_season_str(season) or competition.current_season_label),
                    "teams_created": 0,
                    "teams_updated": 0,
                    "matched_club_mappings_updated": 0,
                },
            }

            errors = []

            for index, team_data in enumerate(teams_data):
                summary["records_processed"] += 1

                try:
                    raw_team = teams_payload[index] if index < len(teams_payload) else {}

                    with transaction.atomic():
                        _, created, updated = self._upsert_team_directory_entry(
                            competition=competition,
                            team_data=team_data,
                            provider=provider,
                        )

                        mapping_updated = False

                        if raw_team:
                            provider_team_data = normalize_competition_team(raw_team)
                            identity = ClubExternalIdentity.objects.filter(
                                provider=provider,
                                external_id=str(provider_team_data["external_id"]),
                            ).first()

                            if identity:
                                _, _, mapping_updated = self._upsert_club_external_identity(
                                    club=identity.club,
                                    team_data=provider_team_data,
                                    provider=provider,
                                )

                    if created:
                        summary["records_created"] += 1
                        summary["metadata"]["teams_created"] += 1
                    elif updated:
                        summary["records_updated"] += 1
                        summary["metadata"]["teams_updated"] += 1

                    if mapping_updated:
                        summary["records_updated"] += 1
                        summary["metadata"]["matched_club_mappings_updated"] += 1

                except Exception as exc:
                    summary["error_count"] += 1
                    errors.append(
                        f"team:{team_data.get('external_id', 'unknown')} {exc}"
                    )

            if errors:
                summary["status"] = ProviderSyncStatus.PARTIAL
                summary["raw_error_summary"] = "\n".join(errors)

            self._finish_sync_job_success(job, summary)

            return {
                "job": job,
                "competition": competition,
                "summary": summary,
            }
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    def sync_team_squad_directory(
        self,
        competition_external_id,
        team_external_id,
        season=None,
        provider="football_data",
        triggered_by=None,
    ):
        job = self._start_sync_job(
            provider=provider,
            resource_type="team_directory",
            resource_external_id=str(team_external_id),
            triggered_by=triggered_by,
            metadata={
                "competition_external_id": str(competition_external_id),
                "season": _season_str(season),
            },
        )

        try:
            competition = self._ensure_competition_record(
                competition_external_id=competition_external_id,
                provider=provider,
            )

            season_label = _season_str(season) or competition.current_season_label or ""
            fallback_used = False

            try:
                team_payload = self.client.get_team(team_external_id)
                team_data = normalize_team_directory_entry(
                    team_payload,
                    competition_external_id=competition.external_id,
                    season_label=season_label,
                )

                team_entry, team_created, team_updated = self._upsert_team_directory_entry(
                    competition=competition,
                    team_data=team_data,
                    provider=provider,
                )

                # Reuse the already-fetched team payload to avoid a second API call per team.
                players_data = normalize_team_players_payload(
                    team_payload.get("squad") or [],
                    team_external_id=team_external_id,
                )
            except FootballDataAuthenticationError:
                fallback_used = True
                team_entry = TeamDirectoryEntry.objects.filter(
                    competition=competition,
                    season_label=season_label,
                    provider=provider,
                    external_id=str(team_external_id),
                ).first()
                if not team_entry:
                    raise

                players_data = self._build_understat_fallback_players_data(
                    team_entry=team_entry,
                    season_label=season_label,
                    provider=provider,
                )
                team_created = False
                team_updated = False

            summary = {
                "status": ProviderSyncStatus.SUCCESS,
                "records_processed": 0,
                "records_created": 1 if team_created else 0,
                "records_updated": 1 if team_updated else 0,
                "error_count": 0,
                "raw_error_summary": "",
                "metadata": {
                    "competition_external_id": str(competition_external_id),
                    "competition_id": competition.id,
                    "team_external_id": str(team_external_id),
                    "team_id": team_entry.id,
                    "season_label": team_entry.season_label,
                    "player_directory_created": 0,
                    "player_directory_updated": 0,
                    "players_marked_inactive": 0,
                    "fallback_used": fallback_used,
                    "fallback_provider": "understat" if fallback_used else "",
                },
            }

            errors = []
            seen_external_ids = set()

            for player_data in players_data:
                summary["records_processed"] += 1
                seen_external_ids.add(str(player_data.get("external_player_id") or ""))

                try:
                    canonical_player = self._resolve_or_create_canonical_player_for_directory_data(
                        player_data=player_data,
                        provider=provider,
                    )

                    _, created, updated = self._upsert_player_directory_entry(
                        team_entry=team_entry,
                        player_data=player_data,
                        canonical_player=canonical_player,
                        provider=provider,
                    )

                    if created:
                        summary["records_created"] += 1
                        summary["metadata"]["player_directory_created"] += 1
                    elif updated:
                        summary["records_updated"] += 1
                        summary["metadata"]["player_directory_updated"] += 1

                except Exception as exc:
                    summary["error_count"] += 1
                    errors.append(
                        f"player:{player_data.get('external_player_id', 'unknown')} {exc}"
                    )

            players_marked_inactive = self._deactivate_missing_team_players(
                team_entry=team_entry,
                active_external_ids=seen_external_ids,
            )

            if players_marked_inactive:
                summary["records_updated"] += players_marked_inactive
                summary["metadata"]["players_marked_inactive"] = players_marked_inactive

            if errors:
                summary["status"] = ProviderSyncStatus.PARTIAL
                summary["raw_error_summary"] = "\n".join(errors)

            self._finish_sync_job_success(job, summary)

            return {
                "job": job,
                "competition": competition,
                "team": team_entry,
                "summary": summary,
            }
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    def _build_understat_fallback_players_data(self, *, team_entry, season_label, provider):
        if not getattr(settings, "UNDERSTAT_ENABLED", True):
            raise FootballDataAuthenticationError(
                "Football-data authentication failed and Understat fallback is disabled."
            )

        understat_players = []
        understat_team_name = ""
        attempted_names = []

        for candidate in self._understat_team_name_candidates(team_entry):
            attempted_names.append(candidate)
            try:
                candidate_players = self._get_understat_client().get_team_players(
                    candidate,
                    season_label,
                )
            except Exception:
                continue

            if candidate_players:
                understat_team_name = candidate
                understat_players = candidate_players
                break

        if not understat_players:
            # TODO: Coverage still missing for Rotherham United FC (2023) and
            # Plymouth Argyle FC (2023, 2024). Add a dedicated fix later.
            raise FootballDataAuthenticationError(
                "Football-data authentication failed and Understat fallback could not fetch squad data "
                f"for '{team_entry.name}' ({season_label}). Tried: {', '.join(attempted_names)}"
            )

        normalized_players = []
        for index, raw_player in enumerate(understat_players):
            external_player_id = self._resolve_understat_player_external_id(raw_player, index)
            player_name = str(
                raw_player.get("player_name")
                or raw_player.get("player")
                or raw_player.get("name")
                or ""
            ).strip()
            if not player_name:
                player_name = f"Unknown Understat Player {index + 1}"

            normalized_players.append(
                {
                    "team_external_id": str(team_entry.external_id),
                    "provider": provider,
                    "external_player_id": external_player_id,
                    "player_name": player_name,
                    "first_name": "",
                    "last_name": "",
                    "date_of_birth": None,
                    "nationality": "",
                    "primary_position": "",
                    "raw_position": str(raw_player.get("position") or "").strip(),
                    "squad_number": None,
                    "is_active": True,
                    "metadata": {
                        "source": "understat_fallback",
                        "understat_team": understat_team_name,
                        "season_label": str(season_label),
                    },
                }
            )

        return normalized_players

    def _resolve_understat_player_external_id(self, raw_player, index):
        base_id = str(
            raw_player.get("id")
            or raw_player.get("player_id")
            or raw_player.get("playerId")
            or ""
        ).strip()
        if not base_id:
            base_id = f"missing-{index + 1}"
        return f"understat:{base_id}"

    def _understat_team_name_candidates(self, team_entry):
        candidates = []

        try:
            candidates.append(resolve_understat_team_name_for_entry(team_entry))
        except TeamMappingNotFoundError:
            pass

        source_values = [team_entry.name, team_entry.short_name, team_entry.tla]
        for value in source_values:
            if not value:
                continue
            for candidate in self._expanded_team_name_variants(value):
                try:
                    canonical = resolve_understat_team_name(candidate)
                    candidates.append(canonical)
                except TeamMappingNotFoundError:
                    candidates.append(candidate)

        deduped = []
        seen = set()
        for candidate in candidates:
            cleaned = str(candidate or "").strip()
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(cleaned)
        return deduped

    def _expanded_team_name_variants(self, raw_name):
        base = str(raw_name or "").strip()
        if not base:
            return []

        variants = [base]
        normalized = unicodedata.normalize("NFKD", base)
        ascii_name = "".join(ch for ch in normalized if not unicodedata.combining(ch)).strip()
        variants.append(ascii_name)

        no_prefix = re.sub(r"^(UD|CD|US|AC|AS|SV|VfL|1\.\s*FC)\s+", "", ascii_name, flags=re.IGNORECASE).strip()
        variants.append(no_prefix)
        no_suffix = re.sub(r"\b(FC|CF|AFC|HSC|Calcio)\b", "", no_prefix, flags=re.IGNORECASE)
        no_suffix = re.sub(r"\s+", " ", no_suffix).strip()
        variants.append(no_suffix)

        no_trailing_year = re.sub(r"\s+\d{2,4}$", "", no_suffix).strip()
        variants.append(no_trailing_year)

        for token in [" Town", " United", " Foot"]:
            if no_trailing_year.endswith(token):
                variants.append(no_trailing_year[: -len(token)].strip())

        return [item for item in variants if item]

    def _get_understat_client(self):
        if self._understat_client is None:
            self._understat_client = UnderstatClient()
        return self._understat_client

    def sync_competition_table(
        self,
        competition_external_id,
        season=None,
        snapshot_label="latest",
        provider="football_data",
        triggered_by=None,
    ):
        job = self._start_sync_job(
            provider=provider,
            resource_type="competition_table",
            resource_external_id=str(competition_external_id),
            triggered_by=triggered_by,
            metadata={
                "season": _season_str(season),
                "snapshot_label": snapshot_label,
            },
        )

        try:
            competition = self._ensure_competition_record(
                competition_external_id=competition_external_id,
                provider=provider,
            )

            payload = self.client.get_competition_table(competition_external_id, season=season)
            table_data = normalize_competition_table(
                payload,
                competition_external_id=competition.external_id,
                season_label=_season_str(season),
                snapshot_label=snapshot_label,
            )

            with transaction.atomic():
                snapshot, snapshot_created, snapshot_updated = self._upsert_competition_table_snapshot(
                    competition=competition,
                    table_data=table_data,
                )
                rows_replaced, previous_rows = self._replace_competition_table_rows(
                    snapshot=snapshot,
                    competition=competition,
                    rows_data=table_data.get("rows") or [],
                    provider=provider,
                )

            summary = {
                "status": ProviderSyncStatus.SUCCESS,
                "records_processed": rows_replaced,
                "records_created": (1 if snapshot_created else 0) + rows_replaced,
                "records_updated": (1 if snapshot_updated else 0) + (1 if previous_rows else 0),
                "error_count": 0,
                "raw_error_summary": "",
                "metadata": {
                    "competition_external_id": str(competition_external_id),
                    "competition_id": competition.id,
                    "snapshot_id": snapshot.id,
                    "season_label": snapshot.season_label,
                    "snapshot_label": snapshot.snapshot_label,
                    "matchday": snapshot.matchday,
                    "rows_replaced": rows_replaced,
                    "previous_rows_deleted": previous_rows,
                },
            }

            self._finish_sync_job_success(job, summary)

            return {
                "job": job,
                "competition": competition,
                "snapshot": snapshot,
                "summary": summary,
            }
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    def sync_competition_fixtures(
        self,
        competition_external_id,
        season=None,
        matchday=None,
        status=None,
        date_from=None,
        date_to=None,
        stage=None,
        group=None,
        provider="football_data",
        triggered_by=None,
    ):
        job = self._start_sync_job(
            provider=provider,
            resource_type="competition_fixtures",
            resource_external_id=str(competition_external_id),
            triggered_by=triggered_by,
            metadata={
                "season": _season_str(season),
                "matchday": matchday,
                "status": status or "",
                "date_from": date_from or "",
                "date_to": date_to or "",
                "stage": stage or "",
                "group": group or "",
            },
        )

        try:
            competition = self._ensure_competition_record(
                competition_external_id=competition_external_id,
                provider=provider,
            )

            payload = self.client.get_competition_matches(
                competition_external_id,
                season=season,
                matchday=matchday,
                status=status,
                date_from=date_from,
                date_to=date_to,
                stage=stage,
                group=group,
            )
            fixtures_data = normalize_competition_matches_payload(
                payload,
                competition_external_id=competition.external_id,
                season_label=_season_str(season),
            )

            summary = {
                "status": ProviderSyncStatus.SUCCESS,
                "records_processed": 0,
                "records_created": 0,
                "records_updated": 0,
                "error_count": 0,
                "raw_error_summary": "",
                "metadata": {
                    "competition_external_id": str(competition_external_id),
                    "competition_id": competition.id,
                    "season_label": fixtures_data[0]["season_label"] if fixtures_data else (_season_str(season) or competition.current_season_label),
                },
            }

            errors = []

            for fixture_data in fixtures_data:
                summary["records_processed"] += 1

                try:
                    _, created, updated = self._upsert_competition_fixture(
                        competition=competition,
                        fixture_data=fixture_data,
                        provider=provider,
                    )

                    if created:
                        summary["records_created"] += 1
                    elif updated:
                        summary["records_updated"] += 1

                except Exception as exc:
                    summary["error_count"] += 1
                    errors.append(
                        f"fixture:{fixture_data.get('external_match_id', 'unknown')} {exc}"
                    )

            if errors:
                summary["status"] = ProviderSyncStatus.PARTIAL
                summary["raw_error_summary"] = "\n".join(errors)

            self._finish_sync_job_success(job, summary)

            return {
                "job": job,
                "competition": competition,
                "summary": summary,
            }
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    def sync_competition_scorers(
        self,
        competition_external_id,
        season=None,
        matchday=None,
        provider="football_data",
        triggered_by=None,
    ):
        job = self._start_sync_job(
            provider=provider,
            resource_type="competition_scorers",
            resource_external_id=str(competition_external_id),
            triggered_by=triggered_by,
            metadata={
                "season": _season_str(season),
                "matchday": matchday,
            },
        )

        try:
            competition = self._ensure_competition_record(
                competition_external_id=competition_external_id,
                provider=provider,
            )

            payload = self.client.get_competition_scorers(
                competition_external_id,
                season=season,
                matchday=matchday,
            )
            scorers_data = normalize_competition_scorers_payload(
                payload,
                competition_external_id=competition.external_id,
                season_label=_season_str(season),
            )
            resolved_season_label = (
                scorers_data[0]["season_label"]
                if scorers_data
                else (_season_str(season) or competition.current_season_label or "")
            )

            with transaction.atomic():
                scorers_created, scorers_deleted = self._replace_competition_scorers(
                    competition=competition,
                    season_label=resolved_season_label,
                    scorers_data=scorers_data,
                    provider=provider,
                )

            summary = {
                "status": ProviderSyncStatus.SUCCESS,
                "records_processed": scorers_created,
                "records_created": scorers_created,
                "records_updated": 1 if scorers_deleted else 0,
                "error_count": 0,
                "raw_error_summary": "",
                "metadata": {
                    "competition_external_id": str(competition_external_id),
                    "competition_id": competition.id,
                    "season_label": resolved_season_label,
                    "scorers_recreated": scorers_created,
                    "previous_scorers_deleted": scorers_deleted,
                },
            }

            self._finish_sync_job_success(job, summary)

            return {
                "job": job,
                "competition": competition,
                "summary": summary,
            }
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    def _start_sync_job(
        self,
        provider,
        resource_type,
        resource_external_id,
        triggered_by=None,
        metadata=None,
    ):
        return ProviderSyncJob.objects.create(
            provider=provider,
            resource_type=resource_type,
            resource_external_id=str(resource_external_id or ""),
            status=ProviderSyncStatus.STARTED,
            triggered_by=triggered_by,
            metadata=metadata or {},
        )

    def _finish_sync_job_success(self, job, summary):
        job.status = summary.get("status", ProviderSyncStatus.SUCCESS)
        job.finished_at = timezone.now()
        job.records_processed = summary.get("records_processed", 0)
        job.records_created = summary.get("records_created", 0)
        job.records_updated = summary.get("records_updated", 0)
        job.error_count = summary.get("error_count", 0)
        job.raw_error_summary = summary.get("raw_error_summary", "")
        job.metadata = summary.get("metadata", {})
        job.save(
            update_fields=[
                "status",
                "finished_at",
                "records_processed",
                "records_created",
                "records_updated",
                "error_count",
                "raw_error_summary",
                "metadata",
            ]
        )

    def _finish_sync_job_failure(self, job, exc):
        job.status = ProviderSyncStatus.FAILED
        job.finished_at = timezone.now()
        job.error_count = max(job.error_count, 1)
        job.raw_error_summary = str(exc)
        job.save(
            update_fields=[
                "status",
                "finished_at",
                "error_count",
                "raw_error_summary",
            ]
        )

    def _resolve_club_external_team_id(self, club, provider):
        identity = ClubExternalIdentity.objects.filter(
            club=club,
            provider=provider,
            is_primary=True,
        ).first()

        if not identity:
            identity = ClubExternalIdentity.objects.filter(
                club=club,
                provider=provider,
            ).first()

        if not identity:
            raise ValueError(f"Club {club.id} has no {provider} team mapping.")

        return identity.external_id

    def _ensure_competition_record(self, competition_external_id, provider):
        competition = Competition.objects.filter(
            provider=provider,
            external_id=str(competition_external_id),
        ).first()

        if competition:
            return competition

        payload = self.client.get_competition(competition_external_id)
        competition_data = normalize_competition(payload)
        competition, _, _ = self._upsert_competition(
            competition_data=competition_data,
            provider=provider,
        )
        return competition

    def _upsert_competition(self, competition_data, provider):
        external_id = str(competition_data["external_id"])
        now = timezone.now()

        competition = Competition.objects.filter(
            provider=provider,
            external_id=external_id,
        ).first()

        created = False
        updated = False

        if not competition:
            competition = Competition(
                provider=provider,
                external_id=external_id,
            )
            created = True

        changed_fields = []

        values = {
            "code": competition_data.get("code", ""),
            "name": competition_data.get("name", ""),
            "area_name": competition_data.get("area_name", ""),
            "emblem_url": competition_data.get("emblem_url", ""),
            "current_season_label": competition_data.get("current_season_label", ""),
            "current_season_start_date": competition_data.get("current_season_start_date"),
            "current_season_end_date": competition_data.get("current_season_end_date"),
            "current_matchday": competition_data.get("current_matchday"),
            "last_synced_at": now,
            "metadata": competition_data.get("metadata", {}) or {},
        }

        for field_name, value in values.items():
            if getattr(competition, field_name) != value:
                setattr(competition, field_name, value)
                changed_fields.append(field_name)

        if created:
            competition.save()
            return competition, True, False

        if changed_fields:
            competition.save(update_fields=changed_fields)
            updated = True

        return competition, False, updated

    def _upsert_club_external_identity(self, club, team_data, provider):
        external_id = str(team_data["external_id"])
        now = timezone.now()

        identity = ClubExternalIdentity.objects.filter(
            provider=provider,
            external_id=external_id,
        ).first()

        created = False
        updated = False

        if identity and identity.club_id != club.id:
            raise ValueError(
                f"{provider} team {external_id} is already linked to club {identity.club_id}."
            )

        if not identity:
            identity = ClubExternalIdentity(
                club=club,
                provider=provider,
                external_id=external_id,
            )
            created = True

        changed_fields = []

        values = {
            "provider_display_name": team_data.get("provider_display_name", ""),
            "country": team_data.get("country", ""),
            "competition_context": team_data.get("competition_context", ""),
            "is_primary": True,
            "metadata": team_data.get("metadata", {}) or {},
            "last_synced_at": now,
        }

        for field_name, value in values.items():
            if getattr(identity, field_name) != value:
                setattr(identity, field_name, value)
                changed_fields.append(field_name)

        if created:
            identity.save()
            ClubExternalIdentity.objects.filter(
                club=club,
                provider=provider,
                is_primary=True,
            ).exclude(pk=identity.pk).update(is_primary=False)
            return identity, True, False

        if changed_fields:
            identity.save(update_fields=changed_fields)
            updated = True

        ClubExternalIdentity.objects.filter(
            club=club,
            provider=provider,
            is_primary=True,
        ).exclude(pk=identity.pk).update(is_primary=False)

        return identity, False, updated

    def _resolve_or_create_player_from_provider(self, player_data, provider):
        external_identity = PlayerExternalIdentity.objects.select_related("player").filter(
            provider=provider,
            external_id=str(player_data["external_id"]),
        ).first()

        if external_identity:
            player = external_identity.player
            updated = self._apply_player_updates(player, player_data)
            return player, False, updated

        matched_player = self._find_existing_player_match(player_data)

        if matched_player:
            updated = self._apply_player_updates(matched_player, player_data)
            return matched_player, False, updated

        create_values = self._build_player_create_values(player_data)
        player = Player.objects.create(**create_values)
        return player, True, False

    def _find_existing_player_match(self, player_data):
        first_name = player_data.get("first_name", "").strip()
        last_name = player_data.get("last_name", "").strip()
        date_of_birth = player_data.get("date_of_birth")

        if not first_name or not last_name or not date_of_birth:
            return None

        return Player.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            date_of_birth=date_of_birth,
        ).first()

    def _build_player_create_values(self, player_data):
        first_name, last_name = self._resolved_player_names(player_data)

        values = {
            "first_name": first_name,
            "last_name": last_name,
            "display_name": player_data.get("display_name", "")[:50],
            "date_of_birth": player_data.get("date_of_birth"),
            "nationality": player_data.get("nationality", ""),
            "primary_position": player_data.get("primary_position", ""),
            "is_active": True,
        }

        model_fields = self._model_field_names(Player)

        return {
            key: value
            for key, value in values.items()
            if key in model_fields and value is not None
        }

    def _apply_player_updates(self, player, player_data):
        model_fields = self._model_field_names(Player)
        changed_fields = []

        first_name, last_name = self._resolved_player_names(player_data)

        candidate_values = {
            "display_name": player_data.get("display_name", "")[:50],
            "date_of_birth": player_data.get("date_of_birth"),
            "nationality": player_data.get("nationality", ""),
            "primary_position": player_data.get("primary_position", ""),
        }

        if not getattr(player, "first_name", "") and first_name:
            candidate_values["first_name"] = first_name

        if not getattr(player, "last_name", "") and last_name:
            candidate_values["last_name"] = last_name

        for field_name, value in candidate_values.items():
            if field_name not in model_fields:
                continue
            if value in (None, ""):
                continue
            if getattr(player, field_name) != value:
                setattr(player, field_name, value)
                changed_fields.append(field_name)

        if changed_fields:
            player.save(update_fields=changed_fields)
            return True

        return False

    def _upsert_player_external_identity(self, player, player_data, provider):
        external_id = str(player_data["external_id"])
        now = timezone.now()

        identity = PlayerExternalIdentity.objects.filter(
            provider=provider,
            external_id=external_id,
        ).first()

        created = False
        updated = False

        if identity and identity.player_id != player.id:
            raise ValueError(
                f"{provider} player {external_id} is already linked to player {identity.player_id}."
            )

        if not identity:
            identity = PlayerExternalIdentity(
                player=player,
                provider=provider,
                external_id=external_id,
            )
            created = True

        changed_fields = []

        values = {
            "provider_display_name": player_data.get("display_name", ""),
            "provider_position": player_data.get("raw_provider_position", ""),
            "external_team_id": str(player_data.get("external_team_id", "") or ""),
            "is_primary": True,
            "last_synced_at": now,
            "metadata": player_data.get("metadata", {}) or {},
        }

        for field_name, value in values.items():
            if getattr(identity, field_name) != value:
                setattr(identity, field_name, value)
                changed_fields.append(field_name)

        if created:
            identity.save()
            PlayerExternalIdentity.objects.filter(
                player=player,
                provider=provider,
                is_primary=True,
            ).exclude(pk=identity.pk).update(is_primary=False)
            return identity, True, False

        if changed_fields:
            identity.save(update_fields=changed_fields)
            updated = True

        PlayerExternalIdentity.objects.filter(
            player=player,
            provider=provider,
            is_primary=True,
        ).exclude(pk=identity.pk).update(is_primary=False)

        return identity, False, updated

    def _ensure_club_player_for_player(
        self,
        club,
        player,
        player_data,
        triggered_by=None,
    ):
        model_fields = self._model_field_names(ClubPlayer)

        if "player" not in model_fields:
            raise ValueError("ClubPlayer.player is required for provider sync.")

        club_player = ClubPlayer.objects.filter(
            club=club,
            player=player,
        ).order_by("id").first()

        created = False
        updated = False

        if not club_player:
            club_player = ClubPlayer(
                club=club,
                player=player,
            )
            created = True

        first_name, last_name = self._resolved_player_names(player_data)

        candidate_values = {
            "first_name": first_name,
            "last_name": last_name,
            "display_name": player_data.get("display_name", "")[:50],
            "primary_position": player_data.get("primary_position", "") or getattr(player, "primary_position", ""),
            "date_of_birth": getattr(player, "date_of_birth", None),
            "height_cm": getattr(player, "height_cm", None),
            "squad_number": player_data.get("squad_number"),
            "is_active": True,
        }

        changed_fields = []

        for field_name, value in candidate_values.items():
            if field_name not in model_fields:
                continue
            if value is None:
                continue
            if getattr(club_player, field_name, None) != value:
                setattr(club_player, field_name, value)
                changed_fields.append(field_name)

        if created and "created_by" in model_fields and getattr(club_player, "created_by_id", None) is None:
            created_by = triggered_by or getattr(club, "creator", None)
            if created_by is not None:
                club_player.created_by = created_by
                changed_fields.append("created_by")

        if created:
            club_player.save()
            return club_player, True, False

        if changed_fields:
            club_player.save(update_fields=changed_fields)
            updated = True

        return club_player, False, updated

    def _upsert_team_directory_entry(self, competition, team_data, provider):
        external_id = str(team_data["external_id"])
        season_label = str(team_data.get("season_label") or competition.current_season_label or "")
        now = timezone.now()

        team_entry = TeamDirectoryEntry.objects.filter(
            competition=competition,
            season_label=season_label,
            provider=provider,
            external_id=external_id,
        ).first()

        created = False
        updated = False

        if not team_entry:
            team_entry = TeamDirectoryEntry(
                competition=competition,
                season_label=season_label,
                provider=provider,
                external_id=external_id,
            )
            created = True

        changed_fields = []

        values = {
            "name": team_data.get("name", ""),
            "short_name": team_data.get("short_name", ""),
            "tla": team_data.get("tla", ""),
            "area_name": team_data.get("area_name", ""),
            "emblem_url": team_data.get("emblem_url", ""),
            "venue": team_data.get("venue", ""),
            "website": team_data.get("website", ""),
            "founded_year": team_data.get("founded_year"),
            "last_synced_at": now,
            "metadata": team_data.get("metadata", {}) or {},
        }

        for field_name, value in values.items():
            if getattr(team_entry, field_name) != value:
                setattr(team_entry, field_name, value)
                changed_fields.append(field_name)

        if created:
            team_entry.save()
            return team_entry, True, False

        if changed_fields:
            team_entry.save(update_fields=changed_fields)
            updated = True

        return team_entry, False, updated

    def _upsert_player_directory_entry(
        self,
        team_entry,
        player_data,
        canonical_player,
        provider,
    ):
        external_player_id = str(player_data["external_player_id"])
        now = timezone.now()

        entry = PlayerDirectoryEntry.objects.filter(
            team=team_entry,
            provider=provider,
            external_player_id=external_player_id,
        ).first()

        created = False
        updated = False

        if not entry:
            entry = PlayerDirectoryEntry(
                team=team_entry,
                provider=provider,
                external_player_id=external_player_id,
            )
            created = True

        changed_fields = []

        values = {
            "canonical_player": canonical_player,
            "player_name": player_data.get("player_name", ""),
            "first_name": player_data.get("first_name", ""),
            "last_name": player_data.get("last_name", ""),
            "date_of_birth": player_data.get("date_of_birth"),
            "nationality": player_data.get("nationality", ""),
            "primary_position": player_data.get("primary_position", ""),
            "raw_position": player_data.get("raw_position", ""),
            "squad_number": player_data.get("squad_number"),
            "is_active": player_data.get("is_active", True),
            "last_synced_at": now,
            "metadata": player_data.get("metadata", {}) or {},
        }

        for field_name, value in values.items():
            if getattr(entry, field_name) != value:
                setattr(entry, field_name, value)
                changed_fields.append(field_name)

        if created:
            entry.save()
            return entry, True, False

        if changed_fields:
            entry.save(update_fields=changed_fields)
            updated = True

        return entry, False, updated

    def _deactivate_missing_team_players(self, team_entry, active_external_ids):
        if not active_external_ids:
            return 0

        return PlayerDirectoryEntry.objects.filter(
            team=team_entry,
            is_active=True,
        ).exclude(
            external_player_id__in=list(active_external_ids),
        ).update(
            is_active=False,
            updated_at=timezone.now(),
        )

    def _upsert_competition_table_snapshot(self, competition, table_data):
        season_label = str(table_data.get("season_label") or competition.current_season_label or "")
        snapshot_label = str(table_data.get("snapshot_label") or "latest")
        now = timezone.now()

        snapshot = CompetitionTableSnapshot.objects.filter(
            competition=competition,
            season_label=season_label,
            snapshot_label=snapshot_label,
        ).first()

        created = False
        updated = False

        if not snapshot:
            snapshot = CompetitionTableSnapshot(
                competition=competition,
                season_label=season_label,
                snapshot_label=snapshot_label,
            )
            created = True

        changed_fields = []

        values = {
            "matchday": table_data.get("matchday"),
            "fetched_at": table_data.get("fetched_at"),
            "synced_at": now,
            "metadata": table_data.get("metadata", {}) or {},
        }

        for field_name, value in values.items():
            if getattr(snapshot, field_name) != value:
                setattr(snapshot, field_name, value)
                changed_fields.append(field_name)

        if created:
            snapshot.save()
            return snapshot, True, False

        if changed_fields:
            snapshot.save(update_fields=changed_fields)
            updated = True

        return snapshot, False, updated

    def _replace_competition_table_rows(
        self,
        snapshot,
        competition,
        rows_data,
        provider,
    ):
        previous_rows = snapshot.rows.count()
        snapshot.rows.all().delete()

        created_count = 0

        for row_data in rows_data:
            external_team_id = str(row_data.get("external_team_id") or "")
            team_entry = self._find_team_directory_entry(
                competition=competition,
                season_label=snapshot.season_label,
                provider=provider,
                external_team_id=external_team_id,
            )

            CompetitionTableRow.objects.create(
                snapshot=snapshot,
                team=team_entry,
                position=row_data.get("position") or 0,
                external_team_id=external_team_id,
                team_name=row_data.get("team_name", ""),
                played=row_data.get("played") or 0,
                won=row_data.get("won") or 0,
                drawn=row_data.get("drawn") or 0,
                lost=row_data.get("lost") or 0,
                goals_for=row_data.get("goals_for") or 0,
                goals_against=row_data.get("goals_against") or 0,
                goal_difference=row_data.get("goal_difference") or 0,
                points=row_data.get("points") or 0,
                form=row_data.get("form", ""),
                metadata=row_data.get("metadata", {}) or {},
            )
            created_count += 1

        return created_count, previous_rows

    def _upsert_competition_fixture(self, competition, fixture_data, provider):
        external_match_id = str(fixture_data["external_match_id"])
        season_label = str(fixture_data.get("season_label") or competition.current_season_label or "")
        now = timezone.now()

        fixture = CompetitionFixture.objects.filter(
            competition=competition,
            season_label=season_label,
            external_match_id=external_match_id,
        ).first()

        created = False
        updated = False

        if not fixture:
            fixture = CompetitionFixture(
                competition=competition,
                season_label=season_label,
                external_match_id=external_match_id,
            )
            created = True

        home_external_team_id = str(fixture_data.get("home_external_team_id") or "")
        away_external_team_id = str(fixture_data.get("away_external_team_id") or "")

        home_team = self._find_team_directory_entry(
            competition=competition,
            season_label=season_label,
            provider=provider,
            external_team_id=home_external_team_id,
        )
        away_team = self._find_team_directory_entry(
            competition=competition,
            season_label=season_label,
            provider=provider,
            external_team_id=away_external_team_id,
        )

        changed_fields = []

        values = {
            "status": fixture_data.get("status", ""),
            "kickoff_at": fixture_data.get("kickoff_at"),
            "matchday": fixture_data.get("matchday"),
            "home_team": home_team,
            "away_team": away_team,
            "home_external_team_id": home_external_team_id,
            "home_team_name": fixture_data.get("home_team_name", ""),
            "away_external_team_id": away_external_team_id,
            "away_team_name": fixture_data.get("away_team_name", ""),
            "home_score": fixture_data.get("home_score"),
            "away_score": fixture_data.get("away_score"),
            "synced_at": now,
            "metadata": fixture_data.get("metadata", {}) or {},
        }

        for field_name, value in values.items():
            if getattr(fixture, field_name) != value:
                setattr(fixture, field_name, value)
                changed_fields.append(field_name)

        if created:
            fixture.save()
            return fixture, True, False

        if changed_fields:
            fixture.save(update_fields=changed_fields)
            updated = True

        return fixture, False, updated

    def _replace_competition_scorers(
        self,
        competition,
        season_label,
        scorers_data,
        provider,
    ):
        existing = CompetitionTopScorer.objects.filter(
            competition=competition,
            season_label=season_label,
        )
        deleted_count = existing.count()
        existing.delete()

        created_count = 0

        for scorer_data in scorers_data:
            external_team_id = str(scorer_data.get("external_team_id") or "")
            external_player_id = str(scorer_data.get("external_player_id") or "")

            team_entry = self._find_team_directory_entry(
                competition=competition,
                season_label=season_label,
                provider=provider,
                external_team_id=external_team_id,
            )
            canonical_player = self._resolve_canonical_player_by_external_id(
                provider=provider,
                external_player_id=external_player_id,
                fallback_data=scorer_data,
            )

            CompetitionTopScorer.objects.create(
                competition=competition,
                season_label=season_label,
                canonical_player=canonical_player,
                team=team_entry,
                rank=scorer_data.get("rank") or 0,
                external_player_id=external_player_id,
                player_name=scorer_data.get("player_name", ""),
                team_name=scorer_data.get("team_name", ""),
                external_team_id=external_team_id,
                goals=scorer_data.get("goals") or 0,
                penalties=scorer_data.get("penalties"),
                synced_at=timezone.now(),
                metadata=scorer_data.get("metadata", {}) or {},
            )
            created_count += 1

        return created_count, deleted_count

    def _find_team_directory_entry(
        self,
        competition,
        season_label,
        provider,
        external_team_id,
    ):
        if not external_team_id:
            return None

        return TeamDirectoryEntry.objects.filter(
            competition=competition,
            season_label=season_label,
            provider=provider,
            external_id=str(external_team_id),
        ).first()

    def _resolve_canonical_player_for_directory_data(self, player_data, provider):
        external_player_id = str(player_data.get("external_player_id") or "")
        if external_player_id:
            player = self._resolve_canonical_player_by_external_id(
                provider=provider,
                external_player_id=external_player_id,
                fallback_data=player_data,
            )
            if player:
                return player

        match_data = {
            "first_name": player_data.get("first_name", ""),
            "last_name": player_data.get("last_name", ""),
            "date_of_birth": player_data.get("date_of_birth"),
        }
        return self._find_existing_player_match(match_data)

    def _resolve_or_create_canonical_player_for_directory_data(self, player_data, provider):
        player = self._resolve_canonical_player_for_directory_data(
            player_data=player_data,
            provider=provider,
        )

        if player is None:
            create_data = {
                "first_name": player_data.get("first_name", ""),
                "last_name": player_data.get("last_name", ""),
                "display_name": player_data.get("player_name", ""),
                "date_of_birth": player_data.get("date_of_birth"),
                "nationality": "",
                "primary_position": "",
            }
            create_values = self._build_player_create_values(create_data)
            player = Player.objects.create(**create_values)

        self._ensure_player_external_identity_for_directory_player(
            player=player,
            player_data=player_data,
            provider=provider,
        )

        return player

    def _ensure_player_external_identity_for_directory_player(self, player, player_data, provider):
        external_player_id = str(player_data.get("external_player_id") or "").strip()
        if not external_player_id:
            return

        payload = {
            "external_id": external_player_id,
            "display_name": str(player_data.get("player_name") or "").strip(),
            "raw_provider_position": str(player_data.get("raw_position") or "").strip(),
            "external_team_id": str(player_data.get("team_external_id") or "").strip(),
            "metadata": {
                "source": "livefootball_directory",
                "season_label": str(
                    player_data.get("season_label")
                    or player_data.get("metadata", {}).get("season_label")
                    or ""
                ).strip(),
            },
        }

        self._upsert_player_external_identity(
            player=player,
            player_data=payload,
            provider=provider,
        )

    def _resolve_canonical_player_by_external_id(
        self,
        provider,
        external_player_id,
        fallback_data=None,
    ):
        if not external_player_id:
            return None

        identity = PlayerExternalIdentity.objects.select_related("player").filter(
            provider=provider,
            external_id=str(external_player_id),
        ).first()

        if identity:
            return identity.player

        if not fallback_data:
            return None

        first_name = str(
            fallback_data.get("first_name")
            or fallback_data.get("metadata", {}).get("player_first_name")
            or ""
        ).strip()
        last_name = str(
            fallback_data.get("last_name")
            or fallback_data.get("metadata", {}).get("player_last_name")
            or ""
        ).strip()
        date_of_birth = fallback_data.get("date_of_birth")

        if not date_of_birth:
            dob_text = str(
                fallback_data.get("metadata", {}).get("player_date_of_birth") or ""
            ).strip()
            if dob_text:
                try:
                    date_of_birth = date.fromisoformat(dob_text[:10])
                except ValueError:
                    date_of_birth = None

        if first_name and last_name and date_of_birth:
            return Player.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name,
                date_of_birth=date_of_birth,
            ).first()

        return None

    def _resolved_player_names(self, player_data):
        first_name = (player_data.get("first_name") or "").strip()
        last_name = (player_data.get("last_name") or "").strip()
        display_name = (player_data.get("display_name") or "").strip()
        full_name = (player_data.get("full_name") or "").strip()

        if first_name or last_name:
            return first_name, last_name

        source_name = full_name or display_name

        if not source_name:
            return "Unknown", ""

        parts = source_name.split()

        if len(parts) == 1:
            return parts[0][:50], ""

        return parts[0][:50], " ".join(parts[1:])[:50]

    def _format_player_error(self, raw_player, exc):
        raw_id = raw_player.get("id", "unknown")
        raw_name = raw_player.get("name") or raw_player.get("fullName") or "unknown"
        return f"player:{raw_id}:{raw_name} {exc}"

    def _model_field_names(self, model_class):
        return {
            field.name
            for field in model_class._meta.get_fields()
            if getattr(field, "concrete", False)
        }


def link_club_to_provider_team(*args, **kwargs):
    return FootballDataSyncService().link_club_to_provider_team(*args, **kwargs)


def sync_club_team_squad(*args, **kwargs):
    return FootballDataSyncService().sync_club_team_squad(*args, **kwargs)


def sync_provider_team(*args, **kwargs):
    return FootballDataSyncService().sync_provider_team(*args, **kwargs)


def sync_competitions(*args, **kwargs):
    return FootballDataSyncService().sync_competitions(*args, **kwargs)


def sync_competition_teams(*args, **kwargs):
    return FootballDataSyncService().sync_competition_teams(*args, **kwargs)


def sync_team_squad_directory(*args, **kwargs):
    return FootballDataSyncService().sync_team_squad_directory(*args, **kwargs)


def sync_competition_table(*args, **kwargs):
    return FootballDataSyncService().sync_competition_table(*args, **kwargs)


def sync_competition_fixtures(*args, **kwargs):
    return FootballDataSyncService().sync_competition_fixtures(*args, **kwargs)


def sync_competition_scorers(*args, **kwargs):
    return FootballDataSyncService().sync_competition_scorers(*args, **kwargs)