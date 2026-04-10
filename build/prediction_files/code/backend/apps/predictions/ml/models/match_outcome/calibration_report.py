from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.preprocessing import label_binarize

from ml.models.match_outcome.config import (
    DEFAULT_LEAGUES,
    DEFAULT_MODEL_TYPE,
    DEFAULT_SEASONS,
    PROCESSED_DIR,
    TEST_SEASONS,
    resolve_latest_model_path,
)
from ml.models.match_outcome.prepare_data import (
    get_feature_columns,
    get_temporal_split,
    prepare_dataset,
)
from ml.models.match_outcome.predict import get_predictor


DEFAULT_REPORT_PATH = PROCESSED_DIR / "match_outcome_calibration_report.json"
DEFAULT_N_BINS = 10


def _compute_ece(
    y_true_idx: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int,
) -> float:
    n_classes = y_prob.shape[1]
    total_predictions = len(y_true_idx) * n_classes
    ece = 0.0

    for cls in range(n_classes):
        probs = y_prob[:, cls]
        actuals = (y_true_idx == cls).astype(float)

        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
        for b in range(n_bins):
            mask = (probs >= bin_edges[b]) & (probs < bin_edges[b + 1])
            if b == n_bins - 1:
                mask = (probs >= bin_edges[b]) & (probs <= bin_edges[b + 1])

            count = mask.sum()
            if count == 0:
                continue

            avg_predicted = float(probs[mask].mean())
            avg_actual = float(actuals[mask].mean())
            ece += count * abs(avg_predicted - avg_actual)

    return float(ece / total_predictions)


def _build_reliability_data(
    y_true_idx: np.ndarray,
    y_prob: np.ndarray,
    classes: list[str],
    n_bins: int,
) -> dict[str, dict[str, list[float]]]:
    reliability: dict[str, dict[str, list[float]]] = {}

    for idx, cls in enumerate(classes):
        y_binary = (y_true_idx == idx).astype(int)
        prob_cls = y_prob[:, idx]

        try:
            prob_true, prob_pred = calibration_curve(
                y_binary,
                prob_cls,
                n_bins=n_bins,
                strategy="uniform",
            )
            reliability[cls] = {
                "prob_true": prob_true.tolist(),
                "prob_pred": prob_pred.tolist(),
            }
        except ValueError:
            reliability[cls] = {
                "prob_true": [],
                "prob_pred": [],
            }

    return reliability


def build_match_outcome_calibration_report(
    model_path: Path | None,
    leagues: list[str],
    seasons: list[str],
    test_seasons: list[str],
    n_bins: int,
) -> dict:
    if model_path is None:
        model_path = resolve_latest_model_path(DEFAULT_MODEL_TYPE)

    predictor = get_predictor(model_path=model_path)

    df = prepare_dataset(leagues=leagues, seasons=seasons, save=False)
    feature_cols = get_feature_columns(df)
    X_train, X_test, y_train, y_test = get_temporal_split(df, test_seasons)

    X_model = X_test[feature_cols]
    y_proba = predictor.model.predict_proba(X_model)
    classes = [str(cls) for cls in predictor.model.classes_]
    class_to_idx = {label: i for i, label in enumerate(classes)}

    y_true_idx = np.array([class_to_idx[str(label)] for label in y_test.to_numpy()])
    predictions = np.argmax(y_proba, axis=1)

    multiclass_brier = float(
        np.mean(
            np.sum(
                (
                    label_binarize(y_true_idx, classes=np.arange(len(classes)))
                    - y_proba
                ) ** 2,
                axis=1,
            )
        )
    )

    per_class_brier = {
        cls: float(
            brier_score_loss(
                (y_true_idx == idx).astype(int),
                y_proba[:, idx],
            )
        )
        for idx, cls in enumerate(classes)
    }

    report = {
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
            "accuracy": float((predictions == y_true_idx).mean()),
            "log_loss": float(log_loss(y_true_idx, y_proba, labels=np.arange(len(classes)))),
            "brier_multiclass": multiclass_brier,
            "ece": _compute_ece(y_true_idx, y_proba, n_bins=n_bins),
            "brier_per_class": per_class_brier,
        },
        "reliability": _build_reliability_data(y_true_idx, y_proba, classes, n_bins=n_bins),
        "generated_at": pd.Timestamp.utcnow().isoformat(),
    }

    return report


def save_report(report: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def _print_summary(report: dict, output_path: Path) -> None:
    metrics = report["metrics"]
    print("\nMatch Outcome calibration report")
    print("-" * 50)
    print(f"Model:             {report['model_type']} ({report['version']})")
    print(f"Test seasons:      {report['test_seasons']}")
    print(f"Matches:           {report['matches_evaluated']}")
    print(f"Accuracy:          {metrics['accuracy']:.4f}")
    print(f"Log loss:          {metrics['log_loss']:.4f}")
    print(f"Brier (multiclass):{metrics['brier_multiclass']:.4f}")
    print(f"ECE:               {metrics['ece']:.4f}")
    print(f"Saved report to:   {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate calibration report for Engine 2 (Match Outcome).",
    )
    parser.add_argument("--model-path", type=str, default=None)
    parser.add_argument("--leagues", nargs="+", default=DEFAULT_LEAGUES)
    parser.add_argument("--seasons", nargs="+", default=DEFAULT_SEASONS)
    parser.add_argument("--test-seasons", nargs="+", default=TEST_SEASONS)
    parser.add_argument("--n-bins", type=int, default=DEFAULT_N_BINS)
    parser.add_argument("--output", type=str, default=str(DEFAULT_REPORT_PATH))

    args = parser.parse_args()

    model_path = Path(args.model_path) if args.model_path else None

    report = build_match_outcome_calibration_report(
        model_path=model_path,
        leagues=[str(l) for l in args.leagues],
        seasons=[str(s) for s in args.seasons],
        test_seasons=[str(s) for s in args.test_seasons],
        n_bins=int(args.n_bins),
    )

    output_path = Path(args.output)
    save_report(report, output_path)
    _print_summary(report, output_path)


if __name__ == "__main__":
    main()
