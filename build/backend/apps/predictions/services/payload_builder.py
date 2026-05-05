from __future__ import annotations

import datetime

from apps.predictions.services.base_handler import QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery
from apps.predictions.services.unknown_handler import CAPABILITIES_SUMMARY


def build_payload(parsed_query: ParsedQuery, handler_result: QueryPayload) -> dict:
    engine_data = handler_result.engine_data
    if parsed_query.intent == IntentClass.ODDS_COMPARISON and isinstance(engine_data, dict):
        engine_data = {**engine_data}
        engine_data.setdefault("benchmark", None)

    payload = {
        "intent": parsed_query.intent.value,
        "entities": {
            "home_team": parsed_query.home_team,
            "away_team": parsed_query.away_team,
            "team": parsed_query.team,
            "player_name": parsed_query.player_name,
            "league": parsed_query.league,
            "season": parsed_query.season,
        },
        "engine_data": engine_data,
        "partial": handler_result.partial,
        "error": handler_result.error,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }
    if parsed_query.intent == IntentClass.UNKNOWN:
        payload["capabilities"] = CAPABILITIES_SUMMARY
    return payload
