from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.sync_pipeline.orchestration import trigger_publication_rebuild
from apps.sync_pipeline.selectors import get_source_health
from apps.sync_pipeline.services import (
    TRIGGERED_BY_CELERY,
    close_sync_run_failure,
    close_sync_run_success,
    open_sync_run,
    record_provider_request,
)
from apps.predictions.tasks import rebuild_predictions_publication_task
from apps.playerdata.tasks import refresh_understat_all_leagues_task
from common.constants import DatasetName, ProviderName
from common.provider_policy import acquire_task_lock, get_lock_key, is_budget_safe
from common.sync_constants import BUDGET_SAFETY_MARGIN

_logger = logging.getLogger(__name__)


@shared_task(name='apps.sync_pipeline.tasks.refresh_football_data_metadata_task', bind=True, max_retries=3)
def refresh_football_data_metadata_task(self):
    provider = ProviderName.FOOTBALL_DATA
    dataset = DatasetName.FIXTURES
    scope = 'metadata'
    lock_key = get_lock_key(provider, dataset, scope)

    with acquire_task_lock(lock_key, timeout_seconds=300):
        _check_football_data_budget()
        run = open_sync_run(provider, dataset, scope, TRIGGERED_BY_CELERY)
        try:
            from services.providers.football_data.sync import FootballDataSyncService
            sync = FootballDataSyncService()
            result = sync.sync_competitions()
            record_provider_request(provider, count=1)
            summary = result.get('summary', {})
            rows_seen = summary.get('records_processed', 0)
            rows_changed = summary.get('records_created', 0) + summary.get('records_updated', 0)
            close_sync_run_success(run, rows_seen=rows_seen, rows_changed=rows_changed)
            trigger_publication_rebuild('livefootball')
        except Exception as exc:
            close_sync_run_failure(run, error_summary=str(exc))
            raise self.retry(exc=exc, countdown=60)


@shared_task(name='apps.sync_pipeline.tasks.refresh_football_data_fixtures_task', bind=True, max_retries=3)
def refresh_football_data_fixtures_task(self):
    provider = ProviderName.FOOTBALL_DATA
    dataset = DatasetName.FIXTURES
    scope = 'all_competitions'
    lock_key = get_lock_key(provider, dataset, scope)

    with acquire_task_lock(lock_key, timeout_seconds=300):
        _check_football_data_budget()
        run = open_sync_run(provider, dataset, scope, TRIGGERED_BY_CELERY)
        try:
            from apps.livefootball.tasks import refresh_livefootball_from_football_data
            refresh_livefootball_from_football_data.delay()
            close_sync_run_success(run, rows_seen=0, rows_changed=0)
            trigger_publication_rebuild('livefootball')
        except Exception as exc:
            close_sync_run_failure(run, error_summary=str(exc))
            raise self.retry(exc=exc, countdown=60)


@shared_task(name='apps.sync_pipeline.tasks.refresh_football_data_scorers_squads_task', bind=True, max_retries=3)
def refresh_football_data_scorers_squads_task(self):
    provider = ProviderName.FOOTBALL_DATA
    dataset = DatasetName.SCORERS
    scope = 'all_competitions'
    lock_key = get_lock_key(provider, dataset, scope)

    with acquire_task_lock(lock_key, timeout_seconds=600):
        _check_football_data_budget()
        run = open_sync_run(provider, dataset, scope, TRIGGERED_BY_CELERY)
        try:
            from apps.livefootball.models import Competition
            from services.providers.football_data.sync import FootballDataSyncService

            sync = FootballDataSyncService()
            total_seen = 0
            total_changed = 0

            for competition in Competition.objects.filter(
                provider=ProviderName.FOOTBALL_DATA,
            ).exclude(external_id='').exclude(external_id=None):
                try:
                    result = sync.sync_competition_scorers(
                        competition_external_id=competition.external_id,
                    )
                    record_provider_request(provider, count=1)
                    s = result.get('summary', {})
                    total_seen += s.get('records_processed', 0)
                    total_changed += s.get('records_created', 0) + s.get('records_updated', 0)
                except Exception as exc:
                    _logger.warning('Scorers sync failed for competition %s: %s', competition.external_id, exc)

            close_sync_run_success(run, rows_seen=total_seen, rows_changed=total_changed)
            trigger_publication_rebuild('livefootball')
        except Exception as exc:
            close_sync_run_failure(run, error_summary=str(exc))
            raise self.retry(exc=exc, countdown=60)


@shared_task(name='apps.sync_pipeline.tasks.refresh_understat_cycle_task', bind=True, max_retries=3)
def refresh_understat_cycle_task(self):
    provider = ProviderName.UNDERSTAT
    dataset = DatasetName.PLAYER_STATS
    scope = 'all_leagues'
    lock_key = get_lock_key(provider, dataset, scope)

    with acquire_task_lock(lock_key, timeout_seconds=300):
        run = open_sync_run(provider, dataset, scope, TRIGGERED_BY_CELERY)
        try:
            rebuild_predictions_publication_task.delay()
            refresh_understat_all_leagues_task.delay()
            close_sync_run_success(run, rows_seen=0, rows_changed=0)
        except Exception as exc:
            close_sync_run_failure(run, error_summary=str(exc))
            raise self.retry(exc=exc, countdown=60)


def _kill_orphaned_chrome():
    """Kill any Chrome/Chromedriver processes left over from a failed WhoScored session."""
    import subprocess
    try:
        subprocess.run(
            ['pkill', '-f', 'chrome'],
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass


@shared_task(name='apps.sync_pipeline.tasks.refresh_whoscored_cycle_task', bind=True, max_retries=1)
def refresh_whoscored_cycle_task(self):
    provider = ProviderName.WHOSCORED
    dataset = DatasetName.PLAYER_STATS
    scope = 'all_leagues'
    lock_key = get_lock_key(provider, dataset, scope)

    SUPPORTED_LEAGUES = ['EPL', 'La_Liga', 'Bundesliga', 'Serie_A', 'Ligue_1']
    WHOSCORED_DATASETS = ['matches', 'players', 'teams']
    current_season = str(timezone.now().year - 1)

    with acquire_task_lock(lock_key, timeout_seconds=3600):
        run = open_sync_run(provider, dataset, scope, TRIGGERED_BY_CELERY)
        total_seen = 0

        try:
            from apps.predictions.data_collection.pipelines.collect_source_dataset import collect_source_dataset
            from apps.predictions.data_collection.core.enums import SOURCE_WHOSCORED

            for league in SUPPORTED_LEAGUES:
                league_client = None
                try:
                    from apps.predictions.data_collection.extractors.whoscored.matches import get_whoscored_client
                    league_client = get_whoscored_client(league, current_season)
                except Exception as exc:
                    _logger.warning('WhoScored client init failed for %s: %s', league, exc)

                for ds in WHOSCORED_DATASETS:
                    try:
                        result = collect_source_dataset(
                            source=SOURCE_WHOSCORED,
                            dataset=ds,
                            league=league,
                            season=current_season,
                        )
                        record_provider_request(provider, count=1)
                        canonical_df = result.get('canonical_df')
                        total_seen += len(canonical_df) if canonical_df is not None and not canonical_df.empty else 0
                    except Exception as exc:
                        _logger.warning('WhoScored collect failed for %s/%s/%s: %s', league, ds, current_season, exc)

                # Explicitly close the browser after each league to prevent memory accumulation
                if league_client is not None:
                    try:
                        driver = getattr(league_client, '_driver', None)
                        if driver is not None:
                            driver.quit()
                    except Exception:
                        pass
                _kill_orphaned_chrome()

            close_sync_run_success(run, rows_seen=total_seen, rows_changed=total_seen)
            trigger_publication_rebuild('predictions')
        except Exception as exc:
            _kill_orphaned_chrome()
            close_sync_run_failure(run, error_summary=str(exc))


@shared_task(name='apps.sync_pipeline.tasks.refresh_sofascore_cycle_task', bind=True, max_retries=1)
def refresh_sofascore_cycle_task(self):
    provider = ProviderName.SOFASCORE
    dataset = DatasetName.PLAYER_STATS
    scope = 'all_leagues'

    health = get_source_health(provider)
    if health and not health.session_valid:
        _logger.warning('SofaScore session invalid. Run refresh_sofascore_session command.')
        return

    lock_key = get_lock_key(provider, dataset, scope)

    SUPPORTED_LEAGUES = ['EPL', 'La_Liga', 'Bundesliga', 'Serie_A', 'Ligue_1']
    SOFASCORE_DATASETS = ['matches', 'players', 'teams']
    current_season = str(timezone.now().year - 1)

    with acquire_task_lock(lock_key, timeout_seconds=1800):
        run = open_sync_run(provider, dataset, scope, TRIGGERED_BY_CELERY)
        total_seen = 0
        session_expired = False

        try:
            from apps.predictions.data_collection.pipelines.collect_source_dataset import collect_source_dataset
            from apps.predictions.data_collection.core.enums import SOURCE_SOFASCORE
            from apps.sync_pipeline.services import mark_provider_session_invalid

            for league in SUPPORTED_LEAGUES:
                if session_expired:
                    break
                for ds in SOFASCORE_DATASETS:
                    try:
                        result = collect_source_dataset(
                            source=SOURCE_SOFASCORE,
                            dataset=ds,
                            league=league,
                            season=current_season,
                        )
                        record_provider_request(provider, count=1)
                        canonical_df = result.get('canonical_df')
                        total_seen += len(canonical_df) if canonical_df is not None and not canonical_df.empty else 0
                    except Exception as exc:
                        exc_str = str(exc).lower()
                        if any(tok in exc_str for tok in ('401', '403', 'session', 'unauthorized', 'forbidden')):
                            _logger.warning('SofaScore session expired during %s/%s: %s', league, ds, exc)
                            mark_provider_session_invalid(provider)
                            close_sync_run_failure(run, f'SESSION_EXPIRED: {exc}')
                            session_expired = True
                            break
                        _logger.warning('SofaScore collect failed for %s/%s/%s: %s', league, ds, current_season, exc)

            if not session_expired:
                close_sync_run_success(run, rows_seen=total_seen, rows_changed=total_seen)
                trigger_publication_rebuild('predictions')
        except Exception as exc:
            close_sync_run_failure(run, error_summary=str(exc))


@shared_task(name='apps.sync_pipeline.tasks.refresh_native_stats_cycle_task', bind=True, max_retries=3)
def refresh_native_stats_cycle_task(self):
    # SyncRun tracking is owned by refresh_livefootball_native_stats — this task
    # just prevents duplicate dispatches via the lock and keeps Beat as the sole scheduler.
    lock_key = get_lock_key(ProviderName.NATIVE_STATS, DatasetName.NATIVE_STATS_OVERVIEW, 'homepage')
    try:
        with acquire_task_lock(lock_key, timeout_seconds=300):
            from apps.livefootball.tasks import refresh_livefootball_native_stats
            refresh_livefootball_native_stats.apply_async(queue='queue_native_stats')
    except Exception as exc:
        _logger.error('refresh_native_stats_cycle_task failed to dispatch: %s', exc)
        raise self.retry(exc=exc, countdown=60)


@shared_task(name='apps.sync_pipeline.tasks.refresh_transfermarkt_cycle_task', bind=True, max_retries=2)
def refresh_transfermarkt_cycle_task(self):
    """
    Weekly sync of player DOBs from Transfermarkt across all supported leagues.
    Upserts PlayerExternalIdentity records and backfills Player.date_of_birth
    for any player whose DOB is currently null.
    """
    provider = ProviderName.TRANSFERMARKT
    dataset = DatasetName.PLAYER_STATS
    scope = 'all_leagues'
    lock_key = get_lock_key(provider, dataset, scope)

    SUPPORTED_LEAGUES = ['EPL', 'La_Liga', 'Bundesliga', 'Serie_A', 'Ligue_1']
    season_year = timezone.now().year - 1

    with acquire_task_lock(lock_key, timeout_seconds=3600):
        run = open_sync_run(provider, dataset, scope, TRIGGERED_BY_CELERY)
        total_seen = 0
        total_updated = 0
        try:
            from services.providers.transfermarkt.sync import TransfermarktSyncService
            sync = TransfermarktSyncService()

            for league in SUPPORTED_LEAGUES:
                try:
                    result = sync.sync_league_player_dobs(league, season_year)
                    record_provider_request(provider, count=1)
                    s = result.get('summary', {})
                    total_seen += s.get('records_processed', 0)
                    total_updated += s.get('records_updated', 0)
                except Exception as exc:
                    _logger.warning('Transfermarkt sync failed for league %s: %s', league, exc)

            close_sync_run_success(run, rows_seen=total_seen, rows_changed=total_updated)
        except Exception as exc:
            close_sync_run_failure(run, str(exc))
            raise self.retry(exc=exc, countdown=300)


@shared_task(name='apps.sync_pipeline.tasks.aggregate_sync_health_task')
def aggregate_sync_health_task():
    from apps.sync_pipeline.models import SourceHealth, SyncRun
    from datetime import timedelta
    from common.constants import SyncStatus

    threshold = getattr(settings, 'PIPELINE_DEGRADED_THRESHOLD', 3)
    degraded = SourceHealth.objects.filter(consecutive_failures__gte=threshold)
    for h in degraded:
        _logger.warning(
            'Provider %s has %d consecutive failures — DEGRADED',
            h.provider,
            h.consecutive_failures,
        )

    stuck_cutoff = timezone.now() - timedelta(hours=2)
    stuck_runs = SyncRun.objects.filter(
        status=SyncStatus.RUNNING,
        started_at__lt=stuck_cutoff,
    )
    stuck_count = stuck_runs.update(
        status=SyncStatus.FAILED,
        finished_at=timezone.now(),
        error_summary='Auto-marked FAILED by aggregate_sync_health_task: stuck > 2h.',
    )
    if stuck_count:
        _logger.warning(
            'aggregate_sync_health_task: marked %d stuck RUNNING runs as FAILED', stuck_count
        )

def _check_football_data_budget():
    health = get_source_health(ProviderName.FOOTBALL_DATA)
    daily_limit = getattr(settings, 'FOOTBALL_DATA_DAILY_REQUEST_LIMIT', 100)
    if health and not is_budget_safe(health.requests_used, daily_limit, BUDGET_SAFETY_MARGIN):
        raise RuntimeError(
            f'football_data budget exhausted: {health.requests_used}/{daily_limit} used'
        )

@shared_task(name='apps.sync_pipeline.tasks.refresh_odds_snapshots_task', bind=True, max_retries=1)
def refresh_odds_snapshots_task(self):
    from django.conf import settings as _settings
    from common.constants import DatasetName, ProviderName

    if not getattr(_settings, 'ODDS_API_ENABLED', False):
        _logger.info('ODDS_API_ENABLED=False — skipping odds refresh')
        return

    daily_limit = getattr(_settings, 'ODDS_API_DAILY_REQUEST_LIMIT', 15)
    health = get_source_health(ProviderName.THE_ODDS_API)
    if health and not is_budget_safe(health.requests_used, daily_limit, BUDGET_SAFETY_MARGIN):
        run = open_sync_run(
            ProviderName.THE_ODDS_API, DatasetName.ODDS, 'upcoming_fixtures',
            triggered_by=TRIGGERED_BY_CELERY,
        )
        close_sync_run_failure(run, 'BUDGET_EXHAUSTED')
        _logger.warning('Odds API budget exhausted — skipping refresh')
        return

    lock_key = get_lock_key(ProviderName.THE_ODDS_API, DatasetName.ODDS, 'upcoming_fixtures')
    with acquire_task_lock(lock_key, timeout_seconds=3600):
        run = open_sync_run(
            ProviderName.THE_ODDS_API, DatasetName.ODDS, 'upcoming_fixtures',
            triggered_by=TRIGGERED_BY_CELERY,
        )
        try:
            from apps.predictions.services.odds.fetch_task import fetch_and_persist_odds
            result = fetch_and_persist_odds()
            record_provider_request(ProviderName.THE_ODDS_API, count=result.get('requests_used', 1))
            close_sync_run_success(
                run,
                rows_seen=result.get('fixtures_seen', 0),
                rows_changed=result.get('snapshots_created', 0),
            )
        except Exception as exc:
            close_sync_run_failure(run, str(exc))
            raise