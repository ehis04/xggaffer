from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch
import datetime

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.predictions.services.chat_service import FALLBACK_RESPONSE, HANDLER_MAP
from apps.predictions.services.intent_types import IntentClass
from apps.predictions.services.narrator import LLMNarrator
from apps.predictions.services.base_handler import QueryPayload
from apps.predictions.services.simulation_handler import SimulationHandler

@pytest.fixture
def client():
    return APIClient()


GLOSSARY_PAYLOAD = {
    "intent": "GLOSSARY",
    "entities": {
        "home_team": None,
        "away_team": None,
        "team": None,
        "player_name": None,
        "league": None,
        "season": None,
    },
    "engine_data": {"term": "xg", "definition": "Expected Goals."},
    "partial": False,
    "error": None,
    "timestamp": "2026-04-12T00:00:00Z",
}


class TestHandleChatQuery:
    def test_glossary_returns_dict(self):
        from apps.predictions.services.chat_service import handle_chat_query

        result = handle_chat_query("what is xG")
        assert isinstance(result, dict)
        assert "prose" in result
        assert "structured_data" in result
        assert "intent" in result
        assert "entities" in result
        assert "used_fallback" in result
        assert "query_type" in result
        assert result["intent"] == "GLOSSARY"

    def test_match_intent_entities(self):
        from apps.predictions.services.chat_service import handle_chat_query

        result = handle_chat_query("who wins Arsenal vs Chelsea")
        assert result["intent"] == "MATCH_PREDICTION"
        assert result["entities"]["home_team"] == "Arsenal"
        assert result["entities"]["away_team"] == "Chelsea"

    def test_unknown_intent(self):
        from apps.predictions.services.chat_service import handle_chat_query

        result = handle_chat_query("asdfgh xyz random gibberish 12345")
        assert result["intent"] == "UNKNOWN"
        assert isinstance(result["prose"], str)
        assert len(result["prose"]) > 0

    def test_never_raises_on_router_failure(self):
        from apps.predictions.services.chat_service import handle_chat_query
        from apps.predictions.services.query_router import QueryRouter

        with patch.object(QueryRouter, "route", side_effect=RuntimeError("boom")):
            result = handle_chat_query("any query")
        assert isinstance(result, dict)
        assert "prose" in result

    def test_narrator_failure_uses_fallback(self):
        from apps.predictions.services.chat_service import handle_chat_query

        with patch.object(LLMNarrator, "narrate", side_effect=Exception("API down")):
            result = handle_chat_query("what is xG")
        assert result["used_fallback"] is True

    def test_handler_map_covers_all_intents(self):
        for intent in IntentClass:
            assert intent in HANDLER_MAP, f"Missing handler for {intent}"

    def test_odds_query_dispatches_through_handler_map(self):
        from apps.predictions.services.chat_service import handle_chat_query

        with patch(
            "apps.predictions.services.odds_handler.OddsHandler.handle",
            return_value=QueryPayload(
                intent=IntentClass.ODDS_COMPARISON,
                engine_data={
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                    "market": {"favourite": "home"},
                    "support": {
                        "warning": "Use market comparisons responsibly.",
                        "resources": [
                            {
                                "label": "Ireland safer gambling support",
                                "region": "Ireland",
                                "support_type": "support",
                            }
                        ],
                    },
                },
                partial=False,
                error=None,
            ),
        ), patch.object(LLMNarrator, "narrate", return_value=("odds prose", False)):
            result = handle_chat_query("compare Arsenal vs Chelsea with bookmaker odds")

        assert result["intent"] == "ODDS_COMPARISON"
        assert result["query_type"] == "ODDS_COMPARISON"
        assert "engine_data" in result["structured_data"]
        assert result["structured_data"]["engine_data"]["support"]["resources"]
        assert "benchmark" in result["structured_data"]["engine_data"]
        assert result["structured_data"]["engine_data"]["support"]["warning"]

    def test_odds_handler_failure_still_returns_safe_payload(self):
        from apps.predictions.services.chat_service import handle_chat_query

        with patch(
            "apps.predictions.services.odds_handler.OddsHandler.handle",
            side_effect=Exception("odds handler down"),
        ), patch.object(LLMNarrator, "narrate", return_value=("fallback prose", True)):
            result = handle_chat_query("compare Arsenal vs Chelsea with bookmaker odds")

        assert result["intent"] == "ODDS_COMPARISON"
        assert result["query_type"] == "ODDS_COMPARISON"
        assert result["used_fallback"] is True
        assert result["structured_data"]["partial"] is True
        assert result["structured_data"]["error"] == "odds handler down"


class TestSimulationHandler:
    def test_uses_latest_freeze_date_not_latest_computed_snapshot(self):
        class QuerySetStub:
            def __init__(self, record):
                self.record = record
                self.order_fields = None

            def order_by(self, *fields):
                self.order_fields = fields
                return self

            def first(self):
                return self.record

        selected_record = SimpleNamespace(
            season="2025",
            freeze_date=datetime.date(2026, 5, 5),
            results=[{"team": "Live Projection"}],
            n_simulations=5000,
        )
        queryset = QuerySetStub(selected_record)

        parsed_query = type(
            "ParsedQueryStub",
            (),
            {"league": "EPL", "season": "2025"},
        )()

        with patch("apps.predictions.models.SimulationResult") as simulation_result:
            simulation_result.objects.filter.return_value = queryset
            payload = SimulationHandler().handle(parsed_query)

        assert payload.partial is False
        assert payload.engine_data["freeze_date"] == "2026-05-05"
        assert payload.engine_data["table"] == [{"team": "Live Projection"}]
        assert queryset.order_fields == ("-freeze_date", "-computed_at")


class TestNarrator:
    def test_fallback_no_api_key(self):
        with override_settings(ANTHROPIC_API_KEY=""):
            narrator = LLMNarrator()
            prose, used_fallback = narrator.narrate(GLOSSARY_PAYLOAD, "test query")
        assert used_fallback is True
        assert isinstance(prose, str)
        assert len(prose) > 0

    def test_fallback_match_prediction_format(self):
        with override_settings(ANTHROPIC_API_KEY=""):
            narrator = LLMNarrator()
        payload = {
            "intent": "MATCH_PREDICTION",
            "entities": {"home_team": "Arsenal", "away_team": "Chelsea"},
            "engine_data": {
                "prediction": "Home",
                "probabilities": {"home": 0.61, "draw": 0.23, "away": 0.16},
            },
            "partial": False,
            "error": None,
        }
        result = narrator._fallback_response(payload)
        assert "Prediction" in result
        assert "%" in result

    def test_fallback_omits_source_coverage(self):
        with override_settings(ANTHROPIC_API_KEY=""):
            narrator = LLMNarrator()

        payload = {
            "intent": "FORM_ANALYSIS",
            "entities": {"team": "Arsenal", "home_team": "Arsenal"},
            "engine_data": {
                "recent_form": "WWDWL",
                "wins": 20,
                "draws": 6,
                "losses": 4,
                "avg_xg": 1.9,
                "source_coverage": {
                    "used_sources": ["sofascore", "understat"],
                    "missing_sources": ["whoscored"],
                },
            },
            "partial": False,
            "error": None,
        }

        result = narrator._fallback_response(payload)
        assert "Data sources used" not in result
        assert "Missing for this query" not in result

    def test_fallback_tactical_mentions_profile_season_when_different(self):
        with override_settings(ANTHROPIC_API_KEY=""):
            narrator = LLMNarrator()

        payload = {
            "intent": "TACTICAL_QUERY",
            "entities": {"team": "Real Madrid", "home_team": "Real Madrid"},
            "engine_data": {
                "cluster_label": "High Press 4-3-3",
                "requested_season": "2025",
                "profile_season": "2023/2024",
            },
            "partial": False,
            "error": None,
        }

        result = narrator._fallback_response(payload)
        assert "Requested season was 2025" in result
        assert "2023/2024" in result


@pytest.mark.django_db
class TestChatView:
    def test_valid_query_200(self, client):
        response = client.post(
            "/api/predictions/chat/",
            {"query": "what is xG"},
            format="json",
        )
        assert response.status_code == 200
        assert "prose" in response.data

    def test_empty_query_400(self, client):
        response = client.post(
            "/api/predictions/chat/",
            {"query": ""},
            format="json",
        )
        assert response.status_code == 400

    def test_missing_query_400(self, client):
        response = client.post(
            "/api/predictions/chat/",
            {},
            format="json",
        )
        assert response.status_code == 400

    def test_handle_chat_query_exception_500(self, client):
        with patch(
            "apps.predictions.services.chat_service.handle_chat_query",
            side_effect=Exception("crash"),
        ):
            response = client.post(
                "/api/predictions/chat/",
                {"query": "test"},
                format="json",
            )
        assert response.status_code == 500
        assert "error" in response.data
