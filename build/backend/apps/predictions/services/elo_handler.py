from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery

_logger = logging.getLogger(__name__)

ELO_HISTORY_PATH = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "processed"
    / "elo_ratings.csv"
)


def _team_in_history(history_df, team: str) -> bool:
    return (
        (history_df["home_team"] == team).any()
        or (history_df["away_team"] == team).any()
    )


class EloHandler(EngineHandler):
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        team = parsed_query.team or parsed_query.home_team
        league = parsed_query.league or "EPL"
        today = date.today()
        try:
            from apps.predictions.ml.engines.elo import (
                get_elo_at_date,
                elo_to_probabilities,
                load_elo_history,
            )
            import pandas as pd

            history_df = load_elo_history(ELO_HISTORY_PATH)

            if not _team_in_history(history_df, team):
                return QueryPayload(
                    intent=IntentClass.ELO_QUERY,
                    engine_data={},
                    partial=True,
                    error=f"No Elo history found for '{team}'.",
                )

            today_ts = pd.Timestamp(today)
            home_rating = get_elo_at_date(history_df, team, today_ts)

            engine_data: dict = {
                "team": team,
                "league": league,
                "elo_rating": home_rating,
            }

            if parsed_query.home_team and parsed_query.away_team:
                away = parsed_query.away_team
                if _team_in_history(history_df, away):
                    away_rating = get_elo_at_date(history_df, away, today_ts)
                    probs = elo_to_probabilities(home_rating, away_rating)
                    engine_data["away_team"] = away
                    engine_data["away_elo_rating"] = away_rating
                    engine_data["win_probabilities"] = probs

            return QueryPayload(
                intent=IntentClass.ELO_QUERY,
                engine_data=engine_data,
                partial=False,
                error=None,
            )
        except FileNotFoundError:
            return QueryPayload(
                intent=IntentClass.ELO_QUERY,
                engine_data={},
                partial=True,
                error="Elo history file not found.",
            )
        except Exception as exc:
            _logger.exception("EloHandler failed: %s", exc)
            return QueryPayload(
                intent=IntentClass.ELO_QUERY,
                engine_data={},
                partial=True,
                error=str(exc),
            )