from __future__ import annotations

import logging
import math
from pathlib import Path

import pandas as pd

from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery
from apps.predictions.services.source_policy import (
    apply_source_priority,
    latest_available_season,
    source_coverage_metadata,
)

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
DEFAULT_SEASON = "2025"
RANKING_COLUMNS = [
    "wins", "draws", "losses", "goals_for", "goals_against",
    "xg_for", "xg_against", "npxg_for", "xpts",
    "ppda", "oppda", "clean_sheets", "possession_pct",
    "shots", "shots_on_target",
]


class RankingsHandler(EngineHandler):
    @staticmethod
    def _coerce_number(value: object) -> int | float | None:
        if pd.isna(value):
            return None

        if isinstance(value, bool):
            return int(value)

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            if not math.isfinite(value):
                return None
            return int(value) if value.is_integer() else round(value, 3)

        try:
            parsed = float(str(value).strip())
        except (TypeError, ValueError):
            return None

        if not math.isfinite(parsed):
            return None
        return int(parsed) if parsed.is_integer() else round(parsed, 3)

    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        league = parsed_query.league or DEFAULT_LEAGUE

        try:
            df = pd.read_csv(TEAMS_CSV_PATH)
            season = parsed_query.season or latest_available_season(df, default=DEFAULT_SEASON)
            mask = (df["league"] == league) & (df["season"] == int(season))
            season_df = df[mask].copy()
            season_df, used_sources = apply_source_priority(
                season_df,
                dedupe_keys=["league", "season", "team"],
            )

            if season_df.empty:
                return QueryPayload(
                    intent=IntentClass.TEAM_RANKINGS,
                    engine_data={},
                    partial=True,
                    error=f"No team data found for {league} {season}.",
                )

            for col in ("wins", "draws"):
                if col not in season_df.columns:
                    season_df[col] = 0
                season_df[col] = pd.to_numeric(season_df[col], errors="coerce").fillna(0)

            season_df["points"] = (season_df["wins"] * 3 + season_df["draws"]).fillna(0)
            season_df = season_df.sort_values("points", ascending=False).reset_index(drop=True)
            season_df["position"] = season_df.index + 1

            rows = []
            for _, row in season_df.iterrows():
                team_name = row.get("team")
                if pd.isna(team_name) or str(team_name).strip() == "":
                    continue

                points = self._coerce_number(row.get("points"))
                entry: dict = {
                    "position": int(row["position"]),
                    "team": str(team_name),
                    "points": int(points) if points is not None else 0,
                }
                for col in RANKING_COLUMNS:
                    if col in season_df.columns and pd.notna(row[col]):
                        coerced = self._coerce_number(row[col])
                        if coerced is not None:
                            entry[col] = coerced
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
                    "source_coverage": source_coverage_metadata(
                        intent=IntentClass.TEAM_RANKINGS.value,
                        used_sources=used_sources,
                    ),
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