from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings

from apps.livefootball.models import NativeStatsSnapshot
from apps.livefootball.publication import run_livefootball_publication
from apps.livefootball.services.native_stats import (
    fetch_native_stats_homepage_payload,
    persist_native_stats_snapshot,
)
from apps.sync_pipeline.services import (
    TRIGGERED_BY_CELERY,
    close_sync_run_failure,
    close_sync_run_success,
    open_sync_run,
    record_provider_request,
)
from common.constants import DatasetName, ProviderName
from common.utils import utcnow

_logger = logging.getLogger(__name__)


@shared_task(name='apps.livefootball.tasks.refresh_livefootball_from_football_data', bind=True, max_retries=3)
def refresh_livefootball_from_football_data(self):
    from services.providers.football_data.sync import FootballDataSyncService

    if not getattr(settings, 'FOOTBALL_DATA_ENABLED', True):
        _logger.info('FOOTBALL_DATA_ENABLED=False — skipping livefootball sync')
        return

    sync = FootballDataSyncService()
    total_seen = 0
    total_changed = 0

    run = open_sync_run(
        ProviderName.FOOTBALL_DATA,
        DatasetName.FIXTURES,
        'livefootball',
        triggered_by=TRIGGERED_BY_CELERY,
    )

    try:
        competitions_result = sync.sync_competitions(triggered_by=None)
        record_provider_request(ProviderName.FOOTBALL_DATA, count=1)
        summary = competitions_result.get('summary', {})
        total_seen += summary.get('records_processed', 0)
        total_changed += summary.get('records_created', 0) + summary.get('records_updated', 0)

        from apps.livefootball.models import Competition
        for competition in Competition.objects.filter(provider=ProviderName.FOOTBALL_DATA):
            ext_id = competition.external_id
            if not ext_id:
                continue

            try:
                fixtures_result = sync.sync_competition_fixtures(
                    competition_external_id=ext_id,
                    triggered_by=None,
                )
                record_provider_request(ProviderName.FOOTBALL_DATA, count=1)
                s = fixtures_result.get('summary', {})
                total_seen += s.get('records_processed', 0)
                total_changed += s.get('records_created', 0) + s.get('records_updated', 0)
            except Exception as exc:
                _logger.warning('fixtures sync failed for %s: %s', ext_id, exc)

            try:
                table_result = sync.sync_competition_table(
                    competition_external_id=ext_id,
                    triggered_by=None,
                )
                record_provider_request(ProviderName.FOOTBALL_DATA, count=1)
                s = table_result.get('summary', {})
                total_seen += s.get('records_processed', 0)
                total_changed += s.get('records_created', 0) + s.get('records_updated', 0)
            except Exception as exc:
                _logger.warning('table sync failed for %s: %s', ext_id, exc)

            try:
                scorers_result = sync.sync_competition_scorers(
                    competition_external_id=ext_id,
                    triggered_by=None,
                )
                record_provider_request(ProviderName.FOOTBALL_DATA, count=1)
                s = scorers_result.get('summary', {})
                total_seen += s.get('records_processed', 0)
                total_changed += s.get('records_created', 0) + s.get('records_updated', 0)
            except Exception as exc:
                _logger.warning('scorers sync failed for %s: %s', ext_id, exc)

        close_sync_run_success(run, rows_seen=total_seen, rows_changed=total_changed)
        rebuild_livefootball_publication.delay()

    except Exception as exc:
        close_sync_run_failure(run, str(exc))
        raise self.retry(exc=exc)


@shared_task(name='apps.livefootball.tasks.refresh_livefootball_native_stats', bind=True, max_retries=2)
def refresh_livefootball_native_stats(self):
    run = open_sync_run(
        ProviderName.NATIVE_STATS,
        DatasetName.NATIVE_STATS_OVERVIEW,
        'homepage',
        triggered_by=TRIGGERED_BY_CELERY,
    )

    try:
        payload = fetch_native_stats_homepage_payload()
        persist_native_stats_snapshot(NativeStatsSnapshot.SURFACE_HOMEPAGE, payload)

        rows_seen = sum(
            len(v) if isinstance(v, list) else (1 if v else 0)
            for v in payload.values()
        )
        close_sync_run_success(run, rows_seen=rows_seen, rows_changed=rows_seen)
        rebuild_livefootball_publication.delay()

    except Exception as exc:
        close_sync_run_failure(run, str(exc))
        raise self.retry(exc=exc)


@shared_task(name='apps.livefootball.tasks.rebuild_livefootball_publication', bind=True)
def rebuild_livefootball_publication(self):
    try:
        run_livefootball_publication(source_max_fetched_at=utcnow())
    except Exception as exc:
        _logger.error('Livefootball publication rebuild failed: %s', exc)