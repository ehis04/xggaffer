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


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def scrape_all_leagues(self):
    try:
        logger.info("Starting scheduled scrape of all leagues")

        current_year = timezone.now().year
        understat_season = str(_latest_understat_season_year(current_year))
        sofascore_season = str(current_year - 1)

        # Understat and Sofascore do not always expose the same active season key.
        _run_collection(
            [SOURCE_UNDERSTAT],
            ALL_DATASETS,
            SUPPORTED_LEAGUES,
            [understat_season],
            "scrape_all_leagues",
        )
        _run_collection(
            [SOURCE_SOFASCORE],
            ALL_DATASETS,
            SUPPORTED_LEAGUES,
            [sofascore_season],
            "scrape_all_leagues",
        )

        logger.info("Scheduled scrape completed successfully")
        _check_recent_scrapes_and_alert()
    except Exception as exc:
        logger.error(f"Scraping task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def scrape_specific_league(league, season):
    try:
        logger.info(f"Scraping {league} {season}")
        _run_collection(ALL_SOURCES, ALL_DATASETS, [league], [season], f"scrape_specific_league:{league}/{season}")
        logger.info(f"Successfully scraped {league} {season}")
    except Exception as e:
        logger.error(f"Failed to scrape {league} {season}: {e}", exc_info=True)
        raise


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
