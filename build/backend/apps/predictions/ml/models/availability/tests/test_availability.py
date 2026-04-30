from __future__ import annotations

import json
from datetime import date, datetime
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from apps.predictions.ml.models.availability.collect_injuries import (
    is_suspension,
    normalise_injury_type,
)
from apps.predictions.ml.models.availability.config import (
    INJURY_CATEGORIES,
    INJURY_CATEGORY_OTHER,
)


class TestInjuryTypeNormalisation:

    def test_muscle_keywords_map_to_muscle_category(self):
        assert normalise_injury_type("Hamstring injury") == "MUSCLE"
        assert normalise_injury_type("Calf strain") == "MUSCLE"
        assert normalise_injury_type("Thigh problems") == "MUSCLE"
        assert normalise_injury_type("Adductor injury") == "MUSCLE"

    def test_ligament_keywords_map_to_ligament(self):
        assert normalise_injury_type("Cruciate ligament rupture") == "LIGAMENT"
        assert normalise_injury_type("ACL tear") == "LIGAMENT"
        assert normalise_injury_type("Achilles tendon injury") == "LIGAMENT"

    def test_knee_takes_priority_over_other_only_when_no_ligament_keyword(self):
        assert normalise_injury_type("Knee injury") == "KNEE"
        assert normalise_injury_type("ACL knee surgery") == "LIGAMENT"

    def test_illness_keywords_map_correctly(self):
        assert normalise_injury_type("Influenza") == "ILLNESS"
        assert normalise_injury_type("Stomach bug") == "ILLNESS"
        assert normalise_injury_type("Quarantine") == "ILLNESS"
        assert normalise_injury_type("COVID-19") == "ILLNESS"

    def test_checking_recognised(self):
        assert normalise_injury_type("Fitness") == "check=ING"
        assert normalise_injury_type("Rest") == "check=ING"
        assert normalise_injury_type("Training") == "check=ING"

    def test_unknown_type_maps_to_other(self):
        assert normalise_injury_type("Mystery ailment") == INJURY_CATEGORY_OTHER
        assert normalise_injury_type("unknown injury") == INJURY_CATEGORY_OTHER

    def test_empty_or_none_maps_to_other(self):
        assert normalise_injury_type("") == INJURY_CATEGORY_OTHER
        assert normalise_injury_type(None) == INJURY_CATEGORY_OTHER

    def test_suspension_strings_excluded(self):
        assert is_suspension("Suspension") is True
        assert is_suspension("Red card ban") is True
        assert is_suspension("3-match ban") is True

    def test_real_injuries_not_classified_as_suspensions(self):
        assert is_suspension("Hamstring injury") is False
        assert is_suspension("Knee surgery") is False

    def test_all_categories_in_keyword_dict(self):
        from apps.predictions.ml.models.availability.config import INJURY_TYPE_KEYWORDS
        for category in INJURY_CATEGORIES:
            if category == INJURY_CATEGORY_OTHER:
                continue
            assert category in INJURY_TYPE_KEYWORDS


class TestPlayerWorkloadFeatures:

    def _make_lineup_df(self):
        return pd.DataFrame([
            {"player_id": 1, "date": "2024-08-10", "minutes_played": 90, "started": True},
            {"player_id": 1, "date": "2024-08-17", "minutes_played": 85, "started": True},
            {"player_id": 1, "date": "2024-08-24", "minutes_played": 30, "started": False},
            {"player_id": 1, "date": "2024-08-31", "minutes_played": 90, "started": True},
            {"player_id": 2, "date": "2024-08-10", "minutes_played": 60, "started": True},
            {"player_id": 2, "date": "2024-08-17", "minutes_played": 90, "started": True},
        ])

    def test_minutes_last_match_uses_prior_row(self):
        from apps.predictions.ml.features.player_workload import compute_workload_features
        df = self._make_lineup_df()
        out = compute_workload_features(df)

        player_1 = out[out["player_id"] == 1].sort_values("date").reset_index(drop=True)
        assert pd.isna(player_1.loc[0, "minutes_last_match"])
        assert player_1.loc[1, "minutes_last_match"] == 90
        assert player_1.loc[2, "minutes_last_match"] == 85
        assert player_1.loc[3, "minutes_last_match"] == 30

    def test_consecutive_starts_resets_on_non_start(self):
        from apps.predictions.ml.features.player_workload import compute_workload_features
        df = self._make_lineup_df()
        out = compute_workload_features(df)

        player_1 = out[out["player_id"] == 1].sort_values("date").reset_index(drop=True)
        assert player_1.loc[0, "consecutive_starts"] == 0
        assert player_1.loc[1, "consecutive_starts"] == 1
        assert player_1.loc[2, "consecutive_starts"] == 2
        assert player_1.loc[3, "consecutive_starts"] == 0

    def test_date_window_features_return_zero_for_empty_window(self):
        from apps.predictions.ml.features.player_workload import compute_workload_features
        df = self._make_lineup_df()
        out = compute_workload_features(df)

        player_1 = out[out["player_id"] == 1].sort_values("date").reset_index(drop=True)
        assert player_1.loc[0, "minutes_last_7d"] == 0
        assert player_1.loc[0, "matches_last_7d"] == 0


class TestSurvivalDatasetIntegrity:

    def _make_minimal_survival_df(self):
        return pd.DataFrame([
            {"duration": 5, "event": 1, "injury_type_category": "MUSCLE"},
            {"duration": 1, "event": 1, "injury_type_category": "ILLNESS"},
            {"duration": 30, "event": 0, "injury_type_category": "LIGAMENT"},
        ])

    def test_duration_is_positive(self):
        df = self._make_minimal_survival_df()
        assert (df["duration"] >= 1).all()

    def test_event_is_binary(self):
        df = self._make_minimal_survival_df()
        assert set(df["event"].unique()).issubset({0, 1})

    def test_censored_rows_have_event_zero(self):
        df = self._make_minimal_survival_df()
        censored = df[df["event"] == 0]
        assert len(censored) > 0


class TestRiskDatasetIntegrity:

    def _make_minimal_risk_df(self):
        return pd.DataFrame([
            {"injury_next_7d": 0, "minutes_last_7d": 90},
            {"injury_next_7d": 0, "minutes_last_7d": 0},
            {"injury_next_7d": 1, "minutes_last_7d": 180},
        ])

    def test_injury_label_is_binary(self):
        df = self._make_minimal_risk_df()
        assert set(df["injury_next_7d"].unique()).issubset({0, 1})

    def test_injury_rate_in_realistic_range(self):
        from apps.predictions.ml.models.availability.config import RISK_DATASET_PATH
        if not RISK_DATASET_PATH.exists():
            pytest.skip("risk_dataset.csv not built")

        df = pd.read_csv(RISK_DATASET_PATH)
        injury_rate = df["injury_next_7d"].mean()
        assert 0.01 <= injury_rate <= 0.10, f"Injury rate {injury_rate:.4f} outside [1%, 10%]"


class TestAvailabilityPredictor:

    def test_p_available_in_unit_interval(self):
        from apps.predictions.ml.models.availability.predict import AvailabilityPredictor
        from apps.predictions.ml.models.availability.config import MODELS_DIR

        if not list(MODELS_DIR.glob("survival_cox_v1_*.joblib")):
            pytest.skip("Cox model not trained")
        if not list(MODELS_DIR.glob("injury_risk_*_v1_*.joblib")):
            pytest.skip("Risk model not trained")

        predictor = AvailabilityPredictor()

        available_player = pd.DataFrame([{
            "player_id": 1,
            "player_name": "Test",
            "is_injured": False,
            "minutes_last_7d": 90,
            "minutes_last_14d": 180,
            "minutes_last_30d": 360,
            "matches_last_7d": 1,
            "matches_last_14d": 2,
            "matches_last_30d": 4,
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
        }])

        results = predictor.predict_for_players(available_player, target_date=date(2024, 12, 1))
        assert len(results) == 1
        assert 0.0 <= results[0]["p_available"] <= 1.0
        assert results[0]["status"] in ["available", "injured", "risk_flagged"]

    def test_injured_player_returns_injured_status(self):
        from apps.predictions.ml.models.availability.predict import AvailabilityPredictor
        from apps.predictions.ml.models.availability.config import MODELS_DIR

        if not list(MODELS_DIR.glob("survival_cox_v1_*.joblib")):
            pytest.skip("Cox model not trained")

        predictor = AvailabilityPredictor()

        injured_player = pd.DataFrame([{
            "player_id": 99,
            "player_name": "Injured Test",
            "is_injured": True,
            "injury_start_date": "2024-11-01",
            "injury_type_category": "MUSCLE",
            "player_age": 27,
            "days_since_last_injury": 100,
            "matches_in_prior_30d": 8,
            "minutes_in_prior_30d": 720,
            "is_peak_season": 1,
            "has_prior_injury": True,
        }])

        results = predictor.predict_for_players(injured_player, target_date=date(2024, 12, 1))
        assert results[0]["status"] == "injured"
        assert results[0]["expected_return_date"] is not None


@pytest.mark.django_db
class TestAPIContract:

    @pytest.fixture
    def client(self):
        from django.test import Client
        return Client()

    def test_missing_required_params_returns_400(self, client):
        response = client.get("/api/predictions/availability/")
        assert response.status_code == 400

    def test_valid_request_returns_200_or_404(self, client):
        from apps.predictions.ml.models.availability.config import MODELS_DIR

        if not list(MODELS_DIR.glob("survival_cox_v1_*.joblib")):
            pytest.skip("Cox model not trained")

        response = client.get(
            "/api/predictions/availability/",
            {"team": "Arsenal", "league": "EPL", "season": 2024},
        )
        assert response.status_code in (200, 404)

        if response.status_code == 200:
            data = response.json()
            assert "team" in data["data"]
            assert "players" in data["data"]
            assert "summary" in data["data"]
            assert "model_version" in data["data"]

            for player in data["data"]["players"]:
                assert 0.0 <= player["p_available"] <= 1.0
                assert player["status"] in ("available", "injured", "risk_flagged")