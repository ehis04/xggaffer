from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery
from apps.predictions.services.source_policy import (
    filter_by_season_tokens,
    fuse_source_rows,
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


def _numeric_value(row: pd.DataFrame, column: str) -> float | None:
    if row.empty or column not in row.columns:
        return None
    value = pd.to_numeric(pd.Series([row[column].iloc[0]]), errors="coerce").iloc[0]
    if pd.isna(value):
        return None
    return float(value)


class StatHandler(EngineHandler):
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        league = parsed_query.league or DEFAULT_LEAGUE
        home = parsed_query.home_team
        away = parsed_query.away_team
        try:
            df = pd.read_csv(TEAMS_CSV_PATH, low_memory=False)
            season = parsed_query.season or latest_available_season(df)
            season_df = df[df["league"] == league]
            season_df = filter_by_season_tokens(season_df, season)
            season_df, used_sources = fuse_source_rows(
                season_df,
                dedupe_keys=["league", "team"],
            )

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
                    home_value = _numeric_value(home_row, col)
                    away_value = _numeric_value(away_row, col)
                    if home_value is None or away_value is None:
                        continue
                    stats[col] = {
                        home: home_value,
                        away: away_value,
                    }

            home_npxg = _numeric_value(home_row, "npxg_for")
            away_npxg = _numeric_value(away_row, "npxg_for")
            home_npxga = _numeric_value(home_row, "npxg_against")
            away_npxga = _numeric_value(away_row, "npxg_against")
            if None not in (home_npxg, away_npxg, home_npxga, away_npxga):
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
                    "source_coverage": source_coverage_metadata(
                        intent=IntentClass.STAT_COMPARISON.value,
                        used_sources=used_sources,
                    ),
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