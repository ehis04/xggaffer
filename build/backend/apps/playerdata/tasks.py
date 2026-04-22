from __future__ import annotations

import logging

from celery import shared_task

from apps.playerdata.publication import run_playerdata_publication
from apps.sync_pipeline.services import (
    TRIGGERED_BY_CELERY,
    close_sync_run_failure,
    close_sync_run_success,
    open_sync_run,
    record_provider_request,
)
from common.constants import DatasetName, ProviderName

_logger = logging.getLogger(__name__)

SUPPORTED_LEAGUES = ['EPL', 'La_Liga', 'Bundesliga', 'Serie_A', 'Ligue_1']
CURRENT_SEASON = '2024'


@shared_task(name='apps.playerdata.tasks.refresh_understat_all_leagues_task', bind=True, max_retries=3)
def refresh_understat_all_leagues_task(self):
    from services.providers.understat.sync import sync_understat_league_season

    total_seen = 0
    total_changed = 0
    errors = []

    for league_code in SUPPORTED_LEAGUES:
        run = open_sync_run(
            ProviderName.UNDERSTAT,
            DatasetName.LEAGUE_STATS,
            f'{league_code}/{CURRENT_SEASON}',
            triggered_by=TRIGGERED_BY_CELERY,
        )
        try:
            result = sync_understat_league_season(
                league_code=league_code,
                season_label=CURRENT_SEASON,
            )
            record_provider_request(ProviderName.UNDERSTAT, count=1)
            summary = result.get('summary', {})
            seen = summary.get('records_processed', 0)
            changed = summary.get('records_created', 0) + summary.get('records_updated', 0)
            total_seen += seen
            total_changed += changed
            close_sync_run_success(run, rows_seen=seen, rows_changed=changed)
        except Exception as exc:
            _logger.warning('Understat sync failed for %s/%s: %s', league_code, CURRENT_SEASON, exc)
            close_sync_run_failure(run, str(exc))
            errors.append(f'{league_code}: {exc}')

    if len(errors) < len(SUPPORTED_LEAGUES):
        rebuild_playerdata_publication_task.delay()
    else:
        _logger.error('All understat league syncs failed: %s', errors)


@shared_task(name='apps.playerdata.tasks.rebuild_playerdata_publication_task', bind=True)
def rebuild_playerdata_publication_task(self):
    try:
        run_playerdata_publication('all')
    except Exception as exc:
        _logger.error('rebuild_playerdata_publication_task failed: %s', exc)