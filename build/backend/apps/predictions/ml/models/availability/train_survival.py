from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from lifelines.utils import concordance_index

from apps.predictions.ml.models.availability.config import (
    DURATION_COL,
    EVENT_COL,
    MODELS_DIR,
    SURVIVAL_DATASET_PATH,
    SURVIVAL_FEATURES,
)
from apps.predictions.ml.models.availability.runtime import ensure_workspace_venv

logger = logging.getLogger(__name__)

TRAIN_SEASON_MAX = 2023
TEST_SEASON = 2024
DEFAULT_PENALIZER = 0.1
HAS_PRIOR_INJURY_COL = "has_prior_injury"
MODEL_VERSION = "v1"
MODEL_NAME_PREFIX = "survival_cox"


def load_survival_dataset(path: Path = SURVIVAL_DATASET_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
    return df


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df[HAS_PRIOR_INJURY_COL] = df["days_since_last_injury"].notna().astype(int)

    median_gap = df["days_since_last_injury"].median()
    df["days_since_last_injury"] = df["days_since_last_injury"].fillna(median_gap)

    df["player_age"] = df["player_age"].fillna(df["player_age"].median())
    df["matches_in_prior_30d"] = df["matches_in_prior_30d"].fillna(0)
    df["minutes_in_prior_30d"] = df["minutes_in_prior_30d"].fillna(0)

    return df


def temporal_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_df = df[df["season"] <= TRAIN_SEASON_MAX].copy()
    test_df = df[df["season"] == TEST_SEASON].copy()
    return train_df, test_df


def build_model_matrix(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    columns = feature_cols + [DURATION_COL, EVENT_COL]
    return df[columns].copy()


def train_cox_model(
    train_df: pd.DataFrame,
    feature_cols: list[str],
    penalizer: float = DEFAULT_PENALIZER,
) -> CoxPHFitter:
    matrix = build_model_matrix(train_df, feature_cols)
    matrix = matrix.dropna()

    cph = CoxPHFitter(penalizer=penalizer)
    cph.fit(matrix, duration_col=DURATION_COL, event_col=EVENT_COL)
    return cph


def evaluate_cox_model(
    cph: CoxPHFitter,
    test_df: pd.DataFrame,
    feature_cols: list[str],
) -> dict:
    matrix = build_model_matrix(test_df, feature_cols)
    matrix = matrix.dropna()

    if matrix.empty:
        return {"c_index": float("nan"), "test_size": 0}

    partial_hazard = cph.predict_partial_hazard(matrix)
    c_index = concordance_index(
        matrix[DURATION_COL],
        -partial_hazard,
        matrix[EVENT_COL],
    )
    return {"c_index": c_index, "test_size": len(matrix)}


def search_penalizer(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_cols: list[str],
    candidates: tuple[float, ...] = (0.01, 0.1, 1.0),
) -> tuple[float, dict]:
    best_penalizer = candidates[0]
    best_score = -np.inf
    best_metrics: dict = {}

    for penalizer in candidates:
        cph = train_cox_model(train_df, feature_cols, penalizer=penalizer)
        metrics = evaluate_cox_model(cph, test_df, feature_cols)
        logger.info("penalizer=%.3f -> c_index=%.4f", penalizer, metrics["c_index"])

        if metrics["c_index"] > best_score:
            best_score = metrics["c_index"]
            best_penalizer = penalizer
            best_metrics = metrics

    return best_penalizer, best_metrics


def save_model(cph: CoxPHFitter, feature_cols: list[str], median_gap: float) -> Path:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = MODELS_DIR / f"{MODEL_NAME_PREFIX}_{MODEL_VERSION}_{timestamp}.joblib"

    artifact = {
        "model": cph,
        "feature_columns": feature_cols,
        "imputation": {"days_since_last_injury_median": median_gap},
        "trained_at": timestamp,
    }
    joblib.dump(artifact, output_path)
    return output_path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    df = load_survival_dataset()
    logger.info("Loaded survival dataset: %d rows", len(df))

    df = prepare_features(df)
    median_gap = df["days_since_last_injury"].median()

    feature_cols = SURVIVAL_FEATURES + [HAS_PRIOR_INJURY_COL]

    train_df, test_df = temporal_split(df)
    logger.info("Train: %d rows | Test: %d rows", len(train_df), len(test_df))

    if len(test_df) == 0:
        logger.warning("Test split is empty - check temporal boundary")

    best_penalizer, best_metrics = search_penalizer(train_df, test_df, feature_cols)
    logger.info("Best penalizer: %.3f (c_index=%.4f)", best_penalizer, best_metrics["c_index"])

    final_model = train_cox_model(train_df, feature_cols, penalizer=best_penalizer)

    print()
    print("=== COX PH MODEL SUMMARY ===")
    final_model.print_summary()
    print()
    print(f"Test C-index: {best_metrics['c_index']:.4f}")
    print(f"Test size: {best_metrics['test_size']}")
    print(f"Baseline C-index (random): 0.50")

    output_path = save_model(final_model, feature_cols, median_gap)
    print()
    print(f"Saved model: {output_path}")


if __name__ == "__main__":
    ensure_workspace_venv("apps.predictions.ml.models.availability.train_survival")
    main()