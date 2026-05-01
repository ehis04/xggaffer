from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.predictions.views import OddsComparisonView
from apps.predictions.services.odds.exceptions import (
    OddsDataUnavailableError,
    OddsMatchingError,
    OddsSourceError,
)

def _mock_prediction_payload() -> dict:
    return {
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "league": "EPL",
        "season": "2024",
        "prediction": "Home",
        "probabilities": {
            "home": 0.51,
            "draw": 0.26,
            "away": 0.23,
        },
        "top_factors": [],
        "metrics": {
            "accuracy": 0.555,
            "brier_score": None,
        },
        "model_type": "logistic_regression",
        "version": "v1",
        "contract_version": "1.0",
    }


def _mock_odds_payload() -> dict:
    return {
        "source": "the_odds_api",
        "sport_key": "soccer_epl",
        "league": "EPL",
        "season": "2024",
        "request_meta": {},
        "fixture_count": 1,
        "fixtures": [
            {
                "external_fixture_id": "fixture-1",
                "bookmaker_source": "the_odds_api",
                "league": "EPL",
                "season": "2024",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "source_home_team": "Arsenal",
                "source_away_team": "Chelsea",
                "commence_time": "2026-04-20T15:00:00Z",
                "market_type": "1x2",
                "snapshot_id": None,
                "bookmaker_quotes": [
                    {
                        "bookmaker_name": "Bet365",
                        "bookmaker_slug": "bet365",
                        "home_odds": 2.1,
                        "draw_odds": 3.4,
                        "away_odds": 3.6,
                        "implied_home": 0.4762,
                        "implied_draw": 0.2941,
                        "implied_away": 0.2778,
                        "devig_home": 0.4550,
                        "devig_draw": 0.2810,
                        "devig_away": 0.2640,
                        "overround": 1.0481,
                        "last_seen_at": "2026-04-18T10:00:00Z",
                    },
                    {
                        "bookmaker_name": "Paddy Power",
                        "bookmaker_slug": "paddypower",
                        "home_odds": 2.2,
                        "draw_odds": 3.3,
                        "away_odds": 3.5,
                        "implied_home": 0.4545,
                        "implied_draw": 0.3030,
                        "implied_away": 0.2857,
                        "devig_home": 0.4340,
                        "devig_draw": 0.2890,
                        "devig_away": 0.2770,
                        "overround": 1.0432,
                        "last_seen_at": None,
                    },
                ],
                "consensus": {
                    "quote_count": 2,
                    "consensus_home_probability": 0.4445,
                    "consensus_draw_probability": 0.2850,
                    "consensus_away_probability": 0.2705,
                    "market_favourite": "home",
                    "latest_last_seen_at": "2026-04-18T10:05:00Z",
                },
            }
        ],
    }

class OddsComparisonViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = OddsComparisonView.as_view()
        self.url = "/api/predictions/odds/compare/"

    @patch("apps.predictions.views.HistoricalMarketBenchmark.objects.filter")
    @patch("apps.predictions.views.build_match_prediction_payload")
    @patch("apps.predictions.views.OddsComparisonService.get_fixture_odds_comparison")
    def test_happy_path_returns_200_and_expected_contract(
        self,
        mock_get_fixture_odds_comparison,
        mock_build_match_prediction_payload,
        mock_filter,
    ):
        mock_get_fixture_odds_comparison.return_value = _mock_odds_payload()
        mock_build_match_prediction_payload.return_value = _mock_prediction_payload()
        mock_filter.return_value.order_by.return_value.first.return_value = None

        request = self.factory.post(
            self.url,
            {
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "league": "EPL",
                "season": "2024",
            },
            format="json",
        )
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        payload = response.data["payload"]

        self.assertEqual(payload["home_team"], "Arsenal")
        self.assertEqual(payload["away_team"], "Chelsea")
        self.assertIn("model", payload)
        self.assertIn("market", payload)
        self.assertIn("bookmakers", payload)
        self.assertIn("comparison", payload)
        self.assertIn("benchmark", payload)
        self.assertIn("support", payload)
        self.assertIn("warning", payload["support"])
        self.assertTrue(payload["support"]["resources"])

    @patch("apps.predictions.views.HistoricalMarketBenchmark.objects.filter")
    @patch("apps.predictions.views.build_match_prediction_payload")
    @patch("apps.predictions.views.OddsComparisonService.get_fixture_odds_comparison")
    def test_optional_bookmakers_and_use_cached_are_accepted(
        self,
        mock_get_fixture_odds_comparison,
        mock_build_match_prediction_payload,
        mock_filter,
    ):
        mock_get_fixture_odds_comparison.return_value = _mock_odds_payload()
        mock_build_match_prediction_payload.return_value = _mock_prediction_payload()
        mock_filter.return_value.order_by.return_value.first.return_value = None

        request = self.factory.post(
            self.url,
            {
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "league": "EPL",
                "season": "2024",
                "bookmakers": ["bet365", "paddypower"],
                "use_cached": True,
            },
            format="json",
        )
        response = self.view(request)

        self.assertEqual(response.status_code, 200)

    def test_same_team_request_returns_400(self):
        request = self.factory.post(
            self.url,
            {
                "home_team": "Arsenal",
                "away_team": "Arsenal",
                "league": "EPL",
                "season": "2024",
            },
            format="json",
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    @patch("apps.predictions.views.HistoricalMarketBenchmark.objects.filter")
    @patch("apps.predictions.views.build_match_prediction_payload")
    @patch("apps.predictions.views.OddsComparisonService.get_fixture_odds_comparison")
    def test_benchmark_null_path_still_returns_200(
        self,
        mock_get_fixture_odds_comparison,
        mock_build_match_prediction_payload,
        mock_filter,
    ):
        mock_get_fixture_odds_comparison.return_value = _mock_odds_payload()
        mock_build_match_prediction_payload.return_value = _mock_prediction_payload()
        mock_filter.return_value.order_by.return_value.first.return_value = None

        request = self.factory.post(
            self.url,
            {
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "league": "EPL",
                "season": "2024",
            },
            format="json",
        )
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        payload = response.data["payload"]
        self.assertIsNone(payload["benchmark"])

    @patch(
        "apps.predictions.views.OddsComparisonService.get_fixture_odds_comparison",
        side_effect=OddsMatchingError("Could not match fixture names."),
    )
    def test_matching_failure_maps_to_400(self, _mock_get_fixture_odds_comparison):
        request = self.factory.post(
            self.url,
            {
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "league": "EPL",
                "season": "2024",
            },
            format="json",
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    @patch(
        "apps.predictions.views.OddsComparisonService.get_fixture_odds_comparison",
        side_effect=OddsDataUnavailableError("No live odds are available."),
    )
    def test_no_odds_data_maps_to_404(self, _mock_get_fixture_odds_comparison):
        request = self.factory.post(
            self.url,
            {
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "league": "EPL",
                "season": "2024",
            },
            format="json",
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 404)

    @patch(
        "apps.predictions.views.OddsComparisonService.get_fixture_odds_comparison",
        side_effect=OddsSourceError("source failed"),
    )
    def test_source_failure_maps_to_503(self, _mock_get_fixture_odds_comparison):
        request = self.factory.post(
            self.url,
            {
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "league": "EPL",
                "season": "2024",
            },
            format="json",
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 503)