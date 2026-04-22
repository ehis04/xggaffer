from __future__ import annotations

from typing import Any

import pandas as pd

from data_collection.core.enums import SOURCE_WHOSCORED
from data_collection.reconcilers.matches import (
    normalize_league_name,
    normalize_season,
    normalize_team_name,
    spaces_to_underscores,
)
from data_collection.schemas.team_schema import TEAM_ALL_COLUMNS


WHOSCORED_TO_CANONICAL_LEAGUE = {
    "ENG-Premier League": "EPL",
    "EPL": "EPL",
    "ESP-La Liga": "La_Liga",
    "La_Liga": "La_Liga",
    "GER-Bundesliga": "Bundesliga",
    "Bundesliga": "Bundesliga",
    "ITA-Serie A": "Serie_A",
    "Serie_A": "Serie_A",
    "FRA-Ligue 1": "Ligue_1",
    "Ligue_1": "Ligue_1",
    "RUS-Premier League": "RFPL",
    "RFPL": "RFPL",
}

CORE_COLUMN_ALIASES = {
    "league": ["league"],
    "season": ["season"],
    "team": ["team", "team_name", "name"],
    "source_team_id": ["source_team_id", "team_id", "id"],
    "matches_played": ["matches_played", "MP", "mp", "played", "apps"],
    "wins": ["wins", "W", "w"],
    "draws": ["draws", "D", "d"],
    "losses": ["losses", "L", "l"],
    "goals_for": ["goals_for", "GF", "gf"],
    "goals_against": ["goals_against", "GA", "ga"],
    "goal_difference": ["goal_difference", "GD", "gd"],
    "points": ["points", "Pts", "pts"],
}


def _is_missing(value: Any) -> bool:
    return value is None or pd.isna(value)


def _clean_string(value: Any) -> str | None:
    if _is_missing(value):
        return None
    text = str(value).strip()
    return text or None


def _pick_first_value(row: pd.Series, aliases: list[str]) -> Any:
    for alias in aliases:
        if alias in row.index:
            value = row[alias]
            if not _is_missing(value):
                return value
    return None


def _coerce_numeric(value: Any) -> int | float | None:
    if _is_missing(value):
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)) and not pd.isna(value):
        return int(value) if float(value).is_integer() else float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        numeric = float(text)
    except ValueError:
        return None
    return int(numeric) if numeric.is_integer() else numeric


def _normalize_league(raw_league: Any, fallback_league: str) -> str:
    raw_value = _clean_string(raw_league)
    fallback_value = _clean_string(fallback_league)
    if raw_value and raw_value in WHOSCORED_TO_CANONICAL_LEAGUE:
        return WHOSCORED_TO_CANONICAL_LEAGUE[raw_value]
    normalized = normalize_league_name(raw_value or fallback_value)
    if normalized and normalized in WHOSCORED_TO_CANONICAL_LEAGUE:
        return WHOSCORED_TO_CANONICAL_LEAGUE[normalized]
    return normalized or fallback_value or raw_value or ""


def _build_fallback_source_team_id(*, league: Any, season: Any, team: Any) -> str | None:
    league_token = spaces_to_underscores(_normalize_league(league, str(league or "")))
    season_token = normalize_season(season)
    team_token = spaces_to_underscores(normalize_team_name(team))
    if not league_token or not season_token or not team_token:
        return None
    return f"whoscored_team::{league_token}::{season_token}::{team_token}"


def _filter_to_team_schema(row: dict[str, Any]) -> dict[str, Any]:
    return {column: row.get(column) for column in TEAM_ALL_COLUMNS if column in row}


def transform_whoscored_teams(raw_df: pd.DataFrame, league: str, season: str) -> pd.DataFrame:
    empty_cols = [col for col in TEAM_ALL_COLUMNS if col in {"source", "source_team_id", "season", "league", "team"}]

    if raw_df is None:
        return pd.DataFrame(columns=empty_cols)

    if not isinstance(raw_df, pd.DataFrame):
        raw_df = pd.DataFrame(raw_df)

    if raw_df.empty:
        return pd.DataFrame(columns=empty_cols)

    rows: list[dict[str, Any]] = []

    for _, raw_row in raw_df.iterrows():
        raw_team = _pick_first_value(raw_row, CORE_COLUMN_ALIASES["team"])
        canonical_team = normalize_team_name(raw_team)
        canonical_league = _normalize_league(
            _pick_first_value(raw_row, CORE_COLUMN_ALIASES["league"]), league
        )
        canonical_season = normalize_season(
            _pick_first_value(raw_row, CORE_COLUMN_ALIASES["season"]) or season
        )

        source_team_id = _clean_string(_pick_first_value(raw_row, CORE_COLUMN_ALIASES["source_team_id"]))
        if source_team_id is None:
            source_team_id = _build_fallback_source_team_id(
                league=canonical_league,
                season=canonical_season,
                team=canonical_team,
            )

        canonical_row: dict[str, Any] = {
            "source": SOURCE_WHOSCORED,
            "source_team_id": source_team_id,
            "season": canonical_season,
            "league": canonical_league,
            "team": canonical_team,
            "matches_played": _coerce_numeric(_pick_first_value(raw_row, CORE_COLUMN_ALIASES["matches_played"])),
            "wins": _coerce_numeric(_pick_first_value(raw_row, CORE_COLUMN_ALIASES["wins"])),
            "draws": _coerce_numeric(_pick_first_value(raw_row, CORE_COLUMN_ALIASES["draws"])),
            "losses": _coerce_numeric(_pick_first_value(raw_row, CORE_COLUMN_ALIASES["losses"])),
            "goals_for": _coerce_numeric(_pick_first_value(raw_row, CORE_COLUMN_ALIASES["goals_for"])),
            "goals_against": _coerce_numeric(_pick_first_value(raw_row, CORE_COLUMN_ALIASES["goals_against"])),
            "goal_difference": _coerce_numeric(_pick_first_value(raw_row, CORE_COLUMN_ALIASES["goal_difference"])),
            "points": _coerce_numeric(_pick_first_value(raw_row, CORE_COLUMN_ALIASES["points"])),
        }

        rows.append(_filter_to_team_schema(canonical_row))

    transformed_df = pd.DataFrame(rows)
    ordered_columns = [column for column in TEAM_ALL_COLUMNS if column in transformed_df.columns]
    if ordered_columns:
        transformed_df = transformed_df.loc[:, ordered_columns]

    return transformed_df


__all__ = [
    "WHOSCORED_TO_CANONICAL_LEAGUE",
    "transform_whoscored_teams",
]
