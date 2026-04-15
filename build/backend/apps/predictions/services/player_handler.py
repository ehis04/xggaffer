from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery

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
        season = parsed_query.season or DEFAULT_SEASON
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
            df = pd.read_csv(PLAYERS_CSV_PATH)
            mask = df["season"] == int(season)
            if league:
                mask &= df["league"] == league
            if team:
                mask &= df["team"] == team
            season_df = df[mask]

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