from __future__ import annotations

from rest_framework.request import Request

from apps.predictions.utils.widget_freshness import get_engine_widget_freshness
from apps.predictions.views.widget_base import WidgetBaseView

CONFIDENCE_HIGH_THRESHOLD = 0.55
CONFIDENCE_MEDIUM_THRESHOLD = 0.45


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

        if not home_team or not away_team:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("home_team and away_team are required.")

        from apps.predictions.ml.models.match_outcome.interpret import explain_match

        result = explain_match(home_team, away_team, "EPL", "2024", top_n=5)
        result.pop("all_contributions", None)

        probs = result.get("probabilities", {})
        home_prob = probs.get("home", 0.0)
        draw_prob = probs.get("draw", 0.0)
        away_prob = probs.get("away", 0.0)
        max_prob = max(home_prob, draw_prob, away_prob)

        top_factors = result.get("top_factors", [])

        data = {
            "home_team": home_team,
            "away_team": away_team,
            "home_prob": home_prob,
            "draw_prob": draw_prob,
            "away_prob": away_prob,
            "prediction": result.get("prediction", ""),
            "top_drivers": top_factors,
            "elo_home": None,
            "elo_away": None,
        }

        explanation = {
            "summary_text": (
                f"{home_team} vs {away_team}: model predicts {result.get('prediction', '')}."
            ),
            "top_factors": top_factors,
        }

        confidence_score = max_prob
        band = _confidence_band(max_prob)

        freshness = get_engine_widget_freshness("outcome")

        summary = {
            "headline": f"{home_team} vs {away_team}",
            "home_team": home_team,
            "away_team": away_team,
        }

        return {
            "widget_type": "match_prediction_card",
            "data": data,
            "explanation": explanation,
            "confidence": {"score": round(confidence_score, 4), "band": band},
            "freshness": freshness,
            "summary": summary,
        }