from __future__ import annotations

from typing import Iterable

import pandas as pd

from data_collection.core.enums import SOURCE_WHOSCORED
from data_collection.schemas.player_schema import OPTIONAL_COLUMNS, REQUIRED_COLUMNS

CANONICAL_PLAYER_COLUMNS = list(dict.fromkeys(REQUIRED_COLUMNS + OPTIONAL_COLUMNS))


def transform_whoscored_players(
    raw_df: pd.DataFrame,
    league: str,
    season: str,
) -> pd.DataFrame:
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(columns=CANONICAL_PLAYER_COLUMNS)

    transformed = pd.DataFrame(index=raw_df.index)

    source_team_column = _preferred_column("source_team_id", "team_id")
    position_column = _preferred_column("position", "pos")
    country_column = _preferred_column("country", "nationality")
    minutes_column = _preferred_column("minutes", "minutes_played")
    games_column = _preferred_column("games", "appearances", "matches")

    transformed["source"] = SOURCE_WHOSCORED
    transformed["source_player_id"] = _coalesce(
        raw_df,
        ["player_id", "playerId", "source_player_id", "id"],
    )
    transformed[source_team_column] = _coalesce(
        raw_df,
        ["team_id", "teamId", "source_team_id"],
    )
    transformed["season"] = _clean_text(
        _coalesce(raw_df, ["season"])
    ).fillna(str(season).strip())
    transformed["league"] = _clean_text(
        _coalesce(raw_df, ["league"])
    ).fillna(str(league).strip())
    transformed["name"] = _clean_text(
        _coalesce(raw_df, ["player_name", "name", "player"])
    )
    transformed["team"] = _clean_text(
        _coalesce(raw_df, ["team_name", "team"])
    )
    transformed[position_column] = _clean_text(
        _coalesce(raw_df, ["position", "pos"])
    )
    transformed[country_column] = _clean_text(
        _coalesce(raw_df, ["country", "nationality"])
    )
    transformed[minutes_column] = _coalesce(
        raw_df,
        ["mins_played", "minutesPlayed", "minutes_played", "minutes"],
    )
    transformed[games_column] = _coalesce(
        raw_df,
        ["apps", "appearances", "games", "matches"],
    )
    transformed["rating"] = _coalesce(raw_df, ["rating"])
    transformed["yellow_cards"] = _coalesce(raw_df, ["yellow_cards", "yellowCards"])
    transformed["red_cards"] = _coalesce(raw_df, ["red_cards", "redCards"])
    transformed["tackles"] = _coalesce(raw_df, ["tackles", "tacklesWon"])
    transformed["interceptions"] = _coalesce(raw_df, ["interceptions"])
    transformed["clearances"] = _coalesce(raw_df, ["clearances"])
    transformed["blocks"] = _coalesce(raw_df, ["blocks", "blockedShots"])
    transformed["recoveries"] = _coalesce(raw_df, ["recoveries", "ballRecovery"])
    transformed["duels_won"] = _coalesce(raw_df, ["duels_won", "duelsWon"])
    transformed["aerial_duels_won"] = _coalesce(raw_df, ["aerial_duels_won", "aerialDuelsWon"])
    transformed["fouls_committed"] = _coalesce(raw_df, ["fouls_committed", "foulsCommitted"])
    transformed["fouls_won"] = _coalesce(raw_df, ["fouls_won", "wasFouled", "foulsWon"])

    for column in transformed.columns:
        if column in {"source", "season", "league", "name", "team", position_column, country_column}:
            transformed[column] = _clean_text(transformed[column])

    numeric_columns = {
        "source_player_id", source_team_column, minutes_column, games_column,
        "rating", "yellow_cards", "red_cards", "tackles", "interceptions",
        "clearances", "blocks", "recoveries", "duels_won", "aerial_duels_won",
        "fouls_committed", "fouls_won",
    }
    for column in numeric_columns:
        if column in transformed.columns:
            transformed[column] = pd.to_numeric(transformed[column], errors="coerce")

    transformed = transformed.replace({"": pd.NA})

    keep_mask = ~(
        transformed["source_player_id"].isna()
        & transformed["name"].isna()
        & transformed["team"].isna()
    )
    transformed = transformed.loc[keep_mask].copy()

    for column in CANONICAL_PLAYER_COLUMNS:
        if column not in transformed.columns:
            transformed[column] = pd.NA

    transformed = transformed[CANONICAL_PLAYER_COLUMNS]

    dedupe_columns = [
        column for column in ["source", "source_player_id", "season", "team"]
        if column in transformed.columns
    ]
    if dedupe_columns:
        transformed = transformed.drop_duplicates(subset=dedupe_columns, keep="first")

    return transformed.reset_index(drop=True)


def _preferred_column(*candidates: str) -> str:
    for candidate in candidates:
        if candidate in CANONICAL_PLAYER_COLUMNS:
            return candidate
    return candidates[0]


def _coalesce(df: pd.DataFrame, candidates: Iterable[str]) -> pd.Series:
    existing = [column for column in candidates if column in df.columns]
    if not existing:
        return pd.Series(pd.NA, index=df.index, dtype="object")
    merged = df[existing].copy().replace({"": pd.NA})
    if len(existing) == 1:
        return merged.iloc[:, 0]
    return merged.bfill(axis=1).iloc[:, 0]


def _clean_text(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip()
    return text.replace({"": pd.NA})
