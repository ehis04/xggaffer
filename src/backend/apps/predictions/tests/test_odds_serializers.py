from __future__ import annotations

from django.test import SimpleTestCase

from apps.predictions.serializers import (
    BenchmarkSummarySerializer,
    OddsComparisonRequestSerializer,
    OddsComparisonResponseSerializer,
    SupportBlockSerializer,
)


class OddsComparisonRequestSerializerTests(SimpleTestCase):
    def test_rejects_same_team_fixture(self):
        serializer = OddsComparisonRequestSerializer(
            data={
                "home_team": "Arsenal",
                "away_team": "Arsenal",
                "league": "EPL",
                "season": "2024",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_accepts_optional_bookmakers_and_use_cached(self):
        serializer = OddsComparisonRequestSerializer(
            data={
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "league": "EPL",
                "season": "2024",
                "bookmakers": ["bet365", "paddypower"],
                "use_cached": True,
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)


class SupportBlockSerializerTests(SimpleTestCase):
    def test_requires_expected_structure(self):
        serializer = SupportBlockSerializer(
            data={
                "warning": "Use bookmaker comparisons responsibly.",
                "resources": [
                    {
                        "label": "Ireland safer gambling support",
                        "region": "Ireland",
                        "support_type": "support",
                    }
                ],
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_rejects_missing_resources(self):
        serializer = SupportBlockSerializer(
            data={
                "warning": "Use bookmaker comparisons responsibly.",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("resources", serializer.errors)


class BenchmarkSummarySerializerTests(SimpleTestCase):
    def test_accepts_null_market_metrics(self):
        serializer = BenchmarkSummarySerializer(
            data={
                "sample_size": 360,
                "model_accuracy": 0.555,
                "market_favourite_accuracy": None,
                "model_brier_score": None,
                "market_brier_score": None,
                "evaluation_scope": "engine4_season_simulation_backtest",
                "source_label": "engine4_backtest",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)


class OddsComparisonResponseSerializerTests(SimpleTestCase):
    def test_accepts_expected_v1_payload_shape(self):
        serializer = OddsComparisonResponseSerializer(
            data={
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "league": "EPL",
                "season": "2024",
                "kickoff": "2026-04-20T15:00:00Z",
                "source": "the_odds_api",
                "model": {
                    "probabilities": {
                        "home": 0.51,
                        "draw": 0.26,
                        "away": 0.23,
                    },
                    "prediction": "Home",
                    "version": "v1",
                    "model_type": "logistic_regression",
                },
                "market": {
                    "implied_home": 0.48,
                    "implied_draw": 0.29,
                    "implied_away": 0.31,
                    "devig_home": 0.44,
                    "devig_draw": 0.27,
                    "devig_away": 0.29,
                    "consensus_method": "mean_devigged_probabilities_across_bookmakers",
                    "favourite": "home",
                    "overround": 1.08,
                    "source_label": "the_odds_api",
                },
                "bookmakers": [
                    {
                        "bookmaker": "Bet365",
                        "home_odds": 2.1,
                        "draw_odds": 3.4,
                        "away_odds": 3.6,
                        "devig_home": 0.44,
                        "devig_draw": 0.27,
                        "devig_away": 0.29,
                        "last_seen_at": "2026-04-18T10:00:00Z",
                    }
                ],
                "comparison": {
                    "model_favourite": "home",
                    "market_favourite": "home",
                    "biggest_edge_side": "home",
                    "biggest_edge_points": 7.0,
                    "agreement": True,
                    "summary": "xgGaffer is 7.0 percentage points higher on Arsenal than the market.",
                },
                "benchmark": {
                    "sample_size": 360,
                    "model_accuracy": 0.555,
                    "market_favourite_accuracy": None,
                    "model_brier_score": None,
                    "market_brier_score": None,
                    "evaluation_scope": "engine4_season_simulation_backtest",
                    "source_label": "engine4_backtest",
                },
                "support": {
                    "warning": "Use bookmaker comparisons responsibly.",
                    "resources": [
                        {
                            "label": "Ireland safer gambling support",
                            "region": "Ireland",
                            "support_type": "support",
                        }
                    ],
                },
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)