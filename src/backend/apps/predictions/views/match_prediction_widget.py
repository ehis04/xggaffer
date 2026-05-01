from __future__ import annotations

import logging

from rest_framework.request import Request

from apps.predictions.ml.models.match_outcome.config import DEMO_SEASON
from apps.predictions.utils.elo_reader import get_elo_rating
from apps.predictions.utils.widget_freshness import get_engine_widget_freshness
from apps.predictions.views.widget_base import WidgetBaseView

_logger = logging.getLogger(__name__)

CONFIDENCE_HIGH_THRESHOLD = 0.55
CONFIDENCE_MEDIUM_THRESHOLD = 0.45
ENGINE_2_VERSION = "lr_v1"
OUTCOME_MAP = {"Home": "H", "Draw": "D", "Away": "A"}
DEFAULT_LEAGUE_CODE = "EPL"
DEFAULT_SEASON = DEMO_SEASON


def explain_match(*args, **kwargs):
    from apps.predictions.ml.models.match_outcome.interpret import explain_match as _real
    return _real(*args, **kwargs)


def _confidence_band(max_prob: float) -> str:
    if max_prob > CONFIDENCE_HIGH_THRESHOLD:
        return "high"
    if max_prob > CONFIDENCE_MEDIUM_THRESHOLD:
        return "medium"
    return "low"


class MatchPredictionWidgetView(WidgetBaseView):
    widget_intent = "match-prediction"

    def get_widget_data(self, request: Request) -> dict:
        home_team = request.query_params.get("home_team", "").strip()
        away_team = request.query_params.get("away_team", "").strip()
        league_code = request.query_params.get("league", DEFAULT_LEAGUE_CODE).strip() or DEFAULT_LEAGUE_CODE
        season = request.query_params.get("season", DEFAULT_SEASON).strip() or DEFAULT_SEASON

        if not home_team or not away_team:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("home_team and away_team are required.")

        freshness = get_engine_widget_freshness("outcome")

        try:
            result = explain_match(home_team, away_team, league_code, season, top_n=5)
        except ValueError as exc:
            # Missing feature coverage for team/season should not bubble as a 500.
            _logger.warning(
                "MatchPredictionWidgetView no data for %s vs %s (%s %s): %s",
                home_team,
                away_team,
                league_code,
                season,
                exc,
            )
            return {
                "widget_type": "match_prediction_card",
                "data": None,
                "explanation": {},
                "confidence": {"score": 0.0, "band": "low"},
                "freshness": freshness,
                "summary": {
                    "headline": f"{home_team} vs {away_team}",
                    "home_team": home_team,
                    "away_team": away_team,
                    "note": (
                        f"No prediction data available for {league_code} {season}. "
                        "Try another fixture or season."
                    ),
                },
            }

        result.pop("all_contributions", None)

        probs = result.get("probabilities", {})
        home_prob = probs.get("home", 0.0)
        draw_prob = probs.get("draw", 0.0)
        away_prob = probs.get("away", 0.0)
        max_prob = max(home_prob, draw_prob, away_prob)
        prediction = result.get("prediction", "")
        band = _confidence_band(max_prob)

        top_factors = result.get("top_factors", [])
        elo_home = get_elo_rating(home_team)
        elo_away = get_elo_rating(away_team)

        data = {
            "home_team": home_team,
            "away_team": away_team,
            "home_prob": home_prob,
            "draw_prob": draw_prob,
            "away_prob": away_prob,
            "prediction": prediction,
            "top_drivers": top_factors,
            "elo_home": elo_home,
            "elo_away": elo_away,
        }

        try:
            from apps.predictions.models import PredictionRecord
            PredictionRecord.objects.create(
                home_team=home_team,
                away_team=away_team,
                league_code=league_code,
                predicted_home_prob=home_prob,
                predicted_draw_prob=draw_prob,
                predicted_away_prob=away_prob,
                predicted_outcome=OUTCOME_MAP.get(prediction, "H"),
                confidence_band=band,
                engine_version=ENGINE_2_VERSION,
            )
        except Exception:
            _logger.exception("PredictionRecord write failed")

        explanation = {
            "summary_text": f"{home_team} vs {away_team}: model predicts {prediction}.",
            "top_factors": top_factors,
        }

        return {
            "widget_type": "match_prediction_card",
            "data": data,
            "explanation": explanation,
            "confidence": {"score": round(max_prob, 4), "band": band},
            "freshness": freshness,
            "summary": {
                "headline": f"{home_team} vs {away_team}",
                "home_team": home_team,
                "away_team": away_team,
            },
        }