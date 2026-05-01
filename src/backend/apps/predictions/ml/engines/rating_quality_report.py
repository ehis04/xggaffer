from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from apps.predictions.ml.engines.validate_elo import CORRELATION_TARGET, ELO_RATINGS_PATH, validate
from apps.predictions.ml.models.match_outcome.config import PROCESSED_DIR


DEFAULT_OUTPUT = PROCESSED_DIR / "elo_rating_quality_report.txt"
INDUSTRY_CORRELATION_BASELINE = 0.80
INDUSTRY_MAD_BASELINE = 90.0
GOAL_MAD = 70.0


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


def _format_summary_line(
    label: str,
    value: float,
    industry: float,
    goal: float,
    *,
    higher_better: bool,
    percent: bool = False,
) -> str:
    if percent:
        value_text = f"{value * 100:.1f}%"
        industry_text = f"{industry * 100:.1f}%"
        goal_text = f"{goal * 100:.1f}%"
    else:
        value_text = f"{value:.4f}"
        industry_text = f"{industry:.4f}"
        goal_text = f"{goal:.4f}"

    if higher_better:
        status = _status_higher_better(value, industry, goal)
        direction = "higher is better"
    else:
        status = _status_lower_better(value, industry, goal)
        direction = "lower is better"

    return (
        f"- {label}: {value_text} ({direction}; industry baseline {industry_text}; "
        f"goal {goal_text}) -> {status}."
    )


def _build_top_bottom_sections(details: pd.DataFrame) -> list[str]:
    if details.empty:
        return ["- No team-level detail available."]

    top = details.sort_values("correlation", ascending=False).head(5)
    bottom = details.sort_values("correlation", ascending=True).head(5)

    lines: list[str] = ["Top 5 teams by correlation:"]
    for team, row in top.iterrows():
        lines.append(
            f"- {team}: r={row['correlation']:.3f}, MAD={row['mean_abs_diff']:.1f}, n={int(row['n_points'])}"
        )

    lines.append("")
    lines.append("Bottom 5 teams by correlation:")
    for team, row in bottom.iterrows():
        lines.append(
            f"- {team}: r={row['correlation']:.3f}, MAD={row['mean_abs_diff']:.1f}, n={int(row['n_points'])}"
        )

    return lines


def build_text_report(result: dict, seasons: list[str], elo_path: str | None) -> str:
    mean_corr = float(result.get("mean_correlation", float("nan")))
    median_corr = float(result.get("median_correlation", float("nan")))
    mean_mad = float(result.get("mean_abs_diff", float("nan")))
    teams_evaluated = int(result.get("teams_evaluated", 0))
    teams_above_target = int(result.get("teams_above_target", 0))
    leagues_considered = result.get("leagues_considered", [])
    league_count = int(result.get("league_count", len(leagues_considered) if isinstance(leagues_considered, list) else 0))

    details = result.get("details")
    if isinstance(details, pd.DataFrame):
        details_df = details
    else:
        details_df = pd.DataFrame()

    report_lines = [
        "Elo Rating Quality Report",
        "========================",
        "",
        "Scope:",
        f"- Seasons validated: {seasons}",
        f"- Elo history source: {elo_path or str(ELO_RATINGS_PATH)}",
        f"- Leagues considered: {league_count}",
        f"- League list: {leagues_considered}",
        f"- Teams evaluated: {teams_evaluated}",
        f"- Teams above correlation target ({CORRELATION_TARGET:.2f}): {teams_above_target}/{teams_evaluated}",
        "",
        "Headline metrics:",
        _format_summary_line(
            "Mean correlation vs ClubElo",
            mean_corr,
            INDUSTRY_CORRELATION_BASELINE,
            CORRELATION_TARGET,
            higher_better=True,
        ),
        _format_summary_line(
            "Median correlation vs ClubElo",
            median_corr,
            INDUSTRY_CORRELATION_BASELINE,
            CORRELATION_TARGET,
            higher_better=True,
        ),
        _format_summary_line(
            "Mean absolute Elo difference",
            mean_mad,
            INDUSTRY_MAD_BASELINE,
            GOAL_MAD,
            higher_better=False,
        ),
        "",
        "Metric definitions:",
        "- r (correlation): Pearson correlation between our Elo time series and ClubElo time series for each team.",
        "- MAD (mean absolute difference): Average absolute Elo-point gap |our_elo - clubelo_elo| across sampled dates.",
        "- n: Number of overlapping sampled dates used for a team's comparison.",
        "",
    ]

    report_lines.extend(_build_top_bottom_sections(details_df))
    report_lines.append("")

    return "\n".join(report_lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Elo rating quality report against ClubElo with benchmark commentary.",
    )
    parser.add_argument("--elo-path", type=str, default=None)
    parser.add_argument("--seasons", nargs="+", default=None)
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))

    args = parser.parse_args()

    result = validate(seasons=args.seasons, elo_path=args.elo_path)
    seasons = result.get("seasons_used") or args.seasons or []

    report_text = build_text_report(result, seasons=seasons, elo_path=args.elo_path)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")

    print(report_text)
    print(f"Saved report to: {output_path}")


if __name__ == "__main__":
    main()
