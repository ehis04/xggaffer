from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery
from apps.predictions.services.source_policy import (
    apply_source_priority,
    source_coverage_metadata,
)

_logger = logging.getLogger(__name__)

MATCHES_CSV_PATH = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "processed"
    / "matches"
    / "merged"
    / "all_leagues_all_seasons_matches_merged.csv"
)

H2H_LIMIT = 10
DEFAULT_LEAGUE = "EPL"


class H2HHandler(EngineHandler):
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        home = parsed_query.home_team
        away = parsed_query.away_team

        if not home or not away:
            return QueryPayload(
                intent=IntentClass.HEAD_TO_HEAD,
                engine_data={},
                partial=True,
                error="Two teams required for head-to-head analysis.",
            )

        try:
            df = pd.read_csv(MATCHES_CSV_PATH, low_memory=False)
            df = df[df["is_finished"] == True]
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

            league = parsed_query.league
            if league:
                df = df[df["league"] == league]

            df, used_sources = apply_source_priority(
                df,
                dedupe_keys=["league", "season", "date", "home_team", "away_team"],
            )

            mask = (
                ((df["home_team"] == home) & (df["away_team"] == away)) |
                ((df["home_team"] == away) & (df["away_team"] == home))
            )
            h2h_df = df[mask].sort_values("date", ascending=False).head(H2H_LIMIT)

            if h2h_df.empty:
                return QueryPayload(
                    intent=IntentClass.HEAD_TO_HEAD,
                    engine_data={},
                    partial=True,
                    error=f"No head-to-head history found between {home} and {away}.",
                )

            records = []
            home_wins = away_wins = draws = 0

            for _, row in h2h_df.iterrows():
                hg = int(row["home_goals"])
                ag = int(row["away_goals"])
                h_team = row["home_team"]
                a_team = row["away_team"]

                if hg > ag:
                    winner = h_team
                elif ag > hg:
                    winner = a_team
                else:
                    winner = "Draw"

                if winner == home:
                    home_wins += 1
                elif winner == away:
                    away_wins += 1
                else:
                    draws += 1

                records.append({
                    "date": str(row["date"].date()),
                    "home_team": h_team,
                    "away_team": a_team,
                    "home_goals": hg,
                    "away_goals": ag,
                    "home_xg": round(float(row["home_xg"]), 2) if pd.notna(row["home_xg"]) else None,
                    "away_xg": round(float(row["away_xg"]), 2) if pd.notna(row["away_xg"]) else None,
                    "winner": winner,
                    "league": row["league"],
                    "season": int(row["season"]),
                })

            total = len(records)
            return QueryPayload(
                intent=IntentClass.HEAD_TO_HEAD,
                engine_data={
                    "team_a": home,
                    "team_b": away,
                    "total_meetings": total,
                    f"{home}_wins": home_wins,
                    f"{away}_wins": away_wins,
                    "draws": draws,
                    "home_win_pct": round(home_wins / total, 3),
                    "away_win_pct": round(away_wins / total, 3),
                    "draw_pct": round(draws / total, 3),
                    "matches": records,
                    "source_coverage": source_coverage_metadata(
                        intent=IntentClass.HEAD_TO_HEAD.value,
                        used_sources=used_sources,
                    ),
                },
                partial=False,
                error=None,
            )
        except Exception as exc:
            _logger.exception("H2HHandler failed: %s", exc)
            return QueryPayload(
                intent=IntentClass.HEAD_TO_HEAD,
                engine_data={},
                partial=True,
                error=str(exc),
            )