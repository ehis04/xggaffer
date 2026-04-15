from __future__ import annotations

import logging
from datetime import date as date_type
from pathlib import Path

import pandas as pd

from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery

_logger = logging.getLogger(__name__)

DEFAULT_LEAGUE = "EPL"
DEFAULT_SEASON = "2024"

PLAYERS_CSV_PATH = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "processed"
    / "players"
    / "merged"
    / "all_leagues_all_seasons_players_merged.csv"
)

_RISK_DEFAULTS: dict[str, float] = {
    "minutes_last_7d": 0.0,
    "minutes_last_14d": 0.0,
    "minutes_last_30d": 0.0,
    "matches_last_7d": 0.0,
    "matches_last_14d": 0.0,
    "consecutive_starts": 0.0,
    "days_since_last_rest": 0.0,
    "age": 25.0,
    "prior_injuries_count": 0.0,
    "days_since_last_injury": 0.0,
    "season_phase_mid": 0.0,
    "season_phase_late": 0.0,
    "acwr_7_28": 1.0,
    "minutes_per_match_30d": 0.0,
    "workload_zscore_30d": 0.0,
    "recent_match_density": 0.0,
    "cumulative_workload_per_week": 0.0,
    "has_prior_injury": 0.0,
    "has_recent_rest": 0.0,
}


def _build_player_row(player_name: str, team: str | None) -> dict:
    row = dict(_RISK_DEFAULTS)
    row["player_id"] = None
    row["player_name"] = player_name
    row["team"] = team or ""
    row["is_injured"] = False
    return row


def _get_team_squad(team: str, league: str, season: str) -> list[dict]:
    if not PLAYERS_CSV_PATH.exists():
        return []

    df = pd.read_csv(PLAYERS_CSV_PATH)
    subset = df[
        (df["team"] == team)
        & (df["league"] == league)
        & (df["season"] == int(season))
    ]

    rows = []
    for _, player_row in subset.iterrows():
        row = dict(_RISK_DEFAULTS)
        row["player_id"] = player_row.get("player_id")
        row["player_name"] = player_row.get("name", "")
        row["team"] = team
        row["is_injured"] = False
        rows.append(row)

    return rows


class AvailabilityHandler(EngineHandler):
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        target_date = date_type.today()
        league = parsed_query.league or DEFAULT_LEAGUE
        season = parsed_query.season or DEFAULT_SEASON
        try:
            from apps.predictions.ml.models.availability.predict import AvailabilityPredictor

            predictor = AvailabilityPredictor()

            if parsed_query.player_name:
                player_rows = [_build_player_row(parsed_query.player_name, parsed_query.team)]
            elif parsed_query.team:
                player_rows = _get_team_squad(parsed_query.team, league, season)
                if not player_rows:
                    return QueryPayload(
                        intent=IntentClass.AVAILABILITY_QUERY,
                        engine_data={},
                        partial=True,
                        error=f"No player data found for {parsed_query.team} in {league} {season}.",
                    )
            else:
                return QueryPayload(
                    intent=IntentClass.AVAILABILITY_QUERY,
                    engine_data={},
                    partial=True,
                    error="No player or team specified.",
                )

            players_df = pd.DataFrame(player_rows)
            results = predictor.predict_for_players(players_df, target_date)

            return QueryPayload(
                intent=IntentClass.AVAILABILITY_QUERY,
                engine_data={"players": results, "team": parsed_query.team},
                partial=False,
                error=None,
            )
        except FileNotFoundError:
            return QueryPayload(
                intent=IntentClass.AVAILABILITY_QUERY,
                engine_data={},
                partial=True,
                error="Availability model not available.",
            )
        except Exception as exc:
            _logger.exception("AvailabilityHandler failed: %s", exc)
            return QueryPayload(
                intent=IntentClass.AVAILABILITY_QUERY,
                engine_data={},
                partial=True,
                error=str(exc),
            )