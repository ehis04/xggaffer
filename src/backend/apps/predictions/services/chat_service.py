from __future__ import annotations

import logging
from time import perf_counter

from apps.predictions.data_paths import PROCESSED_DATA_ROOT
from apps.predictions.services.availability_handler import AvailabilityHandler
from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.composite_handler import CompositeHandler
from apps.predictions.services.elo_handler import EloHandler
from apps.predictions.services.glossary_handler import GlossaryHandler
from apps.predictions.services.intent_types import IntentClass, ParsedQuery
from apps.predictions.services.lineup_handler import LineupHandler
from apps.predictions.services.match_handler import MatchHandler
from apps.predictions.services.narrator import LLMNarrator
from apps.predictions.services import payload_builder
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
from apps.predictions.services.odds_handler import OddsHandler

_logger = logging.getLogger(__name__)

_CHAT_CACHE_DATA_FILES = (
    PROCESSED_DATA_ROOT / "matches" / "merged" / "all_leagues_all_seasons_matches_merged.csv",
    PROCESSED_DATA_ROOT / "teams" / "merged" / "all_leagues_all_seasons_teams_merged.csv",
    PROCESSED_DATA_ROOT / "players" / "merged" / "all_leagues_all_seasons_players_merged.csv",
    PROCESSED_DATA_ROOT / "team_season_zone_profiles.csv",
    PROCESSED_DATA_ROOT / "team_match_clusters.csv",
)

_CHAT_CACHE_SCHEMA_VERSION = "2026-04-28-tactical-season-default-v4"


def _chat_data_version() -> str:
    latest_mtime = 0
    for data_file in _CHAT_CACHE_DATA_FILES:
        try:
            mtime = int(data_file.stat().st_mtime)
        except OSError:
            continue
        if mtime > latest_mtime:
            latest_mtime = mtime
    return str(latest_mtime)

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
    IntentClass.ODDS_COMPARISON:    OddsHandler,
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

def handle_chat_query(
    raw_query: str,
    image_b64: str | None = None,
    image_media_type: str | None = None,
) -> dict:
    from django.conf import settings
    from django.core.cache import cache
    from common.cache_keys import make_query_cache_key, CACHE_TTL_CHAT

    _perf_enabled = getattr(settings, "ENABLE_PERFORMANCE_LOGGING", False)
    _perf_logger = logging.getLogger("xggaffer.performance")

    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
    cache_key = make_query_cache_key(
        f"{raw_query}|data_version={_chat_data_version()}|schema_version={_CHAT_CACHE_SCHEMA_VERSION}"
    )

    # Serve cached text-only responses first to avoid rerunning routing,
    # handlers, payload building, and narration for repeated queries.
    if api_key and not image_b64:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    t0 = perf_counter()

    try:
        parsed_query = QueryRouter().route(raw_query)
    except Exception as exc:
        _logger.exception("QueryRouter failed: %s", exc)
        return FALLBACK_RESPONSE

    t1 = perf_counter()

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

    t2 = perf_counter()

    try:
        payload = payload_builder.build_payload(parsed_query, handler_result)
    except Exception as exc:
        _logger.exception("PayloadBuilder failed: %s", exc)
        return FALLBACK_RESPONSE

    t3 = perf_counter()

    try:
        narrator = LLMNarrator()
        prose, used_fallback = narrator.narrate(
            payload,
            raw_query,
            image_b64=image_b64,
            image_media_type=image_media_type,
        )
    except Exception as exc:
        _logger.exception("Narrator failed unexpectedly: %s", exc)
        prose = FALLBACK_RESPONSE["prose"]
        used_fallback = True

    t4 = perf_counter()

    if _perf_enabled:
        _perf_logger.info({
            "event": "chat_timing",
            "routing_ms": round((t1 - t0) * 1000, 2),
            "handler_ms": round((t2 - t1) * 1000, 2),
            "payload_ms": round((t3 - t2) * 1000, 2),
            "narrator_ms": round((t4 - t3) * 1000, 2),
            "total_ms": round((t4 - t0) * 1000, 2),
        })

    result = {
        "prose": prose,
        "structured_data": payload,
        "intent": parsed_query.intent.value,
        "entities": {
            "home_team": getattr(parsed_query, "home_team", None),
            "away_team": getattr(parsed_query, "away_team", None),
            "team": getattr(parsed_query, "team", None),
            "player_name": getattr(parsed_query, "player_name", None),
            "league": getattr(parsed_query, "league", None),
            "season": getattr(parsed_query, "season", None),
        },
        "used_fallback": used_fallback,
        "query_type": parsed_query.intent.value,
    }

    if api_key and not image_b64 and not used_fallback:
        cache.set(cache_key, result, timeout=CACHE_TTL_CHAT)

    return result
