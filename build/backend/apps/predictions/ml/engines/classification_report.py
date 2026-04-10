from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from ml.engines.compute_elo import VALIDATION_SEASON
from ml.engines.elo import (
    DEFAULT_HOME_ADVANTAGE,
    DEFAULT_K_FACTOR,
    compute_elo_history,
    elo_to_probabilities,
)
from ml.features.rolling import ALL_LEAGUES, ALL_SEASONS, load_match_history
from ml.models.match_outcome.config import PROCESSED_DIR


DEFAULT_OUTPUT = PROCESSED_DIR / "elo_classification_report.json"
CLASS_ORDER = ["H", "D", "A"]
RESULT_TO_CODE = {
    0: "A",
    0.5: "D",
    1: "H",
}


def _to_native(value):
    if isinstance(value, dict):
        return {k: _to_native(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_native(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def build_elo_classification_report(
    leagues: list[str],
    seasons: list[str],
    validation_season: str,
    k_factor: float,
    home_advantage: float,
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

    y_true = np.array([
        RESULT_TO_CODE[row.actual_home]
        for row in eval_df.itertuples(index=False)
    ])

    y_pred = []
    for row in eval_df.itertuples(index=False):
        probs = elo_to_probabilities(
            row.home_elo_before,
            row.away_elo_before,
            home_advantage=home_advantage,
        )
        y_pred.append(max(CLASS_ORDER, key=lambda cls: probs[cls]))
    y_pred = np.array(y_pred)

    report = classification_report(
        y_true,
        y_pred,
        labels=CLASS_ORDER,
        output_dict=True,
        zero_division=0,
    )

    cm = confusion_matrix(y_true, y_pred, labels=CLASS_ORDER)

    return {
        "engine": "elo",
        "validation_season": str(validation_season),
        "matches_evaluated": int(len(eval_df)),
        "parameters": {
            "k_factor": float(k_factor),
            "home_advantage": float(home_advantage),
            "leagues": leagues,
            "seasons": seasons,
        },
        "metrics": {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "classification_report": _to_native(report),
            "confusion_matrix": {
                "labels": CLASS_ORDER,
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

    print("\nElo classification report")
    print("-" * 50)
    print(f"Season:              {report['validation_season']}")
    print(f"Matches:             {report['matches_evaluated']}")
    print(f"Accuracy:            {metrics['accuracy']:.4f}")
    print(f"Macro F1:            {clf_report['macro avg']['f1-score']:.4f}")
    print(f"Weighted F1:         {clf_report['weighted avg']['f1-score']:.4f}")
    print(f"Saved report to:     {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate classification report for Engine 1 (Elo).",
    )
    parser.add_argument("--leagues", nargs="+", default=ALL_LEAGUES)
    parser.add_argument("--seasons", nargs="+", default=ALL_SEASONS)
    parser.add_argument("--validation-season", type=str, default=VALIDATION_SEASON)
    parser.add_argument("--k-factor", type=float, default=DEFAULT_K_FACTOR)
    parser.add_argument("--home-advantage", type=float, default=DEFAULT_HOME_ADVANTAGE)
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))

    args = parser.parse_args()

    report = build_elo_classification_report(
        leagues=[str(x) for x in args.leagues],
        seasons=[str(x) for x in args.seasons],
        validation_season=str(args.validation_season),
        k_factor=float(args.k_factor),
        home_advantage=float(args.home_advantage),
    )

    output_path = Path(args.output)
    save_report(report, output_path)
    _print_summary(report, output_path)


if __name__ == "__main__":
    main()
