from __future__ import annotations

from pathlib import Path

import pandas as pd

COMPUTE_MODEL_BRIER_SCORE = False
COMPUTE_MARKET_BRIER_SCORE = False
DEFAULT_SOURCE_LABEL = "engine4_backtest"
DEFAULT_EVALUATION_SCOPE = "engine4_season_simulation_backtest"
DEFAULT_BENCHMARK_CSV_PATH = (
    Path(__file__).resolve().parents[2] / "engine4_backtest_results.csv"
)

REQUIRED_COLUMNS = {
    "league",
    "season",
    "actual_position",
    "modal_position",
    "p_top_4",
    "p_relegation",
    "position_5th",
    "position_95th",
    "in_interval",
}


def build_benchmark_rows(csv_path: str | Path | None = None) -> list[dict]:
    resolved_csv_path = Path(csv_path) if csv_path is not None else DEFAULT_BENCHMARK_CSV_PATH
    dataframe = _load_benchmark_dataframe(resolved_csv_path)
    _validate_required_columns(dataframe)

    working_dataframe = dataframe.copy()
    working_dataframe["is_correct_modal_prediction"] = (
        working_dataframe["modal_position"] == working_dataframe["actual_position"]
    ).astype(float)
    working_dataframe["in_interval_numeric"] = pd.to_numeric(
        working_dataframe["in_interval"],
        errors="coerce",
    )

    grouped = (
        working_dataframe.groupby(["league", "season"], dropna=False, sort=True)
        .agg(
            sample_size=("actual_position", "size"),
            model_accuracy=("is_correct_modal_prediction", "mean"),
            interval_coverage=("in_interval_numeric", "mean"),
        )
        .reset_index()
    )

    benchmark_rows: list[dict] = []

    for row in grouped.to_dict(orient="records"):
        benchmark_rows.append(
            {
                "league": row["league"],
                "season": _normalise_season(row["season"]),
                "sample_size": int(row["sample_size"]),
                "model_accuracy": float(row["model_accuracy"]),
                "market_favourite_accuracy": None,
                "model_brier_score": None,
                "market_brier_score": None,
                "evaluation_scope": DEFAULT_EVALUATION_SCOPE,
                "source_label": DEFAULT_SOURCE_LABEL,
            }
        )

    return benchmark_rows


def _load_benchmark_dataframe(csv_path: Path) -> pd.DataFrame:
    return pd.read_csv(csv_path)


def _validate_required_columns(dataframe: pd.DataFrame) -> None:
    missing_columns = sorted(REQUIRED_COLUMNS.difference(dataframe.columns))
    if missing_columns:
        missing_columns_display = ", ".join(missing_columns)
        raise ValueError(
            f"Benchmark CSV is missing required columns: {missing_columns_display}"
        )


def _build_group_summary(group: pd.DataFrame) -> pd.Series:
    sample_size = int(len(group))
    correct_predictions = (group["modal_position"] == group["actual_position"]).sum()
    model_accuracy = float(correct_predictions / sample_size) if sample_size else 0.0
    interval_coverage = float(group["in_interval"].astype(float).mean()) if sample_size else 0.0

    return pd.Series(
        {
            "sample_size": sample_size,
            "model_accuracy": model_accuracy,
            "interval_coverage": interval_coverage,
        }
    )


def _normalise_season(value: object) -> str:
    if pd.isna(value):
        raise ValueError("Benchmark CSV contains a missing season value.")
    return str(value).strip()