from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from apps.predictions.ml.models.match_outcome.config import (
    DEFAULT_LEAGUES,
    DEFAULT_MODEL_TYPE,
    DEFAULT_SEASONS,
    PROCESSED_DIR,
    TEST_SEASONS,
    resolve_latest_model_path,
)
from apps.predictions.ml.models.match_outcome.prepare_data import (
    get_feature_columns,
    get_temporal_split,
    prepare_dataset,
)
from apps.predictions.ml.models.match_outcome.predict import get_predictor


DEFAULT_OUTPUT = PROCESSED_DIR / "match_outcome_classification_report.json"


def _to_native(value):
    if isinstance(value, dict):
        return {k: _to_native(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_native(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def build_match_outcome_classification_report(
    model_path: Path | None,
    leagues: list[str],
    seasons: list[str],
    test_seasons: list[str],
) -> dict:
    if model_path is None:
        model_path = resolve_latest_model_path(DEFAULT_MODEL_TYPE)

    predictor = get_predictor(model_path=model_path)

    df = prepare_dataset(leagues=leagues, seasons=seasons, save=False)
    feature_cols = get_feature_columns(df)
    X_train, X_test, y_train, y_test = get_temporal_split(df, test_seasons)

    X_model = X_test[feature_cols]
    y_pred = predictor.model.predict(X_model)

    labels = [str(cls) for cls in predictor.model.classes_]
    y_test_arr = y_test.to_numpy()

    report = classification_report(
        y_test_arr,
        y_pred,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )

    cm = confusion_matrix(y_test_arr, y_pred, labels=labels)

    return {
        "engine": "match_outcome",
        "model_path": str(model_path),
        "model_type": predictor.model_type,
        "version": predictor.version,
        "test_seasons": [str(s) for s in test_seasons],
        "matches_evaluated": int(len(X_test)),
        "dataset": {
            "leagues": [str(l) for l in leagues],
            "seasons": [str(s) for s in seasons],
            "train_samples": int(len(X_train)),
            "test_samples": int(len(X_test)),
            "feature_count": int(len(feature_cols)),
        },
        "metrics": {
            "accuracy": float(accuracy_score(y_test_arr, y_pred)),
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

    print("\nMatch Outcome classification report")
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
        description="Generate classification report for Engine 2 (Match Outcome).",
    )
    parser.add_argument("--model-path", type=str, default=None)
    parser.add_argument("--leagues", nargs="+", default=DEFAULT_LEAGUES)
    parser.add_argument("--seasons", nargs="+", default=DEFAULT_SEASONS)
    parser.add_argument("--test-seasons", nargs="+", default=TEST_SEASONS)
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))

    args = parser.parse_args()

    model_path = Path(args.model_path) if args.model_path else None

    report = build_match_outcome_classification_report(
        model_path=model_path,
        leagues=[str(x) for x in args.leagues],
        seasons=[str(x) for x in args.seasons],
        test_seasons=[str(x) for x in args.test_seasons],
    )

    output_path = Path(args.output)
    save_report(report, output_path)
    _print_summary(report, output_path)


if __name__ == "__main__":
    main()
