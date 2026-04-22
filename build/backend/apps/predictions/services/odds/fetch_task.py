from __future__ import annotations

import logging

from apps.predictions.services.odds.service import (
    OddsComparisonService,
    UPCOMING_ODDS_SPORT_KEY_TO_LEAGUE,
)

_logger = logging.getLogger(__name__)


def _parse_csv_setting(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def fetch_and_persist_odds() -> dict:
    from django.conf import settings

    service = OddsComparisonService()

    configured_sport_keys = _parse_csv_setting(
        getattr(settings, "ODDS_SNAPSHOT_SPORT_KEYS", "")
    )
    configured_bookmakers = _parse_csv_setting(
        getattr(settings, "ODDS_SNAPSHOT_BOOKMAKERS", "")
    )

    result = service.refresh_upcoming_fixture_odds(
        sport_keys=configured_sport_keys or tuple(UPCOMING_ODDS_SPORT_KEY_TO_LEAGUE.keys()),
        max_fixtures=getattr(settings, "ODDS_SNAPSHOT_MAX_FIXTURES_PER_RUN", 10),
        lookahead_hours=getattr(settings, "ODDS_SNAPSHOT_LOOKAHEAD_HOURS", 72),
        bookmakers=configured_bookmakers or None,
        persist=True,
    )

    if not result["sport_keys_processed"] and result["errors"]:
        first_error = result["errors"][0]["error"]
        _logger.error("Odds snapshot refresh failed: %s", first_error)
        raise RuntimeError(first_error)

    _logger.info(
        "Odds snapshot refresh completed: sport_keys=%s fixtures_seen=%s snapshots_created=%s requests_used=%s max_fixtures=%s lookahead_hours=%s bookmakers=%s",
        result["sport_keys_processed"],
        result["fixtures_seen"],
        result["snapshots_created"],
        result["requests_used"],
        result["max_fixtures"],
        result["lookahead_hours"],
        result["bookmakers_requested"],
    )
    return result