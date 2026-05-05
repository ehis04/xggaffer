from __future__ import annotations

from typing import Iterable

import pandas as pd

from data_collection.core.enums import SOURCE_SOFASCORE
from data_collection.schemas.player_schema import OPTIONAL_COLUMNS, REQUIRED_COLUMNS

CANONICAL_PLAYER_COLUMNS = list(dict.fromkeys(REQUIRED_COLUMNS + OPTIONAL_COLUMNS))


def transform_sofascore_players(
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

    transformed["source"] = SOURCE_SOFASCORE
    transformed["source_player_id"] = _coalesce(
        raw_df,
        [
            "player__id",
            "player.id",
            "player_id",
            "playerId",
            "source_player_id",
        ],
    )
    transformed[source_team_column] = _coalesce(
        raw_df,
        [
            "team__id",
            "team.id",
            "team_id",
            "teamId",
            "source_team_id",
        ],
    )
    transformed["season"] = _clean_text(
        _coalesce(raw_df, ["requested_season", "season"])
    ).fillna(str(season).strip())
    transformed["league"] = _clean_text(
        _coalesce(raw_df, ["requested_league", "league"])
    ).fillna(str(league).strip())
    transformed["name"] = _clean_text(
        _coalesce(
            raw_df,
            [
                "player__name",
                "player.name",
                "player_name",
                "name",
                "player__shortName",
                "player.shortName",
            ],
        )
    )
    transformed["team"] = _clean_text(
        _coalesce(
            raw_df,
            [
                "team__name",
                "team.name",
                "team_name",
                "team",
            ],
        )
    )
    transformed[position_column] = _clean_text(
        _coalesce(
            raw_df,
            [
                "player__position",
                "player.position",
                "position",
                "pos",
            ],
        )
    )
    transformed[country_column] = _clean_text(
        _coalesce(
            raw_df,
            [
                "player__country__name",
                "player.country.name",
                "player__country__alpha2",
                "player.country.alpha2",
                "country",
                "nationality",
            ],
        )
    )
    transformed[minutes_column] = _coalesce(
        raw_df,
        [
            "statistics__minutesPlayed",
            "statistics.minutesPlayed",
            "minutesPlayed",
            "statistics__minutes",
            "statistics.minutes",
            "minutes_played",
            "minutes",
        ],
    )
    transformed[games_column] = _coalesce(
        raw_df,
        [
            "statistics__appearances",
            "statistics.appearances",
            "appearances",
            "statistics__matches",
            "statistics.matches",
            "matches",
            "statistics__games",
            "statistics.games",
            "games",
        ],
    )
    transformed["rating"] = _coalesce(
        raw_df,
        [
            "statistics__rating",
            "statistics.rating",
            "rating",
        ],
    )
    transformed["yellow_cards"] = _coalesce(
        raw_df,
        [
            "statistics__yellowCards",
            "statistics.yellowCards",
            "yellowCards",
            "yellow_cards",
        ],
    )
    transformed["red_cards"] = _coalesce(
        raw_df,
        [
            "statistics__redCards",
            "statistics.redCards",
            "redCards",
            "red_cards",
        ],
    )
    transformed["tackles"] = _coalesce(
        raw_df,
        [
            "statistics__tacklesWon",
            "statistics.tacklesWon",
            "tacklesWon",
            "statistics__tackles",
            "statistics.tackles",
            "tackles",
        ],
    )
    transformed["interceptions"] = _coalesce(
        raw_df,
        [
            "statistics__interceptions",
            "statistics.interceptions",
            "interceptions",
        ],
    )
    transformed["clearances"] = _coalesce(
        raw_df,
        [
            "statistics__clearances",
            "statistics.clearances",
            "clearances",
        ],
    )
    transformed["blocks"] = _coalesce(
        raw_df,
        [
            "statistics__blockedShots",
            "statistics.blockedShots",
            "blockedShots",
            "statistics__blocks",
            "statistics.blocks",
            "blocks",
        ],
    )
    transformed["recoveries"] = _coalesce(
        raw_df,
        [
            "statistics__ballRecovery",
            "statistics.ballRecovery",
            "ballRecovery",
            "statistics__recoveries",
            "statistics.recoveries",
            "recoveries",
        ],
    )
    transformed["duels_won"] = _coalesce(
        raw_df,
        [
            "statistics__duelsWon",
            "statistics.duelsWon",
            "duelsWon",
            "duels_won",
        ],
    )
    transformed["aerial_duels_won"] = _coalesce(
        raw_df,
        [
            "statistics__aerialDuelsWon",
            "statistics.aerialDuelsWon",
            "aerialDuelsWon",
            "aerial_duels_won",
        ],
    )
    transformed["fouls_committed"] = _coalesce(
        raw_df,
        [
            "statistics__foulsCommitted",
            "statistics.foulsCommitted",
            "foulsCommitted",
            "fouls_committed",
        ],
    )
    transformed["fouls_won"] = _coalesce(
        raw_df,
        [
            "statistics__wasFouled",
            "statistics.wasFouled",
            "wasFouled",
            "statistics__foulsWon",
            "statistics.foulsWon",
            "foulsWon",
            "fouls_won",
        ],
    )

    for column in transformed.columns:
        if column in {"source", "season", "league", "name", "team", position_column, country_column}:
            transformed[column] = _clean_text(transformed[column])

    for column in {
        "source_player_id",
        source_team_column,
        minutes_column,
        games_column,
        "rating",
        "yellow_cards",
        "red_cards",
        "tackles",
        "interceptions",
        "clearances",
        "blocks",
        "recoveries",
        "duels_won",
        "aerial_duels_won",
        "fouls_committed",
        "fouls_won",
    }:
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
        column
        for column in ["source", "source_player_id", "season", "team"]
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

    merged = df[existing].copy()
    merged = merged.replace({"": pd.NA})

    if len(existing) == 1:
        return merged.iloc[:, 0]

    return merged.bfill(axis=1).iloc[:, 0]


def _clean_text(series: pd.Series) -> pd.Series:
    text = series.astype("string")
    text = text.str.strip()
    return text.replace({"": pd.NA})