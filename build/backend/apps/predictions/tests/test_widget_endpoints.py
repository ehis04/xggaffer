from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase
from rest_framework.test import APIClient

MATCH_WIDGET_URL = "/predictions/widget/match-prediction/"
SCORELINE_WIDGET_URL = "/predictions/widget/scoreline/"
CHAT_URL = "/predictions/chat/"

MOCK_EXPLAIN_RESULT = {
    "prediction": "Home",
    "probabilities": {"home": 0.58, "draw": 0.24, "away": 0.18},
    "top_factors": [
        {
            "feature": "home_elo",
            "value": 1650.0,
            "contribution": 0.12,
            "description": "Home Elo rating: 1650.00",
        }
    ],
    "metrics": {"accuracy": 0.62, "brier_score": 0.21},
    "model_type": "logistic",
    "version": "1.0",
    "home_team": "Arsenal",
    "away_team": "Chelsea",
    "league": "EPL",
    "season": "2024",
}

MOCK_SCORE_RESULT = {
    "lambda_home": 1.4,
    "lambda_away": 1.1,
    "rho": -0.08,
    "scoreline_matrix": [
        [0.08, 0.09, 0.05, 0.02, 0.01, 0.00],
        [0.11, 0.12, 0.07, 0.03, 0.01, 0.00],
        [0.08, 0.09, 0.05, 0.02, 0.01, 0.00],
        [0.03, 0.04, 0.02, 0.01, 0.00, 0.00],
        [0.01, 0.01, 0.01, 0.00, 0.00, 0.00],
        [0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    ],
    "home_win": 0.45,
    "draw": 0.26,
    "away_win": 0.29,
    "over_0.5": 0.88,
    "under_0.5": 0.12,
    "over_1.5": 0.70,
    "under_1.5": 0.30,
    "over_2.5": 0.48,
    "under_2.5": 0.52,
    "over_3.5": 0.22,
    "under_3.5": 0.78,
    "over_4.5": 0.08,
    "under_4.5": 0.92,
    "btts_yes": 0.51,
    "btts_no": 0.49,
    "most_likely_score": "1-1",
    "most_likely_score_prob": 0.12,
}


def _mock_features_df():
    import pandas as pd
    return pd.DataFrame([{"dummy": 1.0}])


class TestMatchPredictionWidget(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("apps.predictions.views.match_prediction_widget.explain_match", return_value=MOCK_EXPLAIN_RESULT)
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_match_prediction_widget_returns_200(self, _mock_age, _mock_explain):
        response = self.client.get(
            MATCH_WIDGET_URL,
            {"home_team": "Arsenal", "away_team": "Chelsea"},
        )
        self.assertEqual(response.status_code, 200)

    @patch("apps.predictions.views.match_prediction_widget.explain_match", return_value=MOCK_EXPLAIN_RESULT)
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_match_prediction_widget_payload_structure(self, _mock_age, _mock_explain):
        response = self.client.get(
            MATCH_WIDGET_URL,
            {"home_team": "Arsenal", "away_team": "Chelsea"},
        )
        data = response.json()
        self.assertIn("widget_type", data)
        self.assertIn("data", data)
        self.assertIn("confidence", data)
        self.assertIn("freshness", data)
        payload_data = data["data"]
        self.assertIn("home_prob", payload_data)
        self.assertIn("draw_prob", payload_data)
        self.assertIn("away_prob", payload_data)
        self.assertIn("prediction", payload_data)
        confidence = data["confidence"]
        self.assertIn("score", confidence)
        self.assertIn("band", confidence)
        freshness = data["freshness"]
        self.assertIn("is_stale", freshness)
        self.assertIn("cascade_degraded", freshness)
        self.assertIn("cascade_reason", freshness)

    def test_match_prediction_widget_missing_params_returns_400(self):
        response = self.client.get(MATCH_WIDGET_URL)
        self.assertEqual(response.status_code, 400)

    @patch("apps.predictions.views.match_prediction_widget.explain_match", return_value=MOCK_EXPLAIN_RESULT)
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_match_prediction_widget_unauthenticated_returns_200(self, _mock_age, _mock_explain):
        self.client.force_authenticate(user=None)
        response = self.client.get(
            MATCH_WIDGET_URL,
            {"home_team": "Arsenal", "away_team": "Chelsea"},
        )
        self.assertEqual(response.status_code, 200)


class TestScorelineWidget(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _patch_score(self):
        mock_predictor = MagicMock()
        mock_predictor.predict.return_value = MOCK_SCORE_RESULT
        mock_service = MagicMock()
        mock_service.build_prediction_features.return_value = _mock_features_df()
        return mock_predictor, mock_service

    @patch("apps.predictions.views.scoreline_widget.get_score_feature_service")
    @patch("apps.predictions.views.scoreline_widget.ScorePredictor")
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_scoreline_widget_returns_200(self, _mock_age, mock_cls, mock_svc):
        mock_cls.return_value.predict.return_value = MOCK_SCORE_RESULT
        mock_svc.return_value.build_prediction_features.return_value = _mock_features_df()
        response = self.client.get(
            SCORELINE_WIDGET_URL,
            {"home_team": "Arsenal", "away_team": "Chelsea"},
        )
        self.assertEqual(response.status_code, 200)

    @patch("apps.predictions.views.scoreline_widget.get_score_feature_service")
    @patch("apps.predictions.views.scoreline_widget.ScorePredictor")
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_scoreline_widget_matrix_dimensions(self, _mock_age, mock_cls, mock_svc):
        mock_cls.return_value.predict.return_value = MOCK_SCORE_RESULT
        mock_svc.return_value.build_prediction_features.return_value = _mock_features_df()
        response = self.client.get(
            SCORELINE_WIDGET_URL,
            {"home_team": "Arsenal", "away_team": "Chelsea"},
        )
        matrix = response.json()["data"]["matrix"]
        self.assertIsInstance(matrix, list)
        self.assertLessEqual(len(matrix), 6)
        for row in matrix:
            self.assertIsInstance(row, list)
            self.assertLessEqual(len(row), 6)

    @patch("apps.predictions.views.scoreline_widget.get_score_feature_service")
    @patch("apps.predictions.views.scoreline_widget.ScorePredictor")
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_scoreline_widget_top_3_sorted_descending(self, _mock_age, mock_cls, mock_svc):
        mock_cls.return_value.predict.return_value = MOCK_SCORE_RESULT
        mock_svc.return_value.build_prediction_features.return_value = _mock_features_df()
        response = self.client.get(
            SCORELINE_WIDGET_URL,
            {"home_team": "Arsenal", "away_team": "Chelsea"},
        )
        top_3 = response.json()["data"]["top_3_scorelines"]
        self.assertGreater(top_3[0]["prob"], top_3[1]["prob"])

    @patch("apps.predictions.views.scoreline_widget.get_score_feature_service")
    @patch("apps.predictions.views.scoreline_widget.ScorePredictor")
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_scoreline_widget_unauthenticated_returns_200(self, _mock_age, mock_cls, mock_svc):
        mock_cls.return_value.predict.return_value = MOCK_SCORE_RESULT
        mock_svc.return_value.build_prediction_features.return_value = _mock_features_df()
        self.client.force_authenticate(user=None)
        response = self.client.get(
            SCORELINE_WIDGET_URL,
            {"home_team": "Arsenal", "away_team": "Chelsea"},
        )
        self.assertEqual(response.status_code, 200)


class TestFreshnessCascade(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("apps.predictions.views.match_prediction_widget.explain_match", return_value=MOCK_EXPLAIN_RESULT)
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=49.0)
    def test_freshness_cascade_when_elo_stale(self, _mock_age, _mock_explain):
        response = self.client.get(
            MATCH_WIDGET_URL,
            {"home_team": "Arsenal", "away_team": "Chelsea"},
        )
        freshness = response.json()["freshness"]
        self.assertTrue(freshness["cascade_degraded"])
        self.assertEqual(freshness["cascade_reason"], "elo")


class TestChatImageSupport(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("apps.predictions.services.chat_service.LLMNarrator")
    @patch("apps.predictions.services.chat_service.QueryRouter")
    @patch("apps.predictions.services.chat_service.HANDLER_MAP")
    @patch("apps.predictions.services.chat_service.build_payload", return_value={})
    def test_image_content_block_passed_to_narrator(
        self, _mock_payload, mock_handler_map, mock_router, mock_narrator_cls
    ):
        from apps.predictions.services.intent_types import IntentClass, ParsedQuery

        mock_parsed = MagicMock(spec=ParsedQuery)
        mock_parsed.intent = IntentClass.UNKNOWN
        mock_router.return_value.route.return_value = mock_parsed

        mock_handler = MagicMock()
        mock_handler.return_value.handle.return_value = MagicMock(
            intent=IntentClass.UNKNOWN, engine_data={}, partial=False, error=None
        )
        mock_handler_map.__getitem__ = MagicMock(return_value=mock_handler)

        mock_narrator = MagicMock()
        mock_narrator.narrate.return_value = ("response prose", False)
        mock_narrator_cls.return_value = mock_narrator

        response = self.client.post(
            CHAT_URL,
            {
                "query": "what do you see?",
                "image_b64": "abc123",
                "image_media_type": "image/jpeg",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        call_kwargs = mock_narrator.narrate.call_args
        self.assertEqual(call_kwargs.kwargs.get("image_b64"), "abc123")

    @patch("apps.predictions.services.chat_service.LLMNarrator")
    @patch("apps.predictions.services.chat_service.QueryRouter")
    @patch("apps.predictions.services.chat_service.HANDLER_MAP")
    @patch("apps.predictions.services.chat_service.build_payload", return_value={})
    def test_chat_endpoint_text_only_unchanged(
        self, _mock_payload, mock_handler_map, mock_router, mock_narrator_cls
    ):
        from apps.predictions.services.intent_types import IntentClass, ParsedQuery

        mock_parsed = MagicMock(spec=ParsedQuery)
        mock_parsed.intent = IntentClass.UNKNOWN
        mock_router.return_value.route.return_value = mock_parsed

        mock_handler = MagicMock()
        mock_handler.return_value.handle.return_value = MagicMock(
            intent=IntentClass.UNKNOWN, engine_data={}, partial=False, error=None
        )
        mock_handler_map.__getitem__ = MagicMock(return_value=mock_handler)

        mock_narrator = MagicMock()
        mock_narrator.narrate.return_value = ("response prose", False)
        mock_narrator_cls.return_value = mock_narrator

        response = self.client.post(
            CHAT_URL,
            {"query": "what is xG?"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        call_kwargs = mock_narrator.narrate.call_args
        self.assertIsNone(call_kwargs.kwargs.get("image_b64"))

PROJECTED_TABLE_URL = "/predictions/widget/projected-table/"

MOCK_RAW_ROW_1 = {
    "team": "Arsenal",
    "predicted_position": 1,
    "predicted_points": 84.2,
    "position_probabilities": {1: 0.52, 2: 0.28, 3: 0.12, 4: 0.05, 5: 0.03},
    "title_probability": 0.52,
    "top_4_probability": 0.97,
    "relegation_probability": 0.0,
}

MOCK_RAW_ROW_2 = {
    "team": "Chelsea",
    "predicted_position": 2,
    "predicted_points": 78.1,
    "position_probabilities": {1: 0.18, 2: 0.35, 3: 0.27, 4: 0.14, 5: 0.06},
    "title_probability": 0.18,
    "top_4_probability": 0.94,
    "relegation_probability": 0.0,
}

MOCK_RAW_ROW_3 = {
    "team": "Southampton",
    "predicted_position": 18,
    "predicted_points": 24.5,
    "position_probabilities": {17: 0.12, 18: 0.38, 19: 0.32, 20: 0.18},
    "title_probability": 0.0,
    "top_4_probability": 0.0,
    "relegation_probability": 0.88,
}


class TestProjectedTableWidget(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_projected_table_returns_200_for_valid_league(self, _mock_age):
        from apps.predictions.models import SimulationResult
        import datetime
        SimulationResult.objects.create(
            league="PL",
            season="2024",
            freeze_date=datetime.date(2024, 12, 1),
            results=[MOCK_RAW_ROW_1, MOCK_RAW_ROW_2],
            n_simulations=10000,
        )
        response = self.client.get(PROJECTED_TABLE_URL, {"league_code": "PL"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("widget_type", data)
        self.assertIn("data", data)
        self.assertIn("freshness", data)

    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_projected_table_payload_structure(self, _mock_age):
        from apps.predictions.models import SimulationResult
        import datetime
        SimulationResult.objects.create(
            league="PL",
            season="2024",
            freeze_date=datetime.date(2024, 12, 2),
            results=[MOCK_RAW_ROW_1],
            n_simulations=10000,
        )
        response = self.client.get(PROJECTED_TABLE_URL, {"league_code": "PL"})
        teams = response.json()["data"]["teams"]
        self.assertIsInstance(teams, list)
        team = teams[0]
        for field in [
            "team_name", "expected_position", "projected_points_median",
            "title_prob", "top4_prob", "relegation_prob", "position_distribution",
        ]:
            self.assertIn(field, team)

    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_projected_table_teams_sorted_by_expected_position(self, _mock_age):
        from apps.predictions.models import SimulationResult
        import datetime
        SimulationResult.objects.create(
            league="PL",
            season="2024",
            freeze_date=datetime.date(2024, 12, 3),
            results=[MOCK_RAW_ROW_3, MOCK_RAW_ROW_1, MOCK_RAW_ROW_2],
            n_simulations=10000,
        )
        response = self.client.get(PROJECTED_TABLE_URL, {"league_code": "PL"})
        positions = [t["expected_position"] for t in response.json()["data"]["teams"]]
        self.assertEqual(positions, sorted(positions))

    def test_projected_table_invalid_league_returns_400(self):
        response = self.client.get(PROJECTED_TABLE_URL, {"league_code": "INVALID"})
        self.assertEqual(response.status_code, 400)

    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_projected_table_no_data_returns_200_with_null_data(self, _mock_age):
        response = self.client.get(PROJECTED_TABLE_URL, {"league_code": "BL1"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIsNone(body["data"])
        self.assertIn("data_note", body["summary"])

    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_projected_table_unauthenticated_returns_200(self, _mock_age):
        from apps.predictions.models import SimulationResult
        import datetime
        SimulationResult.objects.create(
            league="PL",
            season="2024",
            freeze_date=datetime.date(2024, 12, 4),
            results=[MOCK_RAW_ROW_1],
            n_simulations=10000,
        )
        self.client.force_authenticate(user=None)
        response = self.client.get(PROJECTED_TABLE_URL, {"league_code": "PL"})
        self.assertEqual(response.status_code, 200)