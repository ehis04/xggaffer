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

DEFAULT_SEASON = "2025"


class ScoreHandler(EngineHandler):
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        league = parsed_query.league or "EPL"
        season = parsed_query.season or DEFAULT_SEASON
        try:
            if parsed_query.season is None and MERGED_MATCHES_CSV.exists():
                season = latest_available_season(pd.read_csv(MERGED_MATCHES_CSV), default=DEFAULT_SEASON)

            from apps.predictions.ml.models.scoreline.predict import ScorePredictor
            from apps.predictions.ml.models.scoreline.score_feature_service import (
                get_score_feature_service,
            )

            service = get_score_feature_service()
            features_df = service.build_prediction_features(
                parsed_query.home_team,
                parsed_query.away_team,
                league,
                season,
            )
            predictor = ScorePredictor()
            result = predictor.predict(features_df)
            result["source_coverage"] = source_coverage_metadata(
                intent=IntentClass.SCORE_PREDICTION.value,
                used_sources=["understat", "sofascore", "whoscored"],
                required_sources=["understat", "sofascore", "whoscored", "football_data", "native_stats_api"],
            )
            return QueryPayload(
                intent=IntentClass.SCORE_PREDICTION,
                engine_data=result,
                partial=False,
                error=None,
            )
        except FileNotFoundError:
            return QueryPayload(
                intent=IntentClass.SCORE_PREDICTION,
                engine_data={},
                partial=True,
                error="Scoreline model not available.",
            )
        except ValueError as exc:
            return QueryPayload(
                intent=IntentClass.SCORE_PREDICTION,
                engine_data={},
                partial=True,
                error=str(exc),
            )
        except Exception as exc:
            _logger.exception("ScoreHandler failed: %s", exc)
            return QueryPayload(
                intent=IntentClass.SCORE_PREDICTION,
                engine_data={},
                partial=True,
                error=str(exc),
            )