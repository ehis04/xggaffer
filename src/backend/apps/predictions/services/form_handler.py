from __future__ import annotations

import logging

import pandas as pd

from apps.predictions.data_paths import PROCESSED_DATA_ROOT
from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery
from apps.predictions.services.source_policy import (
    apply_source_priority,
    filter_by_season_tokens,
    latest_available_season,
    source_coverage_metadata,
)

_logger = logging.getLogger(__name__)

MATCHES_CSV_PATH = (
    PROCESSED_DATA_ROOT
    / "matches"
    / "merged"
    / "all_leagues_all_seasons_matches_merged.csv"
)

FORM_WINDOW = 5
DEFAULT_LEAGUE = "EPL"


class FormHandler(EngineHandler):
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        team = parsed_query.team or parsed_query.home_team
        league = parsed_query.league or DEFAULT_LEAGUE

        if not team:
            return QueryPayload(
                intent=IntentClass.FORM_ANALYSIS,
                engine_data={},
                partial=True,
                error="No team specified for form analysis.",
            )

        try:
            df = pd.read_csv(MATCHES_CSV_PATH, low_memory=False)
            season = parsed_query.season or latest_available_season(df)
            df = df[df["is_finished"] == True]
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

            season_df = df[df["league"] == league]
            season_df = filter_by_season_tokens(season_df, season)
            season_df, used_sources = apply_source_priority(
                season_df,
                dedupe_keys=["league", "season", "date", "home_team", "away_team"],
            )

            home_mask = season_df["home_team"] == team
            away_mask = season_df["away_team"] == team
            team_matches = season_df[home_mask | away_mask].sort_values("date")

            if team_matches.empty:
                return QueryPayload(
                    intent=IntentClass.FORM_ANALYSIS,
                    engine_data={},
                    partial=True,
                    error=f"No finished matches found for {team} in {league} {season}.",
                )

            records = []
            for _, row in team_matches.iterrows():
                is_home = row["home_team"] == team
                gf = int(row["home_goals"] if is_home else row["away_goals"])
                ga = int(row["away_goals"] if is_home else row["home_goals"])
                xg = float(row["home_xg"] if is_home else row["away_xg"])
                xga = float(row["away_xg"] if is_home else row["home_xg"])
                opponent = row["away_team"] if is_home else row["home_team"]
                venue = "home" if is_home else "away"
                result = "W" if gf > ga else ("D" if gf == ga else "L")
                records.append({
                    "date": str(row["date"].date()),
                    "opponent": opponent,
                    "venue": venue,
                    "gf": gf,
                    "ga": ga,
                    "xg": round(xg, 2),
                    "xga": round(xga, 2),
                    "result": result,
                })

            recent = records[-FORM_WINDOW:]
            form_string = "".join(r["result"] for r in recent)

            wins = sum(1 for r in records if r["result"] == "W")
            draws = sum(1 for r in records if r["result"] == "D")
            losses = sum(1 for r in records if r["result"] == "L")

            home_records = [r for r in records if r["venue"] == "home"]
            away_records = [r for r in records if r["venue"] == "away"]

            home_wins = sum(1 for r in home_records if r["result"] == "W")
            away_wins = sum(1 for r in away_records if r["result"] == "W")

            avg_xg = round(sum(r["xg"] for r in records) / len(records), 2) if records else 0.0
            avg_xga = round(sum(r["xga"] for r in records) / len(records), 2) if records else 0.0

            return QueryPayload(
                intent=IntentClass.FORM_ANALYSIS,
                engine_data={
                    "team": team,
                    "league": league,
                    "season": season,
                    "matches_played": len(records),
                    "wins": wins,
                    "draws": draws,
                    "losses": losses,
                    "home_wins": home_wins,
                    "home_played": len(home_records),
                    "away_wins": away_wins,
                    "away_played": len(away_records),
                    "avg_xg": avg_xg,
                    "avg_xga": avg_xga,
                    "recent_form": form_string,
                    "recent_matches": recent,
                    "all_matches": records,
                    "source_coverage": source_coverage_metadata(
                        intent=IntentClass.FORM_ANALYSIS.value,
                        used_sources=used_sources,
                    ),
                },
                partial=False,
                error=None,
            )
        except Exception as exc:
            _logger.exception("FormHandler failed: %s", exc)
            return QueryPayload(
                intent=IntentClass.FORM_ANALYSIS,
                engine_data={},
                partial=True,
                error=str(exc),
            )
