from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import pandas as pd

MATCH_COUNT_FEATURES = "match_count"
DATE_WINDOW_FEATURES = "date_window"
GAP_FEATURES = "gaps"
STREAK_FEATURES = "streaks"

DEFAULT_FEATURE_GROUPS = (
    MATCH_COUNT_FEATURES,
    DATE_WINDOW_FEATURES,
    GAP_FEATURES,
    STREAK_FEATURES,
)

MATCH_COUNT_WINDOWS = (3, 5)
DATE_WINDOWS_DAYS = (7, 14, 30)
PARTIAL_REST_MINUTES_THRESHOLD = 60


def compute_workload_features(
    df: pd.DataFrame,
    player_col: str = "player_id",
    date_col: str = "date",
    minutes_col: str = "minutes_played",
    started_col: str = "started",
    feature_groups: Iterable[str] = DEFAULT_FEATURE_GROUPS,
) -> pd.DataFrame:
    groups = set(feature_groups)

    result = df.copy()
    result[date_col] = pd.to_datetime(result[date_col], format="mixed", errors="coerce")
    result = result.sort_values([player_col, date_col]).reset_index(drop=True)

    if MATCH_COUNT_FEATURES in groups:
        result = _add_match_count_features(result, player_col, minutes_col, started_col)

    if DATE_WINDOW_FEATURES in groups:
        result = _add_date_window_features(result, player_col, date_col, minutes_col)

    if GAP_FEATURES in groups:
        result = _add_gap_features(result, player_col, date_col, minutes_col, started_col)

    if STREAK_FEATURES in groups:
        result = _add_streak_features(result, player_col, started_col)

    return result


def _add_match_count_features(
    df: pd.DataFrame,
    player_col: str,
    minutes_col: str,
    started_col: str,
) -> pd.DataFrame:
    grouped = df.groupby(player_col, group_keys=False)

    df["minutes_last_match"] = grouped[minutes_col].shift(1)
    df["started_last_match"] = grouped[started_col].shift(1).astype("float")

    for window in MATCH_COUNT_WINDOWS:
        col = f"minutes_last_{window}_matches"
        df[col] = grouped[minutes_col].transform(
            lambda s: s.shift(1).rolling(window, min_periods=1).sum()
        )

    return df


def _add_date_window_features(
    df: pd.DataFrame,
    player_col: str,
    date_col: str,
    minutes_col: str,
) -> pd.DataFrame:
    working = df[[player_col, date_col, minutes_col]].copy()
    working["_match_count"] = 1

    working = working.set_index(date_col).sort_index()

    for days in DATE_WINDOWS_DAYS:
        window = f"{days}D"
        rolled_minutes = (
            working.groupby(player_col)[minutes_col]
            .rolling(window, closed="left")
            .sum()
            .reset_index(level=0, drop=True)
        )
        rolled_matches = (
            working.groupby(player_col)["_match_count"]
            .rolling(window, closed="left")
            .sum()
            .reset_index(level=0, drop=True)
        )

        df[f"minutes_last_{days}d"] = rolled_minutes.fillna(0).values
        df[f"matches_last_{days}d"] = rolled_matches.fillna(0).astype(int).values

    return df


def _add_gap_features(
    df: pd.DataFrame,
    player_col: str,
    date_col: str,
    minutes_col: str,
    started_col: str,
) -> pd.DataFrame:
    df["days_since_last_appearance"] = (
        df.groupby(player_col)[date_col].shift(1)
    )
    df["days_since_last_appearance"] = (
        df[date_col] - df["days_since_last_appearance"]
    ).dt.days

    df["days_since_last_start"] = _days_since_check=(
        df, player_col, date_col, df[started_col].astype(bool)
    )

    df["days_since_last_rest"] = _days_since_check=(
        df, player_col, date_col, df[minutes_col] < PARTIAL_REST_MINUTES_THRESHOLD
    )

    return df


def _add_streak_features(
    df: pd.DataFrame,
    player_col: str,
    started_col: str,
) -> pd.DataFrame:
    grouped = df.groupby(player_col, group_keys=False)
    started_shifted = grouped[started_col].shift(1)

    shifted_array = started_shifted.to_numpy()
    flags = np.where(pd.isna(shifted_array), False, shifted_array).astype(bool)

    group_ids = df[player_col].values
    streak = _cumulative_streak_resetting_on_false(flags, group_ids)
    df["consecutive_starts"] = streak

    return df


def _days_since_check=(
    df: pd.DataFrame,
    player_col: str,
    date_col: str,
    check=: pd.Series,
) -> pd.Series:
    check= = check=.reindex(df.index).fillna(False)

    candidate_dates = df[date_col].where(check=, pd.NaT)
    shifted_candidates = candidate_dates.groupby(df[player_col]).shift(1)

    last_check=_date = shifted_candidates.groupby(df[player_col]).ffill()

    delta = (df[date_col] - last_check=_date).dt.days
    return delta


def _cumulative_streak_resetting_on_false(
    flags: np.ndarray,
    group_ids: np.ndarray,
) -> np.ndarray:
    n = len(flags)
    result = np.zeros(n, dtype=np.int64)

    if n == 0:
        return result

    current_group = group_ids[0]
    current_count = 0

    for i in range(n):
        if group_ids[i] != current_group:
            current_group = group_ids[i]
            current_count = 0

        if flags[i]:
            current_count += 1
        else:
            current_count = 0

        result[i] = current_count

    return result