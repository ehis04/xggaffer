from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from apps.predictions.ml.features.player_workload import compute_workload_features
from apps.predictions.ml.models.availability.config import (
    INJURY_SPELLS_PATH,
    LINEUP_DIR,
    PLAYER_DOBS_PATH,
    PLAYER_ID_MAPPING_PATH,
    UNDERSTAT_PLAYERS_PATH,
    UNDERSTAT_SOURCE_FILTER,
)

logger = logging.getLogger(__name__)

ACTIVE_PLAYER_RECENT_DAYS = 60
DEFAULT_AGE_FALLBACK = 25.0
PEAK_SEASON_START_MONTH = 11
PEAK_SEASON_END_MONTH = 3


def get_team_availability_features(
    team_name: str,
    league: str,
    season: int,
    target_date: date,
) -> pd.DataFrame:
    lineups = _load_team_lineups(team_name=team_name, league=league, season=season)
    if lineups.empty:
        return pd.DataFrame()

    lineups_with_workload = compute_workload_features(lineups)

    latest_per_player = (
        lineups_with_workload.sort_values(["player_id", "date"])
        .groupby("player_id")
        .tail(1)
        .reset_index(drop=True)
    )

    latest_observed_date = latest_per_player["date"].max()
    reference_date = pd.Timestamp(target_date)
    if pd.notna(latest_observed_date):
        # Historical season requests often use today's date. Anchor recency to
        # the latest observed lineup date so we still return the active squad.
        reference_date = min(reference_date, latest_observed_date)

    cutoff_date = reference_date - pd.Timedelta(days=ACTIVE_PLAYER_RECENT_DAYS)
    active_players = latest_per_player[latest_per_player["date"] >= cutoff_date].copy()

    if active_players.empty:
        return pd.DataFrame()

    dobs = _load_player_dobs()
    spells = _load_team_injury_spells(player_ids=active_players["player_id"].unique())

    active_players = active_players.merge(dobs, left_on="player_id", right_on="understat_player_id", how="left")
    active_players["age"] = _compute_age(active_players["dob"], target_date)

    injury_status = _build_injury_status(spells, target_date)
    active_players = active_players.merge(injury_status, on="player_id", how="left")

    active_players["is_injured"] = active_players["injury_start_date"].notna()
    active_players["has_prior_injury"] = (
        active_players["prior_injuries_count"].fillna(0) > 0
    )
    active_players["has_recent_rest"] = active_players["days_since_last_rest"].notna()

    active_players["is_peak_season"] = _is_peak_season_flag(target_date)

    active_players = _add_engineered_inference_features(active_players)
    active_players = _add_season_phase_inference(active_players, target_date)

    active_players["matches_in_prior_30d"] = active_players["matches_last_30d"].fillna(0)
    active_players["minutes_in_prior_30d"] = active_players["minutes_last_30d"].fillna(0)
    active_players["player_age"] = active_players["age"]

    return active_players


def _load_team_lineups(team_name: str, league: str, season: int) -> pd.DataFrame:
    path = LINEUP_DIR / f"{league}_{season}_lineups.csv"
    if not path.exists():
        logger.warning("Lineup file not found: %s", path)
        return pd.DataFrame()

    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], format="mixed", errors="coerce")

    understat_players = pd.read_csv(UNDERSTAT_PLAYERS_PATH)
    understat_players = understat_players[
        (understat_players["source"] == UNDERSTAT_SOURCE_FILTER)
        & (understat_players["league"] == league)
        & (understat_players["season"] == season)
        & (understat_players["team"] == team_name)
    ]
    target_player_ids = set(understat_players["source_player_id"].astype(int))

    return df[df["player_id"].isin(target_player_ids)].copy()


def _load_player_dobs() -> pd.DataFrame:
    df = pd.read_csv(PLAYER_DOBS_PATH)
    df["dob"] = pd.to_datetime(df["dob"], errors="coerce")
    df = df.dropna(subset=["understat_player_id"]).copy()
    df["understat_player_id"] = df["understat_player_id"].astype(int)
    return df[["understat_player_id", "dob"]].drop_duplicates(subset=["understat_player_id"])


def _load_team_injury_spells(player_ids: np.ndarray) -> pd.DataFrame:
    df = pd.read_csv(INJURY_SPELLS_PATH)
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
    df = df.dropna(subset=["start_date", "understat_player_id"]).copy()
    df["understat_player_id"] = df["understat_player_id"].astype(int)
    return df[df["understat_player_id"].isin(player_ids)].copy()


def _build_injury_status(spells: pd.DataFrame, target_date: date) -> pd.DataFrame:
    target_ts = pd.Timestamp(target_date)
    rows: list[dict] = []

    for player_id, group in spells.groupby("understat_player_id"):
        prior = group[group["start_date"] < target_ts].sort_values("start_date")
        prior_count = len(prior)

        ongoing_mask = (
            (prior["end_date"].isna() | (prior["end_date"] >= target_ts))
            & (prior["start_date"] <= target_ts)
        )
        ongoing = prior[ongoing_mask]

        if not ongoing.empty:
            current = ongoing.iloc[-1]
            row = {
                "player_id": int(player_id),
                "injury_start_date": current["start_date"].date().isoformat(),
                "injury_type_category": current["injury_type_category"],
                "prior_injuries_count": prior_count - len(ongoing),
                "days_since_last_injury": np.nan,
            }
        else:
            last_completed = prior[prior["end_date"].notna()].sort_values("end_date").tail(1)
            days_since = (
                float((target_ts - last_completed["end_date"].iloc[0]).days)
                if not last_completed.empty
                else np.nan
            )
            row = {
                "player_id": int(player_id),
                "injury_start_date": None,
                "injury_type_category": None,
                "prior_injuries_count": prior_count,
                "days_since_last_injury": days_since,
            }
        rows.append(row)

    if not rows:
        return pd.DataFrame(columns=[
            "player_id", "injury_start_date", "injury_type_category",
            "prior_injuries_count", "days_since_last_injury",
        ])
    return pd.DataFrame(rows)


def _compute_age(dobs: pd.Series, target: date) -> pd.Series:
    target_ts = pd.Timestamp(target)
    delta_days = (target_ts - dobs).dt.days
    age = delta_days / 365.25
    return age.fillna(DEFAULT_AGE_FALLBACK)


def _is_peak_season_flag(target: date) -> int:
    month = target.month
    return int(month >= PEAK_SEASON_START_MONTH or month <= PEAK_SEASON_END_MONTH)


def _add_engineered_inference_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    chronic_baseline = df["minutes_last_30d"].clip(lower=1) / 4.0
    df["acwr_7_28"] = df["minutes_last_7d"] / chronic_baseline

    df["minutes_per_match_30d"] = np.where(
        df["matches_last_30d"] > 0,
        df["minutes_last_30d"] / df["matches_last_30d"].clip(lower=1),
        0.0,
    )
    df["recent_match_density"] = df["matches_last_14d"] / 2.0
    df["workload_zscore_30d"] = 0.0
    df["cumulative_workload_per_week"] = df["minutes_last_30d"] / 4.0

    return df


def _add_season_phase_inference(df: pd.DataFrame, target: date) -> pd.DataFrame:
    month = target.month
    if month in (8, 9, 10):
        early, mid, late = 1, 0, 0
    elif month in (11, 12, 1, 2):
        early, mid, late = 0, 1, 0
    else:
        early, mid, late = 0, 0, 1

    df = df.copy()
    df["season_phase_mid"] = mid
    df["season_phase_late"] = late
    return df