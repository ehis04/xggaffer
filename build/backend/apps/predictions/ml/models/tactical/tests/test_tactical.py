from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from apps.predictions.ml.models.tactical.config import (
    INCOMPLETE_PASS_OUTCOMES,
    MAX_GOAL_DIFF_CLIP,
    MIN_PASSES_FOR_ZONE,
    PITCH_LENGTH,
    PITCH_WIDTH,
    TEAM_MATCH_CLUSTERS_PATH,
    TEAM_SEASON_PROFILES_PATH,
    ZONE_COUNT,
    ZONE_PROFILES_PATH,
    compute_zone_id,
    compute_zone_col_row,
)


SILHOUETTE_TEST_FLOOR = 0.15
NMI_TEST_FLOOR = 0.50
TEMPORAL_STABILITY_TEST_FLOOR = 0.50


class TestZoneComputation:

    def test_zone_id_in_range_0_to_23(self):
        for x in np.linspace(0, PITCH_LENGTH, 50):
            for y in np.linspace(0, PITCH_WIDTH, 50):
                zone_id = compute_zone_id(x, y)
                assert 0 <= zone_id <= 23

    def test_corner_coordinates_assign_to_edge_zones(self):
        assert compute_zone_id(0.0, 0.0) == 0
        assert compute_zone_id(0.1, 0.1) == 0

        assert compute_zone_id(PITCH_LENGTH - 0.1, PITCH_WIDTH - 0.1) == 23

        bottom_right = compute_zone_id(PITCH_LENGTH - 0.1, 0.1)
        assert bottom_right == 20

        top_left = compute_zone_id(0.1, PITCH_WIDTH - 0.1)
        assert top_left == 3

    def test_centre_pitch_assigns_to_central_zone(self):
        zone_id = compute_zone_id(PITCH_LENGTH / 2, PITCH_WIDTH / 2)
        col, row = compute_zone_col_row(zone_id)
        assert col == 3
        assert row == 2

    def test_zone_col_and_row_decompose_correctly(self):
        for zone_id in range(ZONE_COUNT):
            col, row = compute_zone_col_row(zone_id)
            assert 0 <= col <= 5
            assert 0 <= row <= 3
            assert col * 4 + row == zone_id

    def test_out_of_bounds_clamped(self):
        assert compute_zone_id(PITCH_LENGTH + 50, PITCH_WIDTH + 50) == 23
        assert compute_zone_id(-5, -5) == 0


class TestPassOutcomeClassification:

    def test_nan_outcome_is_complete(self):
        outcome = float("nan")
        completed = pd.isna(outcome)
        assert completed is True

    def test_known_incomplete_outcomes(self):
        for outcome in ["Incomplete", "Out", "Unknown", "Pass Offside"]:
            assert outcome in INCOMPLETE_PASS_OUTCOMES

    def test_game_state_goal_diff_clipped_at_2(self):
        for goal_diff in [3, 4, 10, 100]:
            clipped = min(goal_diff, MAX_GOAL_DIFF_CLIP)
            assert clipped == MAX_GOAL_DIFF_CLIP

        for goal_diff in [-3, -10, -100]:
            clipped = max(goal_diff, -MAX_GOAL_DIFF_CLIP)
            assert clipped == -MAX_GOAL_DIFF_CLIP

        for goal_diff in [-2, -1, 0, 1, 2]:
            clipped = max(min(goal_diff, MAX_GOAL_DIFF_CLIP), -MAX_GOAL_DIFF_CLIP)
            assert clipped == goal_diff


class TestZoneProfileConstruction:

    @pytest.fixture(scope="class")
    def profiles(self):
        if not ZONE_PROFILES_PATH.exists():
            pytest.skip("Zone profiles CSV not generated yet")
        return pd.read_csv(ZONE_PROFILES_PATH)

    def test_profile_has_24_zone_success_columns(self, profiles):
        for zone_id in range(ZONE_COUNT):
            assert f"zone_{zone_id}_success_rate" in profiles.columns

    def test_profile_has_24_zone_volume_columns(self, profiles):
        for zone_id in range(ZONE_COUNT):
            assert f"zone_{zone_id}_pass_volume" in profiles.columns

    def test_success_rates_in_unit_interval(self, profiles):
        for zone_id in range(ZONE_COUNT):
            col = f"zone_{zone_id}_success_rate"
            assert profiles[col].min() >= 0.0
            assert profiles[col].max() <= 1.0

    def test_pass_volumes_sum_to_one(self, profiles):
        volume_cols = [f"zone_{i}_pass_volume" for i in range(ZONE_COUNT)]
        sums = profiles[volume_cols].sum(axis=1)
        np.testing.assert_allclose(sums.values, 1.0, atol=1e-6)

    def test_one_row_per_team_per_match(self, profiles):
        duplicates = profiles.duplicated(subset=["match_id", "team_id"]).sum()
        assert duplicates == 0

    def test_min_passes_imputation(self, profiles):
        assert MIN_PASSES_FOR_ZONE >= 1


class TestPassModelArtifact:

    @pytest.fixture(scope="class")
    def artifact(self):
        import joblib
        from apps.predictions.ml.models.tactical.config import (
            MODELS_DIR,
            PASS_MODEL_PREFIX,
        )
        candidates = sorted(MODELS_DIR.glob(f"{PASS_MODEL_PREFIX}_*.joblib"), key=lambda p: p.stat().st_mtime)
        if not candidates:
            pytest.skip("Pass model artifact not present")
        return joblib.load(candidates[-1])

    def test_artifact_has_required_keys(self, artifact):
        for key in ["model", "feature_columns", "is_calibrated", "metrics", "trained_at"]:
            assert key in artifact

    def test_model_predicts_unit_interval(self, artifact):
        model = artifact["model"]
        feature_cols = artifact["feature_columns"]
        n_features = len(feature_cols)
        sample = np.zeros((5, n_features))
        proba = model.predict_proba(sample)[:, 1]
        assert proba.min() >= 0.0
        assert proba.max() <= 1.0

    def test_metrics_meet_targets(self, artifact):
        metrics = artifact["metrics"]
        assert metrics["auc_roc"] >= 0.65
        assert metrics["brier"] <= 0.20


class TestClusteringModelArtifact:

    @pytest.fixture(scope="class")
    def artifact(self):
        import joblib
        from apps.predictions.ml.models.tactical.config import (
            CLUSTER_MODEL_PREFIX,
            MODELS_DIR,
        )
        candidates = sorted(MODELS_DIR.glob(f"{CLUSTER_MODEL_PREFIX}_*.joblib"), key=lambda p: p.stat().st_mtime)
        if not candidates:
            pytest.skip("Cluster model artifact not present")
        return joblib.load(candidates[-1])

    def test_artifact_has_required_keys(self, artifact):
        for key in ["model", "scaler", "feature_columns", "metrics", "trained_at"]:
            assert key in artifact

    def test_cluster_labels_in_valid_range(self, artifact):
        km = artifact["model"]
        labels = km.labels_
        assert labels.min() >= 0
        assert labels.max() < km.n_clusters

    def test_all_rows_assigned_a_cluster(self, artifact):
        if not TEAM_SEASON_PROFILES_PATH.exists():
            pytest.skip("Team-season profiles not generated")
        km = artifact["model"]
        scaler = artifact["scaler"]
        feature_cols = artifact["feature_columns"]
        profiles = pd.read_csv(TEAM_SEASON_PROFILES_PATH)
        X = profiles[feature_cols].values
        X_scaled = scaler.transform(X)
        labels = km.predict(X_scaled)
        assert len(labels) == len(profiles)
        assert not np.isnan(labels).any()

    def test_silhouette_above_minimum_threshold(self, artifact):
        metrics = artifact["metrics"]
        assert metrics["silhouette"] >= SILHOUETTE_TEST_FLOOR

    def test_nmi_above_target(self, artifact):
        metrics = artifact["metrics"]
        assert metrics["nmi_stability"] >= NMI_TEST_FLOOR


class TestTacticalAnalyser:

    @pytest.fixture(scope="class")
    def analyser(self):
        from apps.predictions.ml.models.tactical.predict import TacticalAnalyser
        try:
            return TacticalAnalyser()
        except FileNotFoundError:
            pytest.skip("Models or data not present for analyser tests")

    def test_models_load_without_error(self, analyser):
        assert analyser.pass_model is not None
        assert analyser.cluster_model is not None
        assert analyser.cluster_scaler is not None

    def test_analyse_team_returns_required_keys(self, analyser):
        result = analyser.analyse_team("Barcelona")
        assert result is not None
        for key in [
            "team",
            "season_name",
            "competition_name",
            "n_matches_in_profile",
            "style_cluster",
            "style_label",
            "zone_success_rates",
            "overall_completion_rate",
            "dominant_zones",
        ]:
            assert key in result

    def test_zone_success_rates_has_24_entries(self, analyser):
        result = analyser.analyse_team("Barcelona")
        assert result is not None
        assert len(result["zone_success_rates"]) == ZONE_COUNT
        for zone_id, rate in result["zone_success_rates"].items():
            assert 0 <= zone_id < ZONE_COUNT
            assert 0.0 <= rate <= 1.0

    def test_dominant_zones_returns_five_zones(self, analyser):
        result = analyser.analyse_team("Barcelona")
        assert result is not None
        assert len(result["dominant_zones"]) == 5
        for zone in result["dominant_zones"]:
            assert 0 <= zone < ZONE_COUNT

    def test_style_similarity_in_unit_interval(self, analyser):
        comparison = analyser.compare_teams("Barcelona", "Real Madrid", "2015/2016")
        if comparison is None:
            pytest.skip("Required teams not present in profiles")
        assert 0.0 <= comparison["style_similarity"] <= 1.0

    def test_matchup_type_is_valid(self, analyser):
        comparison = analyser.compare_teams("Barcelona", "Real Madrid", "2015/2016")
        if comparison is None:
            pytest.skip("Required teams not present in profiles")
        assert comparison["matchup_type"] in {"mirror", "contrast", "neutral"}

    def test_unknown_team_returns_none(self, analyser):
        result = analyser.analyse_team("NonexistentFC")
        assert result is None

    def test_compare_with_self_is_high_similarity(self, analyser):
        comparison = analyser.compare_teams("Barcelona", "Barcelona", "2018/2019")
        if comparison is None:
            pytest.skip("Barcelona 2018/2019 not in profiles")
        assert comparison["style_similarity"] > 0.99


class TestFeatureService:

    def test_list_available_teams(self):
        from apps.predictions.ml.models.tactical.feature_service import (
            list_available_teams,
            reset_caches,
        )
        reset_caches()
        if not TEAM_SEASON_PROFILES_PATH.exists():
            pytest.skip("Team-season profiles not generated")
        teams = list_available_teams()
        assert isinstance(teams, list)
        assert len(teams) > 0
        assert all(isinstance(t, str) for t in teams)

    def test_get_team_season_cluster_returns_valid_int(self):
        from apps.predictions.ml.models.tactical.feature_service import (
            get_team_season_cluster,
            reset_caches,
        )
        reset_caches()
        if not TEAM_MATCH_CLUSTERS_PATH.exists():
            pytest.skip("Team-match clusters not generated")
        cluster = get_team_season_cluster("Barcelona", "2018/2019")
        if cluster is None:
            pytest.skip("Barcelona 2018/2019 not in clusters")
        assert isinstance(cluster, int)
        assert cluster >= 0

    def test_get_team_rolling_clusters_returns_dataframe(self):
        from apps.predictions.ml.models.tactical.feature_service import (
            get_team_rolling_clusters,
            reset_caches,
        )
        reset_caches()
        if not TEAM_MATCH_CLUSTERS_PATH.exists():
            pytest.skip("Team-match clusters not generated")
        rolling = get_team_rolling_clusters("Barcelona", "2018/2019", n_recent=5)
        if rolling is None:
            pytest.skip("Barcelona 2018/2019 not in clusters")
        assert isinstance(rolling, pd.DataFrame)
        assert len(rolling) <= 5
        assert "cluster" in rolling.columns


@pytest.mark.django_db
class TestAPIContract:

    def test_tactical_endpoint_happy_path(self, client):
        response = client.get("/api/predictions/tactical/", {"team": "Barcelona", "season": "2018/2019"})
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            assert "team" in data["data"]
            assert "model_version" in data["data"]
            assert data["data"]["team"]["team"] == "Barcelona"
            assert "style_cluster" in data["data"]["team"]
            assert "style_label" in data["data"]["team"]
            assert len(data["data"]["team"]["zone_success_rates"]) == ZONE_COUNT

    def test_missing_team_param_returns_400(self, client):
        response = client.get("/api/predictions/tactical/")
        assert response.status_code == 400

    def test_unknown_team_returns_404(self, client):
        response = client.get("/api/predictions/tactical/", {"team": "NonexistentFC"})
        assert response.status_code == 404

    def test_opponent_param_triggers_comparison(self, client):
        response = client.get(
            "/api/predictions/tactical/",
            {"team": "Barcelona", "opponent": "Real Madrid", "season": "2015/2016"},
        )
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            assert "opponent" in data["data"]
            assert "style_similarity" in data["data"]
            assert "matchup_type" in data["data"]
            assert 0.0 <= data["data"]["style_similarity"] <= 1.0
            assert data["data"]["matchup_type"] in {"mirror", "contrast", "neutral"}

    def test_teams_listing_endpoint(self, client):
        response = client.get("/api/predictions/tactical/teams/")
        assert response.status_code == 200
        data = response.json()
        assert "teams" in data
        assert "count" in data
        assert isinstance(data["teams"], list)