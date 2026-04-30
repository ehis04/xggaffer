from __future__ import annotations

import logging

from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery
from apps.predictions.services.source_policy import SOURCE_PRIORITY, source_coverage_metadata

_logger = logging.getLogger(__name__)

DEFAULT_LEAGUE = "EPL"
DEFAULT_SEASON = "2025"


class SimulationHandler(EngineHandler):
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        league = parsed_query.league or DEFAULT_LEAGUE
        try:
            from apps.predictions.models import SimulationResult

            season = parsed_query.season
            if season is None:
                latest = (
                    SimulationResult.objects.filter(league=league)
                    .order_by("-season", "-computed_at")
                    .first()
                )
                season = latest.season if latest is not None else DEFAULT_SEASON

            record = (
                SimulationResult.objects.filter(league=league, season=season)
                .order_by("-computed_at")
                .first()
            )

            if record is None:
                return QueryPayload(
                    intent=IntentClass.SEASON_SIMULATION,
                    engine_data={},
                    partial=True,
                    error=f"No simulation data for {league} {season}.",
                )

            return QueryPayload(
                intent=IntentClass.SEASON_SIMULATION,
                engine_data={
                    "league": league,
                    "season": season,
                    "freeze_date": record.freeze_date.isoformat(),
                    "n_simulations": record.n_simulations,
                    "table": record.results,
                    "source_coverage": source_coverage_metadata(
                        intent=IntentClass.SEASON_SIMULATION.value,
                        used_sources=SOURCE_PRIORITY,
                    ),
                },
                partial=False,
                error=None,
            )
        except Exception as exc:
            _logger.exception("SimulationHandler failed: %s", exc)
            return QueryPayload(
                intent=IntentClass.SEASON_SIMULATION,
                engine_data={},
                partial=True,
                error=str(exc),
            )