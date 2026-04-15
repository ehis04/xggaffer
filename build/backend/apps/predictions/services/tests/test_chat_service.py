from __future__ import annotations

from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.predictions.services.chat_service import FALLBACK_RESPONSE, HANDLER_MAP
from apps.predictions.services.intent_types import IntentClass
from apps.predictions.services.narrator import LLMNarrator


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