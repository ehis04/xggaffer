from __future__ import annotations

import logging

from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery

_logger = logging.getLogger(__name__)


class TacticalHandler(EngineHandler):
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        try:
            from apps.predictions.ml.models.tactical.predict import TacticalAnalyser

            analyser = TacticalAnalyser()

            if parsed_query.home_team and parsed_query.away_team:
                result = analyser.compare_teams(
                    parsed_query.home_team, parsed_query.away_team
                )
                if result is None:
                    return QueryPayload(
                        intent=IntentClass.TACTICAL_QUERY,
                        engine_data={},
                        partial=True,
                        error=f"No tactical profile found for one or both teams: "
                              f"{parsed_query.home_team}, {parsed_query.away_team}.",
                    )
                engine_data = {
                    "query_type": "comparison",
                    "home_team": parsed_query.home_team,
                    "away_team": parsed_query.away_team,
                    **result,
                }
            else:
                team = parsed_query.team or parsed_query.home_team
                if team is None:
                    return QueryPayload(
                        intent=IntentClass.TACTICAL_QUERY,
                        engine_data={},
                        partial=True,
                        error="No team specified for tactical query.",
                    )
                result = analyser.analyse_team(team)
                if result is None:
                    return QueryPayload(
                        intent=IntentClass.TACTICAL_QUERY,
                        engine_data={},
                        partial=True,
                        error=f"No tactical profile found for '{team}'.",
                    )
                engine_data = {
                    "query_type": "single",
                    "team": team,
                    **result,
                }

            return QueryPayload(
                intent=IntentClass.TACTICAL_QUERY,
                engine_data=engine_data,
                partial=False,
                error=None,
            )
        except FileNotFoundError:
            return QueryPayload(
                intent=IntentClass.TACTICAL_QUERY,
                engine_data={},
                partial=True,
                error="Tactical model not available.",
            )
        except ValueError as exc:
            return QueryPayload(
                intent=IntentClass.TACTICAL_QUERY,
                engine_data={},
                partial=True,
                error=str(exc),
            )
        except Exception as exc:
            _logger.exception("TacticalHandler failed: %s", exc)
            return QueryPayload(
                intent=IntentClass.TACTICAL_QUERY,
                engine_data={},
                partial=True,
                error=str(exc),
            )