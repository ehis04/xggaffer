from __future__ import annotations

import logging
from datetime import date
from typing import Any

from django.db import transaction
from django.utils.dateparse import parse_date

from apps.players.models import Player, PlayerExternalIdentity, ProviderSyncJob, ProviderSyncStatus
from services.providers.transfermarkt.client import TransfermarktClient, TransfermarktError

_logger = logging.getLogger(__name__)

PROVIDER = 'transfermarkt'
RESOURCE_SQUAD = 'squad'
RESOURCE_PLAYER_PROFILE = 'player_profile'

# Season year offset: TM squads for the 2025/26 season are under season_id=2025.
# Transfermarkt uses the season start year.
_CURRENT_SEASON_OFFSET = 1


def _current_tm_season(now_year: int) -> int:
    return now_year - _CURRENT_SEASON_OFFSET


class TransfermarktSyncService:

    def __init__(self, client: TransfermarktClient | None = None) -> None:
        self._client = client or TransfermarktClient()

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def sync_league_player_dobs(
        self,
        league_code: str,
        season_year: int,
        triggered_by=None,
    ) -> dict[str, Any]:
        """
        Fetch every squad in a league/season from Transfermarkt, upsert
        PlayerExternalIdentity records, and backfill Player.date_of_birth
        for any existing Player record that is still missing a DOB.

        Returns a summary dict compatible with the sync_pipeline pattern.
        """
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

        summary = {
            'status': ProviderSyncStatus.SUCCESS if error_count == 0 else ProviderSyncStatus.SUCCESS,
            'records_processed': records_processed,
            'records_created': 0,
            'records_updated': records_updated,
            'error_count': error_count,
            'raw_error_summary': '; '.join(raw_errors[:10]),
            'metadata': {'league': league_code, 'season': season_year, 'teams_seen': len(teams)},
        }
        job.status = ProviderSyncStatus.SUCCESS
        job.records_processed = records_processed
        job.records_updated = records_updated
        job.error_count = error_count
        job.raw_error_summary = summary['raw_error_summary']
        job.metadata = summary['metadata']
        from django.utils import timezone
        job.finished_at = timezone.now()
        job.save()
        return {'job': job, 'summary': summary}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _upsert_player_identity_and_dob(self, player_stub: dict) -> bool:
        """
        Given a raw squad row from parse_squad(), ensure a PlayerExternalIdentity
        exists for this Transfermarkt player ID, and backfill date_of_birth on the
        linked Player if it is missing.

        Returns True if a Player.date_of_birth was set, False otherwise.
        """
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

        # DOB missing — fetch profile outside the identity transaction to avoid
        # holding the lock across a network call.
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

    def _find_or_create_player(self, name: str) -> Player:
        """
        Try to match an existing Player by exact name (case-insensitive).
        If no match, create a stub Player with is_active=False so that it can be
        reconciled with a real player later.
        """
        player = Player.objects.filter(name__iexact=name).first()
        if player:
            return player
        return Player.objects.create(name=name, is_active=False)

    def _start_sync_job(self, resource_type, resource_external_id, triggered_by) -> ProviderSyncJob:
        return ProviderSyncJob.objects.create(
            provider=PROVIDER,
            resource_type=resource_type,
            resource_external_id=str(resource_external_id),
            status=ProviderSyncStatus.STARTED,
            triggered_by=triggered_by,
        )

    def _finish_failure(self, job: ProviderSyncJob, error_msg: str) -> dict:
        from django.utils import timezone
        job.status = ProviderSyncStatus.FAILED
        job.raw_error_summary = error_msg[:500]
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
                'raw_error_summary': error_msg[:500],
                'metadata': {},
            },
        }
