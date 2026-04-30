"""
Sync service for football-data provider records

Fetches football-data API content and syncs it to  the application's club, player, competition, fixture, table, and scorer models
"""

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
from apps.players.models import ProviderSyncJob, ProviderSyncStatus

from common.utils import upsert_record

from ._player_ops import (
    ensure_club_player_for_player,
    format_player_error,
    resolve_canonical_player_by_external_id,
    resolve_or_create_canonical_player_for_directory_data,
    resolve_or_create_player_from_provider,
    upsert_player_external_identity,
)
from ._understat_fallback import build_understat_fallback_players_data
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


# Service for syncing football-data provider content into local models
class FootballDataSyncService:
    def __init__(self, client=None):
        self.client = client or FootballDataClient()
        self._understat_client = None

    # ------------------------------------------------------------------
    # Public sync methods
    # ------------------------------------------------------------------

    # Link a club to a provider team identity
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
                club=club, team_data=team_data, provider=provider,
            )

            summary = self._make_summary({
                "club_id": club.id,
                "club_external_identity_id": identity.id,
                "provider_team_id": team_data["external_id"],
            })
            summary["records_processed"] = 1
            summary["records_created"] = 1 if created else 0
            summary["records_updated"] = 1 if updated else 0

            self._finish_sync_job_success(job, summary)
            return {"job": job, "club_external_identity": identity, "summary": summary}
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    # Sync the squad for a club using its mapped provider team
    def sync_club_team_squad(
        self,
        club,
        external_team_id=None,
        provider="football_data",
        triggered_by=None,
    ):
        resolved_external_team_id = external_team_id or self._resolve_club_external_team_id(
            club=club, provider=provider,
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
                self._upsert_club_external_identity(club=club, team_data=team_data, provider=provider)
            )

            squad_payload = team_payload.get("squad") or []

            summary = self._make_summary({
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
            })
            summary["records_created"] = 1 if club_identity_created else 0
            summary["records_updated"] = 1 if club_identity_updated else 0

            errors = []
            seen_player_ids: set[int] = set()

            for raw_player in squad_payload:
                summary["records_processed"] += 1
                try:
                    player, p_c, p_u, i_c, i_u, cp_c, cp_u = self._process_single_squad_player(
                        raw_player, team_data, provider, club, triggered_by
                    )
                    seen_player_ids.add(player.id)
                    self._tally(summary, p_c, p_u, "players_created", "players_updated")
                    self._tally(summary, i_c, i_u, "player_external_identities_created", "player_external_identities_updated")
                    self._tally(summary, cp_c, cp_u, "club_players_created", "club_players_updated")
                except Exception as exc:
                    summary["error_count"] += 1
                    errors.append(format_player_error(raw_player, exc))

            # Deactivate ClubPlayer records for players no longer in the squad.
            # Only do this when the API returned a non-empty squad so a partial
            # response doesn't silently wipe the whole roster.
            if seen_player_ids:
                departed_count = ClubPlayer.objects.filter(
                    club=club, is_active=True, player__isnull=False,
                ).exclude(player_id__in=seen_player_ids).update(
                    is_active=False, updated_at=timezone.now(),
                )
                if departed_count:
                    summary["records_updated"] += departed_count
                    summary["metadata"]["club_players_deactivated"] += departed_count

            self._finalize_summary(summary, errors)
            self._finish_sync_job_success(job, summary)
            return {"job": job, "club_external_identity": club_identity, "summary": summary}
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    # Sync a provider team and optionally attach players to a linked club
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
                provider=provider, external_id=str(team_data["external_id"]),
            ).first()

            summary = self._make_summary({
                "provider_team_id": team_data["external_id"],
                "mapped_club_id": linked_identity.club_id if linked_identity else None,
                "players_created": 0,
                "players_updated": 0,
                "player_external_identities_created": 0,
                "player_external_identities_updated": 0,
                "club_players_created": 0,
                "club_players_updated": 0,
            })

            errors = []
            club_for_roster = None

            if linked_identity:
                _, _, identity_updated = self._upsert_club_external_identity(
                    club=linked_identity.club, team_data=team_data, provider=provider,
                )
                if identity_updated:
                    summary["records_updated"] += 1
                club_for_roster = linked_identity.club

            for raw_player in squad_payload:
                summary["records_processed"] += 1
                try:
                    _, p_c, p_u, i_c, i_u, cp_c, cp_u = self._process_single_squad_player(
                        raw_player, team_data, provider, club_for_roster, triggered_by
                    )
                    self._tally(summary, p_c, p_u, "players_created", "players_updated")
                    self._tally(summary, i_c, i_u, "player_external_identities_created", "player_external_identities_updated")
                    self._tally(summary, cp_c, cp_u, "club_players_created", "club_players_updated")
                except Exception as exc:
                    summary["error_count"] += 1
                    errors.append(format_player_error(raw_player, exc))

            self._finalize_summary(summary, errors)
            self._finish_sync_job_success(job, summary)
            return {"job": job, "summary": summary}
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    # Sync competitions from the provider into local competition records
    def sync_competitions(
        self,
        areas=None,
        provider="football_data",
        triggered_by=None,
    ):
        areas_list = list(areas) if isinstance(areas, (list, tuple, set)) else areas

        job = self._start_sync_job(
            provider=provider,
            resource_type="competitions",
            resource_external_id="all",
            triggered_by=triggered_by,
            metadata={"areas": areas_list},
        )

        try:
            payload = self.client.get_competitions(areas=areas)
            competitions_data = normalize_competitions_payload(payload)

            summary = self._make_summary({"areas": areas_list, "competition_ids": []})
            errors = []

            for competition_data in competitions_data:
                summary["records_processed"] += 1
                try:
                    competition, created, updated = self._upsert_competition(
                        competition_data=competition_data, provider=provider,
                    )
                    summary["metadata"]["competition_ids"].append(competition.id)
                    self._tally(summary, created, updated)
                except Exception as exc:
                    summary["error_count"] += 1
                    errors.append(f"competition:{competition_data.get('external_id', 'unknown')} {exc}")

            self._finalize_summary(summary, errors)
            self._finish_sync_job_success(job, summary)
            return {"job": job, "summary": summary}
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    # Sync the team directory for a competition and season
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
                competition_external_id=competition_external_id, provider=provider,
            )

            payload = self.client.get_competition_teams(competition_external_id, season=season)
            teams_payload = payload.get("teams") or []
            teams_data = normalize_competition_teams_payload(
                payload,
                competition_external_id=competition.external_id,
                season_label=_season_str(season),
            )

            summary = self._make_summary({
                "competition_external_id": str(competition_external_id),
                "competition_id": competition.id,
                "season_label": teams_data[0]["season_label"] if teams_data else (_season_str(season) or competition.current_season_label),
                "teams_created": 0,
                "teams_updated": 0,
                "matched_club_mappings_updated": 0,
            })
            errors = []

            for index, team_data in enumerate(teams_data):
                summary["records_processed"] += 1
                try:
                    raw_team = teams_payload[index] if index < len(teams_payload) else {}
                    with transaction.atomic():
                        _, created, updated = self._upsert_team_directory_entry(
                            competition=competition, team_data=team_data, provider=provider,
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
                                    club=identity.club, team_data=provider_team_data, provider=provider,
                                )

                    self._tally(summary, created, updated, "teams_created", "teams_updated")
                    if mapping_updated:
                        summary["records_updated"] += 1
                        summary["metadata"]["matched_club_mappings_updated"] += 1
                except Exception as exc:
                    summary["error_count"] += 1
                    errors.append(f"team:{team_data.get('external_id', 'unknown')} {exc}")

            self._finalize_summary(summary, errors)
            self._finish_sync_job_success(job, summary)
            return {"job": job, "competition": competition, "summary": summary}
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    # Sync the player directory for one competition team and season
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
                competition_external_id=competition_external_id, provider=provider,
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
                    competition=competition, team_data=team_data, provider=provider,
                )
                # Reuse the already-fetched team payload to avoid a second API call per team
                players_data = normalize_team_players_payload(
                    team_payload.get("squad") or [], team_external_id=team_external_id,
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
                players_data = build_understat_fallback_players_data(
                    team_entry=team_entry,
                    season_label=season_label,
                    provider=provider,
                    get_client_fn=self._get_understat_client,
                )
                team_created = False
                team_updated = False

            summary = self._make_summary({
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
            })
            summary["records_created"] = 1 if team_created else 0
            summary["records_updated"] = 1 if team_updated else 0

            errors = []
            seen_external_ids = set()

            for player_data in players_data:
                summary["records_processed"] += 1
                seen_external_ids.add(str(player_data.get("external_player_id") or ""))
                try:
                    canonical_player = resolve_or_create_canonical_player_for_directory_data(
                        player_data=player_data, provider=provider,
                    )
                    _, created, updated = self._upsert_player_directory_entry(
                        team_entry=team_entry,
                        player_data=player_data,
                        canonical_player=canonical_player,
                        provider=provider,
                    )
                    self._tally(summary, created, updated, "player_directory_created", "player_directory_updated")
                except Exception as exc:
                    summary["error_count"] += 1
                    errors.append(f"player:{player_data.get('external_player_id', 'unknown')} {exc}")

            players_marked_inactive = self._deactivate_missing_team_players(
                team_entry=team_entry, active_external_ids=seen_external_ids,
            )
            if players_marked_inactive:
                summary["records_updated"] += players_marked_inactive
                summary["metadata"]["players_marked_inactive"] = players_marked_inactive

            self._finalize_summary(summary, errors)
            self._finish_sync_job_success(job, summary)
            return {"job": job, "competition": competition, "team": team_entry, "summary": summary}
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    # Sync a competition table snapshot and replace its rows
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
            metadata={"season": _season_str(season), "snapshot_label": snapshot_label},
        )

        try:
            competition = self._ensure_competition_record(
                competition_external_id=competition_external_id, provider=provider,
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
                    competition=competition, table_data=table_data,
                )
                rows_replaced, previous_rows = self._replace_competition_table_rows(
                    snapshot=snapshot,
                    competition=competition,
                    rows_data=table_data.get("rows") or [],
                    provider=provider,
                )

            summary = self._make_summary({
                "competition_external_id": str(competition_external_id),
                "competition_id": competition.id,
                "snapshot_id": snapshot.id,
                "season_label": snapshot.season_label,
                "snapshot_label": snapshot.snapshot_label,
                "matchday": snapshot.matchday,
                "rows_replaced": rows_replaced,
                "previous_rows_deleted": previous_rows,
            })
            summary["records_processed"] = rows_replaced
            summary["records_created"] = (1 if snapshot_created else 0) + rows_replaced
            summary["records_updated"] = (1 if snapshot_updated else 0) + (1 if previous_rows else 0)

            self._finish_sync_job_success(job, summary)
            return {"job": job, "competition": competition, "snapshot": snapshot, "summary": summary}
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    # Sync fixtures for a competition and season
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
                competition_external_id=competition_external_id, provider=provider,
            )

            payload = self.client.get_competition_matches(
                competition_external_id,
                season=season, matchday=matchday, status=status,
                date_from=date_from, date_to=date_to, stage=stage, group=group,
            )
            fixtures_data = normalize_competition_matches_payload(
                payload,
                competition_external_id=competition.external_id,
                season_label=_season_str(season),
            )

            summary = self._make_summary({
                "competition_external_id": str(competition_external_id),
                "competition_id": competition.id,
                "season_label": fixtures_data[0]["season_label"] if fixtures_data else (_season_str(season) or competition.current_season_label),
            })
            errors = []

            for fixture_data in fixtures_data:
                summary["records_processed"] += 1
                try:
                    _, created, updated = self._upsert_competition_fixture(
                        competition=competition, fixture_data=fixture_data, provider=provider,
                    )
                    self._tally(summary, created, updated)
                except Exception as exc:
                    summary["error_count"] += 1
                    errors.append(f"fixture:{fixture_data.get('external_match_id', 'unknown')} {exc}")

            self._finalize_summary(summary, errors)
            self._finish_sync_job_success(job, summary)
            return {"job": job, "competition": competition, "summary": summary}
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    # Sync top scorers for a competition and season
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
            metadata={"season": _season_str(season), "matchday": matchday},
        )

        try:
            competition = self._ensure_competition_record(
                competition_external_id=competition_external_id, provider=provider,
            )

            payload = self.client.get_competition_scorers(
                competition_external_id, season=season, matchday=matchday,
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

            summary = self._make_summary({
                "competition_external_id": str(competition_external_id),
                "competition_id": competition.id,
                "season_label": resolved_season_label,
                "scorers_recreated": scorers_created,
                "previous_scorers_deleted": scorers_deleted,
            })
            summary["records_processed"] = scorers_created
            summary["records_created"] = scorers_created
            summary["records_updated"] = 1 if scorers_deleted else 0

            self._finish_sync_job_success(job, summary)
            return {"job": job, "competition": competition, "summary": summary}
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    # ------------------------------------------------------------------
    # Summary helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_summary(metadata=None):
        return {
            "status": ProviderSyncStatus.SUCCESS,
            "records_processed": 0,
            "records_created": 0,
            "records_updated": 0,
            "error_count": 0,
            "raw_error_summary": "",
            "metadata": metadata or {},
        }

    @staticmethod
    def _finalize_summary(summary, errors):
        if errors:
            summary["status"] = ProviderSyncStatus.PARTIAL
            summary["raw_error_summary"] = "\n".join(errors)

    @staticmethod
    def _tally(summary, created, updated, created_key=None, updated_key=None):
        if created:
            summary["records_created"] += 1
            if created_key:
                summary["metadata"][created_key] += 1
        elif updated:
            summary["records_updated"] += 1
            if updated_key:
                summary["metadata"][updated_key] += 1

    # ------------------------------------------------------------------
    # Squad player processing
    # ------------------------------------------------------------------

    def _process_single_squad_player(
        self, raw_player, team_data, provider, club_for_roster=None, triggered_by=None
    ):
        """Process one player from a squad payload.
        Returns (player, player_created, player_updated, identity_created, identity_updated,
        club_player_created, club_player_updated)."""
        player_data = normalize_squad_player(raw_player, external_team_id=team_data["external_id"])

        with transaction.atomic():
            player, p_created, p_updated = resolve_or_create_player_from_provider(
                player_data=player_data, provider=provider,
            )
            _, i_created, i_updated = upsert_player_external_identity(
                player=player, player_data=player_data, provider=provider,
            )
            cp_created = cp_updated = False
            if club_for_roster:
                _, cp_created, cp_updated = ensure_club_player_for_player(
                    club=club_for_roster,
                    player=player,
                    player_data=player_data,
                    triggered_by=triggered_by,
                )

        return player, p_created, p_updated, i_created, i_updated, cp_created, cp_updated

    # ------------------------------------------------------------------
    # Sync job management
    # ------------------------------------------------------------------

    def _start_sync_job(
        self, provider, resource_type, resource_external_id, triggered_by=None, metadata=None,
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
        job.save(update_fields=[
            "status", "finished_at", "records_processed", "records_created",
            "records_updated", "error_count", "raw_error_summary", "metadata",
        ])

    def _finish_sync_job_failure(self, job, exc):
        job.status = ProviderSyncStatus.FAILED
        job.finished_at = timezone.now()
        job.error_count = max(job.error_count, 1)
        job.raw_error_summary = str(exc)
        job.save(update_fields=["status", "finished_at", "error_count", "raw_error_summary"])

    # ------------------------------------------------------------------
    # Competition and team record management
    # ------------------------------------------------------------------

    # Resolve the mapped external team ID for a club
    def _resolve_club_external_team_id(self, club, provider):
        identity = (
            ClubExternalIdentity.objects.filter(club=club, provider=provider, is_primary=True).first()
            or ClubExternalIdentity.objects.filter(club=club, provider=provider).first()
        )
        if not identity:
            raise ValueError(f"Club {club.id} has no {provider} team mapping.")
        return identity.external_id

    # Ensure a local competition record exists before syncing related data
    def _ensure_competition_record(self, competition_external_id, provider):
        competition = Competition.objects.filter(
            provider=provider, external_id=str(competition_external_id),
        ).first()
        if competition:
            return competition
        payload = self.client.get_competition(competition_external_id)
        competition_data = normalize_competition(payload)
        competition, _, _ = self._upsert_competition(competition_data=competition_data, provider=provider)
        return competition

    def _upsert_competition(self, competition_data, provider):
        return upsert_record(
            Competition,
            lookup_kwargs={"provider": provider, "external_id": str(competition_data["external_id"])},
            field_values={
                "code": competition_data.get("code", ""),
                "name": competition_data.get("name", ""),
                "area_name": competition_data.get("area_name", ""),
                "emblem_url": competition_data.get("emblem_url", ""),
                "current_season_label": competition_data.get("current_season_label", ""),
                "current_season_start_date": competition_data.get("current_season_start_date"),
                "current_season_end_date": competition_data.get("current_season_end_date"),
                "current_matchday": competition_data.get("current_matchday"),
                "last_synced_at": timezone.now(),
                "metadata": competition_data.get("metadata", {}) or {},
            },
        )

    # Create or update a club external identity mapping, enforcing single-primary
    def _upsert_club_external_identity(self, club, team_data, provider):
        external_id = str(team_data["external_id"])
        now = timezone.now()

        identity = ClubExternalIdentity.objects.filter(
            provider=provider, external_id=external_id,
        ).first()

        created = False
        updated = False

        if identity and identity.club_id != club.id:
            raise ValueError(
                f"{provider} team {external_id} is already linked to club {identity.club_id}."
            )

        if not identity:
            identity = ClubExternalIdentity(club=club, provider=provider, external_id=external_id)
            created = True

        values = {
            "provider_display_name": team_data.get("provider_display_name", ""),
            "country": team_data.get("country", ""),
            "competition_context": team_data.get("competition_context", ""),
            "is_primary": True,
            "metadata": team_data.get("metadata", {}) or {},
            "last_synced_at": now,
        }
        changed = [k for k, v in values.items() if getattr(identity, k) != v]
        for k in changed:
            setattr(identity, k, values[k])

        if created:
            identity.save()
        elif changed:
            identity.save(update_fields=changed)
            updated = True

        ClubExternalIdentity.objects.filter(
            club=club, provider=provider, is_primary=True,
        ).exclude(pk=identity.pk).update(is_primary=False)

        return identity, created, updated

    def _upsert_team_directory_entry(self, competition, team_data, provider):
        season_label = str(team_data.get("season_label") or competition.current_season_label or "")
        return upsert_record(
            TeamDirectoryEntry,
            lookup_kwargs={
                "competition": competition,
                "season_label": season_label,
                "provider": provider,
                "external_id": str(team_data["external_id"]),
            },
            field_values={
                "name": team_data.get("name", ""),
                "short_name": team_data.get("short_name", ""),
                "tla": team_data.get("tla", ""),
                "area_name": team_data.get("area_name", ""),
                "emblem_url": team_data.get("emblem_url", ""),
                "venue": team_data.get("venue", ""),
                "website": team_data.get("website", ""),
                "founded_year": team_data.get("founded_year"),
                "last_synced_at": timezone.now(),
                "metadata": team_data.get("metadata", {}) or {},
            },
        )

    def _upsert_player_directory_entry(self, team_entry, player_data, canonical_player, provider):
        return upsert_record(
            PlayerDirectoryEntry,
            lookup_kwargs={
                "team": team_entry,
                "provider": provider,
                "external_player_id": str(player_data["external_player_id"]),
            },
            field_values={
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
                "last_synced_at": timezone.now(),
                "metadata": player_data.get("metadata", {}) or {},
            },
        )

    def _deactivate_missing_team_players(self, team_entry, active_external_ids):
        if not active_external_ids:
            return 0
        return PlayerDirectoryEntry.objects.filter(
            team=team_entry, is_active=True,
        ).exclude(
            external_player_id__in=list(active_external_ids),
        ).update(is_active=False, updated_at=timezone.now())

    # ------------------------------------------------------------------
    # Table and fixture record management
    # ------------------------------------------------------------------

    def _upsert_competition_table_snapshot(self, competition, table_data):
        season_label = str(table_data.get("season_label") or competition.current_season_label or "")
        return upsert_record(
            CompetitionTableSnapshot,
            lookup_kwargs={
                "competition": competition,
                "season_label": season_label,
                "snapshot_label": str(table_data.get("snapshot_label") or "latest"),
            },
            field_values={
                "matchday": table_data.get("matchday"),
                "fetched_at": table_data.get("fetched_at"),
                "synced_at": timezone.now(),
                "metadata": table_data.get("metadata", {}) or {},
            },
        )

    def _replace_competition_table_rows(self, snapshot, competition, rows_data, provider):
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
        season_label = str(fixture_data.get("season_label") or competition.current_season_label or "")
        home_external_team_id = str(fixture_data.get("home_external_team_id") or "")
        away_external_team_id = str(fixture_data.get("away_external_team_id") or "")
        home_team = self._find_team_directory_entry(
            competition, season_label, provider, home_external_team_id,
        )
        away_team = self._find_team_directory_entry(
            competition, season_label, provider, away_external_team_id,
        )
        return upsert_record(
            CompetitionFixture,
            lookup_kwargs={
                "competition": competition,
                "season_label": season_label,
                "external_match_id": str(fixture_data["external_match_id"]),
            },
            field_values={
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
                "synced_at": timezone.now(),
                "metadata": fixture_data.get("metadata", {}) or {},
            },
        )

    def _replace_competition_scorers(self, competition, season_label, scorers_data, provider):
        existing = CompetitionTopScorer.objects.filter(
            competition=competition, season_label=season_label,
        )
        deleted_count = existing.count()
        existing.delete()
        created_count = 0

        for scorer_data in scorers_data:
            external_team_id = str(scorer_data.get("external_team_id") or "")
            external_player_id = str(scorer_data.get("external_player_id") or "")
            team_entry = self._find_team_directory_entry(
                competition=competition, season_label=season_label,
                provider=provider, external_team_id=external_team_id,
            )
            canonical_player = resolve_canonical_player_by_external_id(
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

    def _find_team_directory_entry(self, competition, season_label, provider, external_team_id):
        if not external_team_id:
            return None
        return TeamDirectoryEntry.objects.filter(
            competition=competition,
            season_label=season_label,
            provider=provider,
            external_id=str(external_team_id),
        ).first()

    # ------------------------------------------------------------------
    # Understat client
    # ------------------------------------------------------------------

    def _get_understat_client(self):
        if self._understat_client is None:
            self._understat_client = UnderstatClient()
        return self._understat_client


# ------------------------------------------------------------------
# Module-level convenience wrappers
# ------------------------------------------------------------------

# Link a club to a provider team using a fresh sync service instance
def link_club_to_provider_team(*args, **kwargs):
    return FootballDataSyncService().link_club_to_provider_team(*args, **kwargs)


# Sync a club team squad using a fresh sync service instance
def sync_club_team_squad(*args, **kwargs):
    return FootballDataSyncService().sync_club_team_squad(*args, **kwargs)


# Sync a provider team using a fresh sync service instance
def sync_provider_team(*args, **kwargs):
    return FootballDataSyncService().sync_provider_team(*args, **kwargs)


# Sync competitions using a fresh sync service instance
def sync_competitions(*args, **kwargs):
    return FootballDataSyncService().sync_competitions(*args, **kwargs)


# Sync competition teams using a fresh sync service instance
def sync_competition_teams(*args, **kwargs):
    return FootballDataSyncService().sync_competition_teams(*args, **kwargs)


# Sync a team squad directory using a fresh sync service instance
def sync_team_squad_directory(*args, **kwargs):
    return FootballDataSyncService().sync_team_squad_directory(*args, **kwargs)


# Sync a competition table using a fresh sync service instance
def sync_competition_table(*args, **kwargs):
    return FootballDataSyncService().sync_competition_table(*args, **kwargs)


# Sync competition fixtures using a fresh sync service instance
def sync_competition_fixtures(*args, **kwargs):
    return FootballDataSyncService().sync_competition_fixtures(*args, **kwargs)


# Sync competition scorers using a fresh sync service instance
def sync_competition_scorers(*args, **kwargs):
    return FootballDataSyncService().sync_competition_scorers(*args, **kwargs)
