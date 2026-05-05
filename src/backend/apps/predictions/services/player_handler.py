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

PLAYERS_CSV_PATH = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "processed"
    / "players"
    / "merged"
    / "all_leagues_all_seasons_players_merged.csv"
)

DEFAULT_SEASON = "2024"

PLAYER_STAT_COLUMNS = [
    "games", "minutes", "goals", "assists", "npg", "xg", "npxg", "xa",
    "shots", "key_passes", "yellow_cards", "red_cards",
    "xg90", "npxg90", "xa90", "sh90", "kp90", "npxg90_xa90",
    "saves", "save_pct", "clean_sheets",
    "pass_accuracy_pct", "successful_dribbles", "tackles_won",
    "interceptions", "aerial_duel_win_pct", "rating",
]
class PlayerHandler(EngineHandler):
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        player_name = parsed_query.player_name
        league = parsed_query.league
        team = parsed_query.team or parsed_query.home_team

        if not player_name:
            return QueryPayload(
                intent=IntentClass.PLAYER_STATS,
                engine_data={},
                partial=True,
                error="No player name specified.",
            )

        try:
            df = pd.read_csv(PLAYERS_CSV_PATH, low_memory=False)
            season = parsed_query.season or latest_available_season(df, default=DEFAULT_SEASON)
            season_df = filter_by_season_tokens(df, season)
            if league:
                season_df = season_df[season_df["league"] == league]
            if team:
                season_df = season_df[season_df["team"] == team]
            season_df, used_sources = fuse_source_rows(
                season_df,
                dedupe_keys=["league", "team", "name"],
            )

            name_lower = player_name.lower()
            exact = season_df[season_df["name"].str.lower() == name_lower]
            if exact.empty:
                contains = season_df[season_df["name"].str.lower().str.contains(name_lower, na=False)]
                row_df = contains
            else:
                row_df = exact

            if row_df.empty:
                return QueryPayload(
                    intent=IntentClass.PLAYER_STATS,
                    engine_data={},
                    partial=True,
                    error=f"No player data found for '{player_name}' in {season}.",
                )

            row = row_df.iloc[0]
            stats: dict = {"name": row["name"], "team": row["team"], "league": row["league"], "season": season, "position": row.get("position", None)}
            for col in PLAYER_STAT_COLUMNS:
                if col in row_df.columns and pd.notna(row[col]):
                    val = row[col]
                    stats[col] = round(float(val), 3) if isinstance(val, float) else int(val)

            stats["source_coverage"] = source_coverage_metadata(
                intent=IntentClass.PLAYER_STATS.value,
                used_sources=used_sources,
            )

            return QueryPayload(
                intent=IntentClass.PLAYER_STATS,
                engine_data=stats,
                partial=False,
                error=None,
            )
        except Exception as exc:
            _logger.exception("PlayerHandler failed: %s", exc)
            return QueryPayload(
                intent=IntentClass.PLAYER_STATS,
                engine_data={},
                partial=True,
                error=str(exc),
            )