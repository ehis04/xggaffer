from __future__ import annotations

import logging
from datetime import date as date_type

from rest_framework.request import Request

from apps.predictions.ml.models.match_outcome.config import DEMO_SEASON
from apps.predictions.utils.widget_freshness import get_engine_widget_freshness
from apps.predictions.views.widget_base import WidgetBaseView

_logger = logging.getLogger(__name__)

RISK_HIGH_THRESHOLD = 0.4
RISK_MEDIUM_THRESHOLD = 0.7

INJURED_STATUSES = {"injured"}
AT_RISK_STATUSES = {"risk_flagged"}

DEFAULT_LEAGUE = "EPL"
DEFAULT_SEASON = DEMO_SEASON


def _get_team_squad(*args, **kwargs):
    from apps.predictions.services.availability_handler import _get_team_squad as _real
    return _real(*args, **kwargs)


def _get_availability_predictor():
    from apps.predictions.ml.models.availability.predict import get_shared_predictor
    return get_shared_predictor()


def _derive_risk_level(p_available: float, status: str | None) -> str:
    if status in INJURED_STATUSES:
        return "unavailable"
    if status in AT_RISK_STATUSES:
        return "at_risk"
    if p_available < RISK_HIGH_THRESHOLD:
        return "unavailable"
    if p_available < RISK_MEDIUM_THRESHOLD:
        return "at_risk"
    return "available"


def _build_player_entry(player: dict) -> dict:
    p_available = float(player.get("p_available") or 0.0)
    status = str(player.get("status") or "")
    risk_level = _derive_risk_level(p_available, status)
    return_date_raw = player.get("expected_return_date")
    return_date = str(return_date_raw) if return_date_raw else None

    return {
        "name": str(player.get("player_name") or ""),
        "availability_prob": p_available,
        "risk_level": risk_level,
        "return_date_estimate": return_date,
    }


def _build_summary(players: list[dict]) -> dict:
    available = sum(1 for p in players if p["risk_level"] == "available")
    at_risk = sum(1 for p in players if p["risk_level"] == "at_risk")
    unavailable = sum(1 for p in players if p["risk_level"] == "unavailable")
    return {
        "available_count": available,
        "high_risk_count": at_risk,
        "unavailable_count": unavailable,
    }


class AvailabilityWidgetView(WidgetBaseView):
    widget_intent = "availability"

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

        freshness = get_engine_widget_freshness("availability")

        try:
            import pandas as pd

            player_rows, _ = _get_team_squad(team, league, season)
            if not player_rows:
                return {
                    "widget_type": "availability",
                    "data": None,
                    "explanation": {},
                    "confidence": {"score": 0.0, "band": "low"},
                    "freshness": freshness,
                    "summary": {"note": "No availability data for this team"},
                }

            players_df = pd.DataFrame(player_rows)
            target_date = date_type.fromisoformat(fixture_date_str)
            raw_results: list[dict] = _get_availability_predictor().predict_for_players(
                players_df, target_date
            )

            players = [_build_player_entry(p) for p in raw_results]
            summary = _build_summary(players)

            return {
                "widget_type": "availability",
                "data": {
                    "team": team,
                    "fixture_date": fixture_date_str,
                    "players": players,
                    "summary": summary,
                },
                "explanation": {},
                "confidence": {"score": 0.7, "band": "medium"},
                "freshness": freshness,
                "summary": summary,
            }

        except Exception as exc:
            _logger.exception("AvailabilityWidgetView failed for team %s: %s", team, exc)
            return {
                "widget_type": "availability",
                "data": None,
                "explanation": {},
                "confidence": {"score": 0.0, "band": "low"},
                "freshness": freshness,
                "summary": {"note": "No availability data for this team"},
            }