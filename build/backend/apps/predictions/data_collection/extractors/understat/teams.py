import logging
from typing import Any, Optional

from services.providers.understat.client import UnderstatClient

logger = logging.getLogger(__name__)


def fetch_understat_teams(league: str, season: str) -> list[dict[str, Any]]:
    """Fetch team data for a league/season using the internal Understat client."""
    client = UnderstatClient()
    return fetch_league_teams_raw(client, league, season)


def fetch_league_teams_raw(
    client: UnderstatClient,
    league: str,
    season: str,
) -> list[dict[str, Any]]:
    """Extract team info from league payload."""
    try:
        league_data = client.get_league_teams(league, season)
    except Exception as exc:
        logger.warning(
            "Understat teams unavailable for %s/%s: %s",
            league,
            season,
            exc,
        )
        return []

    teams_data = league_data.get("teams") or {}

    if not teams_data:
        logger.warning("No team data for %s %s", league, season)
        return []

    raw_teams: list[dict[str, Any]] = []

    for source_team_id, team_info in teams_data.items():
        if not isinstance(team_info, dict):
            continue

        raw_teams.append(
            {
                "source_team_id": str(source_team_id),
                "league": league,
                "season": str(season),
                "team_info": team_info,
                "history": team_info.get("history", []) or [],
            }
        )

    return raw_teams


def fetch_team_match_history_raw(
    client: UnderstatClient,
    team: str,
    season: str,
) -> Optional[dict[str, Any]]:
    """Fetch match history for a team/season."""
    try:
        team_payload = client.get_team_season_payload(team, season)
    except Exception:
        logger.warning("Failed to fetch team season payload for %s %s", team, season)
        return None

    matches_data = team_payload.get("history") or team_payload.get("matches") or []
    history = matches_data if isinstance(matches_data, list) else list(matches_data.values())

    if not history:
        logger.warning("Empty team match history for %s %s", team, season)
        return None

    return {
        "team": team,
        "season": str(season),
        "history": history,
    }
