from __future__ import annotations

import argparse
from pathlib import Path

from ml.engines.calibration_report import build_elo_calibration_report
from ml.engines.classification_report import build_elo_classification_report
from ml.engines.compute_elo import VALIDATION_SEASON
from ml.engines.elo import DEFAULT_HOME_ADVANTAGE, DEFAULT_K_FACTOR
from ml.features.rolling import ALL_LEAGUES, ALL_SEASONS
from ml.models.match_outcome.calibration_report import (
    build_match_outcome_calibration_report,
)
from ml.models.match_outcome.classification_report import (
    build_match_outcome_classification_report,
)
from ml.models.match_outcome.config import PROCESSED_DIR, TEST_SEASONS


DEFAULT_OUTPUT = PROCESSED_DIR / "engine_performance_report.txt"


def _calibration_comment(log_loss: float, ece: float) -> str:
    parts = []

    if ece <= 0.05:
        parts.append("excellent calibration")
    elif ece <= 0.08:
        parts.append("good calibration")
    elif ece <= 0.12:
        parts.append("acceptable calibration")
    else:
        parts.append("weak calibration")

    if log_loss <= 1.00:
        parts.append("strong probability quality")
    elif log_loss <= 1.08:
        parts.append("decent probability quality")
    else:
        parts.append("probabilities are still noisy")

    return ", ".join(parts)


def _classification_comment(accuracy: float, macro_f1: float, draw_recall: float) -> str:
    parts = []

    if accuracy >= 0.54:
        parts.append("strong headline accuracy")
    elif accuracy >= 0.50:
        parts.append("usable headline accuracy")
    else:
        parts.append("headline accuracy below target")

    if macro_f1 >= 0.50:
        parts.append("balanced class performance")
    elif macro_f1 >= 0.44:
        parts.append("moderate class balance")
    else:
        parts.append("class imbalance impact is high")

    if draw_recall >= 0.30:
        parts.append("draw detection is usable")
    elif draw_recall >= 0.15:
        parts.append("draw detection is limited")
    else:
        parts.append("draw detection is weak")

    return ", ".join(parts)


def _fmt_pct(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def _build_engine_block(
    name: str,
    cls_report: dict,
    cal_report: dict,
) -> list[str]:
    cls_metrics = cls_report["metrics"]
    cal_metrics = cal_report["metrics"]

    clf = cls_metrics["classification_report"]
    draw = clf.get("D", {})

    accuracy = float(cls_metrics["accuracy"])
    macro_f1 = float(clf["macro avg"]["f1-score"])
    weighted_f1 = float(clf["weighted avg"]["f1-score"])
    draw_precision = float(draw.get("precision", 0.0))
    draw_recall = float(draw.get("recall", 0.0))

    log_loss = float(cal_metrics["log_loss"])
    brier = float(cal_metrics["brier_multiclass"])
    ece = float(cal_metrics["ece"])

    lines = [
        f"{name}",
        "-" * len(name),
        "Classification quality:",
        f"- Accuracy:        {_fmt_pct(accuracy)}",
        f"- Macro F1:        {macro_f1:.4f}",
        f"- Weighted F1:     {weighted_f1:.4f}",
        f"- Draw precision:  {_fmt_pct(draw_precision)}",
        f"- Draw recall:     {_fmt_pct(draw_recall)}",
        "",
        "Calibration quality:",
        f"- Log loss:        {log_loss:.4f}",
        f"- Brier score:     {brier:.4f}",
        f"- ECE:             {ece:.4f}",
        "",
        "Plain-language interpretation:",
        f"- Classification:  {_classification_comment(accuracy, macro_f1, draw_recall)}.",
        f"- Calibration:     {_calibration_comment(log_loss, ece)}.",
    ]

    return lines


def build_text_report(
    elo_cls: dict,
    elo_cal: dict,
    mo_cls: dict,
    mo_cal: dict,
) -> str:
    elo_lines = _build_engine_block("Engine 1 - Elo", elo_cls, elo_cal)
    mo_lines = _build_engine_block("Engine 2 - Match Outcome", mo_cls, mo_cal)

    elo_ll = float(elo_cal["metrics"]["log_loss"])
    mo_ll = float(mo_cal["metrics"]["log_loss"])
    elo_ece = float(elo_cal["metrics"]["ece"])
    mo_ece = float(mo_cal["metrics"]["ece"])
    elo_acc = float(elo_cls["metrics"]["accuracy"])
    mo_acc = float(mo_cls["metrics"]["accuracy"])

    winner_acc = "Match Outcome" if mo_acc > elo_acc else "Elo"
    winner_ll = "Match Outcome" if mo_ll < elo_ll else "Elo"
    winner_ece = "Match Outcome" if mo_ece < elo_ece else "Elo"

    summary = [
        "Combined Performance Report",
        "===========================",
        "",
        "Executive summary:",
        f"- Better accuracy:               {winner_acc}",
        f"- Better log loss (lower):       {winner_ll}",
        f"- Better calibration ECE (lower):{winner_ece}",
        "",
        "Takeaway:",
        "- Use Match Outcome as primary probability engine when available.",
        "- Keep Elo as a robust fallback and as a stable strength feature for other models.",
        "",
    ]

    return "\n".join(summary + elo_lines + [""] + mo_lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate plain-text performance report for Elo and Match Outcome engines.",
    )
    parser.add_argument("--leagues", nargs="+", default=ALL_LEAGUES)
    parser.add_argument("--seasons", nargs="+", default=ALL_SEASONS)
    parser.add_argument("--validation-season", type=str, default=VALIDATION_SEASON)
    parser.add_argument("--test-seasons", nargs="+", default=TEST_SEASONS)
    parser.add_argument("--k-factor", type=float, default=DEFAULT_K_FACTOR)
    parser.add_argument("--home-advantage", type=float, default=DEFAULT_HOME_ADVANTAGE)
    parser.add_argument("--model-path", type=str, default=None)
    parser.add_argument("--n-bins", type=int, default=10)
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))

    args = parser.parse_args()

    model_path = Path(args.model_path) if args.model_path else None

    elo_cls = build_elo_classification_report(
        leagues=[str(x) for x in args.leagues],
        seasons=[str(x) for x in args.seasons],
        validation_season=str(args.validation_season),
        k_factor=float(args.k_factor),
        home_advantage=float(args.home_advantage),
    )
    elo_cal = build_elo_calibration_report(
        leagues=[str(x) for x in args.leagues],
        seasons=[str(x) for x in args.seasons],
        validation_season=str(args.validation_season),
        k_factor=float(args.k_factor),
        home_advantage=float(args.home_advantage),
        n_bins=int(args.n_bins),
    )

    mo_cls = build_match_outcome_classification_report(
        model_path=model_path,
        leagues=[str(x) for x in args.leagues],
        seasons=[str(x) for x in args.seasons],
        test_seasons=[str(x) for x in args.test_seasons],
    )
    mo_cal = build_match_outcome_calibration_report(
        model_path=model_path,
        leagues=[str(x) for x in args.leagues],
        seasons=[str(x) for x in args.seasons],
        test_seasons=[str(x) for x in args.test_seasons],
        n_bins=int(args.n_bins),
    )

    report_text = build_text_report(elo_cls, elo_cal, mo_cls, mo_cal)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")

    print(report_text)
    print(f"Saved report to: {output_path}")


if __name__ == "__main__":
    main()
