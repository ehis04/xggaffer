from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    classification_report,
    precision_recall_curve,
)
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from apps.predictions.ml.models.availability.config import (
    MODELS_DIR,
    RISK_DATASET_PATH,
    RISK_FEATURES,
    RISK_TARGET,
)

logger = logging.getLogger(__name__)

TRAIN_SEASON_MAX = 2023
TEST_SEASON = 2024
HAS_PRIOR_INJURY_COL = "has_prior_injury"
HAS_RECENT_REST_COL = "has_recent_rest"
MAX_ITER = 1000
DEFAULT_THRESHOLD = 0.50
TARGET_PRECISION_FOR_RECALL = 0.20
DECILE_COUNT = 10
MODEL_VERSION = "v1"
MODEL_NAME_PREFIX = "injury_risk"

XGB_PARAMS = {
    "n_estimators": 300,
    "max_depth": 5,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "objective": "binary:logistic",
    "eval_metric": "aucpr",
    "tree_method": "hist",
    "n_jobs": -1,
    "random_state": 42,
}

CALIBRATION_CV_FOLDS = 3
CALIBRATION_METHOD = "isotonic"


def load_risk_dataset(path: Path = RISK_DATASET_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")
    return df


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = df.copy()

    df[HAS_PRIOR_INJURY_COL] = df["days_since_last_injury"].notna().astype(int)
    df[HAS_RECENT_REST_COL] = df["days_since_last_rest"].notna().astype(int)

    age_median = df["age"].median()
    df["age"] = df["age"].fillna(age_median)

    rest_median = df["days_since_last_rest"].median()
    df["days_since_last_rest"] = df["days_since_last_rest"].fillna(rest_median)

    injury_gap_median = df["days_since_last_injury"].median()
    df["days_since_last_injury"] = df["days_since_last_injury"].fillna(injury_gap_median)

    zscore_median = df["workload_zscore_30d"].median()
    if pd.isna(zscore_median):
        zscore_median = 0.0
    df["workload_zscore_30d"] = df["workload_zscore_30d"].fillna(zscore_median)

    df["acwr_7_28"] = df["acwr_7_28"].fillna(0)
    df["minutes_per_match_30d"] = df["minutes_per_match_30d"].fillna(0)
    df["recent_match_density"] = df["recent_match_density"].fillna(0)
    df["cumulative_workload_per_week"] = df["cumulative_workload_per_week"].fillna(0)

    imputation_params = {
        "age_median": float(age_median),
        "days_since_last_rest_median": float(rest_median),
        "days_since_last_injury_median": float(injury_gap_median),
        "workload_zscore_median": float(zscore_median),
    }

    return df, imputation_params


def temporal_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_df = df[df["season"] <= TRAIN_SEASON_MAX].copy()
    test_df = df[df["season"] == TEST_SEASON].copy()
    return train_df, test_df


def build_feature_columns() -> list[str]:
    return RISK_FEATURES + [HAS_PRIOR_INJURY_COL, HAS_RECENT_REST_COL]


def train_logistic_regression(
    train_df: pd.DataFrame,
    feature_cols: list[str],
) -> tuple[LogisticRegression, StandardScaler]:
    X_train = train_df[feature_cols].values
    y_train = train_df[RISK_TARGET].values

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)

    model = LogisticRegression(
        class_weight="balanced",
        max_iter=MAX_ITER,
        solver="lbfgs",
    )
    model.fit(X_train_scaled, y_train)
    return model, scaler


def train_xgboost(
    train_df: pd.DataFrame,
    feature_cols: list[str],
) -> CalibratedClassifierCV:
    X_train = train_df[feature_cols].values
    y_train = train_df[RISK_TARGET].values

    pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    params = {**XGB_PARAMS, "scale_pos_weight": pos_weight}

    base_model = XGBClassifier(**params)
    calibrated = CalibratedClassifierCV(
        estimator=base_model,
        method=CALIBRATION_METHOD,
        cv=CALIBRATION_CV_FOLDS,
    )
    calibrated.fit(X_train, y_train)
    return calibrated


def evaluate_model_proba(
    y_proba: np.ndarray,
    y_test: np.ndarray,
) -> dict:
    pr_auc = average_precision_score(y_test, y_proba)
    brier = brier_score_loss(y_test, y_proba)
    mean_proba = float(y_proba.mean())

    precisions, recalls, _ = precision_recall_curve(y_test, y_proba)
    recall_at_target = _recall_at_precision(precisions, recalls, TARGET_PRECISION_FOR_RECALL)

    y_pred = (y_proba >= DEFAULT_THRESHOLD).astype(int)
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    decile_lift = _compute_decile_lift(y_proba, y_test)

    return {
        "pr_auc": pr_auc,
        "brier": brier,
        "mean_proba": mean_proba,
        "recall_at_p20": recall_at_target,
        "test_size": len(y_test),
        "positive_rate": float(y_test.mean()),
        "classification_report": report,
        "decile_lift": decile_lift,
    }


def _recall_at_precision(
    precisions: np.ndarray,
    recalls: np.ndarray,
    target_precision: float,
) -> float:
    valid_mask = precisions >= target_precision
    if not valid_mask.any():
        return 0.0
    return float(recalls[valid_mask].max())


def _compute_decile_lift(y_proba: np.ndarray, y_true: np.ndarray) -> pd.DataFrame:
    base_rate = y_true.mean()
    df = pd.DataFrame({"proba": y_proba, "y": y_true})
    df["decile"] = pd.qcut(df["proba"], q=DECILE_COUNT, labels=False, duplicates="drop")

    grouped = df.groupby("decile").agg(
        n=("y", "size"),
        injury_rate=("y", "mean"),
        mean_proba=("proba", "mean"),
    ).reset_index()
    grouped["lift"] = grouped["injury_rate"] / base_rate if base_rate > 0 else 0
    return grouped


def lr_feature_importances(
    model: LogisticRegression,
    feature_cols: list[str],
) -> pd.DataFrame:
    coefs = model.coef_[0]
    df = pd.DataFrame({
        "feature": feature_cols,
        "coefficient": coefs,
        "abs_coefficient": np.abs(coefs),
    })
    return df.sort_values("abs_coefficient", ascending=False).reset_index(drop=True)


def xgb_feature_importances(
    model,
    feature_cols: list[str],
) -> pd.DataFrame:
    if hasattr(model, "calibrated_classifiers_"):
        importances_list = [
            cc.estimator.feature_importances_ for cc in model.calibrated_classifiers_
        ]
        importances = np.mean(importances_list, axis=0)
    else:
        importances = model.feature_importances_

    df = pd.DataFrame({"feature": feature_cols, "importance": importances})
    return df.sort_values("importance", ascending=False).reset_index(drop=True)


def save_artifact(
    model_type: str,
    model,
    scaler: Optional[StandardScaler],
    feature_cols: list[str],
    imputation_params: dict,
) -> Path:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = MODELS_DIR / f"{MODEL_NAME_PREFIX}_{model_type}_{MODEL_VERSION}_{timestamp}.joblib"

    artifact = {
        "model_type": model_type,
        "model": model,
        "scaler": scaler,
        "feature_columns": feature_cols,
        "imputation": imputation_params,
        "trained_at": timestamp,
    }
    joblib.dump(artifact, output_path)
    return output_path


def _print_metrics(label: str, metrics: dict) -> None:
    print()
    print(f"=== {label} ===")
    print(f"PR-AUC: {metrics['pr_auc']:.4f}")
    print(f"Brier:  {metrics['brier']:.4f}")
    print(f"Mean predicted P(injury): {metrics['mean_proba']:.4f}")
    print(f"Baseline (positive rate): {metrics['positive_rate']:.4f}")
    print(f"Recall at precision={TARGET_PRECISION_FOR_RECALL}: {metrics['recall_at_p20']:.4f}")
    print(f"Classification report at threshold={DEFAULT_THRESHOLD}:")
    report = metrics["classification_report"]
    for cls in ["0", "1"]:
        if cls in report:
            r = report[cls]
            print(
                f"  class={cls}: precision={r['precision']:.3f} recall={r['recall']:.3f} "
                f"f1={r['f1-score']:.3f} support={int(r['support'])}"
            )
    print("Decile lift:")
    print(metrics["decile_lift"].to_string(index=False))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    df = load_risk_dataset()
    logger.info("Loaded risk dataset: %d rows", len(df))

    df, imputation_params = prepare_features(df)
    feature_cols = build_feature_columns()
    logger.info("Features: %d", len(feature_cols))

    train_df, test_df = temporal_split(df)
    logger.info(
        "Train: %d rows (%.2f%% positive) | Test: %d rows (%.2f%% positive)",
        len(train_df),
        100 * train_df[RISK_TARGET].mean(),
        len(test_df),
        100 * test_df[RISK_TARGET].mean(),
    )

    if len(test_df) == 0:
        logger.warning("Test split is empty - check temporal boundary")
        return

    logger.info("Training Logistic Regression...")
    lr_model, lr_scaler = train_logistic_regression(train_df, feature_cols)
    lr_proba = lr_model.predict_proba(lr_scaler.transform(test_df[feature_cols].values))[:, 1]
    lr_metrics = evaluate_model_proba(lr_proba, test_df[RISK_TARGET].values)

    logger.info("Training XGBoost...")
    xgb_model = train_xgboost(train_df, feature_cols)
    xgb_proba = xgb_model.predict_proba(test_df[feature_cols].values)[:, 1]
    xgb_metrics = evaluate_model_proba(xgb_proba, test_df[RISK_TARGET].values)

    _print_metrics("LOGISTIC REGRESSION", lr_metrics)
    print()
    print("Top 10 LR features:")
    print(lr_feature_importances(lr_model, feature_cols).head(10).to_string(index=False))

    _print_metrics("XGBOOST", xgb_metrics)
    print()
    print("Top 10 XGBoost features:")
    print(xgb_feature_importances(xgb_model, feature_cols).head(10).to_string(index=False))

    print()
    print("=== SHOOTOUT ===")
    print(f"LR PR-AUC:      {lr_metrics['pr_auc']:.4f}")
    print(f"XGBoost PR-AUC: {xgb_metrics['pr_auc']:.4f}")

    if xgb_metrics["pr_auc"] >= lr_metrics["pr_auc"]:
        print("WINNER: XGBoost")
        winner_path = save_artifact("xgboost", xgb_model, None, feature_cols, imputation_params)
    else:
        print("WINNER: Logistic Regression")
        winner_path = save_artifact("lr", lr_model, lr_scaler, feature_cols, imputation_params)

    print(f"Saved winner: {winner_path}")


if __name__ == "__main__":
    main()