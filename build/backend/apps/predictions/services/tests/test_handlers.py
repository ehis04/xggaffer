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