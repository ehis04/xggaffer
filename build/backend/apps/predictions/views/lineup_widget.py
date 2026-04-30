from __future__ import annotations

import logging
from datetime import date as date_type

from rest_framework.request import Request

from apps.predictions.ml.models.lineup.config import TEST_SEASONS
from apps.predictions.utils.widget_freshness import get_engine_widget_freshness
from apps.predictions.views.widget_base import WidgetBaseView

_logger = logging.getLogger(__name__)

LINEUP_XI_SIZE = 11
CONFIDENCE_HIGH_THRESHOLD = 0.8
CONFIDENCE_MEDIUM_THRESHOLD = 0.6

DEFAULT_LEAGUE = "EPL"
DEFAULT_SEASON = TEST_SEASONS[-1]


def get_latest_team_features(*args, **kwargs):
    from apps.predictions.ml.models.lineup.feature_service import (
        get_latest_team_features as _real,
    )
    return _real(*args, **kwargs)


def predict_match_lineups(*args, **kwargs):
    from apps.predictions.ml.models.lineup.predict import (
        predict_match_lineups as _real,
    )
    return _real(*args, **kwargs)


def _confidence_band(mean_prob: float) -> str:
    if mean_prob >= CONFIDENCE_HIGH_THRESHOLD:
        return "high"
    if mean_prob >= CONFIDENCE_MEDIUM_THRESHOLD:
        return "medium"
    return "low"


_MAX_START_PROB = 0.97


def _shape_player(raw: dict) -> dict:
    return {
        "name": str(raw.get("player_name") or ""),
        "position": str(raw.get("position") or ""),
        "start_prob": min(float(raw.get("p_start") or 0.0), _MAX_START_PROB),
        "stable_id": str(raw["player_id"]) if raw.get("player_id") is not None else None,
    }


class LineupWidgetView(WidgetBaseView):
    widget_intent = "predicted-lineup"

    def get_widget_data(self, request: Request) -> dict:
        team = request.query_params.get("team", "").strip()
        fixture_date_str = request.query_params.get("fixture_date", "").strip()
        league = request.query_params.get("league", DEFAULT_LEAGUE).strip() or DEFAULT_LEAGUE
        season = request.query_params.get("season", DEFAULT_SEASON).strip() or DEFAULT_SEASON

        if not team or not fixture_date_str:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("team and fixture_date are required.")

        try:
            date_type.fromisoformat(fixture_date_str)
        except ValueError:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("fixture_date must be a valid ISO date (YYYY-MM-DD).")

        freshness = get_engine_widget_freshness("lineup")

        try:
            import pandas as pd

            team_df = get_latest_team_features(team, league, season)
            raw = predict_match_lineups(team_df)

            team_result = raw.get(team)
            if not team_result:
                team_result = next(iter(raw.values()), None) if raw else None

            if not team_result:
                return {
                    "widget_type": "predicted_lineup",
                    "data": None,
                    "explanation": {},
                    "confidence": {"score": 0.0, "band": "low"},
                    "freshness": freshness,
                    "summary": {},
                }

            xi_raw: list[dict] = (
                team_result["predicted_xi"].to_dict(orient="records")
                if hasattr(team_result["predicted_xi"], "to_dict")
                else team_result["predicted_xi"]
            )
            all_raw: list[dict] = (
                team_result["all_probabilities"].to_dict(orient="records")
                if hasattr(team_result["all_probabilities"], "to_dict")
                else team_result["all_probabilities"]
            )

            xi_names = {p.get("player_name") for p in xi_raw}
            bench_raw = [p for p in all_raw if p.get("player_name") not in xi_names]

            predicted_xi = [_shape_player(p) for p in xi_raw][:LINEUP_XI_SIZE]

            bench_candidates = sorted(
                [_shape_player(p) for p in bench_raw],
                key=lambda p: p["start_prob"],
                reverse=True,
            )

            mean_prob = (
                sum(p["start_prob"] for p in predicted_xi) / len(predicted_xi)
                if predicted_xi
                else 0.0
            )
            band = _confidence_band(mean_prob)

            return {
                "widget_type": "predicted_lineup",
                "data": {
                    "team": team,
                    "fixture_date": fixture_date_str,
                    "formation": team_result.get("formation"),
                    "predicted_xi": predicted_xi,
                    "bench_candidates": bench_candidates,
                },
                "explanation": {},
                "confidence": {"score": round(mean_prob, 4), "band": band},
                "freshness": freshness,
                "summary": {"formation": team_result.get("formation")},
            }

        except Exception as exc:
            _logger.exception("LineupWidgetView failed for team %s: %s", team, exc)
            return {
                "widget_type": "predicted_lineup",
                "data": None,
                "explanation": {},
                "confidence": {"score": 0.0, "band": "low"},
                "freshness": freshness,
                "summary": {},
            }