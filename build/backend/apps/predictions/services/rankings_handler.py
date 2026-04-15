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

DEFAULT_LEAGUE = "EPL"
DEFAULT_SEASON = "2024"
RANKING_COLUMNS = [
    "wins", "draws", "losses", "goals_for", "goals_against",
    "xg_for", "xg_against", "npxg_for", "xpts",
    "ppda", "oppda", "clean_sheets", "possession_pct",
    "shots", "shots_on_target",
]


class RankingsHandler(EngineHandler):
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        league = parsed_query.league or DEFAULT_LEAGUE
        season = parsed_query.season or DEFAULT_SEASON

        try:
            df = pd.read_csv(TEAMS_CSV_PATH)
            mask = (df["league"] == league) & (df["season"] == int(season))
            season_df = df[mask].copy()

            if season_df.empty:
                return QueryPayload(
                    intent=IntentClass.TEAM_RANKINGS,
                    engine_data={},
                    partial=True,
                    error=f"No team data found for {league} {season}.",
                )

            season_df["points"] = season_df["wins"] * 3 + season_df["draws"]
            season_df = season_df.sort_values("points", ascending=False).reset_index(drop=True)
            season_df["position"] = season_df.index + 1

            rows = []
            for _, row in season_df.iterrows():
                entry: dict = {"position": int(row["position"]), "team": row["team"], "points": int(row["points"])}
                for col in RANKING_COLUMNS:
                    if col in season_df.columns and pd.notna(row[col]):
                        val = row[col]
                        entry[col] = round(float(val), 3) if isinstance(val, float) else int(val)
                rows.append(entry)

            n = len(rows)
            relegation_zone = [r["team"] for r in rows[max(0, n - 3):]]
            top_4 = [r["team"] for r in rows[:4]]
            leader = rows[0]["team"] if rows else None

            return QueryPayload(
                intent=IntentClass.TEAM_RANKINGS,
                engine_data={
                    "league": league,
                    "season": season,
                    "table": rows,
                    "leader": leader,
                    "top_4": top_4,
                    "relegation_zone": relegation_zone,
                },
                partial=False,
                error=None,
            )
        except Exception as exc:
            _logger.exception("RankingsHandler failed: %s", exc)
            return QueryPayload(
                intent=IntentClass.TEAM_RANKINGS,
                engine_data={},
                partial=True,
                error=str(exc),
            )