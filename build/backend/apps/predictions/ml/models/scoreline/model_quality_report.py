from __future__ import annotations

import argparse
from pathlib import Path

from ml.models.scoreline.calibration_report import build_scoreline_calibration_report
from ml.models.scoreline.classification_report import build_scoreline_classification_report
from ml.models.scoreline.config import PROCESSED_DIR, SCORE_ENGINE_LEAGUES, SCORE_ENGINE_SEASONS, TEST_SEASONS


DEFAULT_OUTPUT = PROCESSED_DIR / "scoreline_model_quality_report.txt"

BENCHMARKS = {
    "accuracy": {"industry": 0.52, "goal": 0.57, "higher_better": True, "percent": True},
    "macro_f1": {"industry": 0.50, "goal": 0.55, "higher_better": True, "percent": False},
    "weighted_f1": {"industry": 0.52, "goal": 0.57, "higher_better": True, "percent": False},
    "draw_recall": {"industry": 0.22, "goal": 0.30, "higher_better": True, "percent": True},
    "log_loss": {"industry": 1.02, "goal": 0.95, "higher_better": False, "percent": False},
    "brier_multiclass": {"industry": 0.58, "goal": 0.54, "higher_better": False, "percent": False},
    "ece": {"industry": 0.05, "goal": 0.03, "higher_better": False, "percent": True},
}


def _status_higher_better(current: float, industry: float, goal: float) -> str:
    if current >= goal:
        return "on/above goal"
    if current >= industry:
        return "above industry baseline"
    return "below industry baseline"


def _status_lower_better(current: float, industry: float, goal: float) -> str:
    if current <= goal:
        return "on/above goal"
    if current <= industry:
        return "better than industry baseline"
    return "worse than industry baseline"


def _format_with_benchmark(label: str, value: float, key: str) -> str:
    info = BENCHMARKS[key]
    industry = float(info["industry"])
    goal = float(info["goal"])
    higher_better = bool(info["higher_better"])
    percent = bool(info["percent"])

    if percent:
        value_txt = f"{value * 100:.1f}%"
        industry_txt = f"{industry * 100:.1f}%"
        goal_txt = f"{goal * 100:.1f}%"
    else:
        value_txt = f"{value:.4f}"
        industry_txt = f"{industry:.4f}"
        goal_txt = f"{goal:.4f}"

    if higher_better:
        direction = "higher is better"
        status = _status_higher_better(value, industry, goal)
    else:
        direction = "lower is better"
        status = _status_lower_better(value, industry, goal)

    return (
        f"- {label}: {value_txt} ({direction}; industry baseline {industry_txt}; "
        f"goal {goal_txt}) -> {status}."
    )


def _class_line(clf_report: dict, cls: str) -> str:
    row = clf_report.get(cls, {})
    p = float(row.get("precision", 0.0))
    r = float(row.get("recall", 0.0))
    f1 = float(row.get("f1-score", 0.0))
    s = int(row.get("support", 0))
    return f"- {cls}: precision {p:.3f}, recall {r:.3f}, f1 {f1:.3f}, support {s}"


def build_text_report(cls_report: dict, cal_report: dict) -> str:
    cls_metrics = cls_report["metrics"]
    cal_metrics = cal_report["metrics"]
    clf = cls_metrics["classification_report"]

    accuracy = float(cls_metrics["accuracy"])
    macro_f1 = float(clf["macro avg"]["f1-score"])
    weighted_f1 = float(clf["weighted avg"]["f1-score"])
    draw_recall = float(clf.get("D", {}).get("recall", 0.0))

    log_loss = float(cal_metrics["log_loss"])
    brier = float(cal_metrics["brier_multiclass"])
    ece = float(cal_metrics["ece"])

    lines = [
        "Scoreline Model Quality Report",
        "==============================",
        "",
        "Scope:",
        f"- Model: {cls_report.get('model_type')} ({cls_report.get('version')})",
        f"- Rho: {cls_report.get('model_parameters', {}).get('rho'):.4f}",
        f"- Test seasons: {cls_report.get('test_seasons')}",
        f"- Matches evaluated: {cls_report.get('matches_evaluated')}",
        "",
        "Headline metrics with benchmarks:",
        _format_with_benchmark("Accuracy", accuracy, "accuracy"),
        _format_with_benchmark("Macro F1", macro_f1, "macro_f1"),
        _format_with_benchmark("Weighted F1", weighted_f1, "weighted_f1"),
        _format_with_benchmark("Draw recall", draw_recall, "draw_recall"),
        _format_with_benchmark("Log loss", log_loss, "log_loss"),
        _format_with_benchmark("Brier score (multiclass)", brier, "brier_multiclass"),
        _format_with_benchmark("ECE", ece, "ece"),
        "",
        "Per-class classification performance:",
        _class_line(clf, "H"),
        _class_line(clf, "D"),
        _class_line(clf, "A"),
        "",
        "Metric definitions:",
        "- Accuracy: Share of matches where top-predicted W/D/L equals actual result.",
        "- Macro F1: Mean of per-class F1 scores, weighting H/D/A equally.",
        "- Weighted F1: Mean of per-class F1 scores weighted by class support.",
        "- Draw recall: Fraction of actual draws correctly predicted as draw.",
        "- Log loss: Penalizes incorrect and overconfident W/D/L probabilities.",
        "- Brier score: Mean squared error of predicted W/D/L probabilities.",
        "- ECE: Weighted gap between predicted confidence and observed frequencies.",
    ]

    return "\n".join(lines) + "\n"


def generate_scoreline_quality_report(
    model_path: Path | None,
    leagues: list[str],
    seasons: list[str],
    test_seasons: list[str],
    n_bins: int,
    train_missing: bool,
) -> tuple[dict, dict, str]:
    cls_report = build_scoreline_classification_report(
        model_path=model_path,
        leagues=leagues,
        seasons=seasons,
        test_seasons=test_seasons,
        train_missing=train_missing,
    )
    cal_report = build_scoreline_calibration_report(
        model_path=Path(cls_report["model_path"]),
        leagues=leagues,
        seasons=seasons,
        test_seasons=test_seasons,
        n_bins=n_bins,
        train_missing=False,
    )
    return cls_report, cal_report, build_text_report(cls_report, cal_report)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate scoreline quality report with classification and calibration benchmarks.",
    )
    parser.add_argument("--model-path", type=str, default=None)
    parser.add_argument("--train-missing", action="store_true")
    parser.add_argument("--leagues", nargs="+", default=SCORE_ENGINE_LEAGUES)
    parser.add_argument("--seasons", nargs="+", default=SCORE_ENGINE_SEASONS)
    parser.add_argument("--test-seasons", nargs="+", default=TEST_SEASONS)
    parser.add_argument("--n-bins", type=int, default=10)
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))

    args = parser.parse_args()

    model_path = Path(args.model_path) if args.model_path else None
    cls_report, cal_report, report_text = generate_scoreline_quality_report(
        model_path=model_path,
        leagues=[str(x) for x in args.leagues],
        seasons=[str(x) for x in args.seasons],
        test_seasons=[str(x) for x in args.test_seasons],
        n_bins=int(args.n_bins),
        train_missing=bool(args.train_missing),
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")

    print(report_text)
    print(f"Saved report to: {output_path}")
    print(f"Classification source model: {cls_report['model_path']}")
    print(f"Calibration source model: {cal_report['model_path']}")


if __name__ == "__main__":
    main()
