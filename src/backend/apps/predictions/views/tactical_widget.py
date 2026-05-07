from __future__ import annotations

import logging

from rest_framework.request import Request

from apps.predictions.utils.widget_freshness import get_engine_widget_freshness
from apps.predictions.views.widget_base import WidgetBaseView

_logger = logging.getLogger(__name__)

STATIC_DATASET_STATUS = "static_dataset"
STRENGTH_THRESHOLD = 0.60
WEAKNESS_THRESHOLD = 0.45

ZONE_ROW_MAP = {
    0: "DEF-L", 1: "DEF-C", 2: "DEF-R",
    3: "MID-L", 4: "MID-C", 5: "MID-R",
    6: "ATK-L", 7: "ATK-C", 8: "ATK-R",
}

GRID_ZONE_COUNT = 9


class TacticalAnalyser:
    def __new__(cls, *args, **kwargs):
        from apps.predictions.ml.models.tactical.predict import TacticalAnalyser as _real
        return _real(*args, **kwargs)


def _strength_flag(rate: float, mean_rate: float) -> str:
    if rate >= STRENGTH_THRESHOLD and rate >= mean_rate:
        return "strength"
    if rate <= WEAKNESS_THRESHOLD or rate < mean_rate * 0.85:
        return "weakness"
    return "neutral"


def _build_zone_profiles(zone_success_rates: dict, dominant_zones: list[int]) -> list[dict]:
    grid_rates = {}
    for zone_id_str, rate in zone_success_rates.items():
        zone_id = int(zone_id_str)
        grid_pos = zone_id % GRID_ZONE_COUNT
        zone_name = ZONE_ROW_MAP.get(grid_pos, f"Z{zone_id}")
        if zone_name not in grid_rates or zone_id in dominant_zones:
            grid_rates[zone_name] = float(rate)

    if not grid_rates:
        return []

    mean_rate = sum(grid_rates.values()) / len(grid_rates)

    profiles = []
    for zone_name_key in ZONE_ROW_MAP.values():
        rate = grid_rates.get(zone_name_key)
        if rate is None:
            continue
        profiles.append({
            "zone_name": zone_name_key,
            "pass_success_rate": round(rate, 4),
            "pressure_rate": None,
            "strength_flag": _strength_flag(rate, mean_rate),
        })

    return profiles


def _build_static_freshness(base_freshness: dict) -> dict:
    result = dict(base_freshness)
    result["staleness_status"] = STATIC_DATASET_STATUS
    result["is_stale"] = False
    result["snapshot_published_at"] = None
    result["cascade_degraded"] = False
    result["cascade_reason"] = None
    return result


_TEAM_NAME_MAP = {
    # EPL — odds/fixture names → tactical data names
    "Manchester City": "Man City",
    "Manchester United": "Man Utd",
    "Newcastle United": "Newcastle",
    "Wolverhampton Wanderers": "Wolves",
    # La Liga — odds/fixture names → tactical data names
    "Atletico Madrid": "Atletico",
    "Alaves": "Deportivo Alaves",
    "Levante": "Levante UD",
}


class TacticalSummaryWidgetView(WidgetBaseView):
    widget_intent = "tactical-summary"

    def get_widget_data(self, request: Request) -> dict:
        team = _TEAM_NAME_MAP.get(
            request.query_params.get("team", "").strip(),
            request.query_params.get("team", "").strip(),
        )

        if not team:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("team is required.")

        base_freshness = get_engine_widget_freshness("tactical")
        freshness = _build_static_freshness(base_freshness)

        null_response = {
            "widget_type": "tactical_summary",
            "data": None,
            "explanation": {},
            "confidence": {"score": 0.0, "band": "low"},
            "freshness": freshness,
            "summary": {"coverage_note": "Tactical data not available for this team"},
        }

        try:
            analyser = TacticalAnalyser()
            result = analyser.analyse_team(team)

            if result is None:
                return null_response

            zone_success_rates: dict = result.get("zone_success_rates") or {}
            dominant_zones: list[int] = result.get("dominant_zones") or []
            zone_profiles = _build_zone_profiles(zone_success_rates, dominant_zones)

            cluster_id = result.get("style_cluster")
            style_label = str(result.get("style_label") or "")

            data = {
                "team": team,
                "style_cluster": {
                    "id": cluster_id,
                    "label": style_label,
                    "similar_teams": [],
                },
                "zone_profiles": zone_profiles,
            }

            return {
                "widget_type": "tactical_summary",
                "data": data,
                "explanation": {
                    "competition_name": result.get("competition_name", ""),
                    "n_matches": result.get("n_matches_in_profile", 0),
                    "overall_completion_rate": result.get("overall_completion_rate"),
                    "overall_forward_ratio": result.get("overall_forward_ratio"),
                    "overall_pass_length": result.get("overall_pass_length"),
                    "dominant_zones": dominant_zones,
                },
                "confidence": {"score": 0.75, "band": "medium"},
                "freshness": freshness,
                "summary": {
                    "coverage_note": "La Liga coverage (StatsBomb Open Data)",
                },
            }

        except FileNotFoundError:
            return null_response
        except Exception as exc:
            _logger.exception("TacticalSummaryWidgetView failed for team %s: %s", team, exc)
            return null_response