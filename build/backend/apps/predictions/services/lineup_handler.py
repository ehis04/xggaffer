from __future__ import annotations

import logging

import pandas as pd

from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery
from apps.predictions.services.source_policy import (
    MERGED_MATCHES_CSV,
    latest_available_season,
    source_coverage_metadata,
)

_logger = logging.getLogger(__name__)

DEFAULT_LEAGUE = "EPL"
DEFAULT_SEASON = "2025"


def _serialise_team_result(team_result: dict) -> dict:
    return {
        "formation": team_result["formation"],
        "predicted_xi": team_result["predicted_xi"][
            ["player_id", "player_name", "position", "p_start"]
        ].to_dict(orient="records"),
        "all_probabilities": team_result["all_probabilities"][
            ["player_id", "player_name", "position", "p_start"]
        ].to_dict(orient="records"),
    }


class LineupHandler(EngineHandler):
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        home = parsed_query.home_team or parsed_query.team
        away = parsed_query.away_team
        league = parsed_query.league or DEFAULT_LEAGUE
        season = parsed_query.season or DEFAULT_SEASON
        try:
            if parsed_query.season is None and MERGED_MATCHES_CSV.exists():
                season = latest_available_season(pd.read_csv(MERGED_MATCHES_CSV), default=DEFAULT_SEASON)

            from apps.predictions.ml.models.lineup.feature_service import (
                get_latest_team_features,
            )
            from apps.predictions.ml.models.lineup.predict import predict_match_lineups

            if home is None:
                return QueryPayload(
                    intent=IntentClass.LINEUP_PREDICTION,
                    engine_data={},
                    partial=True,
                    error="No team specified for lineup prediction.",
                )

            home_df = get_latest_team_features(home, league, season)
            combined_df = home_df

            if away:
                try:
                    away_df = get_latest_team_features(away, league, season)
                    combined_df = pd.concat([home_df, away_df], ignore_index=True)
                except ValueError as exc:
                    _logger.warning("Away team features unavailable: %s", exc)

            raw = predict_match_lineups(combined_df)

            engine_data = {
                team_name: _serialise_team_result(team_result)
                for team_name, team_result in raw.items()
            }
            engine_data["source_coverage"] = source_coverage_metadata(
                intent=IntentClass.LINEUP_PREDICTION.value,
                used_sources=["understat", "sofascore", "whoscored"],
                required_sources=["understat", "sofascore", "whoscored", "football_data", "native_stats_api"],
            )

            return QueryPayload(
                intent=IntentClass.LINEUP_PREDICTION,
                engine_data=engine_data,
                partial=False,
                error=None,
            )
        except FileNotFoundError:
            return QueryPayload(
                intent=IntentClass.LINEUP_PREDICTION,
                engine_data={},
                partial=True,
                error="Lineup model not available.",
            )
        except ValueError as exc:
            return QueryPayload(
                intent=IntentClass.LINEUP_PREDICTION,
                engine_data={},
                partial=True,
                error=str(exc),
            )
        except Exception as exc:
            _logger.exception("LineupHandler failed: %s", exc)
            return QueryPayload(
                intent=IntentClass.LINEUP_PREDICTION,
                engine_data={},
                partial=True,
                error=str(exc),
            )