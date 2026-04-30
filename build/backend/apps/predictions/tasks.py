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

@shared_task(name='apps.predictions.tasks.refresh_elo_ratings_task', bind=True)
def refresh_elo_ratings_task(self):
    from apps.predictions.ml.engines.compute_elo import compute, DEFAULT_OUTPUT
    from apps.predictions.ml.engines.elo import DEFAULT_K_FACTOR, DEFAULT_HOME_ADVANTAGE
    from apps.predictions.ml.features.rolling import ALL_LEAGUES, ALL_SEASONS
    from apps.predictions.models import populate_elo_from_csv

    try:
        _logger.info('refresh_elo_ratings_task: computing ELO for %d leagues x %d seasons', len(ALL_LEAGUES), len(ALL_SEASONS))
        compute(
            leagues=ALL_LEAGUES,
            seasons=ALL_SEASONS,
            k_factor=DEFAULT_K_FACTOR,
            home_advantage=DEFAULT_HOME_ADVANTAGE,
            output_path=str(DEFAULT_OUTPUT),
        )
        _logger.info('refresh_elo_ratings_task: ELO CSV written, syncing to DB')
        stats = populate_elo_from_csv(str(DEFAULT_OUTPUT))
        _logger.info('refresh_elo_ratings_task: DB sync complete — %s', stats)
    except Exception as exc:
        _logger.error('refresh_elo_ratings_task failed: %s', exc, exc_info=True)
        raise


@shared_task(name='apps.predictions.tasks.compute_odds_accuracy_task', bind=True)
def compute_odds_accuracy_task(self):
    from django.core.management import call_command
    from common.utils import current_football_season
    season = current_football_season()
    try:
        call_command('compute_odds_accuracy', league='all', season=season)
        _logger.info('compute_odds_accuracy_task: completed for all leagues season=%s', season)
    except Exception as exc:
        _logger.error('compute_odds_accuracy_task failed: %s', exc, exc_info=True)


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
        from common.cache_keys import clear_surface_cache
        cleared = clear_surface_cache("odds")
        _logger.info('refresh_upcoming_fixture_odds_task: odds cache cleared, deleted=%s', cleared)

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

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

_logger = logging.getLogger(__name__)

POST_MATCH_DELAY_HOURS = 3
RESOLUTION_BATCH_SIZE = 100
FINAL_MATCH_STATUSES = {"final", "finished", "ft", "full_time", "full-time"}


def _derive_outcome(home_score: int | None, away_score: int | None) -> str | None:
    if home_score is None or away_score is None:
        return None
    if home_score > away_score:
        return "H"
    if away_score > home_score:
        return "A"
    return "D"


def _find_fixture(home_team: str, away_team: str, league_code: str, CompetitionFixture):
    """
    Locate a finished fixture for these teams.

    Three passes in order of confidence:
      1. Exact team name match + competition code filter
      2. Exact team name match, no competition filter (handles league code mismatches)
      3. icontains on both names (handles Understat short names vs full fixture names,
         e.g. 'Leeds' → 'Leeds United')

    In each pass we take the most recently finished fixture so that stale test records
    made against historical matchups still resolve correctly.
    """
    from apps.predictions.utils.league_codes import to_competition_code
    from django.db.models import Q

    competition_code = to_competition_code(league_code)
    finished_filter = Q(
        status__in=[s.upper() for s in FINAL_MATCH_STATUSES]
    ) | Q(
        status__in=list(FINAL_MATCH_STATUSES)
    )

    base_finished = CompetitionFixture.objects.filter(finished_filter)

    # Pass 1: exact names + competition code
    if competition_code:
        fixture = base_finished.filter(
            home_team_name=home_team,
            away_team_name=away_team,
            competition__code=competition_code,
        ).order_by("-kickoff_at").first()
        if fixture:
            return fixture

    # Pass 2: exact names, any competition
    fixture = base_finished.filter(
        home_team_name=home_team,
        away_team_name=away_team,
    ).order_by("-kickoff_at").first()
    if fixture:
        return fixture

    # Pass 3: icontains — Understat short names vs football-data.org full names
    fixture = base_finished.filter(
        home_team_name__icontains=home_team,
        away_team_name__icontains=away_team,
    ).order_by("-kickoff_at").first()
    return fixture


@shared_task(name="apps.predictions.tasks.resolve_prediction_results", bind=True, max_retries=3)
def resolve_prediction_results(self) -> int:
    from apps.predictions.models import PredictionRecord
    from apps.livefootball.models import CompetitionFixture

    cutoff = timezone.now() - timedelta(hours=POST_MATCH_DELAY_HOURS)

    unresolved = list(
        PredictionRecord.objects.filter(
            actual_result__isnull=True,
            predicted_at__lt=cutoff,
        )[:RESOLUTION_BATCH_SIZE]
    )

    resolved_count = 0

    for record in unresolved:
        try:
            fixture = _find_fixture(
                record.home_team, record.away_team, record.league_code, CompetitionFixture
            )

            if fixture is None:
                continue

            actual = _derive_outcome(fixture.home_score, fixture.away_score)
            if actual is None:
                continue

            PredictionRecord.objects.filter(pk=record.pk).update(
                actual_result=actual,
                resolved_at=timezone.now(),
                correct=(actual == record.predicted_outcome),
            )
            resolved_count += 1

        except Exception as exc:
            _logger.exception(
                "Resolution failed for PredictionRecord pk=%s: %s", record.pk, exc
            )
            continue

    _logger.info("resolve_prediction_results: resolved %d records", resolved_count)
    return resolved_count
