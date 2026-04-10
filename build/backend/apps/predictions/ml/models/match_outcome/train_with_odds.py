from __future__ import annotations

from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    log_loss,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, label_binarize

from ml.models.match_outcome.config import (
    FRONTEND_CONTRACT_VERSION,
    MODEL_VERSION,
    MODELS_DIR,
    RANDOM_SEED,
)
from ml.models.match_outcome.prepare_data import (
    FEATURE_COLUMNS_WITH_ODDS,
    prepare_dataset,
    get_feature_columns,
    get_temporal_split,
)


LR_MAX_ITER = 1000
LR_C = 0.001
CALIBRATION_METHOD = "sigmoid"
CALIBRATION_CV = 5
MODEL_TYPE = "logistic_regression"
ALL_LEAGUES = ["EPL", "La_Liga", "Bundesliga", "Serie_A", "Ligue_1"]
ALL_SEASONS = [str(y) for y in range(2014, 2026)]
TEST_SEASONS = ["2024"]


def compute_multiclass_brier(y_true, y_proba, classes) -> float:
    y_bin = label_binarize(y_true, classes=classes)
    return float(np.mean(np.sum((y_bin - y_proba) ** 2, axis=1)))


def train_and_save(
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
    test_seasons: list[str] | None = None,
) -> dict:
    leagues = leagues or ALL_LEAGUES
    seasons = seasons or ALL_SEASONS
    test_seasons = test_seasons or TEST_SEASONS

    print("Preparing dataset with odds...")
    df = prepare_dataset(
        leagues=leagues,
        seasons=seasons,
        save=True,
        include_odds=True,
    )

    feature_cols = get_feature_columns(df, include_odds=True)
    X_train, X_test, y_train, y_test = get_temporal_split(df, test_seasons, include_odds=True)

    print(f"\nTrain: {len(X_train)} matches, Test: {len(X_test)} matches")
    print(f"Features: {len(feature_cols)}")

    base_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(
            C=LR_C,
            max_iter=LR_MAX_ITER,
            random_state=RANDOM_SEED,
            solver="lbfgs",
        )),
    ])

    print("Training base model...")
    base_pipeline.fit(X_train, y_train)
    y_pred_raw = base_pipeline.predict(X_test)
    y_proba_raw = base_pipeline.predict_proba(X_test)
    raw_classes = base_pipeline.classes_
    raw_accuracy = accuracy_score(y_test, y_pred_raw)
    raw_brier = compute_multiclass_brier(y_test, y_proba_raw, raw_classes)
    raw_logloss = log_loss(y_test, y_proba_raw, labels=raw_classes)

    print(f"  Raw accuracy: {raw_accuracy:.3f}")

    print("Calibrating...")
    calibrated_model = CalibratedClassifierCV(
        estimator=Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                C=LR_C,
                max_iter=LR_MAX_ITER,
                random_state=RANDOM_SEED,
                solver="lbfgs",
            )),
        ]),
        method=CALIBRATION_METHOD,
        cv=CALIBRATION_CV,
    )
    calibrated_model.fit(X_train, y_train)

    y_pred = calibrated_model.predict(X_test)
    y_proba = calibrated_model.predict_proba(X_test)
    classes = calibrated_model.classes_

    accuracy = accuracy_score(y_test, y_pred)
    brier = compute_multiclass_brier(y_test, y_proba, classes)
    logloss = log_loss(y_test, y_proba, labels=classes)
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    conf_matrix = confusion_matrix(y_test, y_pred, labels=["H", "D", "A"])

    print(f"  Calibrated accuracy: {accuracy:.3f}")
    print(f"  Brier: {brier:.4f}")
    print(f"  Log loss: {logloss:.4f}")
    print(f"\n{classification_report(y_test, y_pred, zero_division=0)}")

    trained_at = datetime.now().isoformat()

    artifact = {
        "model": calibrated_model,
        "feature_columns": feature_cols,
        "model_type": MODEL_TYPE,
        "metrics": {
            "accuracy": accuracy,
            "brier_score": brier,
            "log_loss": logloss,
            "report": report,
            "confusion_matrix": conf_matrix,
            "calibrated": True,
            "calibration_method": CALIBRATION_METHOD,
            "raw_accuracy": raw_accuracy,
            "raw_brier_score": raw_brier,
            "raw_log_loss": raw_logloss,
        },
        "training_info": {
            "leagues": leagues,
            "seasons": seasons,
            "test_seasons": test_seasons,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "trained_at": trained_at,
            "frontend_contract_version": FRONTEND_CONTRACT_VERSION,
            "deterministic_explanation_model": True,
            "includes_odds": True,
            "odds_features": [
                "market_home_prob",
                "market_draw_prob",
                "market_away_prob",
            ],
            "hyperparameters": {
                "C": LR_C,
                "max_iter": LR_MAX_ITER,
                "calibration_method": CALIBRATION_METHOD,
                "calibration_cv": CALIBRATION_CV,
            },
        },
        "version": MODEL_VERSION,
    }

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_filename = f"match_outcome_{MODEL_TYPE}_with_odds_{MODEL_VERSION}_{timestamp}.joblib"
    model_path = MODELS_DIR / model_filename
    joblib.dump(artifact, model_path)

    print(f"\nModel saved to: {model_path}")
    print(f"Feature count: {len(feature_cols)}")
    print(f"Artifact keys: {list(artifact.keys())}")

    return {
        "model_path": str(model_path),
        "accuracy": accuracy,
        "brier_score": brier,
        "log_loss": logloss,
        "feature_count": len(feature_cols),
    }


if __name__ == "__main__":
    result = train_and_save()
    print(f"\nDone. Model at: {result['model_path']}")