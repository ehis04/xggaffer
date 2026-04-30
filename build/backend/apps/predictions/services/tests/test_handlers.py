from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from apps.predictions.services.base_handler import QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery
from apps.predictions.services.payload_builder import build_payload


def _make_query(**kwargs) -> ParsedQuery:
    defaults = dict(
        intent=IntentClass.MATCH_PREDICTION,
        home_team="Arsenal",
        away_team="Chelsea",
        team=None,
        player_name=None,
        league="EPL",
        season="2024",
        confidence=0.9,
        raw_query="test",
        error_code=None,
    )
    defaults.update(kwargs)
    return ParsedQuery(**defaults)


class TestMatchHandler:
    def test_success(self):
        from apps.predictions.services.match_handler import MatchHandler

        mock_result = {"prediction": "Home", "probabilities": {}, "top_factors": []}
        with patch(
            "apps.predictions.services.match_handler.MatchHandler.handle",
            return_value=QueryPayload(
                intent=IntentClass.MATCH_PREDICTION,
                engine_data=mock_result,
                partial=False,
                error=None,
            ),
        ):
            q = _make_query()
            result = MatchHandler().handle(q)
            assert result.intent == IntentClass.MATCH_PREDICTION
            assert result.partial is False

    def test_file_not_found(self):
        from apps.predictions.services.match_handler import MatchHandler

        with patch(
            "apps.predictions.ml.models.match_outcome.interpret.explain_match",
            side_effect=FileNotFoundError,
        ):
            q = _make_query()
            result = MatchHandler().handle(q)
            assert result.partial is True
            assert result.error is not None

    def test_value_error(self):
        from apps.predictions.services.match_handler import MatchHandler

        with patch(
            "apps.predictions.ml.models.match_outcome.interpret.explain_match",
            side_effect=ValueError("team not found"),
        ):
            q = _make_query()
            result = MatchHandler().handle(q)
            assert result.partial is True
            assert "team not found" in result.error


class TestEloHandler:
    def _make_history_df(self, team: str = "Arsenal") -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "home_team": team,
                    "away_team": "Chelsea",
                    "date": pd.Timestamp("2024-01-01"),
                    "home_elo_after": 1500.0,
                    "away_elo_after": 1450.0,
                }
            ]
        )

    def test_success(self):
        from apps.predictions.services.elo_handler import EloHandler

        history_df = self._make_history_df()
        with patch(
            "apps.predictions.services.elo_handler.EloHandler.handle",
            return_value=QueryPayload(
                intent=IntentClass.ELO_QUERY,
                engine_data={"team": "Arsenal", "elo_rating": 1500.0},
                partial=False,
                error=None,
            ),
        ):
            q = _make_query(intent=IntentClass.ELO_QUERY, home_team=None, away_team=None, team="Arsenal")
            result = EloHandler().handle(q)
            assert result.partial is False
            assert result.engine_data["elo_rating"] == 1500.0

    def test_team_not_found(self):
        from apps.predictions.services.elo_handler import EloHandler

        empty_df = pd.DataFrame(columns=["home_team", "away_team", "date", "home_elo_after", "away_elo_after"])
        with patch("apps.predictions.ml.engines.elo.load_elo_history", return_value=empty_df):
            q = _make_query(intent=IntentClass.ELO_QUERY, home_team=None, away_team=None, team="UnknownFC")
            result = EloHandler().handle(q)
            assert result.partial is True


class TestGlossaryHandler:
    def test_known_term(self):
        from apps.predictions.services.glossary_handler import GlossaryHandler

        q = _make_query(
            intent=IntentClass.GLOSSARY,
            home_team=None,
            away_team=None,
            raw_query="what is xG",
        )
        result = GlossaryHandler().handle(q)
        assert result.partial is False
        assert result.engine_data["term"] == "xg"

    def test_unknown_term(self):
        from apps.predictions.services.glossary_handler import GlossaryHandler

        q = _make_query(
            intent=IntentClass.GLOSSARY,
            home_team=None,
            away_team=None,
            raw_query="what is zylofon",
        )
        result = GlossaryHandler().handle(q)
        assert result.partial is True


class TestUnknownHandler:
    def test_returns_capabilities(self):
        from apps.predictions.services.unknown_handler import UnknownHandler

        q = _make_query(intent=IntentClass.UNKNOWN, home_team=None, away_team=None)
        result = UnknownHandler().handle(q)
        assert result.partial is False
        assert "capabilities" in result.engine_data


class TestPayloadBuilder:
    def test_schema_match_prediction(self):
        pq = _make_query()
        qp = QueryPayload(
            intent=IntentClass.MATCH_PREDICTION,
            engine_data={"prediction": "Home"},
            partial=False,
            error=None,
        )
        payload = build_payload(pq, qp)
        assert set(payload.keys()) == {"intent", "entities", "engine_data", "partial", "error", "timestamp"}
        assert "capabilities" not in payload

    def test_schema_unknown(self):
        pq = _make_query(intent=IntentClass.UNKNOWN, home_team=None, away_team=None, error_code=None)
        qp = QueryPayload(intent=IntentClass.UNKNOWN, engine_data={}, partial=False, error=None)
        payload = build_payload(pq, qp)
        assert "capabilities" in payload

    def test_timestamp_format(self):
        pq = _make_query()
        qp = QueryPayload(intent=IntentClass.MATCH_PREDICTION, engine_data={}, partial=False, error=None)
        payload = build_payload(pq, qp)
        assert payload["timestamp"].endswith("Z")


class TestCompositeHandler:
    def test_sub_handler_exception_does_not_propagate(self):
        from apps.predictions.services.composite_handler import CompositeHandler
        from apps.predictions.services.match_handler import MatchHandler

        with patch.object(MatchHandler, "handle", side_effect=Exception("engine down")):
            q = _make_query(intent=IntentClass.COMPOSITE_MATCH)
            result = CompositeHandler().handle(q)
            assert result.partial is True
            assert "match_error" in result.engine_data

class TestOddsHandler:
    def test_success(self):
        from apps.predictions.services.odds_handler import OddsHandler

        with patch(
            "apps.predictions.services.odds_handler.OddsComparisonService.__init__",
            return_value=None,
        ), patch(
            "apps.predictions.services.odds_handler.OddsComparisonService.get_fixture_odds_comparison",
            return_value=self._mock_odds_payload(),
        ), patch(
            "apps.predictions.services.odds_handler.build_match_prediction_payload",
            return_value=self._mock_prediction_payload(),
        ), patch(
            "apps.predictions.services.odds_handler.HistoricalMarketBenchmark.objects.filter",
        ) as mock_filter:
            mock_filter.return_value.order_by.return_value.first.return_value = None

            q = _make_query(
                intent=IntentClass.ODDS_COMPARISON,
                raw_query="compare Arsenal vs Chelsea with bookmaker odds",
            )
            result = OddsHandler().handle(q)

        assert result.intent == IntentClass.ODDS_COMPARISON
        assert result.partial is False
        assert result.error is None
        assert result.engine_data["home_team"] == "Arsenal"
        assert result.engine_data["away_team"] == "Chelsea"
        assert "model" in result.engine_data
        assert "market" in result.engine_data
        assert "bookmakers" in result.engine_data
        assert "comparison" in result.engine_data
        assert "support" in result.engine_data

    def test_missing_odds_data_returns_partial_response(self):
        from apps.predictions.services.odds.exceptions import OddsDataUnavailableError
        from apps.predictions.services.odds_handler import OddsHandler

        with patch(
            "apps.predictions.services.odds_handler.OddsComparisonService.__init__",
            return_value=None,
        ), patch(
            "apps.predictions.services.odds_handler.OddsComparisonService.get_fixture_odds_comparison",
            side_effect=OddsDataUnavailableError("No live odds are available."),
        ):
            q = _make_query(
                intent=IntentClass.ODDS_COMPARISON,
                raw_query="compare Arsenal vs Chelsea with bookmaker odds",
            )
            result = OddsHandler().handle(q)

        assert result.intent == IntentClass.ODDS_COMPARISON
        assert result.partial is True
        assert "No live odds are available" in result.error
        assert "support" in result.engine_data

    def test_source_failure_returns_partial_response(self):
        from apps.predictions.services.odds.exceptions import OddsSourceError
        from apps.predictions.services.odds_handler import OddsHandler

        with patch(
            "apps.predictions.services.odds_handler.OddsComparisonService.__init__",
            return_value=None,
        ), patch(
            "apps.predictions.services.odds_handler.OddsComparisonService.get_fixture_odds_comparison",
            side_effect=OddsSourceError("source failed"),
        ):
            q = _make_query(
                intent=IntentClass.ODDS_COMPARISON,
                raw_query="compare Arsenal vs Chelsea with bookmaker odds",
            )
            result = OddsHandler().handle(q)

        assert result.intent == IntentClass.ODDS_COMPARISON
        assert result.partial is True
        assert result.error == "Live odds data is temporarily unavailable."
        assert "support" in result.engine_data

    def test_support_block_is_present_in_happy_path(self):
        from apps.predictions.services.odds_handler import OddsHandler

        with patch(
            "apps.predictions.services.odds_handler.OddsComparisonService.__init__",
            return_value=None,
        ), patch(
            "apps.predictions.services.odds_handler.OddsComparisonService.get_fixture_odds_comparison",
            return_value=self._mock_odds_payload(),
        ), patch(
            "apps.predictions.services.odds_handler.build_match_prediction_payload",
            return_value=self._mock_prediction_payload(),
        ), patch(
            "apps.predictions.services.odds_handler.HistoricalMarketBenchmark.objects.filter",
        ) as mock_filter:
            mock_filter.return_value.order_by.return_value.first.return_value = None

            q = _make_query(
                intent=IntentClass.ODDS_COMPARISON,
                raw_query="compare Arsenal vs Chelsea with bookmaker odds",
            )
            result = OddsHandler().handle(q)

        assert result.partial is False
        assert "support" in result.engine_data
        assert result.engine_data["support"]["resources"]

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


class TestTacticalHandler:
    def test_model_load_failure_returns_profile_fallback(self):
        from apps.predictions.services.tactical_handler import TacticalHandler

        q = _make_query(
            intent=IntentClass.TACTICAL_QUERY,
            home_team=None,
            away_team=None,
            team="Real Madrid",
            season="2025",
            raw_query="What tactical style does Real Madrid use?",
        )

        fallback_payload = {
            "query_type": "single",
            "team": "Real Madrid",
            "requested_season": "2025",
            "profile_season": "2023-24",
            "season_name": "2023-24",
            "competition_name": "La Liga",
            "n_matches_in_profile": 38,
            "cluster_label": "elite_final_third_possession",
            "style_label": "elite_final_third_possession",
            "overall_completion_rate": 0.88,
            "overall_forward_ratio": 0.60,
            "overall_pass_length": 18.7,
            "dominant_zones": [15, 10, 12, 19, 11],
        }

        with patch(
            "apps.predictions.ml.models.tactical.predict.TacticalAnalyser",
            side_effect=ModuleNotFoundError("No module named 'xgboost'"),
        ), patch(
            "apps.predictions.services.tactical_handler._fallback_single_profile",
            return_value=fallback_payload,
        ):
            result = TacticalHandler().handle(q)

        assert result.intent == IntentClass.TACTICAL_QUERY
        assert result.partial is False
        assert result.error is None
        assert result.engine_data["cluster_label"] == "elite_final_third_possession"
        assert result.engine_data["fallback_policy"]
        assert result.engine_data["source_coverage"]["intent"] == IntentClass.TACTICAL_QUERY.value

    def test_live_unavailable_falls_back_to_stored_snapshot(self):
        from apps.predictions.services.odds.exceptions import OddsDataUnavailableError
        from apps.predictions.services.odds_handler import OddsHandler

        stored_fixture = {
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
            "snapshot_id": 99,
            "fetched_at": "2026-04-18T10:10:00Z",
            "bookmaker_quotes": self._mock_odds_payload()["fixtures"][0]["bookmaker_quotes"],
            "consensus": self._mock_odds_payload()["fixtures"][0]["consensus"],
            "is_historical": True,
        }

        with patch(
            "apps.predictions.services.odds_handler.OddsComparisonService.__init__",
            return_value=None,
        ), patch(
            "apps.predictions.services.odds_handler.OddsComparisonService.get_fixture_odds_comparison",
            side_effect=OddsDataUnavailableError("No live odds are available."),
        ), patch(
            "apps.predictions.services.odds_handler.OddsComparisonService.get_stored_fixture_odds",
            return_value=stored_fixture,
        ), patch(
            "apps.predictions.services.odds_handler.build_match_prediction_payload",
            return_value=self._mock_prediction_payload(),
        ), patch(
            "apps.predictions.services.odds_handler.HistoricalMarketBenchmark.objects.filter",
        ) as mock_filter:
            mock_filter.return_value.order_by.return_value.first.return_value = None

            q = _make_query(
                intent=IntentClass.ODDS_COMPARISON,
                raw_query="compare Arsenal vs Chelsea with bookmaker odds",
            )
            result = OddsHandler().handle(q)

        assert result.partial is False
        assert result.engine_data["is_historical"] is True
        assert result.engine_data["odds_fetched_at"] == "2026-04-18T10:10:00Z"
        assert "support" in result.engine_data

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
            "fixtures": [
                {
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                    "commence_time": "2026-04-20T15:00:00Z",
                    "bookmaker_quotes": [
                        {
                            "bookmaker_name": "Book A",
                            "home_odds": 2.10,
                            "draw_odds": 3.40,
                            "away_odds": 3.60,
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
                            "bookmaker_name": "Book B",
                            "home_odds": 2.20,
                            "draw_odds": 3.30,
                            "away_odds": 3.50,
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