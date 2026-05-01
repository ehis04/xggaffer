from __future__ import annotations

from rest_framework.request import Request

from apps.predictions.ml.models.match_outcome.config import DEMO_SEASON
from apps.predictions.utils.widget_freshness import get_engine_widget_freshness
from apps.predictions.views.widget_base import WidgetBaseView

SCORELINE_MATRIX_MAX_GOALS = 5
OVER_UNDER_THRESHOLD = 2.5
DEFAULT_LEAGUE = "EPL"
DEFAULT_SEASON = DEMO_SEASON


def get_score_feature_service():
    from apps.predictions.ml.models.scoreline.score_feature_service import (
        get_score_feature_service as _real,
    )
    return _real()


class ScorePredictor:
    def __new__(cls, *args, **kwargs):
        from apps.predictions.ml.models.scoreline.predict import ScorePredictor as _real
        return _real(*args, **kwargs)


def _top_3_scorelines(matrix: list[list[float]]) -> list[dict]:
    cells = []
    for home_goals, row in enumerate(matrix):
        for away_goals, prob in enumerate(row):
            cells.append({
                "scoreline": f"{home_goals}-{away_goals}",
                "prob": prob,
            })
    cells.sort(key=lambda c: c["prob"], reverse=True)
    return cells[:3]


def _over_under_probs(matrix: list[list[float]]) -> dict:
    over = 0.0
    for home_goals, row in enumerate(matrix):
        for away_goals, prob in enumerate(row):
            if home_goals + away_goals > OVER_UNDER_THRESHOLD:
                over += prob
    return {"over_2_5": round(over, 4), "under_2_5": round(1.0 - over, 4)}


def _btts_prob(matrix: list[list[float]]) -> float:
    btts = 0.0
    for home_goals, row in enumerate(matrix):
        for away_goals, prob in enumerate(row):
            if home_goals > 0 and away_goals > 0:
                btts += prob
    return round(btts, 4)


class ScorelineWidgetView(WidgetBaseView):
    widget_intent = "scoreline"

    def get_widget_data(self, request: Request) -> dict:
        home_team = request.query_params.get("home_team", "").strip()
        away_team = request.query_params.get("away_team", "").strip()

        league = request.query_params.get("league", DEFAULT_LEAGUE).strip() or DEFAULT_LEAGUE
        season = request.query_params.get("season", DEFAULT_SEASON).strip() or DEFAULT_SEASON

        if not home_team or not away_team:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("home_team and away_team are required.")

        service = get_score_feature_service()
        features_df = service.build_prediction_features(
            home_team, away_team, league, season
        )
        predictor = ScorePredictor()
        result = predictor.predict(features_df)

        full_matrix: list[list[float]] = result["scoreline_matrix"]
        max_idx = SCORELINE_MATRIX_MAX_GOALS + 1
        matrix = [row[:max_idx] for row in full_matrix[:max_idx]]

        top_3 = _top_3_scorelines(matrix)
        ou_probs = _over_under_probs(matrix)
        btts = _btts_prob(matrix)

        data = {
            "matrix": matrix,
            "top_3_scorelines": top_3,
            "over_under_probs": ou_probs,
            "btts_prob": btts,
        }

        freshness = get_engine_widget_freshness("score")

        return {
            "widget_type": "scoreline_distribution",
            "data": data,
            "explanation": {},
            "confidence": {"score": top_3[0]["prob"] if top_3 else 0.0, "band": "medium"},
            "freshness": freshness,
            "summary": {
                "headline": f"{home_team} vs {away_team}",
                "home_team": home_team,
                "away_team": away_team,
            },
        }