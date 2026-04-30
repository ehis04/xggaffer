"""
Transfermarkt sync service for player dates of birth and injury data

Fetches Transfermarkt squad, profile, and injury pages then updates provider identities, player records, and club injury availability data
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.players.models import Player, PlayerExternalIdentity, ProviderSyncJob, ProviderSyncStatus
from services.providers.transfermarkt.client import TransfermarktClient, TransfermarktError

_logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Provider constants
# --------------------------------------------------------------------------

PROVIDER = 'transfermarkt'
RESOURCE_SQUAD = 'squad'
RESOURCE_PLAYER_PROFILE = 'player_profile'
RESOURCE_CLUB_INJURIES = 'club_injuries'

# Transfermarkt squads use the season start year
RAW_ERROR_MAX_ITEMS = 10
RAW_ERROR_MAX_LENGTH = 500


# --------------------------------------------------------------------------
# Injury classification helpers
# --------------------------------------------------------------------------

_MUSCLE_KEYWORDS = ('muscle', 'strain', 'hamstring', 'thigh', 'calf', 'groin', 'quad', 'adductor')
_LIGAMENT_KEYWORDS = ('ligament', 'cruciate', 'acl', 'mcl', 'pcl', 'collateral', 'ankle lig')
_BONE_KEYWORDS = ('fracture', 'broken', 'bone', 'stress fracture', 'metatarsal')
_TENDON_KEYWORDS = ('tendon', 'achilles')
_CARTILAGE_KEYWORDS = ('cartilage', 'meniscus')
_HEAD_KEYWORDS = ('head', 'concussion', 'skull', 'facial')
_ILLNESS_KEYWORDS = ('illness', 'sick', 'virus', 'covid', 'flu', 'infection', 'appendix')
_SUSPENSION_KEYWORDS = ('suspension', 'ban', 'red card')


# Map a raw Transfermarkt injury description to an internal injury type
def _classify_injury_type(raw: str) -> str:
    t = raw.lower()
    if any(k in t for k in _MUSCLE_KEYWORDS):
        return 'muscle'
    if any(k in t for k in _LIGAMENT_KEYWORDS):
        return 'ligament'
    if any(k in t for k in _BONE_KEYWORDS):
        return 'bone'
    if any(k in t for k in _TENDON_KEYWORDS):
        return 'tendon'
    if any(k in t for k in _CARTILAGE_KEYWORDS):
        return 'cartilage'
    if any(k in t for k in _HEAD_KEYWORDS):
        return 'head'
    if any(k in t for k in _ILLNESS_KEYWORDS):
        return 'illness'
    if any(k in t for k in _SUSPENSION_KEYWORDS):
        return 'suspension'
    return 'other'


# Map days out to an internal injury severity value
def _classify_severity(days_out: Optional[int]) -> str:
    if days_out is None:
        return 'moderate'
    if days_out < 14:
        return 'minor'
    if days_out <= 28:
        return 'moderate'
    return 'severe'


# Return True when an injury spell is ongoing on the given date
def _is_spell_current(spell: dict, today: date) -> bool:
    end_date_str: Optional[str] = spell.get('end_date')
    if end_date_str is None:
        return True
    end_date = parse_date(end_date_str)
    return end_date is not None and end_date >= today


# --------------------------------------------------------------------------
# Transfermarkt sync service
# --------------------------------------------------------------------------

# Service for syncing Transfermarkt player identity, DOB, and injury data
class TransfermarktSyncService:

    # Set up the sync service with a Transfermarkt client
    def __init__(self, client: TransfermarktClient | None = None) -> None:
        self._client = client or TransfermarktClient()

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    # Sync player dates of birth for every squad in a league season
    def sync_league_player_dobs(
        self,
        league_code: str,
        season_year: int,
        triggered_by=None,
    ) -> dict[str, Any]:
        job = self._start_sync_job(
            resource_type=RESOURCE_SQUAD,
            resource_external_id=f'{league_code}/{season_year}',
            triggered_by=triggered_by,
        )

        records_processed = 0
        records_updated = 0
        error_count = 0
        raw_errors: list[str] = []

        try:
            teams = self._client.fetch_league_teams(league_code, season_year)
        except TransfermarktError as exc:
            _logger.warning('Transfermarkt: failed to fetch teams for %s/%s: %s', league_code, season_year, exc)
            return self._finish_failure(job, str(exc))

        for team in teams:
            tm_team_id = team['tm_team_id']
            try:
                squad_soup = self._client.fetch_squad_page(tm_team_id, season_year)
                squad = self._client.parse_squad(squad_soup)
            except TransfermarktError as exc:
                _logger.warning('Transfermarkt: squad fetch failed for team %s: %s', tm_team_id, exc)
                error_count += 1
                raw_errors.append(f'team {tm_team_id}: {exc}')
                continue

            for player_stub in squad:
                records_processed += 1
                try:
                    updated = self._upsert_player_identity_and_dob(player_stub)
                    if updated:
                        records_updated += 1
                except Exception as exc:
                    _logger.debug('Transfermarkt: player identity upsert failed for %s: %s', player_stub.get('tm_player_id'), exc)
                    error_count += 1
                    raw_errors.append(f'player {player_stub.get("tm_player_id")}: {exc}')

        summary = self._make_summary(
            metadata={'league': league_code, 'season': season_year, 'teams_seen': len(teams)}
        )
        summary['records_processed'] = records_processed
        summary['records_updated'] = records_updated
        summary['error_count'] = error_count
        summary['status'] = ProviderSyncStatus.PARTIAL if error_count else ProviderSyncStatus.SUCCESS
        summary['raw_error_summary'] = '; '.join(raw_errors[:RAW_ERROR_MAX_ITEMS])[:RAW_ERROR_MAX_LENGTH]

        self._finish_sync_job_success(job, summary)
        return {'job': job, 'summary': summary}

    # Sync current injury data for all active players in a club
    def sync_club_player_injuries(
        self,
        club,
        triggered_by=None,
    ) -> dict[str, Any]:
        from apps.clubs.models import ClubPlayer, ClubPlayerInjury

        job = self._start_sync_job(
            resource_type=RESOURCE_CLUB_INJURIES,
            resource_external_id=str(club.id),
            triggered_by=triggered_by,
        )

        records_processed = 0
        records_created = 0
        records_updated = 0
        error_count = 0
        raw_errors: list[str] = []

        today = date.today()

        club_players = (
            ClubPlayer.objects
            .filter(club=club, is_active=True, player__isnull=False)
            .select_related('player')
        )

        for cp in club_players:
            identity = PlayerExternalIdentity.objects.filter(
                player_id=cp.player_id,
                provider=PROVIDER,
            ).first()

            if identity is None:
                continue

            records_processed += 1
            tm_player_id = int(identity.external_id)

            try:
                injury_soup = self._client.fetch_injury_page(tm_player_id)
                spells = self._client.parse_injury_spells(injury_soup)
            except TransfermarktError as exc:
                _logger.warning(
                    'Transfermarkt: injury fetch failed for player %s (club_player %s): %s',
                    tm_player_id, cp.id, exc,
                )
                error_count += 1
                raw_errors.append(f'player {tm_player_id}: {exc}')
                continue

            # Pick the most recent ongoing spell from the parsed Transfermarkt rows
            current_spell: Optional[dict] = None
            for spell in spells:
                if _is_spell_current(spell, today):
                    current_spell = spell
                    break

            existing = ClubPlayerInjury.objects.filter(
                club_player=cp,
                is_current=True,
            ).first()

            if current_spell:
                injury_type = _classify_injury_type(current_spell.get('injury_type_raw', ''))
                severity = _classify_severity(current_spell.get('days_out'))
                start_date = parse_date(current_spell['start_date']) or today
                end_date_str = current_spell.get('end_date')
                estimated_return = parse_date(end_date_str) if end_date_str else None
                raw_label = current_spell.get('injury_type_raw', '')

                if existing:
                    changed = (
                        existing.injury_type != injury_type
                        or existing.severity != severity
                        or existing.estimated_return != estimated_return
                    )
                    if changed:
                        existing.injury_type = injury_type
                        existing.severity = severity
                        existing.estimated_return = estimated_return
                        existing.notes = raw_label
                        existing.save(update_fields=[
                            'injury_type', 'severity', 'estimated_return', 'notes', 'updated_at',
                        ])
                        records_updated += 1
                else:
                    ClubPlayerInjury.objects.create(
                        club_player=cp,
                        injury_type=injury_type,
                        severity=severity,
                        availability_status=ClubPlayerInjury.AvailabilityStatus.INJURED,
                        injured_at=start_date,
                        estimated_return=estimated_return,
                        notes=raw_label,
                        is_current=True,
                    )
                    records_created += 1
            else:
                # Resolve any stale current injury when the player is no longer injured
                if existing:
                    existing.resolve()
                    records_updated += 1

        summary = self._make_summary(
            metadata={'club_id': club.id, 'club_name': str(club)},
        )
        summary['records_processed'] = records_processed
        summary['records_created'] = records_created
        summary['records_updated'] = records_updated
        summary['error_count'] = error_count
        summary['status'] = ProviderSyncStatus.PARTIAL if error_count else ProviderSyncStatus.SUCCESS
        summary['raw_error_summary'] = '; '.join(raw_errors[:RAW_ERROR_MAX_ITEMS])[:RAW_ERROR_MAX_LENGTH]

        self._finish_sync_job_success(job, summary)
        return {'job': job, 'summary': summary}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    # Upsert a Transfermarkt player identity and backfill missing date of birth
    def _upsert_player_identity_and_dob(self, player_stub: dict) -> bool:
        tm_player_id = str(player_stub['tm_player_id'])
        player_name: str = player_stub['player_name']
        player_slug: str | None = player_stub.get('player_slug')

        with transaction.atomic():
            identity, _ = PlayerExternalIdentity.objects.get_or_create(
                provider=PROVIDER,
                external_id=tm_player_id,
                defaults={
                    'player': self._find_or_create_player(player_name),
                    'provider_display_name': player_name,
                    'provider_position': player_stub.get('position') or '',
                },
            )

            player: Player = identity.player

            if player.date_of_birth:
                return False

        # Fetch the DOB outside the transaction to avoid holding a lock during a network call
        try:
            profile_soup = self._client.fetch_player_profile(
                int(tm_player_id),
                player_slug=player_slug or 'player',
            )
            dob_str = self._client.parse_player_dob(profile_soup)
        except TransfermarktError as exc:
            _logger.debug('Transfermarkt: DOB fetch failed for player %s: %s', tm_player_id, exc)
            return False

        if not dob_str:
            return False

        parsed_dob: date | None = parse_date(dob_str)
        if parsed_dob is None:
            return False

        Player.objects.filter(pk=player.pk, date_of_birth__isnull=True).update(
            date_of_birth=parsed_dob,
        )
        return True

    # Find an existing player by name or create an inactive placeholder
    def _find_or_create_player(self, name: str) -> Player:
        player = Player.objects.filter(name__iexact=name).first()
        if player:
            return player
        return Player.objects.create(name=name, is_active=False)

    # Create a provider sync job for a Transfermarkt operation
    def _start_sync_job(self, resource_type, resource_external_id, triggered_by) -> ProviderSyncJob:
        return ProviderSyncJob.objects.create(
            provider=PROVIDER,
            resource_type=resource_type,
            resource_external_id=str(resource_external_id),
            status=ProviderSyncStatus.STARTED,
            triggered_by=triggered_by,
        )

    # Build the default summary structure for sync results
    @staticmethod
    def _make_summary(metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            'status': ProviderSyncStatus.SUCCESS,
            'records_processed': 0,
            'records_created': 0,
            'records_updated': 0,
            'error_count': 0,
            'raw_error_summary': '',
            'metadata': metadata or {},
        }

    # Mark a sync job as successful or partially successful
    @staticmethod
    def _finish_sync_job_success(job: ProviderSyncJob, summary: dict[str, Any]) -> None:
        job.status = summary.get('status', ProviderSyncStatus.SUCCESS)
        job.finished_at = timezone.now()
        job.records_processed = summary.get('records_processed', 0)
        job.records_created = summary.get('records_created', 0)
        job.records_updated = summary.get('records_updated', 0)
        job.error_count = summary.get('error_count', 0)
        job.raw_error_summary = summary.get('raw_error_summary', '')
        job.metadata = summary.get('metadata', {})
        job.save(update_fields=[
            'status',
            'finished_at',
            'records_processed',
            'records_created',
            'records_updated',
            'error_count',
            'raw_error_summary',
            'metadata',
        ])

    # Mark a sync job as failed and return a failed summary
    def _finish_failure(self, job: ProviderSyncJob, error_msg: str) -> dict:
        job.status = ProviderSyncStatus.FAILED
        job.raw_error_summary = error_msg[:RAW_ERROR_MAX_LENGTH]
        job.finished_at = timezone.now()
        job.save()
        return {
            'job': job,
            'summary': {
                'status': ProviderSyncStatus.FAILED,
                'records_processed': 0,
                'records_created': 0,
                'records_updated': 0,
                'error_count': 1,
                'raw_error_summary': error_msg[:RAW_ERROR_MAX_LENGTH],
                'metadata': {},
            },
        }