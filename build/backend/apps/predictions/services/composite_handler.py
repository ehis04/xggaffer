from __future__ import annotations

import logging

from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery

_logger = logging.getLogger(__name__)


class CompositeHandler(EngineHandler):
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        from apps.predictions.services.match_handler import MatchHandler
        from apps.predictions.services.elo_handler import EloHandler
        from apps.predictions.services.availability_handler import AvailabilityHandler
        from apps.predictions.services.lineup_handler import LineupHandler

        results: dict = {}
        any_partial = False

        for key, handler_cls in [
            ("match", MatchHandler),
            ("elo", EloHandler),
            ("availability", AvailabilityHandler),
            ("lineup", LineupHandler),
        ]:
            try:
                r = handler_cls().handle(parsed_query)
                results[key] = r.engine_data
                if r.partial:
                    results[f"{key}_error"] = r.error
                    any_partial = True
            except Exception as exc:
                _logger.exception("CompositeHandler sub-handler %s failed: %s", key, exc)
                results[key] = {}
                results[f"{key}_error"] = str(exc)
                any_partial = True

        return QueryPayload(
            intent=IntentClass.COMPOSITE_MATCH,
            engine_data=results,
            partial=any_partial,
            error=None,
        )