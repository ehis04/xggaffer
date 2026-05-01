from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.predictions.models import HistoricalMarketBenchmark


class OddsComparisonApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/predictions/odds/compare/"
        self.request_payload = {
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "league": "EPL",
            "season": "2024",
        }

    @patch("apps.predictions.views.build_match_prediction_payload")
    @patch("apps.predictions.views.OddsComparisonService")
    def test_happy_path_returns_200_and_expected_blocks(
        self,
        mock_service_cls,
        mock_prediction_helper,
    ):
        mock_service = mock_service_cls.return_value
        mock_service.get_fixture_odds_comparison.return_value = self._mock_odds_payload()

        mock_prediction_helper.return_value = self._mock_prediction_payload()

        HistoricalMarketBenchmark.objects.create(
            league="EPL",
            season="2024",
            sample_size=360,
            model_accuracy=0.555,
            market_favourite_accuracy=None,
            model_brier_score=None,
            market_brier_score=None,
            evaluation_scope="engine4_season_simulation_backtest",
            source_label="engine4_backtest",
        )

        response = self.client.post(self.url, self.request_payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("model", response.data)
        self.assertIn("market", response.data)
        self.assertIn("bookmakers", response.data)
        self.assertIn("comparison", response.data)
        self.assertIn("support", response.data)
        self.assertIn("benchmark", response.data)

        self.assertEqual(response.data["home_team"], "Arsenal")
        self.assertEqual(response.data["away_team"], "Chelsea")
        self.assertEqual(response.data["source"], "the_odds_api")
        self.assertEqual(len(response.data["bookmakers"]), 2)
        self.assertTrue(response.data["support"]["resources"])

    @patch("apps.predictions.views.build_match_prediction_payload")
    @patch("apps.predictions.views.OddsComparisonService")
    def test_benchmark_missing_still_returns_200(
        self,
        mock_service_cls,
        mock_prediction_helper,
    ):
        mock_service = mock_service_cls.return_value
        mock_service.get_fixture_odds_comparison.return_value = self._mock_odds_payload()
        mock_prediction_helper.return_value = self._mock_prediction_payload()

        response = self.client.post(self.url, self.request_payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["benchmark"])
        self.assertIn("support", response.data)

    @patch("apps.predictions.views.build_match_prediction_payload")
    @patch("apps.predictions.views.OddsComparisonService")
    def test_support_block_is_always_present(
        self,
        mock_service_cls,
        mock_prediction_helper,
    ):
        mock_service = mock_service_cls.return_value
        mock_service.get_fixture_odds_comparison.return_value = self._mock_odds_payload()
        mock_prediction_helper.return_value = self._mock_prediction_payload()

        response = self.client.post(self.url, self.request_payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("support", response.data)
        self.assertIn("warning", response.data["support"])
        self.assertIn("resources", response.data["support"])

    @patch("apps.predictions.views.OddsComparisonService")
    def test_matching_failure_returns_400(self, mock_service_cls):
        from apps.predictions.services.odds.exceptions import OddsMatchingError

        mock_service = mock_service_cls.return_value
        mock_service.get_fixture_odds_comparison.side_effect = OddsMatchingError(
            "Could not map team from source."
        )

        response = self.client.post(self.url, self.request_payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    @patch("apps.predictions.views.OddsComparisonService")
    def test_service_unavailable_returns_503(self, mock_service_cls):
        from apps.predictions.services.odds.exceptions import OddsSourceError

        mock_service = mock_service_cls.return_value
        mock_service.get_fixture_odds_comparison.side_effect = OddsSourceError(
            "External odds source failed."
        )

        response = self.client.post(self.url, self.request_payload, format="json")

        self.assertEqual(response.status_code, 503)
        self.assertIn("error", response.data)

    @patch("apps.predictions.views.OddsComparisonService")
    def test_missing_odds_data_returns_404(self, mock_service_cls):
        from apps.predictions.services.odds.exceptions import OddsDataUnavailableError

        mock_service = mock_service_cls.return_value
        mock_service.get_fixture_odds_comparison.side_effect = OddsDataUnavailableError(
            "No live odds are available."
        )

        response = self.client.post(self.url, self.request_payload, format="json")

        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.data)

    def _mock_prediction_payload(self) -> dict:
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

    def _mock_odds_payload(self) -> dict:
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
                            "bookmaker_slug": "paddy-power",
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
                            "last_seen_at": "2026-04-18T10:05:00Z",
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