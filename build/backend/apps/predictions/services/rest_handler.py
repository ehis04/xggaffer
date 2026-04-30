from __future__ import annotations

import logging
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

MATCHES_CSV_PATH = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "processed"
    / "matches"
    / "merged"
    / "all_leagues_all_seasons_matches_merged.csv"
)

DEFAULT_LEAGUE = "EPL"
DEFAULT_SEASON = "2025"
CONGESTION_WINDOW_DAYS = 28


class RestHandler(EngineHandler):
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        team = parsed_query.team or parsed_query.home_team
        league = parsed_query.league or DEFAULT_LEAGUE

        if not team:
            return QueryPayload(
                intent=IntentClass.REST_DAYS,
                engine_data={},
                partial=True,
                error="No team specified for rest analysis.",
            )

        try:
            df = pd.read_csv(MATCHES_CSV_PATH, low_memory=False)
            season = parsed_query.season or latest_available_season(df, default=DEFAULT_SEASON)
            df = df[df["is_finished"] == True]
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

            season_df = df[
                (df["league"] == league) & (df["season"] == int(season))
            ]
            season_df, used_sources = apply_source_priority(
                season_df,
                dedupe_keys=["league", "season", "date", "home_team", "away_team"],
            )

            mask = (season_df["home_team"] == team) | (season_df["away_team"] == team)
            team_df = season_df[mask].sort_values("date")

            if team_df.empty:
                return QueryPayload(
                    intent=IntentClass.REST_DAYS,
                    engine_data={},
                    partial=True,
                    error=f"No match data for {team} in {league} {season}.",
                )

            dates = team_df["date"].dropna().tolist()
            rest_intervals: list[int] = []
            for i in range(1, len(dates)):
                delta = (dates[i] - dates[i - 1]).days
                rest_intervals.append(delta)

            avg_rest = round(sum(rest_intervals) / len(rest_intervals), 1) if rest_intervals else None
            min_rest = min(rest_intervals) if rest_intervals else None
            max_rest = max(rest_intervals) if rest_intervals else None

            last_date = dates[-1]
            window_start = last_date - pd.Timedelta(days=CONGESTION_WINDOW_DAYS)
            recent_count = sum(1 for d in dates if d >= window_start)

            last_match_row = team_df.iloc[-1]
            last_opponent = (
                last_match_row["away_team"]
                if last_match_row["home_team"] == team
                else last_match_row["home_team"]
            )

            return QueryPayload(
                intent=IntentClass.REST_DAYS,
                engine_data={
                    "team": team,
                    "league": league,
                    "season": season,
                    "matches_played": len(dates),
                    "avg_days_between_matches": avg_rest,
                    "min_days_between_matches": min_rest,
                    "max_days_between_matches": max_rest,
                    "matches_in_last_28_days": recent_count,
                    "last_match_date": str(last_date.date()),
                    "last_opponent": last_opponent,
                    "rest_intervals": rest_intervals,
                    "source_coverage": source_coverage_metadata(
                        intent=IntentClass.REST_DAYS.value,
                        used_sources=used_sources,
                    ),
                },
                partial=False,
                error=None,
            )
        except Exception as exc:
            _logger.exception("RestHandler failed: %s", exc)
            return QueryPayload(
                intent=IntentClass.REST_DAYS,
                engine_data={},
                partial=True,
                error=str(exc),
            )