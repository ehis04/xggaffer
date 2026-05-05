from __future__ import annotations

from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery

CAPABILITIES_SUMMARY: dict = {
    "match_prediction": {
        "description": "Predict who wins a match",
        "example": "Who wins Arsenal vs Chelsea?",
    },
    "score_prediction": {
        "description": "Predict the expected scoreline",
        "example": "What score will Arsenal vs Chelsea be?",
    },
    "season_simulation": {
        "description": "See title race, top 4, and relegation probabilities",
        "example": "Who wins the Premier League this season?",
    },
    "elo_query": {
        "description": "Check team strength ratings",
        "example": "What is Arsenal's Elo rating?",
    },
    "availability_query": {
        "description": "Check player injury risk and availability",
        "example": "Is Saka fit for Arsenal?",
    },
    "lineup_prediction": {
        "description": "Predict which players start",
        "example": "What lineup will Arsenal use?",
    },
    "tactical_query": {
        "description": "Analyse team style and compare tactical profiles",
        "example": "How does Arsenal play?",
    },
    "stat_comparison": {
        "description": "Compare xG, pressing, and other stats between teams",
        "example": "Compare Arsenal and Chelsea xG",
    },
    "glossary": {
        "description": "Explain football analytics terms",
        "example": "What is xG?",
    },
    "supported_leagues": ["EPL", "La_Liga", "Bundesliga", "Serie_A", "Ligue_1"],
    "supported_seasons": "2014-2025/26",
}


class UnknownHandler(EngineHandler):
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        return QueryPayload(
            intent=IntentClass.UNKNOWN,
            engine_data={
                "error_code": parsed_query.error_code,
                "capabilities": CAPABILITIES_SUMMARY,
            },
            partial=False,
            error=None,
        )
