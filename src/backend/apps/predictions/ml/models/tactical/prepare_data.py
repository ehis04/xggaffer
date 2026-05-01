from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from apps.predictions.ml.models.tactical.config import (
    MAX_GOAL_DIFF_CLIP,
    MIN_PASSES_FOR_DIRECTIONAL,
    MIN_PASSES_FOR_ZONE,
    PASS_EVENTS_PATH,
    PASS_FEATURES,
    PASS_HEIGHT_ENCODING,
    PROCESSED_DIR,
    RARE_CATEGORY_LABEL,
    RARE_TECHNIQUE_THRESHOLD,
    TARGET,
    ZONE_COUNT,
    ZONE_PROFILES_PATH,
)


logger = logging.getLogger(__name__)

LA_LIGA_NAME = "La Liga"
CHAMPIONS_LEAGUE_NAME = "Champions League"

TEST_SEASON_NAMES = ["2018/2019", "2019/2020", "2020/2021"]

BODY_PART_REFERENCE = "Right Foot"
BODY_PART_KEEP = ["Left Foot", "Head", "Other"]

TECHNIQUE_REFERENCE = "Normal"

UNKNOWN_HEIGHT_DEFAULT = 0


def load_pass_events(path: Path = PASS_EVENTS_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


def _encode_pass_height(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["pass_height_encoded"] = (
        df["pass_height"].map(PASS_HEIGHT_ENCODING).fillna(UNKNOWN_HEIGHT_DEFAULT).astype(int)
    )
    return df


def _consolidate_body_part(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["body_part_clean"] = df["body_part"].fillna("Unknown")
    df.loc[
        ~df["body_part_clean"].isin(["Left Foot", "Right Foot", "Head"]),
        "body_part_clean",
    ] = "Other"
    return df


def _consolidate_technique(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["pass_technique_clean"] = df["pass_technique"].fillna(TECHNIQUE_REFERENCE)
    counts = df["pass_technique_clean"].value_counts(normalize=True)
    rare = set(counts[counts < RARE_TECHNIQUE_THRESHOLD].index)
    df.loc[df["pass_technique_clean"].isin(rare), "pass_technique_clean"] = RARE_CATEGORY_LABEL
    return df


def _one_hot_body_part(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    df = df.copy()
    new_cols = []
    for value in BODY_PART_KEEP:
        col = f"body_part_{value.lower().replace(' ', '_')}"
        df[col] = (df["body_part_clean"] == value).astype(int)
        new_cols.append(col)
    return df, new_cols


def _one_hot_technique(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    df = df.copy()
    techniques = sorted(t for t in df["pass_technique_clean"].unique() if t != TECHNIQUE_REFERENCE)
    new_cols = []
    for value in techniques:
        col = f"pass_technique_{value.lower().replace(' ', '_').replace('-', '_')}"
        df[col] = (df["pass_technique_clean"] == value).astype(int)
        new_cols.append(col)
    return df, new_cols


def _clip_goal_diff(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["game_state_goal_diff"] = df["game_state_goal_diff"].clip(
        lower=-MAX_GOAL_DIFF_CLIP, upper=MAX_GOAL_DIFF_CLIP
    )
    return df


def _coerce_booleans(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["under_pressure"] = df["under_pressure"].fillna(False).astype(int)
    df["is_forward_pass"] = df["is_forward_pass"].fillna(False).astype(int)
    return df


def _temporal_split(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    is_la_liga = df["competition_name"] == LA_LIGA_NAME
    is_test_season = df["season_name"].isin(TEST_SEASON_NAMES)

    test_mask = is_la_liga & is_test_season
    train_mask = ~test_mask

    train_df = df[train_mask].copy()
    test_df = df[test_mask].copy()
    return train_df, test_df


def build_pass_dataset(
    path: Path = PASS_EVENTS_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    df = load_pass_events(path)
    logger.info("Loaded %d pass rows", len(df))

    df = _encode_pass_height(df)
    df = _consolidate_body_part(df)
    df = _consolidate_technique(df)
    df, body_part_cols = _one_hot_body_part(df)
    df, technique_cols = _one_hot_technique(df)
    df = _clip_goal_diff(df)
    df = _coerce_booleans(df)

    feature_cols = list(PASS_FEATURES) + body_part_cols + technique_cols

    keep_cols = feature_cols + [
        TARGET,
        "match_id",
        "season_id",
        "season_name",
        "competition_name",
        "team_id",
        "team_name",
    ]
    df = df[keep_cols].copy()

    df = df.dropna(subset=feature_cols + [TARGET])

    train_df, test_df = _temporal_split(df)

    logger.info(
        "Train: %d rows (completion=%.4f) | Test: %d rows (completion=%.4f)",
        len(train_df),
        train_df[TARGET].mean(),
        len(test_df),
        test_df[TARGET].mean(),
    )
    logger.info("Feature count: %d", len(feature_cols))

    return train_df, test_df, feature_cols


def build_zone_profiles(
    path: Path = PASS_EVENTS_PATH,
    output_path: Path = ZONE_PROFILES_PATH,
) -> pd.DataFrame:
    df = load_pass_events(path)
    logger.info("Loaded %d pass rows for zone profile aggregation", len(df))

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    df["is_forward_pass_int"] = df["is_forward_pass"].astype(int)

    grouped = df.groupby(["match_id", "team_id"])

    profile_rows = []
    for (match_id, team_id), group in grouped:
        match_completion = group[TARGET].mean()
        match_forward = group["is_forward_pass_int"].mean()
        match_length = group["pass_length"].mean()
        total_passes = len(group)

        zone_agg = group.groupby("zone_id").agg(
            zone_total=("pass_completed", "size"),
            zone_completed=("pass_completed", "sum"),
            zone_forward=("is_forward_pass_int", "sum"),
            zone_length=("pass_length", "mean"),
        )

        row = {
            "match_id": match_id,
            "team_id": team_id,
            "team_name": group["team_name"].iloc[0],
            "competition_name": group["competition_name"].iloc[0],
            "season_id": group["season_id"].iloc[0],
            "season_name": group["season_name"].iloc[0],
            "overall_completion_rate": match_completion,
            "overall_forward_ratio": match_forward,
            "overall_pass_length": match_length,
            "total_passes": total_passes,
        }

        for zone_id in range(ZONE_COUNT):
            if zone_id in zone_agg.index:
                z_total = int(zone_agg.loc[zone_id, "zone_total"])
                z_completed = int(zone_agg.loc[zone_id, "zone_completed"])
                z_forward = int(zone_agg.loc[zone_id, "zone_forward"])
                z_length = float(zone_agg.loc[zone_id, "zone_length"])
            else:
                z_total = 0
                z_completed = 0
                z_forward = 0
                z_length = match_length

            if z_total >= MIN_PASSES_FOR_ZONE:
                success_rate = z_completed / z_total
            else:
                success_rate = match_completion

            if z_total >= MIN_PASSES_FOR_DIRECTIONAL:
                forward_ratio = z_forward / z_total
                mean_length = z_length
            else:
                forward_ratio = match_forward
                mean_length = match_length

            volume = z_total / total_passes if total_passes > 0 else 0.0

            row[f"zone_{zone_id}_success_rate"] = success_rate
            row[f"zone_{zone_id}_pass_volume"] = volume
            row[f"zone_{zone_id}_forward_ratio"] = forward_ratio
            row[f"zone_{zone_id}_mean_length"] = mean_length

        profile_rows.append(row)

    profiles = pd.DataFrame(profile_rows)
    profiles.to_csv(output_path, index=False)
    logger.info("Saved %d team-match zone profiles to %s", len(profiles), output_path)
    return profiles

def build_team_season_profiles(
    team_match_profiles: pd.DataFrame,
    output_path: Path = None,
) -> pd.DataFrame:
    from apps.predictions.ml.models.tactical.config import (
        MIN_MATCHES_FOR_TEAM_SEASON,
        TEAM_SEASON_PROFILES_PATH,
    )

    if output_path is None:
        output_path = TEAM_SEASON_PROFILES_PATH

    feature_cols = (
        [f"zone_{i}_success_rate" for i in range(ZONE_COUNT)]
        + [f"zone_{i}_pass_volume" for i in range(ZONE_COUNT)]
        + [f"zone_{i}_forward_ratio" for i in range(ZONE_COUNT)]
        + [f"zone_{i}_mean_length" for i in range(ZONE_COUNT)]
        + ["overall_completion_rate", "overall_forward_ratio", "overall_pass_length"]
    )

    grouped = team_match_profiles.groupby(["team_id", "season_id"])

    season_rows = []
    for (team_id, season_id), group in grouped:
        if len(group) < MIN_MATCHES_FOR_TEAM_SEASON:
            continue
        row = {
            "team_id": team_id,
            "season_id": season_id,
            "team_name": group["team_name"].iloc[0],
            "competition_name": group["competition_name"].iloc[0],
            "season_name": group["season_name"].iloc[0],
            "n_matches": len(group),
        }
        for col in feature_cols:
            row[col] = group[col].mean()
        season_rows.append(row)

    profiles = pd.DataFrame(season_rows)
    profiles.to_csv(output_path, index=False)
    logger.info(
        "Saved %d team-season zone profiles to %s", len(profiles), output_path
    )
    return profiles


def get_clustering_feature_columns() -> list[str]:
    return (
        [f"zone_{i}_success_rate" for i in range(ZONE_COUNT)]
        + [f"zone_{i}_pass_volume" for i in range(ZONE_COUNT)]
        + [f"zone_{i}_forward_ratio" for i in range(ZONE_COUNT)]
        + [f"zone_{i}_mean_length" for i in range(ZONE_COUNT)]
    )

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    print()
    print("=== PART A: PASS FEATURE MATRIX ===")
    train_df, test_df, feature_cols = build_pass_dataset()
    print(f"Feature columns ({len(feature_cols)}):")
    for f in feature_cols:
        print(f"  {f}")
    print()
    print(f"Train rows:           {len(train_df):,}")
    print(f"Test rows:            {len(test_df):,}")
    print(f"Train completion:     {train_df[TARGET].mean():.4f}")
    print(f"Test completion:      {test_df[TARGET].mean():.4f}")
    print()
    print("Train season distribution:")
    print(train_df.groupby(["competition_name", "season_name"]).size().to_string())
    print()
    print("Test season distribution:")
    print(test_df.groupby(["competition_name", "season_name"]).size().to_string())

    print()
    print("=== PART B: TEAM-MATCH ZONE PROFILES ===")
    profiles = build_zone_profiles()
    print(f"Profiles shape:       {profiles.shape}")
    print(f"Unique teams:         {profiles['team_name'].nunique()}")
    print(f"Unique matches:       {profiles['match_id'].nunique()}")
    print()
    print("Pass volume row sums (should be ~1.0):")
    volume_cols = [f"zone_{i}_pass_volume" for i in range(ZONE_COUNT)]
    volume_sums = profiles[volume_cols].sum(axis=1)
    print(f"  min={volume_sums.min():.6f}  mean={volume_sums.mean():.6f}  max={volume_sums.max():.6f}")
    print()
    print("Forward ratio summary (selected zones):")
    forward_cols = [f"zone_{i}_forward_ratio" for i in [0, 5, 10, 14, 20]]
    print(profiles[forward_cols].describe().T[["min", "mean", "max"]].to_string())

    print()
    print("=== PART C: TEAM-SEASON ZONE PROFILES ===")
    season_profiles = build_team_season_profiles(profiles)
    print(f"Season profiles shape: {season_profiles.shape}")
    print(f"Unique teams:          {season_profiles['team_name'].nunique()}")
    print(f"Unique seasons:        {season_profiles['season_name'].nunique()}")
    print()
    print("Matches per team-season:")
    print(season_profiles["n_matches"].describe())

if __name__ == "__main__":
    main()