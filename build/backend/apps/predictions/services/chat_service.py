from __future__ import annotations

import logging

from apps.predictions.services.availability_handler import AvailabilityHandler
from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.composite_handler import CompositeHandler
from apps.predictions.services.elo_handler import EloHandler
from apps.predictions.services.glossary_handler import GlossaryHandler
from apps.predictions.services.intent_types import IntentClass, ParsedQuery
from apps.predictions.services.lineup_handler import LineupHandler
from apps.predictions.services.match_handler import MatchHandler
from apps.predictions.services.narrator import LLMNarrator
from apps.predictions.services.payload_builder import build_payload
from apps.predictions.services.query_router import QueryRouter
from apps.predictions.services.score_handler import ScoreHandler
from apps.predictions.services.simulation_handler import SimulationHandler
from apps.predictions.services.stat_handler import StatHandler
from apps.predictions.services.tactical_handler import TacticalHandler
from apps.predictions.services.form_handler import FormHandler
from apps.predictions.services.h2h_handler import H2HHandler
from apps.predictions.services.player_handler import PlayerHandler
from apps.predictions.services.rankings_handler import RankingsHandler
from apps.predictions.services.rest_handler import RestHandler
from apps.predictions.services.unknown_handler import UnknownHandler

_logger = logging.getLogger(__name__)

HANDLER_MAP: dict[IntentClass, type[EngineHandler]] = {
    IntentClass.MATCH_PREDICTION:   MatchHandler,
    IntentClass.SCORE_PREDICTION:   ScoreHandler,
    IntentClass.SEASON_SIMULATION:  SimulationHandler,
    IntentClass.ELO_QUERY:          EloHandler,
    IntentClass.AVAILABILITY_QUERY: AvailabilityHandler,
    IntentClass.LINEUP_PREDICTION:  LineupHandler,
    IntentClass.TACTICAL_QUERY:     TacticalHandler,
    IntentClass.COMPOSITE_MATCH:    CompositeHandler,
    IntentClass.STAT_COMPARISON:    StatHandler,
    IntentClass.FORM_ANALYSIS:      FormHandler,
    IntentClass.HEAD_TO_HEAD:       H2HHandler,
    IntentClass.PLAYER_STATS:       PlayerHandler,
    IntentClass.TEAM_RANKINGS:      RankingsHandler,
    IntentClass.REST_DAYS:          RestHandler,
    IntentClass.GLOSSARY:           GlossaryHandler,
    IntentClass.UNKNOWN:            UnknownHandler,
}

FALLBACK_RESPONSE = {
    "prose": "xgGaffer encountered an error processing your query. Please try again.",
    "structured_data": {},
    "intent": IntentClass.UNKNOWN.value,
    "entities": {},
    "used_fallback": True,
    "query_type": IntentClass.UNKNOWN.value,
}


def handle_chat_query(raw_query: str) -> dict:
    try:
        parsed_query = QueryRouter().route(raw_query)
    except Exception as exc:
        _logger.exception("QueryRouter failed: %s", exc)
        return FALLBACK_RESPONSE

    try:
        handler_cls = HANDLER_MAP[parsed_query.intent]
        handler_result = handler_cls().handle(parsed_query)
    except Exception as exc:
        _logger.exception("Handler dispatch failed: %s", exc)
        handler_result = QueryPayload(
            intent=parsed_query.intent,
            engine_data={},
            partial=True,
            error=str(exc),
        )

    try:
        payload = build_payload(parsed_query, handler_result)
    except Exception as exc:
        _logger.exception("PayloadBuilder failed: %s", exc)
        return FALLBACK_RESPONSE

    try:
        narrator = LLMNarrator()
        prose, used_fallback = narrator.narrate(payload, raw_query)
    except Exception as exc:
        _logger.exception("Narrator failed unexpectedly: %s", exc)
        prose = FALLBACK_RESPONSE["prose"]
        used_fallback = True

    return {
        "prose": prose,
        "structured_data": payload,
        "intent": parsed_query.intent.value,
        "entities": {
            "home_team": parsed_query.home_team,
            "away_team": parsed_query.away_team,
            "team": parsed_query.team,
            "player_name": parsed_query.player_name,
            "league": parsed_query.league,
            "season": parsed_query.season,
        },
        "used_fallback": used_fallback,
        "query_type": parsed_query.intent.value,
    }