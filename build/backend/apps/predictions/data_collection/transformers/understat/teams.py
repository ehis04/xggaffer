from typing import Any, Mapping, Optional

from ...core.enums import SOURCE_UNDERSTAT
from ...models.records import TeamRow, build_row
from ...schemas import TEAM_ALL_COLUMNS


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


def first_non_empty(mapping: Mapping[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return None


def extract_result_counts(history: list[Mapping[str, Any]]) -> tuple[int, int, int]:
    wins = 0
    draws = 0
    losses = 0

    for match in history:
        result = str(match.get("result", "")).strip().lower()

        if result in {"w", "win", "won"}:
            wins += 1
            continue
        if result in {"d", "draw", "drawn"}:
            draws += 1
            continue
        if result in {"l", "loss", "lost"}:
            losses += 1
            continue

        goals_for = extract_goals_for(match)
        goals_against = extract_goals_against(match)

        if goals_for > goals_against:
            wins += 1
        elif goals_for < goals_against:
            losses += 1
        else:
            draws += 1

    return wins, draws, losses


def extract_goals_for(match: Mapping[str, Any]) -> int:
    value = first_non_empty(
        match,
        ["scored", "goals", "goals_for", "gf"],
    )
    return safe_int(value)


def extract_goals_against(match: Mapping[str, Any]) -> int:
    value = first_non_empty(
        match,
        ["missed", "goals_against", "ga", "goals_allowed"],
    )
    return safe_int(value)


def transform_understat_team_raw(
    raw_team: Mapping[str, Any],
    league: str,
    season: str,
) -> TeamRow:
    team_info = raw_team.get("team_info") or {}
    history = raw_team.get("history") or []

    source_team_id = clean_text(raw_team.get("source_team_id"))
    team_name = clean_text(
        team_info.get("title")
        or raw_team.get("team")
    )

    matches_played = len([match for match in history if isinstance(match, dict)])

    wins, draws, losses = extract_result_counts(history)
    goals_for = sum(extract_goals_for(match) for match in history if isinstance(match, dict))
    goals_against = sum(extract_goals_against(match) for match in history if isinstance(match, dict))

    xg_for = round(sum(safe_float(match.get("xG")) for match in history if isinstance(match, dict)), 2)
    xg_against = round(sum(safe_float(match.get("xGA")) for match in history if isinstance(match, dict)), 2)
    npxg_for = round(sum(safe_float(match.get("npxG")) for match in history if isinstance(match, dict)), 2)
    npxg_against = round(sum(safe_float(match.get("npxGA")) for match in history if isinstance(match, dict)), 2)
    xpts = round(sum(safe_float(match.get("xpts")) for match in history if isinstance(match, dict)), 2)
    deep_completions_for = sum(safe_int(match.get("deep")) for match in history if isinstance(match, dict))
    deep_completions_against = sum(safe_int(match.get("deep_allowed")) for match in history if isinstance(match, dict))

    ppda_att = sum(
        safe_float((match.get("ppda") or {}).get("att"))
        for match in history
        if isinstance(match, dict)
    )
    ppda_def = sum(
        safe_float((match.get("ppda") or {}).get("def"))
        for match in history
        if isinstance(match, dict)
    )
    oppda_att = sum(
        safe_float((match.get("ppda_allowed") or {}).get("att"))
        for match in history
        if isinstance(match, dict)
    )
    oppda_def = sum(
        safe_float((match.get("ppda_allowed") or {}).get("def"))
        for match in history
        if isinstance(match, dict)
    )

    ppda = round(ppda_att / ppda_def, 2) if ppda_def > 0 else 0.0
    oppda = round(oppda_att / oppda_def, 2) if oppda_def > 0 else 0.0

    row_values: dict[str, Any] = {
        "source": SOURCE_UNDERSTAT,
        "source_team_id": source_team_id,
        "season": normalize_season(season or raw_team.get("season")),
        "league": league,
        "team": team_name,
        "matches_played": matches_played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "xg_for": xg_for,
        "xg_against": xg_against,
        "npxg_for": npxg_for,
        "npxg_against": npxg_against,
        "xpts": xpts,
        "deep_completions_for": deep_completions_for,
        "deep_completions_against": deep_completions_against,
        "ppda_att": round(ppda_att, 2),
        "ppda_def": round(ppda_def, 2),
        "oppda_att": round(oppda_att, 2),
        "oppda_def": round(oppda_def, 2),
        "ppda": ppda,
        "oppda": oppda,
    }

    return build_row(TEAM_ALL_COLUMNS, row_values)


def transform_understat_teams_raw(
    raw_teams: list[Mapping[str, Any]],
    league: str,
    season: str,
) -> list[TeamRow]:
    return [
        transform_understat_team_raw(raw_team, league, season)
        for raw_team in raw_teams
    ]


def transform_understat_teams(raw_df: Any, league: str = "", season: str = "", **_kwargs) -> Any:
    import pandas as pd

    raw_teams = raw_df if isinstance(raw_df, list) else raw_df.to_dict("records")
    result_rows = transform_understat_teams_raw(raw_teams, league=league, season=season)
    return pd.DataFrame(result_rows)