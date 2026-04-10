import logging
from typing import Any, Iterable, Optional

from services.providers.understat.client import UnderstatClient

logger = logging.getLogger(__name__)


def fetch_understat_team_summaries(league: str, season: str) -> list[dict[str, Any]]:
    """Fetch team summary data for a league/season using the internal Understat client."""
    client = UnderstatClient()
    try:
        league_data = client.get_league_teams(league, season)
    except Exception as exc:
        logger.warning(
            "Understat team summaries unavailable for %s/%s: %s",
            league,
            season,
            exc,
        )
        return []

    teams_data = league_data.get("teams") or {}
    if not isinstance(teams_data, dict):
        return []

    # Current league payload already includes per-team history entries.
    raw_summaries: list[dict[str, Any]] = []
    for team_info in teams_data.values():
        if not isinstance(team_info, dict):
            continue
        team_name = str(team_info.get("title", "")).strip()
        if not team_name:
            continue
        raw_summaries.append(
            {
                "team": team_name,
                "season": str(season),
                "history": team_info.get("history") or [],
                "context": team_info,
            }
        )

    return raw_summaries


def fetch_team_summary_raw(
    client: UnderstatClient,
    team: str,
    season: str,
) -> Optional[dict[str, Any]]:
    """Fetch match history and context for a team/season."""
    try:
        team_payload = client.get_team_season_payload(team, season)
    except Exception:
        logger.warning("Failed to fetch team season payload for %s %s", team, season)
        return None

    match_data = team_payload.get("history") or team_payload.get("matches") or {}
    history = match_data if isinstance(match_data, list) else list((match_data or {}).values())

    if not history:
        logger.warning("No team summary raw data for %s %s", team, season)
        return None

    return {
        "team": team,
        "season": str(season),
        "history": history or [],
        "context": team_payload or {},
    }


def fetch_teams_summaries_raw(
    client: UnderstatClient,
    teams: Iterable[str],
    season: str,
) -> list[dict[str, Any]]:
    raw_summaries: list[dict[str, Any]] = []

    for team in teams:
        try:
            raw_summary = fetch_team_summary_raw(client, str(team), str(season))
        except Exception:
            logger.exception(
                "Failed to fetch Understat raw team summary for team %s season %s",
                team,
                season,
            )
            continue

        if raw_summary is not None:
            raw_summaries.append(raw_summary)

    return raw_summaries
