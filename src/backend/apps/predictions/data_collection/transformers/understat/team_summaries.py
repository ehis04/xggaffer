from typing import Any, Mapping, Optional

from ...core.enums import SOURCE_UNDERSTAT
from ...models.records import TeamSummaryRow, build_row
from ...schemas import TEAM_SUMMARY_ALL_COLUMNS


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


def extract_goals_for(match: Mapping[str, Any]) -> int:
    value = first_non_empty(match, ["scored", "goals", "goals_for", "gf"])
    return safe_int(value)


def extract_goals_against(match: Mapping[str, Any]) -> int:
    value = first_non_empty(match, ["missed", "goals_against", "ga", "goals_allowed"])
    return safe_int(value)


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


def sum_context_metric(
    context_bucket: Mapping[str, Any],
    key: str,
    against: bool = False,
) -> int:
    total = 0

    for _, data in context_bucket.items():
        if not isinstance(data, dict):
            continue

        target = data.get("against", {}) if against else data
        total += safe_int(target.get(key))

    return total


def transform_understat_team_summary_raw(
    raw_summary: Mapping[str, Any],
    league: str,
    season: str,
) -> TeamSummaryRow:
    history = [
        match
        for match in (raw_summary.get("history") or [])
        if isinstance(match, dict)
    ]
    context = raw_summary.get("context") or {}

    team_name = clean_text(raw_summary.get("team"))

    matches_played = len(history)
    wins, draws, losses = extract_result_counts(history)

    goals_for = sum(extract_goals_for(match) for match in history)
    goals_against = sum(extract_goals_against(match) for match in history)

    xg_for = round(sum(safe_float(match.get("xG")) for match in history), 2)
    xg_against = round(sum(safe_float(match.get("xGA")) for match in history), 2)
    npxg_for = round(sum(safe_float(match.get("npxG")) for match in history), 2)
    npxg_against = round(sum(safe_float(match.get("npxGA")) for match in history), 2)
    xpts = round(sum(safe_float(match.get("xpts")) for match in history), 2)

    ppda_att = sum(safe_float((match.get("ppda") or {}).get("att")) for match in history)
    ppda_def = sum(safe_float((match.get("ppda") or {}).get("def")) for match in history)
    oppda_att = sum(safe_float((match.get("ppda_allowed") or {}).get("att")) for match in history)
    oppda_def = sum(safe_float((match.get("ppda_allowed") or {}).get("def")) for match in history)

    ppda = round(ppda_att / ppda_def, 2) if ppda_def > 0 else 0.0
    oppda = round(oppda_att / oppda_def, 2) if oppda_def > 0 else 0.0

    deep_completions_for = sum(safe_int(match.get("deep")) for match in history)
    deep_completions_against = sum(safe_int(match.get("deep_allowed")) for match in history)

    formation_context = context.get("formation", {}) or {}
    shots = sum_context_metric(formation_context, "shots", against=False)
    shots_allowed = sum_context_metric(formation_context, "shots", against=True)

    row_values: dict[str, Any] = {
        "source": SOURCE_UNDERSTAT,
        "season": normalize_season(season or raw_summary.get("season")),
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
        "ppda": ppda,
        "oppda": oppda,
        "deep_completions_for": deep_completions_for,
        "deep_completions_against": deep_completions_against,
        "shots": shots,
        "shots_allowed": shots_allowed,
    }

    return build_row(TEAM_SUMMARY_ALL_COLUMNS, row_values)


def transform_understat_team_summaries_raw(
    raw_summaries: list[Mapping[str, Any]],
    league: str,
    season: str,
) -> list[TeamSummaryRow]:
    return [
        transform_understat_team_summary_raw(raw_summary, league, season)
        for raw_summary in raw_summaries
    ]


def transform_understat_team_summaries(raw_df: Any, league: str = "", season: str = "", **_kwargs) -> Any:
    import pandas as pd

    raw_summaries = raw_df if isinstance(raw_df, list) else raw_df.to_dict("records")
    result_rows = transform_understat_team_summaries_raw(raw_summaries, league=league, season=season)
    return pd.DataFrame(result_rows)