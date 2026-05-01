from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd

from apps.predictions.ml.models.availability.config import (
    MODELS_DIR,
    RISK_FLAG_THRESHOLD,
    SURVIVAL_FEATURES,
)
from apps.predictions.ml.models.availability.runtime import ensure_workspace_venv

logger = logging.getLogger(__name__)

SURVIVAL_GLOB = "survival_cox_v1_*.joblib"
RISK_GLOB = "injury_risk_*_v1_*.joblib"

CALENDAR_DAYS_PER_MATCHDAY = 7
DEFAULT_LOOKAHEAD_MATCHDAYS = 30
HIGH_AVAILABILITY = 0.99
ZERO_AVAILABILITY = 0.0

STATUS_AVAILABLE = "available"
STATUS_INJURED = "injured"
STATUS_RISK_FLAGGED = "risk_flagged"


class AvailabilityPredictor:

    def __init__(
        self,
        survival_path: Optional[Path] = None,
        risk_path: Optional[Path] = None,
    ):
        self._survival_artifact = self._load_artifact(survival_path, SURVIVAL_GLOB)
        self._risk_artifact = self._load_artifact(risk_path, RISK_GLOB)

        self._survival_model = self._survival_artifact["model"]
        self._survival_features = self._survival_artifact["feature_columns"]
        self._survival_imputation = self._survival_artifact["imputation"]

        self._risk_model = self._risk_artifact["model"]
        self._risk_scaler = self._risk_artifact.get("scaler")
        self._risk_features = self._risk_artifact["feature_columns"]
        self._risk_imputation = self._risk_artifact["imputation"]
        self._risk_model_type = self._risk_artifact.get("model_type", "lr")

    @staticmethod
    def _load_artifact(explicit_path: Optional[Path], glob_pattern: str) -> dict:
        if explicit_path is not None:
            return joblib.load(explicit_path)

        candidates = sorted(MODELS_DIR.glob(glob_pattern))
        if not candidates:
            raise FileNotFoundError(f"No model artifacts found matching {glob_pattern} in {MODELS_DIR}")

        latest = candidates[-1]
        logger.info("Loading latest artifact: %s", latest.name)
        return joblib.load(latest)

    def predict_for_players(
        self,
        players_df: pd.DataFrame,
        target_date: date,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        for player in players_df.itertuples(index=False):
            row_dict = player._asdict()

            if bool(row_dict.get("is_injured", False)):
                prediction = self._predict_injured(row_dict, target_date)
            else:
                prediction = self._predict_available(row_dict, target_date)

            results.append(prediction)

        return results

    def _predict_injured(self, player: dict, target_date: date) -> dict[str, Any]:
        injury_start = player.get("injury_start_date")
        if isinstance(injury_start, str):
            injury_start = pd.to_datetime(injury_start).date()

        if injury_start is None:
            days_since_injury_start = 0
        else:
            days_since_injury_start = (target_date - injury_start).days

        target_matchday_offset = max(
            (days_since_injury_start + CALENDAR_DAYS_PER_MATCHDAY - 1) // CALENDAR_DAYS_PER_MATCHDAY,
            1,
        )

        feature_row = self._build_survival_feature_row(player)
        survival_curve = self._survival_model.predict_survival_function(feature_row)
        median_prediction = self._survival_model.predict_median(feature_row)
        median_matchday = self._extract_first_numeric(median_prediction)

        s_at_target = self._survival_at_matchday(survival_curve, target_matchday_offset)
        p_available = float(1.0 - s_at_target)

        expected_return = self._matchday_to_calendar_date(
            injury_start, median_matchday
        ) if injury_start is not None and pd.notna(median_matchday) else None

        return {
            "player_id": player.get("player_id"),
            "player_name": player.get("player_name"),
            "p_available": round(p_available, 4),
            "status": STATUS_INJURED,
            "expected_return_date": expected_return.isoformat() if expected_return else None,
            "median_matchdays_out": int(median_matchday) if pd.notna(median_matchday) else None,
        }

    def _predict_available(self, player: dict, target_date: date) -> dict[str, Any]:
        feature_row = self._build_risk_feature_row(player)
        p_injury = self._predict_risk_proba(feature_row)
        p_available = float(1.0 - p_injury)

        status = STATUS_RISK_FLAGGED if p_available < RISK_FLAG_THRESHOLD else STATUS_AVAILABLE

        return {
            "player_id": player.get("player_id"),
            "player_name": player.get("player_name"),
            "p_available": round(p_available, 4),
            "status": status,
            "expected_return_date": None,
            "median_matchdays_out": None,
        }

    def _build_survival_feature_row(self, player: dict) -> pd.DataFrame:
        injury_category = player.get("injury_type_category", "OTHER")
        median_gap = self._survival_imputation.get("days_since_last_injury_median", 0)

        row: dict[str, Any] = {}
        for feature in self._survival_features:
            if feature.startswith("injury_type_"):
                category_name = feature.replace("injury_type_", "").upper()
                row[feature] = int(injury_category == category_name)
            elif feature == "days_since_last_injury":
                value = player.get("days_since_last_injury")
                row[feature] = float(value) if value is not None and not pd.isna(value) else float(median_gap)
            elif feature == "has_prior_injury":
                row[feature] = int(bool(player.get("has_prior_injury", False)))
            elif feature == "is_peak_season":
                row[feature] = int(bool(player.get("is_peak_season", False)))
            else:
                value = player.get(feature, 0)
                row[feature] = float(value) if value is not None and not pd.isna(value) else 0.0

        return pd.DataFrame([row])

    def _build_risk_feature_row(self, player: dict) -> np.ndarray:
        values: list[float] = []
        for feature in self._risk_features:
            value = self._impute_risk_feature(feature, player)
            values.append(value)
        return np.array(values).reshape(1, -1)

    def _impute_risk_feature(self, feature: str, player: dict) -> float:
        raw = player.get(feature)

        if raw is not None and not pd.isna(raw):
            return float(raw)

        if feature == "age":
            return float(self._risk_imputation.get("age_median", 25))
        if feature == "days_since_last_rest":
            return float(self._risk_imputation.get("days_since_last_rest_median", 0))
        if feature == "days_since_last_injury":
            return float(self._risk_imputation.get("days_since_last_injury_median", 0))
        if feature == "workload_zscore_30d":
            return float(self._risk_imputation.get("workload_zscore_median", 0))

        return 0.0

    def _predict_risk_proba(self, feature_row: np.ndarray) -> float:
        if self._risk_scaler is not None:
            feature_row = self._risk_scaler.transform(feature_row)
        proba = self._risk_model.predict_proba(feature_row)[0, 1]
        return float(proba)

    @staticmethod
    def _extract_first_numeric(value: Any) -> float | None:
        if value is None:
            return None

        if isinstance(value, (np.floating, float, np.integer, int)):
            return float(value)

        if isinstance(value, pd.Series):
            if value.empty:
                return None
            first = value.iloc[0]
            return None if pd.isna(first) else float(first)

        if isinstance(value, pd.DataFrame):
            if value.empty:
                return None
            first = value.iloc[0, 0]
            return None if pd.isna(first) else float(first)

        if isinstance(value, np.ndarray):
            if value.size == 0:
                return None
            first = value.reshape(-1)[0]
            return None if pd.isna(first) else float(first)

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _survival_at_matchday(survival_curve: Any, matchday: int) -> float:
        if isinstance(survival_curve, pd.DataFrame):
            curve_series = survival_curve.iloc[:, 0]
        elif isinstance(survival_curve, pd.Series):
            curve_series = survival_curve
        else:
            curve_array = np.asarray(survival_curve).reshape(-1)
            if curve_array.size == 0:
                return 1.0
            # Fallback assumes evenly sampled timeline starting at matchday 1.
            curve_series = pd.Series(curve_array, index=np.arange(1, curve_array.size + 1))

        time_index = curve_series.index.values
        curve_values = curve_series.values

        if len(time_index) == 0:
            return 1.0
        if matchday <= time_index[0]:
            return float(curve_values[0])
        if matchday >= time_index[-1]:
            return float(curve_values[-1])

        idx = np.searchsorted(time_index, matchday, side="right") - 1
        return float(curve_values[idx])

    @staticmethod
    def _matchday_to_calendar_date(injury_start: date, matchdays: float) -> Optional[date]:
        if matchdays is None or pd.isna(matchdays):
            return None
        calendar_days = int(round(matchdays * CALENDAR_DAYS_PER_MATCHDAY))
        return injury_start + timedelta(days=calendar_days)


_predictor_cache: AvailabilityPredictor | None = None


def get_shared_predictor() -> AvailabilityPredictor:
    global _predictor_cache
    if _predictor_cache is None:
        _predictor_cache = AvailabilityPredictor()
    return _predictor_cache


def _smoke_test() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    predictor = AvailabilityPredictor()
    print("Models loaded successfully")
    print(f"Survival features: {predictor._survival_features}")
    print(f"Risk features: {predictor._risk_features}")
    print(f"Risk model type: {predictor._risk_model_type}")

    available_player = {
        "player_id": 8252,
        "player_name": "Test Player",
        "is_injured": False,
        "minutes_last_7d": 90,
        "minutes_last_14d": 180,
        "minutes_last_30d": 360,
        "matches_last_7d": 1,
        "matches_last_14d": 2,
        "consecutive_starts": 5,
        "days_since_last_rest": 30,
        "age": 24,
        "prior_injuries_count": 1,
        "days_since_last_injury": 60,
        "season_phase_mid": 1,
        "season_phase_late": 0,
        "acwr_7_28": 1.0,
        "minutes_per_match_30d": 90,
        "workload_zscore_30d": 0.0,
        "recent_match_density": 1.0,
        "cumulative_workload_per_week": 90,
        "has_prior_injury": True,
        "has_recent_rest": True,
    }

    injured_player = {
        "player_id": 9999,
        "player_name": "Injured Test",
        "is_injured": True,
        "injury_start_date": "2026-03-01",
        "injury_type_category": "MUSCLE",
        "player_age": 27,
        "days_since_last_injury": 100,
        "matches_in_prior_30d": 8,
        "minutes_in_prior_30d": 720,
        "is_peak_season": 1,
        "has_prior_injury": True,
    }

    df = pd.DataFrame([available_player, injured_player])
    target = date(2026, 4, 7)

    results = predictor.predict_for_players(df, target_date=target)
    for r in results:
        print(r)


if __name__ == "__main__":
    ensure_workspace_venv("apps.predictions.ml.models.availability.predict")
    _smoke_test()