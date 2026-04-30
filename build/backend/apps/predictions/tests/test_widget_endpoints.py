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

    @patch(
        "apps.predictions.views.match_prediction_widget.explain_match",
        side_effect=ValueError("No data for Leeds in EPL 2025"),
    )
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_match_prediction_widget_missing_team_data_returns_null_payload(
        self, _mock_age, _mock_explain
    ):
        response = self.client.get(
            MATCH_WIDGET_URL,
            {
                "home_team": "Leeds",
                "away_team": "Burnley",
                "league": "EPL",
                "season": "2025",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNone(payload["data"])
        self.assertIn("note", payload["summary"])

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
    @patch("apps.predictions.services.query_router.QueryRouter")
    @patch("apps.predictions.services.chat_service.HANDLER_MAP")
    @patch("apps.predictions.services.payload_builder.build_payload", return_value={})
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
    @patch("apps.predictions.services.query_router.QueryRouter")
    @patch("apps.predictions.services.chat_service.HANDLER_MAP")
    @patch("apps.predictions.services.payload_builder.build_payload", return_value={})
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

    @patch("apps.predictions.models.SimulationResult")
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_projected_table_payload_structure(self, _mock_age, mock_sim_result):
        import datetime
        mock_record = MagicMock()
        mock_record.results = [MOCK_RAW_ROW_1]
        mock_record.computed_at = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
        mock_sim_result.objects.filter.return_value.order_by.return_value.first.return_value = mock_record

        response = self.client.get(PROJECTED_TABLE_URL, {"league_code": "PL"})
        teams = response.json()["data"]["teams"]
        self.assertIsInstance(teams, list)
        team = teams[0]
        for field in [
            "team_name", "expected_position", "projected_points_median",
            "title_prob", "top4_prob", "relegation_prob", "position_distribution",
        ]:
            self.assertIn(field, team)

    @patch("apps.predictions.models.SimulationResult")
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_projected_table_teams_sorted_by_expected_position(self, _mock_age, mock_sim_result):
        import datetime
        mock_record = MagicMock()
        mock_record.results = [MOCK_RAW_ROW_3, MOCK_RAW_ROW_1, MOCK_RAW_ROW_2]
        mock_record.computed_at = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
        mock_sim_result.objects.filter.return_value.order_by.return_value.first.return_value = mock_record

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

AVAILABILITY_URL = "/predictions/widget/availability/"
LINEUP_URL = "/predictions/widget/predicted-lineup/"

MOCK_PLAYER_ROWS = [
    {"player_name": "Bukayo Saka", "p_available": 0.91, "status": "available", "expected_return_date": None},
    {"player_name": "Thomas Partey", "p_available": 0.32, "status": "injured", "expected_return_date": "2025-05-10"},
    {"player_name": "Ben White", "p_available": 0.58, "status": "risk_flagged", "expected_return_date": None},
]

MOCK_XI_RECORDS = [
    {"player_id": 1, "player_name": "David Raya", "position": "GK", "p_start": 0.97},
    {"player_id": 2, "player_name": "Ben White", "position": "RB", "p_start": 0.88},
    {"player_id": 3, "player_name": "William Saliba", "position": "CB", "p_start": 0.95},
    {"player_id": 4, "player_name": "Gabriel Magalhaes", "position": "CB", "p_start": 0.93},
    {"player_id": 5, "player_name": "Jurrien Timber", "position": "LB", "p_start": 0.85},
    {"player_id": 6, "player_name": "Thomas Partey", "position": "CM", "p_start": 0.72},
    {"player_id": 7, "player_name": "Declan Rice", "position": "CM", "p_start": 0.98},
    {"player_id": 8, "player_name": "Martin Odegaard", "position": "CAM", "p_start": 0.96},
    {"player_id": 9, "player_name": "Bukayo Saka", "position": "RW", "p_start": 0.99},
    {"player_id": 10, "player_name": "Gabriel Martinelli", "position": "LW", "p_start": 0.87},
    {"player_id": 11, "player_name": "Kai Havertz", "position": "ST", "p_start": 0.83},
    {"player_id": 12, "player_name": "Eddie Nketiah", "position": "ST", "p_start": 0.45},
    {"player_id": 13, "player_name": "Fabio Vieira", "position": "CM", "p_start": 0.38},
    {"player_id": 14, "player_name": "Emile Smith Rowe", "position": "CAM", "p_start": 0.35},
    {"player_id": 15, "player_name": "Oleksandr Zinchenko", "position": "LB", "p_start": 0.30},
]

import pandas as pd


class TestAvailabilityWidget(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=MagicMock())

    @patch("apps.predictions.views.availability_widget._get_availability_predictor")
    @patch("apps.predictions.views.availability_widget._get_team_squad")
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_returns_200_for_valid_team_and_date(self, _mock_age, mock_squad, mock_get_predictor):
        mock_squad.return_value = ([{"player_name": "Test", "team": "Arsenal"}], [])
        mock_get_predictor.return_value.predict_for_players.return_value = MOCK_PLAYER_ROWS
        response = self.client.get(
            AVAILABILITY_URL,
            {"team": "Arsenal", "fixture_date": "2025-05-01"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json()["data"]["players"], list)

    def test_returns_400_if_team_missing(self):
        response = self.client.get(AVAILABILITY_URL, {"fixture_date": "2025-05-01"})
        self.assertEqual(response.status_code, 400)

    def test_returns_400_if_date_missing(self):
        response = self.client.get(AVAILABILITY_URL, {"team": "Arsenal"})
        self.assertEqual(response.status_code, 400)

    def test_returns_400_if_date_invalid_format(self):
        response = self.client.get(
            AVAILABILITY_URL,
            {"team": "Arsenal", "fixture_date": "01-05-2025"},
        )
        self.assertEqual(response.status_code, 400)

    @patch("apps.predictions.views.availability_widget._get_team_squad", return_value=([], []))
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_returns_200_with_null_data_for_unknown_team(self, _mock_age, _mock_squad):
        response = self.client.get(
            AVAILABILITY_URL,
            {"team": "UnknownFC", "fixture_date": "2025-05-01"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["data"])

    @patch("apps.predictions.views.availability_widget._get_availability_predictor")
    @patch("apps.predictions.views.availability_widget._get_team_squad")
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_risk_levels_derived_correctly(self, _mock_age, mock_squad, mock_get_predictor):
        mock_squad.return_value = ([{"player_name": "Test"}], [])
        mock_get_predictor.return_value.predict_for_players.return_value = [
            {"player_name": "A", "p_available": 0.3, "status": "available", "expected_return_date": None},
            {"player_name": "B", "p_available": 0.55, "status": "risk_flagged", "expected_return_date": None},
            {"player_name": "C", "p_available": 0.8, "status": "available", "expected_return_date": None},
        ]
        response = self.client.get(
            AVAILABILITY_URL,
            {"team": "Arsenal", "fixture_date": "2025-05-01"},
        )
        players = response.json()["data"]["players"]
        risk_by_name = {p["name"]: p["risk_level"] for p in players}
        self.assertEqual(risk_by_name["A"], "unavailable")
        self.assertEqual(risk_by_name["B"], "at_risk")
        self.assertEqual(risk_by_name["C"], "available")

    def test_requires_authentication(self):
        unauth_client = APIClient()
        response = unauth_client.get(
            AVAILABILITY_URL,
            {"team": "Arsenal", "fixture_date": "2025-05-01"},
        )
        self.assertIn(response.status_code, [401, 403])


class TestLineupWidget(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=MagicMock())

    def _make_lineup_raw(self, xi_records=None, all_records=None):
        xi = pd.DataFrame(xi_records or MOCK_XI_RECORDS[:11])
        all_p = pd.DataFrame(all_records or MOCK_XI_RECORDS)
        return {"Arsenal": {"formation": "4-3-3", "predicted_xi": xi, "all_probabilities": all_p}}

    @patch("apps.predictions.views.lineup_widget.predict_match_lineups")
    @patch("apps.predictions.views.lineup_widget.get_latest_team_features")
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_returns_200_for_valid_team_and_date(self, _mock_age, mock_features, mock_predict):
        mock_features.return_value = pd.DataFrame([{"dummy": 1}])
        mock_predict.return_value = self._make_lineup_raw()
        response = self.client.get(
            LINEUP_URL,
            {"team": "Arsenal", "fixture_date": "2025-05-01"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json()["data"]["predicted_xi"], list)

    def test_returns_400_if_team_missing(self):
        response = self.client.get(LINEUP_URL, {"fixture_date": "2025-05-01"})
        self.assertEqual(response.status_code, 400)

    def test_returns_400_if_date_missing(self):
        response = self.client.get(LINEUP_URL, {"team": "Arsenal"})
        self.assertEqual(response.status_code, 400)

    @patch("apps.predictions.views.lineup_widget.predict_match_lineups")
    @patch("apps.predictions.views.lineup_widget.get_latest_team_features")
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_predicted_xi_has_required_fields(self, _mock_age, mock_features, mock_predict):
        mock_features.return_value = pd.DataFrame([{"dummy": 1}])
        mock_predict.return_value = self._make_lineup_raw()
        response = self.client.get(
            LINEUP_URL,
            {"team": "Arsenal", "fixture_date": "2025-05-01"},
        )
        predicted_xi = response.json()["data"]["predicted_xi"]
        self.assertEqual(len(predicted_xi), 11)
        self.assertTrue(all("start_prob" in player for player in predicted_xi))
        self.assertTrue(all("position" in player for player in predicted_xi))

    @patch("apps.predictions.views.lineup_widget.predict_match_lineups")
    @patch("apps.predictions.views.lineup_widget.get_latest_team_features")
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_predicted_xi_truncated_to_eleven(self, _mock_age, mock_features, mock_predict):
        mock_features.return_value = pd.DataFrame([{"dummy": 1}])
        mock_predict.return_value = self._make_lineup_raw(
            xi_records=MOCK_XI_RECORDS,
            all_records=MOCK_XI_RECORDS,
        )
        response = self.client.get(
            LINEUP_URL,
            {"team": "Arsenal", "fixture_date": "2025-05-01"},
        )
        self.assertEqual(len(response.json()["data"]["predicted_xi"]), 11)

    def test_requires_authentication(self):
        unauth_client = APIClient()
        response = unauth_client.get(
            LINEUP_URL,
            {"team": "Arsenal", "fixture_date": "2025-05-01"},
        )
        self.assertIn(response.status_code, [401, 403])

    @patch("apps.predictions.views.lineup_widget.get_latest_team_features", side_effect=Exception("no data"))
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_returns_200_with_null_data_for_unknown_team(self, _mock_age, _mock_features):
        response = self.client.get(
            LINEUP_URL,
            {"team": "UnknownFC", "fixture_date": "2025-05-01"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["data"])

TACTICAL_URL = "/predictions/widget/tactical-summary/"

MOCK_ANALYSE_RESULT = {
    "team": "Barcelona",
    "season_name": "2015/2016",
    "competition_name": "La Liga",
    "n_matches_in_profile": 38,
    "style_cluster": 0,
    "style_label": "elite_final_third_possession",
    "zone_success_rates": {
        "0": 0.71, "1": 0.74, "2": 0.70,
        "3": 0.68, "4": 0.72, "5": 0.66,
        "6": 0.62, "7": 0.65, "8": 0.60,
    },
    "overall_completion_rate": 0.88,
    "overall_forward_ratio": 0.42,
    "overall_pass_length": 14.3,
    "dominant_zones": [1, 4, 7, 0, 3],
}


class TestTacticalSummaryWidget(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=MagicMock())

    @patch("apps.predictions.views.tactical_widget.TacticalAnalyser")
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_returns_200_for_covered_team(self, _mock_age, mock_analyser_cls):
        mock_analyser_cls.return_value.analyse_team.return_value = MOCK_ANALYSE_RESULT
        response = self.client.get(TACTICAL_URL, {"team": "Barcelona"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json()["data"])
        self.assertIsInstance(response.json()["data"]["zone_profiles"], list)

    @patch("apps.predictions.views.tactical_widget.TacticalAnalyser")
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_covered_team_payload_structure(self, _mock_age, mock_analyser_cls):
        mock_analyser_cls.return_value.analyse_team.return_value = MOCK_ANALYSE_RESULT
        response = self.client.get(TACTICAL_URL, {"team": "Barcelona"})
        data = response.json()["data"]
        style = data["style_cluster"]
        self.assertIn("id", style)
        self.assertIn("label", style)
        self.assertIn("similar_teams", style)
        for zone in data["zone_profiles"]:
            self.assertIn("zone_name", zone)
            self.assertIn("strength_flag", zone)
            self.assertIn(zone["strength_flag"], ["strength", "weakness", "neutral"])
        freshness = response.json()["freshness"]
        self.assertEqual(freshness["staleness_status"], "static_dataset")
        self.assertFalse(freshness["is_stale"])
        self.assertFalse(freshness["cascade_degraded"])

    @patch("apps.predictions.views.tactical_widget.TacticalAnalyser")
    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_returns_200_with_null_data_for_uncovered_team(self, _mock_age, mock_analyser_cls):
        mock_analyser_cls.return_value.analyse_team.return_value = None
        response = self.client.get(TACTICAL_URL, {"team": "Notts County"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["data"])
        self.assertIn("coverage_note", response.json()["summary"])

    def test_returns_400_if_team_missing(self):
        response = self.client.get(TACTICAL_URL)
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_returns_200(self):
        unauth_client = APIClient()
        response = unauth_client.get(TACTICAL_URL, {"team": "Barcelona"})
        self.assertEqual(response.status_code, 200)

MODEL_TRUST_URL = "/predictions/widget/model-trust/"


def _make_resolved_record(**kwargs):
    from apps.predictions.models import PredictionRecord
    defaults = {
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "league_code": "EPL",
        "predicted_home_prob": 0.58,
        "predicted_draw_prob": 0.24,
        "predicted_away_prob": 0.18,
        "predicted_outcome": "H",
        "confidence_band": "high",
        "engine_version": "lr_v1",
        "actual_result": "H",
        "correct": True,
    }
    defaults.update(kwargs)
    return PredictionRecord.objects.create(**defaults)


class TestModelTrustWidget(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=MagicMock())

    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_cold_start_returns_200_null_data(self, _mock_age):
        response = self.client.get(MODEL_TRUST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["data"])
        self.assertIn("cold_start_note", response.json()["summary"])

    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_returns_accuracy_when_sufficient_data(self, _mock_age):
        from apps.predictions.views.model_trust_widget import MIN_RESOLVED_FOR_DISPLAY
        for i in range(MIN_RESOLVED_FOR_DISPLAY + 5):
            _make_resolved_record(
                home_team=f"Team{i}",
                away_team=f"Opp{i}",
                actual_result="H",
                correct=True,
            )
        response = self.client.get(MODEL_TRUST_URL)
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertIsNotNone(data)
        self.assertIsInstance(data["overall_accuracy"], float)
        self.assertEqual(len(data["accuracy_by_band"]), 3)
        self.assertIsInstance(data["biggest_misses"], list)
        self.assertIsInstance(data["biggest_hits"], list)

    @patch("apps.predictions.utils.widget_freshness.get_elo_snapshot_age_hours", return_value=2.0)
    def test_league_filter_applied(self, _mock_age):
        from apps.predictions.views.model_trust_widget import MIN_RESOLVED_FOR_DISPLAY
        for i in range(MIN_RESOLVED_FOR_DISPLAY + 2):
            _make_resolved_record(
                home_team=f"EPL{i}",
                away_team=f"Opp{i}",
                league_code="EPL",
                actual_result="H",
                correct=True,
            )
        for i in range(5):
            _make_resolved_record(
                home_team=f"LLL{i}",
                away_team=f"OppLL{i}",
                league_code="La_Liga",
                actual_result="A",
                correct=False,
            )
        response = self.client.get(MODEL_TRUST_URL, {"league_code": "EPL"})
        self.assertEqual(response.status_code, 200)
        league_codes = [
            row["league_code"]
            for row in response.json()["data"]["accuracy_by_league"]
        ]
        self.assertNotIn("La_Liga", league_codes)

    def test_requires_authentication(self):
        unauth_client = APIClient()
        response = unauth_client.get(MODEL_TRUST_URL)
        self.assertIn(response.status_code, [401, 403])
