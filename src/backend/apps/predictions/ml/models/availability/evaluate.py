from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from lifelines.utils import concordance_index
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    classification_report,
    precision_recall_curve,
)

from apps.predictions.ml.models.availability.config import (
    DURATION_COL,
    EVENT_COL,
    INJURY_CATEGORIES,
    INJURY_CATEGORY_OTHER,
    MODELS_DIR,
    RISK_DATASET_PATH,
    RISK_TARGET,
    SURVIVAL_DATASET_PATH,
)
from apps.predictions.ml.models.availability.train_risk import (
    HAS_PRIOR_INJURY_COL as RISK_HAS_PRIOR,
    HAS_RECENT_REST_COL,
    prepare_features as prepare_risk_features,
    temporal_split as risk_temporal_split,
)
from apps.predictions.ml.models.availability.train_survival import (
    HAS_PRIOR_INJURY_COL as SURVIVAL_HAS_PRIOR,
    prepare_features as prepare_survival_features,
    temporal_split as survival_temporal_split,
)

logger = logging.getLogger(__name__)

SURVIVAL_GLOB = "survival_cox_v1_*.joblib"
RISK_GLOB = "injury_risk_*_v1_*.joblib"

BRIER_TIME_POINTS = (3, 7, 14)
DECILE_COUNT = 10
TOP_FEATURE_COUNT = 10
SAMPLE_TEAM_NAME = "Arsenal"


def _latest_artifact(glob_pattern: str) -> dict:
    candidates = sorted(MODELS_DIR.glob(glob_pattern))
    if not candidates:
        raise FileNotFoundError(f"No models matching {glob_pattern} in {MODELS_DIR}")
    latest = candidates[-1]
    logger.info("Loading: %s", latest.name)
    return joblib.load(latest)


def evaluate_survival_model() -> dict:
    artifact = _latest_artifact(SURVIVAL_GLOB)
    cph = artifact["model"]
    feature_cols = artifact["feature_columns"]

    df = pd.read_csv(SURVIVAL_DATASET_PATH)
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df = prepare_survival_features(df)

    train_df, test_df = survival_temporal_split(df)
    if test_df.empty:
        return {"error": "empty test set"}

    matrix = test_df[feature_cols + [DURATION_COL, EVENT_COL]].dropna()

    partial_hazard = cph.predict_partial_hazard(matrix)
    c_index = concordance_index(
        matrix[DURATION_COL],
        -partial_hazard,
        matrix[EVENT_COL],
    )

    survival_funcs = cph.predict_survival_function(matrix)
    brier_scores = _brier_at_time_points(survival_funcs, matrix, BRIER_TIME_POINTS)

    summary_table = cph.summary[["coef", "exp(coef)", "z", "p"]].copy()
    summary_table["abs_z"] = summary_table["z"].abs()
    top_covariates = summary_table.sort_values("abs_z", ascending=False).head(TOP_FEATURE_COUNT)

    category_table = _duration_by_category(test_df, cph, feature_cols)

    return {
        "c_index": c_index,
        "test_size": len(matrix),
        "events": int(matrix[EVENT_COL].sum()),
        "censored": int((matrix[EVENT_COL] == 0).sum()),
        "brier_scores": brier_scores,
        "top_covariates": top_covariates,
        "category_table": category_table,
    }


def _brier_at_time_points(
    survival_funcs: pd.DataFrame,
    test_matrix: pd.DataFrame,
    time_points: tuple[int, ...],
) -> dict[int, float]:
    durations = test_matrix[DURATION_COL].values
    events = test_matrix[EVENT_COL].values

    scores: dict[int, float] = {}
    for t in time_points:
        s_at_t = _survival_at_time(survival_funcs, t)
        observed = (durations <= t) & (events == 1)
        predicted_event = 1 - s_at_t
        scores[t] = float(brier_score_loss(observed.astype(int), predicted_event))
    return scores


def _survival_at_time(survival_funcs: pd.DataFrame, t: int) -> np.ndarray:
    time_index = survival_funcs.index.values
    if t <= time_index[0]:
        return survival_funcs.iloc[0].values
    if t >= time_index[-1]:
        return survival_funcs.iloc[-1].values
    idx = np.searchsorted(time_index, t, side="right") - 1
    return survival_funcs.iloc[idx].values


def _duration_by_category(
    test_df: pd.DataFrame,
    cph,
    feature_cols: list[str],
) -> pd.DataFrame:
    rows: list[dict] = []
    matrix = test_df[feature_cols + [DURATION_COL, EVENT_COL]].dropna()
    test_with_features = test_df.loc[matrix.index]

    median_predictions = cph.predict_median(matrix).values

    test_with_features = test_with_features.assign(predicted_median=median_predictions)

    for category in INJURY_CATEGORIES:
        if category == INJURY_CATEGORY_OTHER:
            continue
        col = f"injury_type_{category.lower()}"
        if col not in test_with_features.columns:
            continue
        cat_mask = test_with_features[col] == 1
        if not cat_mask.any():
            continue
        cat_data = test_with_features[cat_mask]
        rows.append({
            "category": category,
            "n": len(cat_data),
            "actual_mean": cat_data[DURATION_COL].mean(),
            "actual_median": cat_data[DURATION_COL].median(),
            "predicted_median": cat_data["predicted_median"].mean(),
        })

    return pd.DataFrame(rows).round(2)


def evaluate_risk_model() -> dict:
    artifact = _latest_artifact(RISK_GLOB)
    model = artifact["model"]
    scaler = artifact.get("scaler")
    feature_cols = artifact["feature_columns"]
    model_type = artifact.get("model_type", "lr")

    df = pd.read_csv(RISK_DATASET_PATH)
    df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")
    df, _ = prepare_risk_features(df)

    train_df, test_df = risk_temporal_split(df)
    if test_df.empty:
        return {"error": "empty test set"}

    X_test = test_df[feature_cols].values
    y_test = test_df[RISK_TARGET].values

    if scaler is not None:
        X_test = scaler.transform(X_test)

    y_proba = model.predict_proba(X_test)[:, 1]

    pr_auc = average_precision_score(y_test, y_proba)
    brier = brier_score_loss(y_test, y_proba)

    precisions, recalls, _ = precision_recall_curve(y_test, y_proba)
    recall_at_p20 = _recall_at_precision(precisions, recalls, 0.20)
    recall_at_p10 = _recall_at_precision(precisions, recalls, 0.10)
    recall_at_p05 = _recall_at_precision(precisions, recalls, 0.05)

    decile_lift = _compute_decile_lift(y_proba, y_test)
    feature_importance = _model_feature_importance(model, feature_cols, model_type)

    return {
        "model_type": model_type,
        "test_size": len(y_test),
        "positive_rate": float(y_test.mean()),
        "pr_auc": pr_auc,
        "brier": brier,
        "mean_predicted": float(y_proba.mean()),
        "recall_at_p05": recall_at_p05,
        "recall_at_p10": recall_at_p10,
        "recall_at_p20": recall_at_p20,
        "decile_lift": decile_lift,
        "feature_importance": feature_importance,
    }


def _recall_at_precision(
    precisions: np.ndarray,
    recalls: np.ndarray,
    target: float,
) -> float:
    valid = precisions >= target
    if not valid.any():
        return 0.0
    return float(recalls[valid].max())


def _compute_decile_lift(y_proba: np.ndarray, y_true: np.ndarray) -> pd.DataFrame:
    base = y_true.mean()
    df = pd.DataFrame({"proba": y_proba, "y": y_true})
    df["decile"] = pd.qcut(df["proba"], q=DECILE_COUNT, labels=False, duplicates="drop")
    grouped = df.groupby("decile").agg(
        n=("y", "size"),
        injury_rate=("y", "mean"),
        mean_proba=("proba", "mean"),
    ).reset_index()
    grouped["lift"] = grouped["injury_rate"] / base if base > 0 else 0
    return grouped.round(4)


def _model_feature_importance(
    model,
    feature_cols: list[str],
    model_type: str,
) -> pd.DataFrame:
    if model_type == "xgboost":
        if hasattr(model, "calibrated_classifiers_"):
            importances_list = [
                cc.estimator.feature_importances_ for cc in model.calibrated_classifiers_
            ]
            importances = np.mean(importances_list, axis=0)
        else:
            importances = model.feature_importances_
        df = pd.DataFrame({"feature": feature_cols, "score": importances})
    else:
        coefs = model.coef_[0]
        df = pd.DataFrame({"feature": feature_cols, "score": np.abs(coefs)})

    return df.sort_values("score", ascending=False).head(TOP_FEATURE_COUNT).reset_index(drop=True)


def print_survival_report(report: dict) -> None:
    print()
    print("=" * 70)
    print("MODEL 5A - COX PROPORTIONAL HAZARDS")
    print("=" * 70)
    print(f"Test set: {report['test_size']} spells "
          f"({report['events']} events, {report['censored']} censored)")
    print(f"C-index: {report['c_index']:.4f}  (target: 0.65-0.75, baseline: 0.50)")
    print()
    print("Brier score by time horizon:")
    for t, score in report["brier_scores"].items():
        print(f"  t={t:>2} matchdays: {score:.4f}")
    print()
    print(f"Top {TOP_FEATURE_COUNT} covariates by |z|:")
    print(report["top_covariates"].round(3).to_string())
    print()
    print("Predicted vs actual median duration by injury category:")
    print(report["category_table"].to_string(index=False))


def print_risk_report(report: dict) -> None:
    print()
    print("=" * 70)
    print(f"MODEL 5B - INJURY RISK CLASSIFIER ({report['model_type'].upper()})")
    print("=" * 70)
    print(f"Test set: {report['test_size']} player-weeks "
          f"({report['positive_rate']:.2%} positive)")
    print(f"PR-AUC: {report['pr_auc']:.4f}  (baseline: {report['positive_rate']:.4f})")
    print(f"Brier:  {report['brier']:.4f}")
    print(f"Mean predicted P(injury): {report['mean_predicted']:.4f}")
    print()
    print("Recall at fixed precision points:")
    print(f"  precision >= 0.05: recall = {report['recall_at_p05']:.4f}")
    print(f"  precision >= 0.10: recall = {report['recall_at_p10']:.4f}")
    print(f"  precision >= 0.20: recall = {report['recall_at_p20']:.4f}")
    print()
    print("Decile lift (ranking quality):")
    print(report["decile_lift"].to_string(index=False))
    print()
    print(f"Top {TOP_FEATURE_COUNT} features:")
    print(report["feature_importance"].to_string(index=False))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    survival_report = evaluate_survival_model()
    print_survival_report(survival_report)

    risk_report = evaluate_risk_model()
    print_risk_report(risk_report)

    print()
    print("=" * 70)
    print("DISSERTATION HEADLINE NUMBERS")
    print("=" * 70)
    print(f"Model 5A C-index: {survival_report['c_index']:.4f}")
    print(f"Model 5B PR-AUC:  {risk_report['pr_auc']:.4f}  "
          f"(vs baseline {risk_report['positive_rate']:.4f})")
    top_decile = risk_report["decile_lift"].iloc[-1]
    bottom_decile = risk_report["decile_lift"].iloc[0]
    lift_ratio = top_decile["injury_rate"] / max(bottom_decile["injury_rate"], 1e-9)
    print(f"Model 5B top-decile / bottom-decile lift: {lift_ratio:.2f}x")


if __name__ == "__main__":
    main()