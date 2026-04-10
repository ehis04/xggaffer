import logging
from typing import Any, Iterable, Optional

from services.providers.understat.client import UnderstatClient

logger = logging.getLogger(__name__)


def fetch_understat_matches(league: str, season: str) -> list[dict[str, Any]]:
    """Fetch match data for a league/season using the internal Understat client."""
    client = UnderstatClient()
    try:
        league_data = client.get_league_teams(league, season)
    except Exception as exc:
        logger.warning(
            "Understat matches unavailable for %s/%s: %s",
            league,
            season,
            exc,
        )
        return []

    # Extract match IDs from the league dates payload when present.
    match_ids: list[str] = []
    dates_data = league_data.get("dates") or {}
    if isinstance(dates_data, list):
        for match_info in dates_data:
            if not isinstance(match_info, dict):
                continue
            if not match_info.get("id"):
                continue
            # Keep behavior aligned with previous extractor: include completed matches.
            if not match_info.get("isResult"):
                continue
            match_ids.append(str(match_info.get("id")))
    elif isinstance(dates_data, dict):
        for date_info in dates_data.values():
            if isinstance(date_info, dict):
                for match_info in date_info.values():
                    if isinstance(match_info, dict) and match_info.get("id"):
                        if match_info.get("isResult"):
                            match_ids.append(str(match_info.get("id")))

    return fetch_matches_raw(client, match_ids)


def fetch_match_raw(client: UnderstatClient, match_id: str) -> Optional[dict[str, Any]]:
    """Fetch roster data for a single match; shot data may not be available."""
    match_id = str(match_id)
    shots_data: dict[str, Any] = {}

    # Preferred path: Understat AJAX match payload contains both shots and rosters.
    try:
        match_payload = client._fetch_match_data_api(match_id)
        if isinstance(match_payload, dict):
            shots_value = match_payload.get("shots")
            if isinstance(shots_value, dict):
                shots_data = shots_value
    except Exception:
        pass

    try:
        roster_data = client.get_match_roster(match_id) or {}
    except Exception:
        logger.warning("Failed to fetch roster for match %s", match_id)
        roster_data = {}

    if not shots_data:
        shots_data = roster_data.get("shotsData") or roster_data.get("shots_data") or {}

    if not shots_data and not roster_data:
        logger.warning("No data for match %s", match_id)
        return None

    return {
        "match_id": match_id,
        "shots_data": shots_data,
        "roster_data": roster_data or {},
    }


def fetch_matches_raw(
    client: UnderstatClient,
    match_ids: Iterable[str],
) -> list[dict[str, Any]]:
    """Fetch raw match data for multiple match IDs."""
    raw_matches: list[dict[str, Any]] = []

    for match_id in match_ids:
        try:
            raw_match = fetch_match_raw(client, str(match_id))
        except Exception:
            logger.exception("Failed to fetch Understat raw match %s", match_id)
            continue

        if raw_match is not None:
            raw_matches.append(raw_match)

    return raw_matches
