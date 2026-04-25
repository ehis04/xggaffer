from __future__ import annotations

from rest_framework.request import Request

from apps.predictions.utils.widget_freshness import get_engine_widget_freshness
from apps.predictions.views.widget_base import WidgetBaseView

VALID_LEAGUE_CODES = ["PL", "PD", "BL1", "SA", "FL1"]
CURRENT_SIMULATION_SEASON = "2024"
SEASON_LABEL = "2024/2025"

RELEGATION_ZONE_START: dict[str, int] = {
    "PL": 18,
    "PD": 18,
    "BL1": 16,
    "SA": 18,
    "FL1": 18,
}


def _derive_relegation_prob(
    position_distribution: dict[int, float],
    league_code: str,
    team_count: int,
) -> float:
    start = RELEGATION_ZONE_START.get(league_code, 18)
    return sum(
        prob
        for pos, prob in position_distribution.items()
        if pos >= start
    )


def _build_team_dict(raw_row: dict, league_code: str, team_count: int) -> dict:
    pos_dist_raw: dict = raw_row.get("position_probabilities") or {}
    pos_dist = {int(k): float(v) for k, v in pos_dist_raw.items()}

    predicted_position = int(raw_row.get("predicted_position") or 0)
    predicted_points = float(raw_row.get("predicted_points") or 0.0)
    title_prob = float(raw_row.get("title_probability") or 0.0)
    top4_prob = float(raw_row.get("top_4_probability") or 0.0)
    relegation_prob = float(raw_row.get("relegation_probability") or 0.0)

    pos_dist_str = {str(k): v for k, v in pos_dist.items()}

    return {
        "team_name": str(raw_row.get("team") or ""),
        "expected_position": predicted_position,
        "projected_points_median": predicted_points,
        "projected_points_p10": None,
        "projected_points_p90": None,
        "title_prob": title_prob,
        "top4_prob": top4_prob,
        "relegation_prob": relegation_prob,
        "position_distribution": pos_dist_str,
    }


class ProjectedTableWidgetView(WidgetBaseView):
    widget_intent = "projected-table"

    def get_widget_data(self, request: Request) -> dict:
        league_code = request.query_params.get("league_code", "").strip().upper()

        if league_code not in VALID_LEAGUE_CODES:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                f"Invalid league_code '{league_code}'. "
                f"Valid options: {', '.join(VALID_LEAGUE_CODES)}"
            )

        from apps.predictions.models import SimulationResult

        record = (
            SimulationResult.objects.filter(
                league=league_code,
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
        team_count = len(raw_rows)

        teams = [
            _build_team_dict(row, league_code, team_count)
            for row in raw_rows
        ]
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