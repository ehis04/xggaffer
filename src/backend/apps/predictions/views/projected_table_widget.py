from __future__ import annotations

from rest_framework.request import Request

from apps.predictions.utils.league_codes import COMPETITION_TO_UNDERSTAT
from apps.predictions.utils.widget_freshness import get_engine_widget_freshness
from apps.predictions.views.widget_base import WidgetBaseView

CURRENT_SIMULATION_SEASON = "2025"
SEASON_LABEL = "2025/2026"

RELEGATION_ZONE_START: dict[str, int] = {
    "PL": 18,
    "PD": 18,
    "BL1": 16,
    "SA": 18,
    "FL1": 18,
}


def _build_team_dict(raw_row: dict, league_code: str) -> dict:
    pos_dist_raw: dict = raw_row.get("position_probabilities") or {}
    pos_dist = {str(k): float(v) for k, v in pos_dist_raw.items()}

    # Calculate points range from position distribution
    # Use 10th and 90th percentiles of likely positions
    p10, p90 = _calculate_position_range(pos_dist)

    return {
        "team_name": str(raw_row.get("team") or ""),
        "expected_position": int(raw_row.get("predicted_position") or 0),
        "projected_points_median": float(raw_row.get("predicted_points") or 0.0),
        "projected_points_p10": p10,
        "projected_points_p90": p90,
        "title_prob": float(raw_row.get("title_probability") or 0.0),
        "top4_prob": float(raw_row.get("top_4_probability") or 0.0),
        "relegation_prob": float(raw_row.get("relegation_probability") or 0.0),
        "position_distribution": pos_dist,
    }


def _calculate_position_range(pos_dist: dict) -> tuple[int, int]:
    """Calculate 10th and 90th percentile positions from probability distribution."""
    if not pos_dist:
        return (None, None)

    # Build cumulative distribution
    positions = []
    cumulative = 0.0
    for pos in range(1, 21):
        prob = pos_dist.get(str(pos), 0.0)
        cumulative += prob
        positions.append((pos, cumulative))

    # Find 10th percentile (where cumulative >= 0.1)
    p10 = None
    p90 = None
    for pos, cum in positions:
        if p10 is None and cum >= 0.1:
            p10 = pos
        if cum >= 0.9:
            p90 = pos
            break

    return (p10, p90)


class ProjectedTableWidgetView(WidgetBaseView):
    widget_intent = "projected-table"

    def get_widget_data(self, request: Request) -> dict:
        league_code = request.query_params.get("league_code", "").strip().upper()

        if league_code not in COMPETITION_TO_UNDERSTAT:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                f"Invalid league_code '{league_code}'. "
                f"Valid options: {', '.join(COMPETITION_TO_UNDERSTAT.keys())}"
            )

        understat_code = COMPETITION_TO_UNDERSTAT[league_code]

        from apps.predictions.models import SimulationResult

        record = (
            SimulationResult.objects.filter(
                league__in=[understat_code, league_code],
                season=CURRENT_SIMULATION_SEASON,
            )
            .order_by("-computed_at")
            .first()
        )

        freshness = get_engine_widget_freshness("simulation")

        if record is None:
            return {
                "widget_type": "projected_table",
                "data": None,
                "explanation": {},
                "confidence": {"score": 0.0, "band": "low"},
                "freshness": freshness,
                "summary": {"data_note": "Season projection not yet available"},
            }

        raw_rows: list[dict] = record.results if isinstance(record.results, list) else []

        teams = [_build_team_dict(row, league_code) for row in raw_rows]
        teams.sort(key=lambda t: t["expected_position"])

        snapshot_published_at = (
            record.computed_at.isoformat()
            if not freshness.get("snapshot_published_at")
            else freshness["snapshot_published_at"]
        )
        freshness["snapshot_published_at"] = snapshot_published_at

        return {
            "widget_type": "projected_table",
            "data": {
                "league_code": league_code,
                "season": CURRENT_SIMULATION_SEASON,
                "teams": teams,
            },
            "explanation": {},
            "confidence": {"score": 0.8, "band": "high"},
            "freshness": freshness,
            "summary": {
                "season_label": SEASON_LABEL,
                "team_count": len(teams),
            },
        }