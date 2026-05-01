from typing import Any, Mapping, Optional

from ...core.enums import SOURCE_UNDERSTAT
from ...models.records import PlayerRow, build_row
from ...schemas import PLAYER_ALL_COLUMNS


def calculate_per_90(value: float, minutes: int) -> float:
    if minutes <= 0:
        return 0.0
    return round(value / (minutes / 90), 2)


def safe_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def normalize_season(value: Any) -> str:
    if value is None or value == "":
        return ""

    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return str(value).strip()


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_team_name(value: Any) -> Optional[str]:
    team = clean_text(value)
    if team is None:
        return None
    if "," not in team:
        return team

    # Understat can return multiple clubs for one season (e.g., transfers).
    # Keep the primary club (first token) for single-team downstream joins.
    primary = team.split(",", 1)[0].strip()
    return primary or team


def transform_understat_player_raw(
    raw_player: Mapping[str, Any],
    league: str,
    season: str,
) -> PlayerRow:
    season_stats = raw_player.get("season_stats") or {}

    source_player_id = clean_text(raw_player.get("player_id"))
    player_name = clean_text(
        season_stats.get("player")
        or season_stats.get("player_name")
        or season_stats.get("name")
    )
    # Understat league-player payloads expose club as `team_title`.
    team_name = normalize_team_name(
        season_stats.get("team")
        or season_stats.get("team_title")
        or season_stats.get("club")
    )
    position = clean_text(season_stats.get("position"))

    minutes = safe_int(season_stats.get("time"))
    goals = safe_int(season_stats.get("goals"))
    assists = safe_int(season_stats.get("assists"))
    npg = safe_int(season_stats.get("npg"))
    xg = round(safe_float(season_stats.get("xG")), 2)
    npxg = round(safe_float(season_stats.get("npxG")), 2)
    xa = round(safe_float(season_stats.get("xA")), 2)
    shots = safe_int(season_stats.get("shots"))
    key_passes = safe_int(season_stats.get("key_passes"))
    yellow_cards = safe_int(season_stats.get("yellow_cards"))
    red_cards = safe_int(season_stats.get("red_cards"))
    xg_chain = round(safe_float(season_stats.get("xGChain")), 2)
    xg_buildup = round(safe_float(season_stats.get("xGBuildup")), 2)
    games = safe_int(season_stats.get("games"))

    g90 = calculate_per_90(goals, minutes)
    xg90 = calculate_per_90(xg, minutes)
    npxg90 = calculate_per_90(npxg, minutes)
    xa90 = calculate_per_90(xa, minutes)
    sh90 = calculate_per_90(shots, minutes)
    kp90 = calculate_per_90(key_passes, minutes)

    row_values: dict[str, Any] = {
        "source": SOURCE_UNDERSTAT,
        "source_player_id": source_player_id,
        "season": normalize_season(season or raw_player.get("season")),
        "league": league,
        "name": player_name,
        "team": team_name,
        "position": position,
        "games": games,
        "minutes": minutes,
        "goals": goals,
        "assists": assists,
        "npg": npg,
        "xg": xg,
        "npxg": npxg,
        "xa": xa,
        "shots": shots,
        "key_passes": key_passes,
        "yellow_cards": yellow_cards,
        "red_cards": red_cards,
        "xg_chain": xg_chain,
        "xg_buildup": xg_buildup,
        "g90": g90,
        "xg90": xg90,
        "npxg90": npxg90,
        "xa90": xa90,
        "sh90": sh90,
        "kp90": kp90,
        "xg90_xa90": round(xg90 + xa90, 2),
        "npxg90_xa90": round(npxg90 + xa90, 2),
    }

    return build_row(PLAYER_ALL_COLUMNS, row_values)


def transform_understat_players_raw(
    raw_players: list[Mapping[str, Any]],
    league: str,
    season: str,
) -> list[PlayerRow]:
    return [
        transform_understat_player_raw(raw_player, league, season)
        for raw_player in raw_players
    ]


def transform_understat_players(raw_df: Any, league: str = "", season: str = "", **_kwargs) -> Any:
    import pandas as pd

    raw_players = raw_df if isinstance(raw_df, list) else raw_df.to_dict("records")
    result_rows = transform_understat_players_raw(raw_players, league=league, season=season)
    return pd.DataFrame(result_rows)