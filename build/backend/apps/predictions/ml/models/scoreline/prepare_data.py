from __future__ import annotations

import numpy as np
import pandas as pd

from ml.engines.elo import compute_elo_history
from ml.features.rolling import build_all_features
from ml.models.scoreline.config import (
    DEFAULT_TIME_DECAY_RATE,
    SCORE_ENGINE_LEAGUES,
    SCORE_ENGINE_SEASONS,
    TEST_SEASONS,
)


def prepare_score_dataset(
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
) -> pd.DataFrame:
    leagues = leagues or SCORE_ENGINE_LEAGUES
    seasons = seasons or SCORE_ENGINE_SEASONS

    df = build_all_features(leagues, seasons)

    elo_history, _ = compute_elo_history(df)
    elo_df = pd.DataFrame(elo_history)[["match_id", "elo_difference"]]
    df = df.merge(elo_df, on="match_id", how="left")

    for col in ("home_goals", "away_goals"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["home_goals", "away_goals"])
    df["home_goals"] = df["home_goals"].astype(int)
    df["away_goals"] = df["away_goals"].astype(int)

    return df


def get_temporal_split(
    df: pd.DataFrame,
    test_seasons: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    test_seasons = test_seasons or TEST_SEASONS
    train = df[~df["season"].astype(str).isin(test_seasons)]
    test = df[df["season"].astype(str).isin(test_seasons)]
    return train, test


def compute_match_weights(
    df: pd.DataFrame,
    decay_rate: float = DEFAULT_TIME_DECAY_RATE,
) -> np.ndarray:
    dates = pd.to_datetime(df["date"])
    max_date = dates.max()
    weeks_ago = (max_date - dates).dt.days / 7.0
    return np.exp(-decay_rate * weeks_ago.values)


if __name__ == "__main__":
    df = prepare_score_dataset()
    print(f"Dataset shape: {df.shape}")
    print(f"\nGoal distributions:")
    print(df[["home_goals", "away_goals"]].describe().round(2))
    print(f"\nSeasons: {sorted(df['season'].unique())}")
    print(f"Leagues: {sorted(df['league'].unique())}")
    print(f"\nElo difference range: {df['elo_difference'].min():.1f} to {df['elo_difference'].max():.1f}")

    feature_check = ["home_rolling_xg_10", "away_rolling_xga_10", "elo_difference"]
    for col in feature_check:
        non_null = df[col].notna().sum()
        print(f"{col}: {non_null}/{len(df)} non-null")