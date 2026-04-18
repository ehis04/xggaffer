from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from apps.predictions.ml.models.scoreline.config import PROCESSED_DIR, SCORE_ENGINE_LEAGUES, SCORE_ENGINE_SEASONS, TEST_SEASONS
from apps.predictions.ml.models.scoreline.predict import ScorePredictor, resolve_latest_score_model
from apps.predictions.ml.models.scoreline.prepare_data import get_temporal_split, prepare_score_dataset
from apps.predictions.ml.models.scoreline.train import derive_probabilities, scoreline_matrix, train_score_model


DEFAULT_OUTPUT = PROCESSED_DIR / "scoreline_classification_report.json"
MODEL_TYPE = "score_poisson_dc"
MODEL_VERSION = "v1"


def _to_native(value):
    if isinstance(value, dict):
        return {k: _to_native(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_native(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def _resolve_or_train_model_path(
    model_path: Path | None,
    *,
    train_missing: bool,
    leagues: list[str],
    seasons: list[str],
    test_seasons: list[str],
) -> Path:
    if model_path is not None:
        return model_path

    try:
        return resolve_latest_score_model()
    except FileNotFoundError:
        if not train_missing:
            raise

    print("No scoreline artifact found; training now...")
    train_score_model(
        leagues=leagues,
        seasons=seasons,
        test_seasons=test_seasons,
        save=True,
    )
    return resolve_latest_score_model()


def _predict_wdl_probabilities(
    predictor: ScorePredictor,
    test_df: pd.DataFrame,
) -> np.ndarray:
    lambda_home, lambda_away = predictor.predict_lambdas_batch(test_df)

    rows: list[list[float]] = []
    for i in range(len(test_df)):
        matrix = scoreline_matrix(float(lambda_home[i]), float(lambda_away[i]), float(predictor.rho))
        probs = derive_probabilities(matrix)
        row = np.array([float(probs["home_win"]), float(probs["draw"]), float(probs["away_win"])], dtype=float)
        row = np.nan_to_num(row, nan=0.0, posinf=0.0, neginf=0.0)
        row = np.clip(row, 0.0, 1.0)
        total = float(row.sum())
        if total <= 0.0:
            row = np.array([1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0], dtype=float)
        else:
            row = row / total
        rows.append(row.tolist())

    return np.array(rows)


def build_scoreline_classification_report(
    model_path: Path | None,
    leagues: list[str],
    seasons: list[str],
    test_seasons: list[str],
    train_missing: bool = False,
) -> dict:
    resolved_model_path = _resolve_or_train_model_path(
        model_path,
        train_missing=train_missing,
        leagues=leagues,
        seasons=seasons,
        test_seasons=test_seasons,
    )
    predictor = ScorePredictor(artifact_path=resolved_model_path)
    artifact = joblib.load(resolved_model_path)

    df = prepare_score_dataset(leagues=leagues, seasons=seasons)
    train_df, test_df = get_temporal_split(df, test_seasons)

    y_true = np.where(
        test_df["home_goals"].to_numpy() > test_df["away_goals"].to_numpy(),
        "H",
        np.where(test_df["home_goals"].to_numpy() < test_df["away_goals"].to_numpy(), "A", "D"),
    )

    labels = ["H", "D", "A"]
    y_proba = _predict_wdl_probabilities(predictor, test_df)
    y_pred = np.array([labels[idx] for idx in np.argmax(y_proba, axis=1)])

    report = classification_report(
        y_true,
        y_pred,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    return {
        "engine": "scoreline",
        "model_path": str(resolved_model_path),
        "model_type": MODEL_TYPE,
        "version": MODEL_VERSION,
        "test_seasons": [str(s) for s in test_seasons],
        "matches_evaluated": int(len(test_df)),
        "dataset": {
            "leagues": [str(l) for l in leagues],
            "seasons": [str(s) for s in seasons],
            "train_samples": int(len(train_df)),
            "test_samples": int(len(test_df)),
            "home_features": [str(x) for x in predictor.home_features],
            "away_features": [str(x) for x in predictor.away_features],
        },
        "model_parameters": {
            "rho": float(predictor.rho),
            "trained_at": artifact.get("trained_at"),
            "decay_rate": float(artifact.get("decay_rate", 0.0)),
        },
        "metrics": {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "classification_report": _to_native(report),
            "confusion_matrix": {
                "labels": labels,
                "matrix": cm.tolist(),
            },
        },
        "generated_at": pd.Timestamp.utcnow().isoformat(),
    }


def save_report(report: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def _print_summary(report: dict, output_path: Path) -> None:
    metrics = report["metrics"]
    clf_report = metrics["classification_report"]

    print("\nScoreline classification report")
    print("-" * 50)
    print(f"Model:               {report['model_type']} ({report['version']})")
    print(f"Test seasons:        {report['test_seasons']}")
    print(f"Matches:             {report['matches_evaluated']}")
    print(f"Accuracy:            {metrics['accuracy']:.4f}")
    print(f"Macro F1:            {clf_report['macro avg']['f1-score']:.4f}")
    print(f"Weighted F1:         {clf_report['weighted avg']['f1-score']:.4f}")
    print(f"Saved report to:     {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate classification report for Engine 3 (Scoreline).",
    )
    parser.add_argument("--model-path", type=str, default=None)
    parser.add_argument("--train-missing", action="store_true")
    parser.add_argument("--leagues", nargs="+", default=SCORE_ENGINE_LEAGUES)
    parser.add_argument("--seasons", nargs="+", default=SCORE_ENGINE_SEASONS)
    parser.add_argument("--test-seasons", nargs="+", default=TEST_SEASONS)
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))

    args = parser.parse_args()

    model_path = Path(args.model_path) if args.model_path else None
    report = build_scoreline_classification_report(
        model_path=model_path,
        leagues=[str(x) for x in args.leagues],
        seasons=[str(x) for x in args.seasons],
        test_seasons=[str(x) for x in args.test_seasons],
        train_missing=bool(args.train_missing),
    )

    output_path = Path(args.output)
    save_report(report, output_path)
    _print_summary(report, output_path)


if __name__ == "__main__":
    main()
