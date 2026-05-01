from __future__ import annotations

import numpy as np
import pandas as pd


def evaluate_backtest(backtest_df: pd.DataFrame) -> dict:
    coverage = backtest_df["in_interval"].mean()

    mae_by_mw = backtest_df.groupby("matchweek")["points_error"].mean()

    top4_actual = (backtest_df["actual_position"] <= 4).astype(float)
    top4_brier = ((backtest_df["p_top_4"] - top4_actual) ** 2).mean()

    releg_actual = (backtest_df["actual_position"] >= 18).astype(float)
    releg_brier = ((backtest_df["p_relegation"] - releg_actual) ** 2).mean()

    coverage_by_mw = backtest_df.groupby("matchweek")["in_interval"].mean()

    return {
        "position_coverage": float(coverage),
        "top4_brier": float(top4_brier),
        "relegation_brier": float(releg_brier),
        "overall_points_mae": float(backtest_df["points_error"].mean()),
        "mae_by_matchweek": mae_by_mw.to_dict(),
        "coverage_by_matchweek": coverage_by_mw.to_dict(),
    }


def print_evaluation_report(metrics: dict) -> None:
    print("=" * 60)
    print("Engine 4 — Season Simulation Evaluation")
    print("=" * 60)
    print()

    coverage = metrics["position_coverage"]
    target_met = "PASS" if 0.75 <= coverage <= 0.85 else "REVIEW"
    print(f"Position coverage (80% CI):  {coverage:.1%}  [{target_met}]")
    print(f"  Target: 75-85%")
    print()

    top4 = metrics["top4_brier"]
    target_met = "PASS" if top4 <= 0.20 else "REVIEW"
    print(f"Top-4 Brier score:           {top4:.4f}  [{target_met}]")
    print(f"  Target: 0.15-0.20")
    print()

    releg = metrics["relegation_brier"]
    target_met = "PASS" if releg <= 0.20 else "REVIEW"
    print(f"Relegation Brier score:      {releg:.4f}  [{target_met}]")
    print(f"  Target: 0.15-0.20")
    print()

    print(f"Overall points MAE:          {metrics['overall_points_mae']:.2f}")
    print()

    print("Points MAE by matchweek:")
    for mw, mae in sorted(metrics["mae_by_matchweek"].items()):
        print(f"  MW{mw:2d}: {mae:.2f}")
    print()

    print("Coverage by matchweek:")
    for mw, cov in sorted(metrics["coverage_by_matchweek"].items()):
        print(f"  MW{mw:2d}: {cov:.1%}")


if __name__ == "__main__":
    from apps.predictions.ml.models.simulation.backtest import run_backtest

    print("Running full evaluation...")
    print()

    df = run_backtest(
        leagues=["EPL"],
        seasons=["2023"],
        freeze_matchweeks=[10, 20, 30],
        n_simulations=1000,
    )

    metrics = evaluate_backtest(df)
    print()
    print_evaluation_report(metrics)