from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.preprocessing import label_binarize

from ml.engines.compute_elo import VALIDATION_SEASON
from ml.engines.elo import (
    DEFAULT_HOME_ADVANTAGE,
    DEFAULT_K_FACTOR,
    compute_elo_history,
    elo_to_probabilities,
)
from ml.features.rolling import ALL_LEAGUES, ALL_SEASONS, load_match_history
from ml.models.match_outcome.config import PROCESSED_DIR


DEFAULT_REPORT_PATH = PROCESSED_DIR / "elo_calibration_report.json"
DEFAULT_CLASS_ORDER = ["H", "D", "A"]
DEFAULT_N_BINS = 10


RESULT_TO_CODE = {
    0: "A",
    0.5: "D",
    1: "H",
}


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
    y_true_codes: np.ndarray,
    y_prob: np.ndarray,
    classes: list[str],
    n_bins: int,
) -> dict[str, dict[str, list[float]]]:
    reliability: dict[str, dict[str, list[float]]] = {}

    for idx, cls in enumerate(classes):
        y_binary = (y_true_codes == cls).astype(int)
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


def build_elo_calibration_report(
    leagues: list[str],
    seasons: list[str],
    validation_season: str,
    k_factor: float,
    home_advantage: float,
    n_bins: int,
) -> dict:
    matches_df = load_match_history(leagues, seasons)
    history, _ = compute_elo_history(
        matches_df,
        k_factor=k_factor,
        home_advantage=home_advantage,
    )

    hist_df = pd.DataFrame(history)
    eval_df = hist_df[hist_df["season"].astype(str) == str(validation_season)].copy()

    if eval_df.empty:
        raise ValueError(
            f"No matches found for validation season {validation_season}. "
            f"Available seasons: {sorted(hist_df['season'].astype(str).unique().tolist())}"
        )

    y_true_codes = np.array([
        RESULT_TO_CODE[row.actual_home]
        for row in eval_df.itertuples(index=False)
    ])

    y_prob = np.array([
        [probs["H"], probs["D"], probs["A"]]
        for probs in [
            elo_to_probabilities(
                row.home_elo_before,
                row.away_elo_before,
                home_advantage=home_advantage,
            )
            for row in eval_df.itertuples(index=False)
        ]
    ])

    class_order = DEFAULT_CLASS_ORDER
    class_to_idx = {label: i for i, label in enumerate(class_order)}
    y_true_idx = np.array([class_to_idx[label] for label in y_true_codes])

    predictions = np.argmax(y_prob, axis=1)
    accuracy = float((predictions == y_true_idx).mean())

    multiclass_brier = float(
        np.mean(
            np.sum(
                (
                    label_binarize(y_true_idx, classes=np.arange(len(class_order)))
                    - y_prob
                ) ** 2,
                axis=1,
            )
        )
    )

    per_class_brier = {
        cls: float(
            brier_score_loss(
                (y_true_codes == cls).astype(int),
                y_prob[:, idx],
            )
        )
        for idx, cls in enumerate(class_order)
    }

    report = {
        "engine": "elo",
        "validation_season": str(validation_season),
        "matches_evaluated": int(len(eval_df)),
        "parameters": {
            "k_factor": float(k_factor),
            "home_advantage": float(home_advantage),
            "n_bins": int(n_bins),
            "leagues": leagues,
            "seasons": seasons,
        },
        "metrics": {
            "accuracy": accuracy,
            "log_loss": float(log_loss(y_true_idx, y_prob, labels=np.arange(len(class_order)))),
            "brier_multiclass": multiclass_brier,
            "ece": _compute_ece(y_true_idx, y_prob, n_bins=n_bins),
            "brier_per_class": per_class_brier,
        },
        "reliability": _build_reliability_data(y_true_codes, y_prob, class_order, n_bins=n_bins),
        "generated_at": pd.Timestamp.utcnow().isoformat(),
    }

    return report


def save_report(report: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def _print_summary(report: dict, output_path: Path) -> None:
    metrics = report["metrics"]
    print("\nElo calibration report")
    print("-" * 50)
    print(f"Season:            {report['validation_season']}")
    print(f"Matches:           {report['matches_evaluated']}")
    print(f"Accuracy:          {metrics['accuracy']:.4f}")
    print(f"Log loss:          {metrics['log_loss']:.4f}")
    print(f"Brier (multiclass):{metrics['brier_multiclass']:.4f}")
    print(f"ECE:               {metrics['ece']:.4f}")
    print(f"Saved report to:   {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate calibration report for Engine 1 (Elo).",
    )
    parser.add_argument("--leagues", nargs="+", default=ALL_LEAGUES)
    parser.add_argument("--seasons", nargs="+", default=ALL_SEASONS)
    parser.add_argument("--validation-season", type=str, default=VALIDATION_SEASON)
    parser.add_argument("--k-factor", type=float, default=DEFAULT_K_FACTOR)
    parser.add_argument("--home-advantage", type=float, default=DEFAULT_HOME_ADVANTAGE)
    parser.add_argument("--n-bins", type=int, default=DEFAULT_N_BINS)
    parser.add_argument("--output", type=str, default=str(DEFAULT_REPORT_PATH))

    args = parser.parse_args()

    report = build_elo_calibration_report(
        leagues=[str(x) for x in args.leagues],
        seasons=[str(x) for x in args.seasons],
        validation_season=str(args.validation_season),
        k_factor=float(args.k_factor),
        home_advantage=float(args.home_advantage),
        n_bins=int(args.n_bins),
    )

    output_path = Path(args.output)
    save_report(report, output_path)
    _print_summary(report, output_path)


if __name__ == "__main__":
    main()
