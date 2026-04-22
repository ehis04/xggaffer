import logging

from celery import shared_task
from django.core.mail import mail_admins
from django.utils import timezone

from data_collection.core.enums import (
    DATASET_MATCHES,
    DATASET_PLAYERS,
    DATASET_TEAMS,
    DATASET_TEAM_SUMMARIES,
    SOURCE_UNDERSTAT,
    SOURCE_SOFASCORE,
)
from data_collection.pipelines.collect_source_dataset import collect_source_dataset

from .models import ScrapeLog

logger = logging.getLogger(__name__)

SUPPORTED_LEAGUES = ["EPL", "La_Liga", "Serie_A", "Bundesliga", "Ligue_1"]
ALL_SOURCES = [SOURCE_UNDERSTAT, SOURCE_SOFASCORE]
ALL_DATASETS = [DATASET_MATCHES, DATASET_PLAYERS, DATASET_TEAMS, DATASET_TEAM_SUMMARIES]


def _is_supported_source_dataset(source: str, dataset: str) -> bool:
    if source == SOURCE_SOFASCORE and dataset == DATASET_TEAM_SUMMARIES:
        return False
    return True


def _run_collection(sources, datasets, leagues, seasons, task_label):
    created = updated = failed = skipped = 0

    for source in sources:
        for dataset in datasets:
            if not _is_supported_source_dataset(source, dataset):
                skipped += len(leagues) * len(seasons)
                logger.info(
                    f"[{task_label}] Skipping unsupported combination "
                    f"{source}/{dataset} for {len(leagues)} leagues x {len(seasons)} seasons"
                )
                continue
            for league in leagues:
                for season in seasons:
                    log = ScrapeLog.objects.create(
                        scraper_name=source,
                        target=f"{league} {season} {dataset}",
                        status="running",
                        metadata={"source": source, "dataset": dataset, "league": league, "season": season},
                    )
                    try:
                        result = collect_source_dataset(source=source, dataset=dataset, league=league, season=season)
                        result_dict = result if isinstance(result, dict) else (vars(result) if hasattr(result, "__dict__") else {})

                        log.matches_found = result_dict.get("raw_row_count") or result_dict.get("raw_rows") or 0
                        log.matches_created = result_dict.get("canonical_row_count") or result_dict.get("canonical_rows") or 0
                        log.status = "success"
                        log.completed_at = timezone.now()
                        log.save()
                        created += 1
                    except Exception as exc:
                        log.status = "failed"
                        log.error_message = str(exc)
                        log.completed_at = timezone.now()
                        log.save()
                        failed += 1
                        logger.error(f"[{task_label}] Failed {source}/{dataset}/{league}/{season}: {exc}", exc_info=True)

    logger.info(f"[{task_label}] Done — succeeded={created} failed={failed} skipped={skipped}")
    return created, updated, failed


def _latest_understat_season_year(now_year: int | None = None) -> int:
    """
    Understat season pages are keyed by season start year and usually lag the
    calendar year. In early 2026, the latest stable season key is 2025.
    """
    year = now_year if now_year is not None else timezone.now().year
    return year - 1

@shared_task
def backfill_historical_data():
    try:
        logger.info("Starting historical data backfill")
        current_year = timezone.now().year

        understat_base = _latest_understat_season_year(current_year)
        understat_seasons = [str(understat_base - 2), str(understat_base - 1), str(understat_base)]
        sofascore_base = current_year - 1
        sofascore_seasons = [str(sofascore_base - 2), str(sofascore_base - 1), str(sofascore_base)]

        _run_collection(
            [SOURCE_UNDERSTAT],
            ALL_DATASETS,
            SUPPORTED_LEAGUES,
            understat_seasons,
            "backfill_historical_data",
        )
        _run_collection(
            [SOURCE_SOFASCORE],
            ALL_DATASETS,
            SUPPORTED_LEAGUES,
            sofascore_seasons,
            "backfill_historical_data",
        )
        logger.info("Historical data backfill completed")
    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)
        raise


def _check_recent_scrapes_and_alert():
    recent_logs = ScrapeLog.objects.order_by('-started_at')[:3]

    if len(recent_logs) < 3:
        return

    failed_count = sum(1 for log in recent_logs if log.status == 'failed')

    if failed_count >= 3:
        subject = '⚠️ Multiple scraping failures detected'
        message = f"""
        The last 3 scraping attempts have failed.

        Latest failures:
        {chr(10).join(f"- {log.started_at}: {log.error_message}" for log in recent_logs)}

        Please investigate immediately.
        """

        mail_admins(subject, message, fail_silently=True)
        logger.critical("Multiple scraping failures - admins notified")

_logger = logging.getLogger(__name__)


@shared_task(name='apps.predictions.tasks.promote_model_artefact_task', bind=True)
def promote_model_artefact_task(self, algorithm: str, path: str, trained_at_iso: str):
    from apps.predictions.publication import promote_model_artefact
    from django.utils.dateparse import parse_datetime

    trained_at = parse_datetime(trained_at_iso)
    if not trained_at:
        _logger.error('Invalid trained_at_iso: %s', trained_at_iso)
        return

    record = promote_model_artefact(algorithm=algorithm, path=path, trained_at=trained_at)
    _logger.info('promote_model_artefact_task: promoted %s', record)


@shared_task(name='apps.predictions.tasks.rebuild_predictions_publication_task', bind=True)
def rebuild_predictions_publication_task(self):
    from apps.predictions.publication import run_predictions_publication
    try:
        run_predictions_publication()
    except Exception as exc:
        _logger.error('rebuild_predictions_publication_task failed: %s', exc)

@shared_task(name='apps.predictions.tasks.refresh_upcoming_fixture_odds_task', bind=True, max_retries=1)
def refresh_upcoming_fixture_odds_task(self, sport_keys=None, max_fixtures=None):
    from apps.predictions.services.odds.service import (
        OddsComparisonService,
        UPCOMING_ODDS_SPORT_KEY_TO_LEAGUE,
    )

    service = OddsComparisonService()

    selected_sport_keys = tuple(sport_keys or UPCOMING_ODDS_SPORT_KEY_TO_LEAGUE.keys())

    try:
        result = service.refresh_upcoming_fixture_odds(
            sport_keys=selected_sport_keys,
            max_fixtures=max_fixtures,
            persist=True,
        )
        _logger.info(
            'refresh_upcoming_fixture_odds_task completed: sport_keys=%s fixtures_seen=%s snapshots_created=%s requests_used=%s',
            result.get('sport_keys_processed', []),
            result.get('fixtures_seen', 0),
            result.get('snapshots_created', 0),
            result.get('requests_used', 0),
        )
        return result
    except Exception as exc:
        _logger.error('refresh_upcoming_fixture_odds_task failed: %s', exc, exc_info=True)
        raise


@shared_task(name='apps.predictions.tasks.refresh_fixture_odds_snapshot_task', bind=True, max_retries=1)
def refresh_fixture_odds_snapshot_task(self, fixture_identity: dict):
    from apps.predictions.services.odds.client import DEFAULT_REGIONS
    from apps.predictions.services.odds.service import OddsComparisonService

    required_fields = ['sport_key', 'league', 'season', 'home_team', 'away_team']
    missing_fields = [field for field in required_fields if not fixture_identity.get(field)]

    if missing_fields:
        raise ValueError(
            'refresh_fixture_odds_snapshot_task requires: '
            + ', '.join(required_fields)
            + f'. Missing: {", ".join(missing_fields)}'
        )

    service = OddsComparisonService()

    try:
        result = service.refresh_fixture_odds_snapshot(
            sport_key=fixture_identity['sport_key'],
            league=fixture_identity['league'],
            season=fixture_identity['season'],
            home_team=fixture_identity['home_team'],
            away_team=fixture_identity['away_team'],
            external_fixture_id=fixture_identity.get('external_fixture_id'),
            commence_time=fixture_identity.get('commence_time'),
            bookmakers=fixture_identity.get('bookmakers'),
            regions=fixture_identity.get('regions') or DEFAULT_REGIONS,
        )
        _logger.info(
            'refresh_fixture_odds_snapshot_task completed: fixture=%s snapshot_id=%s quote_count=%s',
            result.get('external_fixture_id'),
            result.get('snapshot_id'),
            result.get('bookmaker_quote_count'),
        )
        return result
    except Exception as exc:
        _logger.error('refresh_fixture_odds_snapshot_task failed: %s', exc, exc_info=True)
        raise