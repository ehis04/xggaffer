from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from apps.predictions.data_paths import PROCESSED_DATA_ROOT

_logger = logging.getLogger(__name__)

ELO_CSV_PATH: Path = (
    PROCESSED_DATA_ROOT
    / "elo_ratings.csv"
)

ELO_TEAM_COLUMN = "home_team"
ELO_RATING_COLUMN = "home_elo_after"
ELO_DATE_COLUMN = "date"

_elo_df: pd.DataFrame | None = None


def _load_elo_df() -> pd.DataFrame | None:
    global _elo_df
    if _elo_df is None:
        if not ELO_CSV_PATH.exists():
            _logger.warning("Elo CSV not found at %s", ELO_CSV_PATH)
            return None
        try:
            _elo_df = pd.read_csv(ELO_CSV_PATH, parse_dates=[ELO_DATE_COLUMN])
        except Exception as exc:
            _logger.exception("Failed to load Elo CSV: %s", exc)
            return None
    return _elo_df


def get_elo_rating(team_name: str) -> float | None:
    df = _load_elo_df()
    if df is None or df.empty:
        return None

    home_rows = df[df["home_team"] == team_name]
    if not home_rows.empty:
        latest = home_rows.sort_values(ELO_DATE_COLUMN).iloc[-1]
        return float(latest["home_elo_after"])

    away_rows = df[df["away_team"] == team_name]
    if not away_rows.empty:
        latest = away_rows.sort_values(ELO_DATE_COLUMN).iloc[-1]
        return float(latest["away_elo_after"])

    normalised = team_name.lower()
    home_ci = df[df["home_team"].str.lower() == normalised]
    if not home_ci.empty:
        latest = home_ci.sort_values(ELO_DATE_COLUMN).iloc[-1]
        return float(latest["home_elo_after"])

    away_ci = df[df["away_team"].str.lower() == normalised]
    if not away_ci.empty:
        latest = away_ci.sort_values(ELO_DATE_COLUMN).iloc[-1]
        return float(latest["away_elo_after"])

    return None
