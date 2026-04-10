import logging
from typing import Any, Iterable, Optional

from services.providers.understat.client import UnderstatClient

logger = logging.getLogger(__name__)


def fetch_understat_players(league: str, season: str) -> list[dict[str, Any]]:
    """Fetch player data for a league/season using the internal Understat client."""
    client = UnderstatClient()
    try:
        league_data = client.get_league_teams(league, season)
    except Exception as exc:
        logger.warning(
            "Understat players unavailable for %s/%s: %s",
            league,
            season,
            exc,
        )
        return []

    players_data = league_data.get("players") or []
    if not isinstance(players_data, list):
        logger.warning("Unexpected players payload type for %s/%s", league, season)
        return []

    # Current Understat league payload already includes season-level player stats.
    raw_players: list[dict[str, Any]] = []
    for player in players_data:
        if not isinstance(player, dict):
            continue
        player_id = player.get("id")
        if player_id is None:
            continue
        raw_players.append(
            {
                "player_id": str(player_id),
                "season": str(season),
                "season_stats": player,
            }
        )

    return raw_players


def fetch_player_season_raw(
    client: UnderstatClient,
    player_id: str,
    season: str,
) -> Optional[dict[str, Any]]:
    player_id = str(player_id)
    try:
        player_stats = client.get_player_stats(player_id, season)
    except Exception:
        logger.warning("No data for player %s season %s", player_id, season)
        return None

    if not player_stats:
        logger.warning("No stats for player %s season %s", player_id, season)
        return None

    return {
        "player_id": player_id,
        "season": str(season),
        "season_stats": player_stats,
    }


def fetch_players_season_raw(
    client: UnderstatClient,
    player_ids: Iterable[str],
    season: str,
) -> list[dict[str, Any]]:
    raw_players: list[dict[str, Any]] = []

    for player_id in player_ids:
        try:
            raw_player = fetch_player_season_raw(client, str(player_id), str(season))
        except Exception:
            logger.exception(
                "Failed to fetch Understat raw player season for player %s season %s",
                player_id,
                season,
            )
            continue

        if raw_player is not None:
            raw_players.append(raw_player)

    return raw_players


def fetch_player_all_seasons_raw(
    client: UnderstatClient,
    player_id: str,
) -> list[dict[str, Any]]:
    player_id = str(player_id)
    try:
        player_data = client.get_player_stats(player_id, season=None)
    except Exception:
        logger.warning("No data for player %s", player_id)
        return []

    if not player_data:
        logger.warning("No data for player %s", player_id)
        return []

    if isinstance(player_data, list):
        raw_seasons = []
        for season_item in player_data:
            if isinstance(season_item, dict):
                season = season_item.get("season")
                if season is not None:
                    raw_seasons.append(
                        {
                            "player_id": player_id,
                            "season": str(season),
                            "season_stats": season_item,
                        }
                    )
        return raw_seasons

    season_list = player_data.get("season", []) if isinstance(player_data, dict) else []

    if not season_list:
        logger.warning("No season list for player %s", player_id)
        return []

    raw_seasons: list[dict[str, Any]] = []

    for season_item in season_list:
        season = season_item.get("season")
        if season is None:
            continue

        raw_seasons.append(
            {
                "player_id": player_id,
                "season": str(season),
                "season_stats": season_item,
            }
        )

    return raw_seasons
