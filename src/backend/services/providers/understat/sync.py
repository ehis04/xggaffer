"""
Understat sync service for club and player enrichment data

Fetches Understat team and player season payloads, normalises them, and stores club, player, and provider identity enrichment records
"""

from __future__ import annotations

import re
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.clubs.models import Club, ClubExternalIdentity, ClubPlayer
from apps.playerdata.models import ClubSeasonEnrichment, PlayerSeasonEnrichment
from apps.players.models import (
    ExternalProvider,
    Player,
    PlayerExternalIdentity,
    ProviderSyncJob,
    ProviderSyncStatus,
)
from apps.predictions.data_collection.config.team_name_mappings import to_canonical
from common.utils import normalise_lookup_name

from .client import UnderstatClient
from .normalisers import (
    normalise_understat_player_season,
    normalise_understat_team_player,
    normalise_understat_team_season,
)
from .team_slugs import canonicalise_understat_team_slug


# ---------------------------------------------------------------------------
# Provider constants
# ---------------------------------------------------------------------------

UNDERSTAT_PROVIDER = ExternalProvider.UNDERSTAT
_GENERIC_CLUB_TOKENS = {
    "fc",
    "cf",
    "afc",
    "ac",
    "sc",
    "sv",
    "fk",
    "if",
    "bk",
}


# ---------------------------------------------------------------------------
# Understat sync service
# ---------------------------------------------------------------------------

# Service for syncing Understat club, player, and league season data
class UnderstatSyncService:

    # Set up the sync service with an Understat client
    def __init__(self, client: UnderstatClient | None = None) -> None:
        self.client = client or UnderstatClient()

    # Sync one club season enrichment record from Understat
    def sync_understat_club_season(
        self,
        club: Club,
        season_label: str,
        competition_code: str | None = None,
        external_team_id: str | None = None,
        triggered_by=None,
    ) -> dict[str, Any]:
        self._assert_understat_enabled()

        resolved_external_team_id = (
            canonicalise_understat_team_slug(external_team_id)
            if external_team_id
            else self._resolve_understat_club_external_id(club)
        )

        job = self._start_sync_job(
            resource_type="club_season",
            resource_external_id=resolved_external_team_id,
            triggered_by=triggered_by,
            metadata={
                "club_id": club.id,
                "season_label": str(season_label),
                "competition_code": competition_code or "",
            },
        )

        try:
            raw_payload = self.client.get_team_season_payload(
                resolved_external_team_id,
                season_label,
            )
            normalised = normalise_understat_team_season(
                raw_payload,
                season_label=season_label,
                competition_code=competition_code,
            )

            identity, identity_created, identity_updated = self._upsert_understat_club_identity(
                club=club,
                external_team_id=resolved_external_team_id,
                provider_display_name=normalised.get("competition_name", "") or club.name,
                competition_code=normalised.get("competition_code", "") or competition_code or "",
                metadata={
                    "source": "understat",
                    "season_label": str(season_label),
                },
            )

            enrichment, enrichment_created, enrichment_updated = self._upsert_club_season_enrichment(
                club=club,
                data=normalised,
            )

            summary = {
                "status": ProviderSyncStatus.SUCCESS,
                "records_processed": 1,
                "records_created": int(identity_created) + int(enrichment_created),
                "records_updated": int(identity_updated) + int(enrichment_updated),
                "error_count": 0,
                "raw_error_summary": "",
                "metadata": {
                    "club_id": club.id,
                    "club_external_identity_id": identity.id,
                    "club_season_enrichment_id": enrichment.id,
                    "season_label": str(season_label),
                    "competition_code": normalised.get("competition_code", "") or "",
                    "provider_team_id": resolved_external_team_id,
                    "identity_created": identity_created,
                    "identity_updated": identity_updated,
                    "enrichment_created": enrichment_created,
                    "enrichment_updated": enrichment_updated,
                },
            }

            self._finish_sync_job_success(job, summary)

            return {
                "job": job,
                "club_external_identity": identity,
                "club_season_enrichment": enrichment,
                "summary": summary,
            }
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    # Sync all player season enrichment rows for one club season
    def sync_understat_club_players_season(
        self,
        club: Club,
        season_label: str,
        competition_code: str | None = None,
        external_team_id: str | None = None,
        triggered_by=None,
    ) -> dict[str, Any]:
        self._assert_understat_enabled()

        resolved_external_team_id = (
            canonicalise_understat_team_slug(external_team_id)
            if external_team_id
            else self._resolve_understat_club_external_id(club)
        )

        job = self._start_sync_job(
            resource_type="club_players_season",
            resource_external_id=resolved_external_team_id,
            triggered_by=triggered_by,
            metadata={
                "club_id": club.id,
                "season_label": str(season_label),
                "competition_code": competition_code or "",
            },
        )

        try:
            raw_payload = self.client.get_team_season_payload(
                resolved_external_team_id,
                season_label,
            )
            raw_players = raw_payload.get("players") or []

            errors: list[str] = []

            summary = {
                "status": ProviderSyncStatus.SUCCESS,
                "records_processed": 0,
                "records_created": 0,
                "records_updated": 0,
                "error_count": 0,
                "raw_error_summary": "",
                "metadata": {
                    "club_id": club.id,
                    "season_label": str(season_label),
                    "competition_code": competition_code or "",
                    "provider_team_id": resolved_external_team_id,
                    "players_matched": 0,
                    "players_unmatched": 0,
                    "player_external_identities_created": 0,
                    "player_external_identities_updated": 0,
                    "player_season_enrichments_created": 0,
                    "player_season_enrichments_updated": 0,
                    "players_competition_filtered": 0,
                    "players_team_row_fallback": 0,
                },
            }

            self._upsert_understat_club_identity(
                club=club,
                external_team_id=resolved_external_team_id,
                provider_display_name=club.name,
                competition_code=competition_code or "",
                metadata={
                    "source": "understat",
                    "season_label": str(season_label),
                },
            )

            for raw_player in raw_players:
                summary["records_processed"] += 1

                try:
                    normalised_player = None
                    external_player_id = str(raw_player.get("id") or "").strip()

                    if competition_code and external_player_id:
                        try:
                            player_payload = self.client.get_player_stats(
                                external_player_id,
                                season=season_label,
                            )
                            if not isinstance(player_payload, dict):
                                raise ValueError("Understat player payload must be a dictionary.")
                            normalised_player = normalise_understat_player_season(
                                player_payload,
                                season_label=season_label,
                                competition_code=competition_code,
                            )

                            # Keep team-page identity hints for local player matching
                            player_metadata = dict(normalised_player.get("metadata", {}) or {})
                            if not player_metadata.get("player_name"):
                                player_metadata["player_name"] = (
                                    raw_player.get("player_name")
                                    or raw_player.get("player")
                                    or raw_player.get("name")
                                    or ""
                                )
                            if not player_metadata.get("position"):
                                player_metadata["position"] = str(raw_player.get("position") or "")
                            normalised_player["metadata"] = player_metadata

                            if not normalised_player.get("external_team_id"):
                                normalised_player["external_team_id"] = resolved_external_team_id

                            if not normalised_player.get("competition_name"):
                                normalised_player["competition_name"] = (
                                    raw_payload.get("league")
                                    or raw_payload.get("competition_name")
                                    or ""
                                )

                            merged_snapshot = dict(normalised_player.get("raw_snapshot", {}) or {})
                            merged_snapshot["team_player_row"] = raw_player
                            normalised_player["raw_snapshot"] = merged_snapshot

                            summary["metadata"]["players_competition_filtered"] += 1
                        except Exception:
                            normalised_player = None

                    if normalised_player is None:
                        normalised_player = normalise_understat_team_player(
                            raw_player,
                            season_label=season_label,
                            competition_code=competition_code,
                            external_team_id=resolved_external_team_id,
                            competition_name=(
                                raw_payload.get("league")
                                or raw_payload.get("competition_name")
                                or ""
                            ),
                        )
                        if competition_code:
                            summary["metadata"]["players_team_row_fallback"] += 1

                    player = self._resolve_understat_player_identity(
                        player_data=normalised_player,
                        club=club,
                    )

                    if not player:
                        summary["metadata"]["players_unmatched"] += 1
                        summary["error_count"] += 1
                        errors.append(
                            self._format_player_match_error(
                                normalised_player,
                                club=club,
                            )
                        )
                        continue

                    summary["metadata"]["players_matched"] += 1

                    identity, identity_created, identity_updated = self._upsert_understat_player_identity(
                        player=player,
                        external_player_id=normalised_player.get("external_player_id", ""),
                        provider_display_name=(
                            normalised_player.get("metadata", {}).get("player_name", "")
                            or player.display_name
                            or player.full_name
                        ),
                        external_team_id=normalised_player.get("external_team_id", "") or "",
                        provider_position=normalised_player.get("metadata", {}).get("position", "") or "",
                        metadata={
                            "source": "understat",
                            "club_id": club.id,
                            "season_label": str(season_label),
                        },
                    )

                    enrichment, enrichment_created, enrichment_updated = self._upsert_player_season_enrichment(
                        player=player,
                        club=club,
                        data=normalised_player,
                    )

                    summary["records_created"] += int(identity_created) + int(enrichment_created)
                    summary["records_updated"] += int(identity_updated) + int(enrichment_updated)
                    summary["metadata"]["player_external_identities_created"] += int(identity_created)
                    summary["metadata"]["player_external_identities_updated"] += int(identity_updated)
                    summary["metadata"]["player_season_enrichments_created"] += int(enrichment_created)
                    summary["metadata"]["player_season_enrichments_updated"] += int(enrichment_updated)

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

    # Sync one player season enrichment record from Understat
    def sync_understat_player_season(
        self,
        player: Player,
        season_label: str,
        competition_code: str | None = None,
        external_player_id: str | None = None,
        club: Club | None = None,
        triggered_by=None,
    ) -> dict[str, Any]:
        self._assert_understat_enabled()

        resolved_external_player_id = (
            str(external_player_id).strip()
            if external_player_id
            else self._resolve_understat_player_external_id(player)
        )

        job = self._start_sync_job(
            resource_type="player_season",
            resource_external_id=resolved_external_player_id,
            triggered_by=triggered_by,
            metadata={
                "player_id": player.id,
                "club_id": club.id if club else None,
                "season_label": str(season_label),
                "competition_code": competition_code or "",
            },
        )

        try:
            raw_payload = self.client.get_player_stats(
                resolved_external_player_id,
                season=season_label,
            )
            normalised = normalise_understat_player_season(
                raw_payload,
                season_label=season_label,
                competition_code=competition_code,
            )

            resolved_club = club
            if resolved_club is None:
                resolved_club = self._resolve_understat_club_from_external_id(
                    normalised.get("external_team_id", "")
                )

            identity, identity_created, identity_updated = self._upsert_understat_player_identity(
                player=player,
                external_player_id=resolved_external_player_id,
                provider_display_name=player.display_name or player.full_name,
                external_team_id=normalised.get("external_team_id", "") or "",
                provider_position="",
                metadata={
                    "source": "understat",
                    "season_label": str(season_label),
                },
            )

            enrichment, enrichment_created, enrichment_updated = self._upsert_player_season_enrichment(
                player=player,
                club=resolved_club,
                data=normalised,
            )

            summary = {
                "status": ProviderSyncStatus.SUCCESS,
                "records_processed": 1,
                "records_created": int(identity_created) + int(enrichment_created),
                "records_updated": int(identity_updated) + int(enrichment_updated),
                "error_count": 0,
                "raw_error_summary": "",
                "metadata": {
                    "player_id": player.id,
                    "club_id": resolved_club.id if resolved_club else None,
                    "player_external_identity_id": identity.id,
                    "player_season_enrichment_id": enrichment.id,
                    "provider_player_id": resolved_external_player_id,
                    "provider_team_id": normalised.get("external_team_id", "") or "",
                    "season_label": str(season_label),
                    "competition_code": normalised.get("competition_code", "") or "",
                    "identity_created": identity_created,
                    "identity_updated": identity_updated,
                    "enrichment_created": enrichment_created,
                    "enrichment_updated": enrichment_updated,
                },
            }

            self._finish_sync_job_success(job, summary)

            return {
                "job": job,
                "player_external_identity": identity,
                "player_season_enrichment": enrichment,
                "summary": summary,
            }
        except Exception as exc:
            self._finish_sync_job_failure(job, exc)
            raise

    # Create a provider sync job for an Understat operation
    def _start_sync_job(
        self,
        *,
        resource_type: str,
        resource_external_id: str,
        triggered_by=None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderSyncJob:
        return ProviderSyncJob.objects.create(
            provider=UNDERSTAT_PROVIDER,
            resource_type=resource_type,
            resource_external_id=str(resource_external_id or ""),
            status=ProviderSyncStatus.STARTED,
            triggered_by=triggered_by,
            metadata=metadata or {},
        )

    # Mark an Understat sync job as successful or partially successful
    def _finish_sync_job_success(
        self,
        job: ProviderSyncJob,
        summary: dict[str, Any],
    ) -> None:
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

    # Mark an Understat sync job as failed
    def _finish_sync_job_failure(
        self,
        job: ProviderSyncJob,
        exc: Exception,
    ) -> None:
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

    # Resolve the Understat external team ID mapped to a club
    def _resolve_understat_club_external_id(self, club: Club) -> str:
        identity = (
            ClubExternalIdentity.objects
            .filter(club=club, provider=UNDERSTAT_PROVIDER, is_primary=True)
            .first()
        )
        if not identity:
            identity = (
                ClubExternalIdentity.objects
                .filter(club=club, provider=UNDERSTAT_PROVIDER)
                .first()
            )

        if not identity:
            raise ValueError(f"Club {club.id} has no understat team mapping.")

        return canonicalise_understat_team_slug(identity.external_id)

    # Resolve the Understat external player ID mapped to a player
    def _resolve_understat_player_external_id(self, player: Player) -> str:
        identity = (
            PlayerExternalIdentity.objects
            .filter(player=player, provider=UNDERSTAT_PROVIDER, is_primary=True)
            .first()
        )
        if not identity:
            identity = (
                PlayerExternalIdentity.objects
                .filter(player=player, provider=UNDERSTAT_PROVIDER)
                .first()
            )

        if not identity:
            raise ValueError(f"Player {player.id} has no understat player mapping.")

        return str(identity.external_id)

    # Resolve an internal club from an Understat external team ID
    def _resolve_understat_club_from_external_id(
        self,
        external_team_id: str,
    ) -> Club | None:
        external_team_id = canonicalise_understat_team_slug(external_team_id)
        if not external_team_id:
            return None

        identity = (
            ClubExternalIdentity.objects
            .select_related("club")
            .filter(
                provider=UNDERSTAT_PROVIDER,
                external_id=external_team_id,
            )
            .first()
        )
        if identity:
            return identity.club

        return None

    # Resolve an internal player from an Understat identity or deterministic club roster match
    def _resolve_understat_player_identity(
        self,
        *,
        player_data: dict[str, Any],
        club: Club | None = None,
    ) -> Player | None:
        external_player_id = str(player_data.get("external_player_id", "") or "").strip()

        if external_player_id:
            identity = (
                PlayerExternalIdentity.objects
                .select_related("player")
                .filter(
                    provider=UNDERSTAT_PROVIDER,
                    external_id=external_player_id,
                )
                .first()
            )
            if identity:
                return identity.player

        if club is None:
            return None

        candidate_name = (
            player_data.get("metadata", {}).get("player_name")
            or player_data.get("club_player_name")
            or ""
        ).strip()

        if not candidate_name:
            return None

        club_players = (
            ClubPlayer.objects
            .select_related("player")
            .filter(club=club, player__isnull=False)
        )

        matches: list[Player] = []
        target = self._normalise_name(candidate_name)

        for club_player in club_players:
            player = club_player.player
            if player is None:
                continue

            possible_names = {
                self._normalise_name(player.full_name),
                self._normalise_name(player.display_name),
                self._normalise_name(
                    f"{club_player.first_name} {club_player.last_name}".strip()
                ),
                self._normalise_name(club_player.display_name),
            }

            possible_names.discard("")

            if target in possible_names:
                matches.append(player)

        unique_player_ids = {player.id for player in matches}
        if len(unique_player_ids) == 1:
            return matches[0]

        return None

    # Create or update an Understat club external identity
    @transaction.atomic
    def _upsert_understat_club_identity(
        self,
        *,
        club: Club,
        external_team_id: str,
        provider_display_name: str = "",
        competition_code: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> tuple[ClubExternalIdentity, bool, bool]:
        external_team_id = canonicalise_understat_team_slug(external_team_id)
        if not external_team_id:
            raise ValueError("Understat club identity requires a non-empty external team id.")

        now = timezone.now()
        identity = (
            ClubExternalIdentity.objects
            .filter(provider=UNDERSTAT_PROVIDER, external_id=external_team_id)
            .first()
        )

        created = False
        updated = False

        if identity and identity.club_id != club.id:
            raise ValueError(
                f"understat team {external_team_id} is already linked to club {identity.club_id}."
            )

        if not identity:
            identity = ClubExternalIdentity(
                club=club,
                provider=UNDERSTAT_PROVIDER,
                external_id=external_team_id,
            )
            created = True

        changed_fields: list[str] = []

        if identity.club_id != club.id:
            identity.club = club
            changed_fields.append("club")

        if provider_display_name and identity.provider_display_name != provider_display_name:
            identity.provider_display_name = provider_display_name
            changed_fields.append("provider_display_name")

        if competition_code and identity.competition_context != competition_code:
            identity.competition_context = competition_code
            changed_fields.append("competition_context")

        merged_metadata = dict(identity.metadata or {})
        if metadata:
            merged_metadata.update(metadata)
        if merged_metadata != (identity.metadata or {}):
            identity.metadata = merged_metadata
            changed_fields.append("metadata")

        if identity.last_synced_at != now:
            identity.last_synced_at = now
            changed_fields.append("last_synced_at")

        if created:
            identity.is_primary = True
            identity.save()
            return identity, True, False

        if changed_fields:
            identity.save(update_fields=changed_fields)
            updated = True

        return identity, False, updated

    # Create or update an Understat player external identity
    @transaction.atomic
    def _upsert_understat_player_identity(
        self,
        *,
        player: Player,
        external_player_id: str,
        provider_display_name: str = "",
        external_team_id: str = "",
        provider_position: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> tuple[PlayerExternalIdentity, bool, bool]:
        external_player_id = str(external_player_id or "").strip()
        if not external_player_id:
            raise ValueError("Understat player identity requires a non-empty external player id.")

        now = timezone.now()
        identity = (
            PlayerExternalIdentity.objects
            .filter(provider=UNDERSTAT_PROVIDER, external_id=external_player_id)
            .first()
        )

        created = False
        updated = False

        if identity and identity.player_id != player.id:
            raise ValueError(
                f"understat player {external_player_id} is already linked to player {identity.player_id}."
            )

        if not identity:
            identity = PlayerExternalIdentity(
                player=player,
                provider=UNDERSTAT_PROVIDER,
                external_id=external_player_id,
            )
            created = True

        changed_fields: list[str] = []

        if identity.player_id != player.id:
            identity.player = player
            changed_fields.append("player")

        if provider_display_name and identity.provider_display_name != provider_display_name:
            identity.provider_display_name = provider_display_name
            changed_fields.append("provider_display_name")

        if external_team_id != identity.external_team_id:
            identity.external_team_id = external_team_id
            changed_fields.append("external_team_id")

        if provider_position and identity.provider_position != provider_position:
            identity.provider_position = provider_position
            changed_fields.append("provider_position")

        merged_metadata = dict(identity.metadata or {})
        if metadata:
            merged_metadata.update(metadata)
        if merged_metadata != (identity.metadata or {}):
            identity.metadata = merged_metadata
            changed_fields.append("metadata")

        if identity.last_synced_at != now:
            identity.last_synced_at = now
            changed_fields.append("last_synced_at")

        if created:
            has_existing_primary = PlayerExternalIdentity.objects.filter(
                player=player,
                provider=UNDERSTAT_PROVIDER,
                is_primary=True,
            ).exists()
            identity.is_primary = not has_existing_primary
            identity.save()
            return identity, True, False

        if changed_fields:
            identity.save(update_fields=changed_fields)
            updated = True

        return identity, False, updated

    # Create or update a club season enrichment record
    @transaction.atomic
    def _upsert_club_season_enrichment(
        self,
        *,
        club: Club,
        data: dict[str, Any],
    ) -> tuple[ClubSeasonEnrichment, bool, bool]:
        lookup = {
            "club": club,
            "provider": data["provider"],
            "season_label": data["season_label"],
            "competition_code": data.get("competition_code", "") or "",
        }

        defaults = {
            "competition_name": data.get("competition_name", "") or "",
            "external_team_id": data.get("external_team_id", "") or "",
            "matches_played": data.get("matches_played", 0),
            "wins": data.get("wins", 0),
            "draws": data.get("draws", 0),
            "losses": data.get("losses", 0),
            "goals_for": data.get("goals_for", 0),
            "goals_against": data.get("goals_against", 0),
            "xg": data.get("xg"),
            "xga": data.get("xga"),
            "npxg": data.get("npxg"),
            "ppda": data.get("ppda"),
            "last_synced_at": timezone.now(),
            "metadata": data.get("metadata", {}) or {},
            "raw_snapshot": data.get("raw_snapshot", {}) or {},
        }

        enrichment, created = ClubSeasonEnrichment.objects.update_or_create(
            **lookup,
            defaults=defaults,
        )
        return enrichment, created, not created

    # Create or update a player season enrichment record
    @transaction.atomic
    def _upsert_player_season_enrichment(
        self,
        *,
        player: Player,
        club: Club | None,
        data: dict[str, Any],
    ) -> tuple[PlayerSeasonEnrichment, bool, bool]:
        lookup = {
            "player": player,
            "provider": data["provider"],
            "season_label": data["season_label"],
            "competition_code": data.get("competition_code", "") or "",
            "external_team_id": data.get("external_team_id", "") or "",
        }

        defaults = {
            "club": club,
            "competition_name": data.get("competition_name", "") or "",
            "external_player_id": data.get("external_player_id", "") or "",
            "matches_played": data.get("matches_played", 0),
            "minutes_played": data.get("minutes_played", 0),
            "goals": data.get("goals", 0),
            "assists": data.get("assists", 0),
            "shots": data.get("shots", 0),
            "xg": data.get("xg"),
            "xa": data.get("xa"),
            "npg": data.get("npg"),
            "npxg": data.get("npxg"),
            "xg_chain": data.get("xg_chain"),
            "xg_buildup": data.get("xg_buildup"),
            "yellow_cards": data.get("yellow_cards", 0),
            "red_cards": data.get("red_cards", 0),
            "key_passes": data.get("key_passes", 0),
            "last_synced_at": timezone.now(),
            "metadata": data.get("metadata", {}) or {},
            "raw_snapshot": data.get("raw_snapshot", {}) or {},
        }

        enrichment, created = PlayerSeasonEnrichment.objects.update_or_create(
            **lookup,
            defaults=defaults,
        )
        return enrichment, created, not created

    # Raise an error if Understat sync is disabled in settings
    def _assert_understat_enabled(self) -> None:
        if not getattr(settings, "UNDERSTAT_ENABLED", False):
            raise ValueError("Understat sync is disabled by configuration.")

    # Format a raw player sync error for the summary
    def _format_player_error(self, raw_player: dict[str, Any], exc: Exception) -> str:
        raw_id = raw_player.get("id", "unknown")
        raw_name = (
            raw_player.get("player_name")
            or raw_player.get("player")
            or raw_player.get("name")
            or "unknown"
        )
        return f"player:{raw_id}:{raw_name} {exc}"

    # Format a deterministic player matching failure for the summary
    def _format_player_match_error(
        self,
        player_data: dict[str, Any],
        *,
        club: Club,
    ) -> str:
        player_name = (
            player_data.get("metadata", {}).get("player_name")
            or "unknown"
        )
        external_player_id = player_data.get("external_player_id", "") or "unknown"
        return (
            f"player:{external_player_id}:{player_name} "
            f"could not be matched deterministically to club {club.id}"
        )

    # Sync every deterministically matched club in an Understat league season
    def sync_understat_league_season(
        self,
        league_code: str,
        season_label: str,
        competition_code: str | None = None,
        triggered_by=None,
    ) -> dict[str, Any]:
        self._assert_understat_enabled()

        resolved_league_code = str(league_code or "").strip()
        if not resolved_league_code:
            raise ValueError("league_code is required.")

        resolved_competition_code = str(competition_code or resolved_league_code).strip()

        job = self._start_sync_job(
            resource_type="league_season",
            resource_external_id=resolved_league_code,
            triggered_by=triggered_by,
            metadata={
                "league_code": resolved_league_code,
                "season_label": str(season_label),
                "competition_code": resolved_competition_code,
            },
        )

        try:
            raw_payload = self.client.get_league_teams(
                resolved_league_code,
                season_label,
            )
            team_entries = self._extract_understat_league_team_entries(raw_payload)

            summary = {
                "status": ProviderSyncStatus.SUCCESS,
                "records_processed": 0,
                "records_created": 0,
                "records_updated": 0,
                "error_count": 0,
                "raw_error_summary": "",
                "metadata": {
                    "league_code": resolved_league_code,
                    "season_label": str(season_label),
                    "competition_code": resolved_competition_code,
                    "teams_seen": len(team_entries),
                    "clubs_matched": 0,
                    "clubs_unmatched": 0,
                    "club_sync_jobs_started": 0,
                },
            }

            errors: list[str] = []

            for team_entry in team_entries:
                summary["records_processed"] += 1

                external_team_id = team_entry.get("external_team_id", "")
                provider_display_name = team_entry.get("provider_display_name", "")

                club = self._resolve_understat_league_club(team_entry)

                if club is None:
                    summary["metadata"]["clubs_unmatched"] += 1
                    summary["error_count"] += 1
                    errors.append(
                        f"league_team:{external_team_id or 'unknown'}:{provider_display_name or 'unknown'} "
                        f"could not be matched deterministically to an internal club"
                    )
                    continue

                summary["metadata"]["clubs_matched"] += 1

                try:
                    if external_team_id:
                        self._upsert_understat_club_identity(
                            club=club,
                            external_team_id=external_team_id,
                            provider_display_name=provider_display_name or club.name,
                            competition_code=resolved_competition_code,
                            metadata={
                                "source": "understat",
                                "season_label": str(season_label),
                                "league_code": resolved_league_code,
                            },
                        )

                    club_result = self.sync_understat_club_season(
                        club=club,
                        season_label=season_label,
                        competition_code=resolved_competition_code,
                        external_team_id=external_team_id or None,
                        triggered_by=triggered_by,
                    )

                    club_summary = club_result.get("summary", {}) or {}
                    summary["records_created"] += club_summary.get("records_created", 0)
                    summary["records_updated"] += club_summary.get("records_updated", 0)
                    summary["metadata"]["club_sync_jobs_started"] += 1

                except Exception as exc:
                    summary["error_count"] += 1
                    errors.append(
                        f"league_team:{external_team_id or 'unknown'}:{provider_display_name or 'unknown'} {exc}"
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

    # Extract team entries from an Understat league payload
    def _extract_understat_league_team_entries(
        self,
        payload: dict[str, Any],
    ) -> list[dict[str, str]]:
        teams = payload.get("teams")
        entries: list[dict[str, str]] = []

        if isinstance(teams, dict):
            iterable = teams.items()
        elif isinstance(teams, list):
            iterable = [(None, item) for item in teams]
        else:
            return entries

        for key, value in iterable:
            if not isinstance(value, dict):
                continue

            provider_display_name = (
                str(
                    value.get("title")
                    or value.get("team_title")
                    or value.get("team_name")
                    or value.get("name")
                    or key
                    or ""
                ).strip()
            )

            raw_external_team_id = str(
                value.get("id")
                or value.get("team_id")
                or key
                or provider_display_name
                or ""
            ).strip()

            # Use the team slug expected by Understat team-season endpoints where possible
            external_team_id = self._to_understat_team_slug(provider_display_name) or raw_external_team_id

            if not provider_display_name and not external_team_id:
                continue

            entries.append(
                {
                    "external_team_id": external_team_id,
                    "provider_display_name": provider_display_name,
                }
            )

        return entries

    # Convert an Understat team display name into the team slug format
    @staticmethod
    def _to_understat_team_slug(provider_display_name: str) -> str:
        name = (provider_display_name or "").strip()
        if not name:
            return ""
        slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
        return slug

    # Resolve an internal club from an Understat league team entry
    def _resolve_understat_league_club(
        self,
        team_entry: dict[str, str],
    ) -> Club | None:
        external_team_id = str(team_entry.get("external_team_id", "") or "").strip()
        provider_display_name = str(team_entry.get("provider_display_name", "") or "").strip()

        if external_team_id:
            identity = (
                ClubExternalIdentity.objects
                .select_related("club")
                .filter(
                    provider=UNDERSTAT_PROVIDER,
                    external_id=external_team_id,
                )
                .first()
            )
            if identity:
                return identity.club

        if provider_display_name:
            exact_name_matches = list(
                Club.objects.filter(name__iexact=provider_display_name)[:2]
            )
            if len(exact_name_matches) == 1:
                return exact_name_matches[0]

            canonical_name = ""
            try:
                canonical_name = to_canonical(provider_display_name, "understat")
            except KeyError:
                canonical_name = ""

            deterministic_candidates = self._resolve_club_by_name_candidates(
                [provider_display_name, canonical_name]
            )
            if len(deterministic_candidates) == 1:
                return deterministic_candidates[0]

        return None

    # Return unique deterministic club matches from normalised candidate names
    def _resolve_club_by_name_candidates(
        self,
        candidate_names: list[str],
    ) -> list[Club]:
        candidate_keys: set[str] = set()

        for name in candidate_names:
            candidate_keys.update(self._name_lookup_keys(name))

        candidate_keys.discard("")
        if not candidate_keys:
            return []

        matches: list[Club] = []
        seen_ids: set[int] = set()

        for club in Club.objects.all():
            club_keys = self._name_lookup_keys(club.name)
            if not (candidate_keys & club_keys):
                continue

            if club.id not in seen_ids:
                matches.append(club)
                seen_ids.add(club.id)

            if len(matches) > 1:
                break

        return matches

    # Build name lookup keys for deterministic club matching
    @classmethod
    def _name_lookup_keys(cls, value: str | None) -> set[str]:
        base = cls._normalise_name(value)
        if not base:
            return set()

        keys = {base}
        stripped = cls._strip_generic_club_tokens(base)
        if stripped:
            keys.add(stripped)
        return keys

    # Remove generic club suffix or prefix tokens from a normalised name
    @classmethod
    def _strip_generic_club_tokens(cls, value: str) -> str:
        tokens = [token for token in value.split() if token not in _GENERIC_CLUB_TOKENS]
        return " ".join(tokens)

    # Normalise a name for deterministic lookup comparisons
    @staticmethod
    def _normalise_name(value: str | None) -> str:
        return normalise_lookup_name(value)


# ---------------------------------------------------------------------------
# Convenience module-level sync wrappers
# ---------------------------------------------------------------------------

# Sync one club season through a new Understat sync service instance
def sync_understat_club_season(*args, **kwargs):
    return UnderstatSyncService().sync_understat_club_season(*args, **kwargs)


# Sync one club's player season records through a new Understat sync service instance
def sync_understat_club_players_season(*args, **kwargs):
    return UnderstatSyncService().sync_understat_club_players_season(*args, **kwargs)


# Sync one player season through a new Understat sync service instance
def sync_understat_player_season(*args, **kwargs):
    return UnderstatSyncService().sync_understat_player_season(*args, **kwargs)


# Sync one league season through a new Understat sync service instance
def sync_understat_league_season(*args, **kwargs):
    return UnderstatSyncService().sync_understat_league_season(*args, **kwargs)
