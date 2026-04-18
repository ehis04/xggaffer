from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery

_logger = logging.getLogger(__name__)

TEAMS_CSV_PATH = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "processed"
    / "teams"
    / "merged"
    / "all_leagues_all_seasons_teams_merged.csv"
)

STAT_COLUMNS = [
    "wins",
    "draws",
    "losses",
    "goals_for",
    "goals_against",
    "xg_for",
    "xg_against",
    "npxg_for",
    "npxg_against",
    "xpts",
    "ppda",
    "oppda",
    "deep_completions_for",
    "deep_completions_against",
    "clean_sheets",
    "possession_pct",
    "shots",
    "shots_on_target",
    "pass_accuracy_pct",
    "tackles",
    "interceptions",
    "saves",
]

DEFAULT_LEAGUE = "EPL"
DEFAULT_SEASON = "2024"


class StatHandler(EngineHandler):
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        league = parsed_query.league or DEFAULT_LEAGUE
        season = parsed_query.season or DEFAULT_SEASON
        home = parsed_query.home_team
        away = parsed_query.away_team
        try:
            df = pd.read_csv(TEAMS_CSV_PATH)
            mask = (df["league"] == league) & (df["season"] == int(season))
            season_df = df[mask]

            home_row = season_df[season_df["team"] == home]
            away_row = season_df[season_df["team"] == away]

            missing = []
            if home_row.empty:
                missing.append(home)
            if away_row.empty:
                missing.append(away)
            if missing:
                return QueryPayload(
                    intent=IntentClass.STAT_COMPARISON,
                    engine_data={},
                    partial=True,
                    error=f"No stat data for: {', '.join(missing)} in {league} {season}.",
                )

            stats: dict = {}
            for col in STAT_COLUMNS:
                if col in season_df.columns:
                    stats[col] = {
                        home: float(home_row[col].iloc[0]),
                        away: float(away_row[col].iloc[0]),
                    }

            home_npxg = float(home_row["npxg_for"].iloc[0])
            away_npxg = float(away_row["npxg_for"].iloc[0])
            home_npxga = float(home_row["npxg_against"].iloc[0])
            away_npxga = float(away_row["npxg_against"].iloc[0])
            stats["npxgd"] = {
                home: round(home_npxg - home_npxga, 4),
                away: round(away_npxg - away_npxga, 4),
            }

            return QueryPayload(
                intent=IntentClass.STAT_COMPARISON,
                engine_data={
                    "home_team": home,
                    "away_team": away,
                    "league": league,
                    "season": season,
                    "stats": stats,
                },
                partial=False,
                error=None,
            )
        except Exception as exc:
            _logger.exception("StatHandler failed: %s", exc)
            return QueryPayload(
                intent=IntentClass.STAT_COMPARISON,
                engine_data={},
                partial=True,
                error=str(exc),
            )