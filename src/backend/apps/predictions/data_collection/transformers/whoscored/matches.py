from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd

from data_collection.core.enums import SOURCE_WHOSCORED
from data_collection.schemas.match_schema import MATCH_ALL_COLUMNS


WHOSCORED_TO_CANONICAL_LEAGUE = {
    "ENG-Premier League": "EPL",
    "ESP-La Liga": "La_Liga",
    "GER-Bundesliga": "Bundesliga",
    "ITA-Serie A": "Serie_A",
    "FRA-Ligue 1": "Ligue_1",
    "RUS-Premier League": "RFPL",
    "EPL": "EPL",
    "La_Liga": "La_Liga",
    "Bundesliga": "Bundesliga",
    "Serie_A": "Serie_A",
    "Ligue_1": "Ligue_1",
    "RFPL": "RFPL",
}

TEAM_NAME_MAP = {
    "ac milan": "AC Milan",
    "atletico madrid": "Atletico Madrid",
    "bayern munchen": "Bayern Munich",
    "borussia monchengladbach": "Borussia Monchengladbach",
    "internazionale": "Inter",
    "man city": "Manchester City",
    "man utd": "Manchester United",
    "newcastle": "Newcastle United",
    "paris saint germain": "PSG",
    "psg": "PSG",
    "spurs": "Tottenham Hotspur",
    "tottenham": "Tottenham Hotspur",
    "wolverhampton": "Wolverhampton Wanderers",
    "wolves": "Wolverhampton Wanderers",
}

CORE_COLUMN_ALIASES = {
    "source_match_id": ["source_match_id", "game_id", "match_id", "id"],
    "date": ["date", "kickoff", "match_date", "start_time", "datetime"],
    "home_team": ["home_team", "home", "home_name"],
    "away_team": ["away_team", "away", "away_name"],
    "home_goals": ["home_goals", "home_score", "homeGoals"],
    "away_goals": ["away_goals", "away_score", "awayGoals"],
    "match_status": ["match_status", "status", "state", "game_status"],
    "league": ["league"],
    "season": ["season"],
}

OPTIONAL_COLUMN_ALIASES = {
    "home_possession": ["home_possession", "possession_home"],
    "away_possession": ["away_possession", "possession_away"],
    "home_passes": ["home_passes"],
    "away_passes": ["away_passes"],
    "home_accurate_passes": ["home_accurate_passes"],
    "away_accurate_passes": ["away_accurate_passes"],
    "home_pass_accuracy": ["home_pass_accuracy"],
    "away_pass_accuracy": ["away_pass_accuracy"],
    "home_corners": ["home_corners", "corners_home"],
    "away_corners": ["away_corners", "corners_away"],
    "home_fouls": ["home_fouls", "fouls_home"],
    "away_fouls": ["away_fouls", "fouls_away"],
    "home_yellow_cards": ["home_yellow_cards", "yellow_cards_home"],
    "away_yellow_cards": ["away_yellow_cards", "yellow_cards_away"],
    "home_red_cards": ["home_red_cards", "red_cards_home"],
    "away_red_cards": ["away_red_cards", "red_cards_away"],
    "home_tackles": ["home_tackles", "tackles_home"],
    "away_tackles": ["away_tackles", "tackles_away"],
    "home_interceptions": ["home_interceptions", "interceptions_home"],
    "away_interceptions": ["away_interceptions", "interceptions_away"],
    "home_clearances": ["home_clearances", "clearances_home"],
    "away_clearances": ["away_clearances", "clearances_away"],
    "home_saves": ["home_saves", "saves_home"],
    "away_saves": ["away_saves", "saves_away"],
    "home_offsides": ["home_offsides", "offsides_home"],
    "away_offsides": ["away_offsides", "offsides_away"],
}

FINAL_STATUS_VALUES = {
    "ft", "full_time", "finished", "after_extra_time", "aet",
    "penalties", "pens", "ap", "ended", "final",
}

LIVE_STATUS_VALUES = {"1h", "2h", "ht", "live", "in_progress", "extra_time", "et"}

SCHEDULED_STATUS_VALUES = {"scheduled", "not_started", "ns", "fixture", "upcoming"}

POSTPONED_STATUS_VALUES = {
    "postponed", "cancelled", "canceled", "suspended", "abandoned", "interrupted",
}

REQUIRED_OUTPUT_COLUMNS = [
    "source", "source_match_id", "league", "season", "date",
    "home_team", "away_team", "home_goals", "away_goals", "match_status", "is_finished",
]


def _materialize_index(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.index, pd.MultiIndex):
        return df.reset_index()
    if any(name is not None for name in df.index.names):
        return df.reset_index()
    return df.copy()


def _is_missing(value: Any) -> bool:
    return pd.isna(value) or value is None


def _clean_string(value: Any) -> str | None:
    if _is_missing(value):
        return None
    text = str(value).strip()
    return text or None


def _ascii_normalize(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _team_lookup_key(value: str) -> str:
    text = _ascii_normalize(value).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_team_name(value: Any) -> str | None:
    text = _clean_string(value)
    if text is None:
        return None
    mapped = TEAM_NAME_MAP.get(_team_lookup_key(text))
    if mapped:
        return mapped
    normalized = _ascii_normalize(text)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized or None


def _normalize_league(raw_league: Any, fallback_league: str) -> str:
    raw_value = _clean_string(raw_league)
    fallback_value = _clean_string(fallback_league)
    if raw_value and raw_value in WHOSCORED_TO_CANONICAL_LEAGUE:
        return WHOSCORED_TO_CANONICAL_LEAGUE[raw_value]
    if fallback_value and fallback_value in WHOSCORED_TO_CANONICAL_LEAGUE:
        return WHOSCORED_TO_CANONICAL_LEAGUE[fallback_value]
    return fallback_value or raw_value or ""


def _normalize_season(raw_season: Any, fallback_season: Any) -> str:
    candidate = _clean_string(raw_season) or _clean_string(fallback_season) or ""
    if not candidate:
        return ""
    if candidate.isdigit() and len(candidate) == 4:
        return candidate
    match = re.match(r"^(\d{4})[/-](\d{2,4})$", candidate)
    if match:
        return match.group(1)
    return candidate[:4] if len(candidate) >= 4 and candidate[:4].isdigit() else candidate


def _normalize_date(value: Any) -> str | None:
    if _is_missing(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce", utc=False)
    return parsed.strftime("%Y-%m-%d") if not pd.isna(parsed) else None


def _coerce_numeric(value: Any) -> int | float | None:
    if _is_missing(value):
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)) and not pd.isna(value):
        return int(value) if float(value).is_integer() else float(value)
    text = str(value).strip().replace("%", "").replace(",", "")
    if not text:
        return None
    try:
        numeric = float(text)
    except ValueError:
        return None
    return int(numeric) if numeric.is_integer() else numeric


def _pick_first_value(row: pd.Series, aliases: list[str]) -> Any:
    for alias in aliases:
        if alias in row.index:
            value = row[alias]
            if not _is_missing(value):
                return value
    return None


def _normalize_status(raw_status: Any, home_goals: Any, away_goals: Any) -> tuple[str | None, bool]:
    status_text = _clean_string(raw_status)
    if status_text:
        key = re.sub(r"[\s\-]+", "_", status_text.lower())
        if key in FINAL_STATUS_VALUES:
            return "final", True
        if key in LIVE_STATUS_VALUES:
            return "live", False
        if key in SCHEDULED_STATUS_VALUES:
            return "scheduled", False
        if key in POSTPONED_STATUS_VALUES:
            return "postponed", False
        return key, False
    if home_goals is not None and away_goals is not None:
        return "final", True
    return None, False


def _filter_to_match_schema(row: dict[str, Any]) -> dict[str, Any]:
    return {column: row.get(column) for column in MATCH_ALL_COLUMNS if column in row}


def transform_whoscored_matches(raw_df: pd.DataFrame, league: str, season: str) -> pd.DataFrame:
    if raw_df is None or (isinstance(raw_df, pd.DataFrame) and raw_df.empty):
        return pd.DataFrame(columns=[col for col in REQUIRED_OUTPUT_COLUMNS if col in MATCH_ALL_COLUMNS])

    if not isinstance(raw_df, pd.DataFrame):
        raw_df = pd.DataFrame(raw_df)

    source_df = _materialize_index(raw_df)
    rows: list[dict[str, Any]] = []

    for _, raw_row in source_df.iterrows():
        home_goals = _coerce_numeric(_pick_first_value(raw_row, CORE_COLUMN_ALIASES["home_goals"]))
        away_goals = _coerce_numeric(_pick_first_value(raw_row, CORE_COLUMN_ALIASES["away_goals"]))
        match_status, is_finished = _normalize_status(
            _pick_first_value(raw_row, CORE_COLUMN_ALIASES["match_status"]),
            home_goals,
            away_goals,
        )

        canonical_row: dict[str, Any] = {
            "source": SOURCE_WHOSCORED,
            "source_match_id": _clean_string(_pick_first_value(raw_row, CORE_COLUMN_ALIASES["source_match_id"])),
            "league": _normalize_league(_pick_first_value(raw_row, CORE_COLUMN_ALIASES["league"]), league),
            "season": _normalize_season(_pick_first_value(raw_row, CORE_COLUMN_ALIASES["season"]), season),
            "date": _normalize_date(_pick_first_value(raw_row, CORE_COLUMN_ALIASES["date"])),
            "home_team": _normalize_team_name(_pick_first_value(raw_row, CORE_COLUMN_ALIASES["home_team"])),
            "away_team": _normalize_team_name(_pick_first_value(raw_row, CORE_COLUMN_ALIASES["away_team"])),
            "home_goals": home_goals,
            "away_goals": away_goals,
            "match_status": match_status,
            "is_finished": is_finished,
        }

        for canonical_name, aliases in OPTIONAL_COLUMN_ALIASES.items():
            value = _pick_first_value(raw_row, aliases)
            numeric_value = _coerce_numeric(value)
            if numeric_value is not None:
                canonical_row[canonical_name] = numeric_value

        rows.append(_filter_to_match_schema(canonical_row))

    transformed_df = pd.DataFrame(rows)
    ordered_columns = [column for column in MATCH_ALL_COLUMNS if column in transformed_df.columns]
    if ordered_columns:
        transformed_df = transformed_df.loc[:, ordered_columns]

    return transformed_df


__all__ = [
    "WHOSCORED_TO_CANONICAL_LEAGUE",
    "TEAM_NAME_MAP",
    "transform_whoscored_matches",
]
