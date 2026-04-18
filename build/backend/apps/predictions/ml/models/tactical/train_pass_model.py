from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from xgboost import XGBClassifier

from apps.predictions.ml.models.tactical.config import (
    MODELS_DIR,
    MODEL_VERSION,
    PASS_MODEL_PREFIX,
    TARGET,
    XGBOOST_PARAMS,
)
from apps.predictions.ml.models.tactical.prepare_data import build_pass_dataset


logger = logging.getLogger(__name__)

CALIBRATION_DEVIATION_THRESHOLD = 0.05
CALIBRATION_METHOD = "isotonic"
CALIBRATION_CV_FOLDS = 3
DECILE_COUNT = 10
TOP_FEATURE_COUNT = 10


def train_xgboost(X_train: pd.DataFrame, y_train: np.ndarray) -> XGBClassifier:
    model = XGBClassifier(**XGBOOST_PARAMS)
    model.fit(X_train, y_train, verbose=False)
    return model


def evaluate_predictions(y_true: np.ndarray, y_proba: np.ndarray) -> dict:
    auc = roc_auc_score(y_true, y_proba)
    brier = brier_score_loss(y_true, y_proba)
    ll = log_loss(y_true, y_proba)
    return {
        "auc_roc": auc,
        "brier": brier,
        "log_loss": ll,
        "mean_proba": float(y_proba.mean()),
        "actual_rate": float(y_true.mean()),
    }


def calibration_table(y_true: np.ndarray, y_proba: np.ndarray) -> pd.DataFrame:
    df = pd.DataFrame({"proba": y_proba, "y": y_true})
    df["decile"] = pd.qcut(df["proba"], q=DECILE_COUNT, labels=False, duplicates="drop")
    grouped = (
        df.groupby("decile")
        .agg(
            n=("y", "size"),
            mean_proba=("proba", "mean"),
            actual_rate=("y", "mean"),
        )
        .reset_index()
    )
    grouped["abs_deviation"] = (grouped["mean_proba"] - grouped["actual_rate"]).abs()
    return grouped


def feature_importance(model: XGBClassifier, feature_cols: list[str]) -> pd.DataFrame:
    importances = model.feature_importances_
    df = pd.DataFrame({"feature": feature_cols, "importance": importances})
    return df.sort_values("importance", ascending=False).reset_index(drop=True)


def maybe_calibrate(
    base_model: XGBClassifier,
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    max_deviation: float,
) -> tuple[object, bool]:
    if max_deviation <= CALIBRATION_DEVIATION_THRESHOLD:
        return base_model, False

    logger.info(
        "Calibration deviation %.4f > %.4f - wrapping with isotonic calibration",
        max_deviation,
        CALIBRATION_DEVIATION_THRESHOLD,
    )
    calibrated = CalibratedClassifierCV(
        estimator=XGBClassifier(**XGBOOST_PARAMS),
        method=CALIBRATION_METHOD,
        cv=CALIBRATION_CV_FOLDS,
    )
    calibrated.fit(X_train, y_train)
    return calibrated, True


def save_model(
    model: object,
    feature_cols: list[str],
    is_calibrated: bool,
    metrics: dict,
) -> Path:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = MODELS_DIR / f"{PASS_MODEL_PREFIX}_{MODEL_VERSION}_{timestamp}.joblib"

    artifact = {
        "model": model,
        "feature_columns": feature_cols,
        "is_calibrated": is_calibrated,
        "metrics": metrics,
        "trained_at": timestamp,
    }
    joblib.dump(artifact, output_path)
    return output_path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    train_df, test_df, feature_cols = build_pass_dataset()

    X_train = train_df[feature_cols]
    y_train = train_df[TARGET].values.astype(int)
    X_test = test_df[feature_cols]
    y_test = test_df[TARGET].values.astype(int)

    logger.info("Training XGBoost on %d rows, %d features", len(X_train), len(feature_cols))
    base_model = train_xgboost(X_train, y_train)

    raw_proba_train = base_model.predict_proba(X_train)[:, 1]
    raw_proba_test = base_model.predict_proba(X_test)[:, 1]

    raw_train_metrics = evaluate_predictions(y_train, raw_proba_train)
    raw_test_metrics = evaluate_predictions(y_test, raw_proba_test)

    raw_calibration = calibration_table(y_test, raw_proba_test)
    raw_max_deviation = float(raw_calibration["abs_deviation"].max())

    print()
    print("=== RAW XGBOOST (no calibration wrapper) ===")
    print(f"Train AUC-ROC:   {raw_train_metrics['auc_roc']:.4f}")
    print(f"Test  AUC-ROC:   {raw_test_metrics['auc_roc']:.4f}")
    print(f"Test  Brier:     {raw_test_metrics['brier']:.4f}")
    print(f"Test  Log loss:  {raw_test_metrics['log_loss']:.4f}")
    print(f"Test  mean P:    {raw_test_metrics['mean_proba']:.4f}")
    print(f"Test  actual:    {raw_test_metrics['actual_rate']:.4f}")
    print()
    print("Calibration table (raw):")
    print(raw_calibration.to_string(index=False))
    print(f"Max abs deviation: {raw_max_deviation:.4f}")

    final_model, was_calibrated = maybe_calibrate(
        base_model, X_train, y_train, raw_max_deviation
    )

    if was_calibrated:
        final_proba_test = final_model.predict_proba(X_test)[:, 1]
        final_test_metrics = evaluate_predictions(y_test, final_proba_test)
        final_calibration = calibration_table(y_test, final_proba_test)

        print()
        print("=== ISOTONIC-CALIBRATED XGBOOST ===")
        print(f"Test AUC-ROC:   {final_test_metrics['auc_roc']:.4f}")
        print(f"Test Brier:     {final_test_metrics['brier']:.4f}")
        print(f"Test Log loss:  {final_test_metrics['log_loss']:.4f}")
        print()
        print("Calibration table (calibrated):")
        print(final_calibration.to_string(index=False))
        winning_metrics = final_test_metrics
    else:
        print()
        print("Calibration acceptable - keeping raw XGBoost.")
        winning_metrics = raw_test_metrics

    print()
    print("=== FEATURE IMPORTANCE (top 10) ===")
    importance_df = feature_importance(base_model, feature_cols)
    print(importance_df.head(TOP_FEATURE_COUNT).to_string(index=False))

    print()
    print("=== BASELINE COMPARISON ===")
    baseline_rate = float(y_train.mean())
    baseline_brier = float(((baseline_rate - y_test) ** 2).mean())
    print(f"Always-predict-{baseline_rate:.4f} baseline AUC-ROC: 0.5000")
    print(f"Always-predict-{baseline_rate:.4f} baseline Brier:   {baseline_brier:.4f}")
    print(f"Model AUC-ROC:                          {winning_metrics['auc_roc']:.4f}")
    print(f"Model Brier:                            {winning_metrics['brier']:.4f}")

    output_path = save_model(final_model, feature_cols, was_calibrated, winning_metrics)
    print()
    print(f"Saved model: {output_path}")


if __name__ == "__main__":
    main()