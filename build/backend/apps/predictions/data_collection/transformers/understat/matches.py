from datetime import datetime
import math
from typing import Any, Mapping

from ...core.enums import SOURCE_UNDERSTAT
from ...models.records import MatchRow, build_row
from ...schemas import MATCH_ALL_COLUMNS


def get_shot_zone(x: float, y: float) -> str:
    in_six_yard_x = x >= 0.943
    in_six_yard_y = 0.365 <= y <= 0.635
    in_penalty_x = x >= 0.828
    in_penalty_y = 0.204 <= y <= 0.796

    if in_six_yard_x and in_six_yard_y:
        return "six_yard"
    if in_penalty_x and in_penalty_y:
        return "penalty_area"
    return "outside_box"


def calculate_xpts(home_xg: float, away_xg: float) -> tuple[float, float]:
    max_goals = 10
    home_win_prob = 0.0
    draw_prob = 0.0
    away_win_prob = 0.0

    for home_goals in range(max_goals):
        for away_goals in range(max_goals):
            home_prob = (math.exp(-home_xg) * (home_xg ** home_goals)) / math.factorial(home_goals)
            away_prob = (math.exp(-away_xg) * (away_xg ** away_goals)) / math.factorial(away_goals)
            joint_prob = home_prob * away_prob

            if home_goals > away_goals:
                home_win_prob += joint_prob
            elif home_goals < away_goals:
                away_win_prob += joint_prob
            else:
                draw_prob += joint_prob

    home_xpts = (home_win_prob * 3) + draw_prob
    away_xpts = (away_win_prob * 3) + draw_prob

    return round(home_xpts, 2), round(away_xpts, 2)


def normalize_season(value: Any) -> str:
    if value is None or value == "":
        return ""

    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return str(value).strip()


def normalize_date(value: Any) -> str:
    if value is None:
        return ""

    raw = str(value).strip()
    if not raw:
        return ""

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return raw[:10]


def flatten_shots(shots_data: Any) -> list[dict[str, Any]]:
    if not shots_data:
        return []

    if isinstance(shots_data, dict):
        if "h" in shots_data and "a" in shots_data:
            home_shots = shots_data.get("h", []) or []
            away_shots = shots_data.get("a", []) or []
            return list(home_shots) + list(away_shots)

        values = list(shots_data.values())
        if values and isinstance(values[0], list):
            flattened: list[dict[str, Any]] = []
            for sublist in values:
                flattened.extend(sublist)
            return flattened

        return [value for value in values if isinstance(value, dict)]

    if isinstance(shots_data, list):
        return [shot for shot in shots_data if isinstance(shot, dict)]

    return []


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


def transform_understat_match_raw(
    raw_match: Mapping[str, Any],
    league: str,
    season: str,
) -> MatchRow:
    shots = flatten_shots(raw_match.get("shots_data"))
    roster = raw_match.get("roster_data") or {}

    if not shots:
        raise ValueError("Understat raw match contains no shot rows")

    first_shot = shots[0]

    row_values: dict[str, Any] = {
        "source": SOURCE_UNDERSTAT,
        "source_match_id": str(raw_match.get("match_id", "")),
        "season": normalize_season(season or first_shot.get("season")),
        "date": normalize_date(first_shot.get("date")),
        "league": league,
        "home_team": first_shot.get("h_team", ""),
        "away_team": first_shot.get("a_team", ""),
        "match_status": "finished",
        "is_finished": True,
        "home_goals": 0,
        "away_goals": 0,
        "home_own_goals": 0,
        "away_own_goals": 0,
        "home_shots": 0,
        "away_shots": 0,
        "home_missed_shots": 0,
        "away_missed_shots": 0,
        "home_blocked_shots": 0,
        "away_blocked_shots": 0,
        "home_saved_shots": 0,
        "away_saved_shots": 0,
        "home_shots_on_post": 0,
        "away_shots_on_post": 0,
        "home_shots_six_yard": 0,
        "away_shots_six_yard": 0,
        "home_shots_penalty_area": 0,
        "away_shots_penalty_area": 0,
        "home_shots_outside_box": 0,
        "away_shots_outside_box": 0,
        "home_shots_open_play": 0,
        "away_shots_open_play": 0,
        "home_shots_set_piece": 0,
        "away_shots_set_piece": 0,
        "home_shots_from_corner": 0,
        "away_shots_from_corner": 0,
        "home_shots_direct_freekick": 0,
        "away_shots_direct_freekick": 0,
        "home_shots_penalty": 0,
        "away_shots_penalty": 0,
        "home_shots_left_foot": 0,
        "away_shots_left_foot": 0,
        "home_shots_right_foot": 0,
        "away_shots_right_foot": 0,
        "home_shots_head": 0,
        "away_shots_head": 0,
        "home_xg": 0.0,
        "away_xg": 0.0,
        "home_xa": 0.0,
        "away_xa": 0.0,
        "home_key_passes": 0,
        "away_key_passes": 0,
        "home_assists": 0,
        "away_assists": 0,
        "home_goal_minutes": [],
        "away_goal_minutes": [],
    }

    result_map = {
        "Goal": "goals",
        "MissedShots": "missed_shots",
        "BlockedShot": "blocked_shots",
        "SavedShot": "saved_shots",
        "ShotOnPost": "shots_on_post",
    }

    situation_map = {
        "OpenPlay": "open_play",
        "SetPiece": "set_piece",
        "FromCorner": "from_corner",
        "DirectFreekick": "direct_freekick",
        "Penalty": "penalty",
    }

    shot_type_map = {
        "LeftFoot": "left_foot",
        "RightFoot": "right_foot",
        "Head": "head",
    }

    home_goal_shots = 0
    away_goal_shots = 0

    for shot in shots:
        side = "home" if shot.get("h_a") == "h" else "away"

        row_values[f"{side}_shots"] += 1
        row_values[f"{side}_xg"] += safe_float(shot.get("xG"))

        result = shot.get("result", "")
        if result in result_map:
            row_values[f"{side}_{result_map[result]}"] += 1

            if result == "Goal":
                if side == "home":
                    home_goal_shots += 1
                else:
                    away_goal_shots += 1

                minute = safe_int(shot.get("minute"))
                row_values[f"{side}_goal_minutes"].append(minute)

        x = safe_float(shot.get("X"))
        y = safe_float(shot.get("Y"))
        zone = get_shot_zone(x, y)
        row_values[f"{side}_shots_{zone}"] += 1

        situation = shot.get("situation", "")
        if situation in situation_map:
            row_values[f"{side}_shots_{situation_map[situation]}"] += 1

        shot_type = shot.get("shotType", "")
        if shot_type in shot_type_map:
            row_values[f"{side}_shots_{shot_type_map[shot_type]}"] += 1

    for roster_key, side_name in (("h", "home"), ("a", "away")):
        side_roster = roster.get(roster_key, {}) or {}
        for player_data in side_roster.values():
            row_values[f"{side_name}_xa"] += safe_float(player_data.get("xA"))
            row_values[f"{side_name}_key_passes"] += safe_int(player_data.get("key_passes"))
            row_values[f"{side_name}_assists"] += safe_int(player_data.get("assists"))
            row_values[f"{side_name}_own_goals"] += safe_int(player_data.get("own_goals"))

    row_values["home_goals"] = home_goal_shots + row_values["away_own_goals"]
    row_values["away_goals"] = away_goal_shots + row_values["home_own_goals"]

    row_values["home_xg"] = round(row_values["home_xg"], 2)
    row_values["away_xg"] = round(row_values["away_xg"], 2)
    row_values["home_xa"] = round(row_values["home_xa"], 2)
    row_values["away_xa"] = round(row_values["away_xa"], 2)

    home_xpts, away_xpts = calculate_xpts(row_values["home_xg"], row_values["away_xg"])
    row_values["home_xpts"] = home_xpts
    row_values["away_xpts"] = away_xpts

    row_values["home_goal_minutes"] = ",".join(map(str, sorted(row_values["home_goal_minutes"])))
    row_values["away_goal_minutes"] = ",".join(map(str, sorted(row_values["away_goal_minutes"])))

    return build_row(MATCH_ALL_COLUMNS, row_values)


def transform_understat_matches_raw(
    raw_matches: list[Mapping[str, Any]],
    league: str,
    season: str,
) -> list[MatchRow]:
    return [
        transform_understat_match_raw(raw_match, league, season)
        for raw_match in raw_matches
    ]


def transform_understat_matches(raw_df: Any, league: str = "", season: str = "", **_kwargs) -> Any:
    import pandas as pd

    if isinstance(raw_df, list):
        result_rows = transform_understat_matches_raw(raw_df, league=league, season=season)
        return pd.DataFrame(result_rows)
    return transform(raw_df, league=league, season=season)


def transform(raw_df: Any, league: str = "", season: str = "", **_kwargs) -> Any:
    import pandas as pd

    if "shots_data" in raw_df.columns:
        raw_matches = raw_df.to_dict("records")
        result_rows = transform_understat_matches_raw(raw_matches, league=league, season=season)
        return pd.DataFrame(result_rows)

    rows = []
    for _, row in raw_df.iterrows():
        record: dict[str, Any] = {"source": SOURCE_UNDERSTAT}

        for key in ("id", "match_id", "source_match_id"):
            val = row.get(key)
            if val is not None:
                record["source_match_id"] = str(val)
                break

        for key in ("datetime", "date"):
            val = row.get(key)
            if val is not None:
                record["date"] = normalize_date(val)
                break

        record["league"] = row.get("league") or league
        record["season"] = normalize_season(row.get("season") or season)

        for key in ("home_team", "h_title"):
            val = row.get(key)
            if val is not None:
                record["home_team"] = str(val)
                break
        if "home_team" not in record:
            h = row.get("h")
            record["home_team"] = h.get("title", "") if isinstance(h, dict) else ""

        for key in ("away_team", "a_title"):
            val = row.get(key)
            if val is not None:
                record["away_team"] = str(val)
                break
        if "away_team" not in record:
            a = row.get("a")
            record["away_team"] = a.get("title", "") if isinstance(a, dict) else ""

        for home_key, away_key in (("home_goals", "away_goals"), ("goals__h", "goals__a")):
            if row.get(home_key) is not None:
                record["home_goals"] = safe_int(row[home_key])
                record["away_goals"] = safe_int(row[away_key])
                break
        if "home_goals" not in record:
            goals = row.get("goals")
            if isinstance(goals, dict):
                record["home_goals"] = safe_int(goals.get("h", 0))
                record["away_goals"] = safe_int(goals.get("a", 0))

        for home_key, away_key in (("xG__h", "xG__a"),):
            if row.get(home_key) is not None:
                record["home_xg"] = safe_float(row[home_key])
                record["away_xg"] = safe_float(row[away_key])
                break
        if "home_xg" not in record:
            xg = row.get("xG")
            if isinstance(xg, dict):
                record["home_xg"] = safe_float(xg.get("h", 0.0))
                record["away_xg"] = safe_float(xg.get("a", 0.0))

        for key in ("match_status", "isResult", "is_finished"):
            val = row.get(key)
            if val is not None:
                if key == "match_status":
                    record["match_status"] = str(val)
                else:
                    record["is_finished"] = bool(val)
                    if "match_status" not in record:
                        record["match_status"] = "finished" if bool(val) else "scheduled"
                break

        rows.append(record)

    return pd.DataFrame(rows)