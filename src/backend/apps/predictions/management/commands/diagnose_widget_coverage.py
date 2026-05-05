from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand

from apps.predictions.ml.features.rolling import (
    LEGACY_MERGED_MATCHES_FILE,
    MERGED_MATCHES_FILE,
)
from apps.predictions.ml.models.lineup.feature_service import FEATURES_CSV
from apps.predictions.ml.models.match_outcome.config import DEFAULT_LEAGUES
from apps.predictions.services.availability_handler import PLAYERS_CSV_PATH


@dataclass(frozen=True)
class CoverageRow:
    league: str
    season: str
    match_teams: int
    lineup_teams: int
    availability_teams: int
    full_stack_teams: int


def _select_existing_path(primary: Path, fallback: Path | None = None) -> Path | None:
    if primary.exists():
        return primary
    if fallback and fallback.exists():
        return fallback
    return None


def _read_csv_or_empty(path: Path | None, usecols: list[str]) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame(columns=usecols)
    return pd.read_csv(path, usecols=lambda c: c in set(usecols), low_memory=False)


def _normalize_season(value: object) -> str:
    raw = str(value).strip()
    if raw.isdigit():
        number = int(raw)
        if number > 2100 and len(raw) == 4:
            return str(2000 + int(raw[:2]))
    return raw


class Command(BaseCommand):
    help = (
        "Diagnose prediction widget data coverage by league and season for "
        "match-prediction, predicted-lineup, and availability widgets."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--league",
            action="append",
            dest="leagues",
            help="League code to inspect (repeatable). Defaults to core leagues.",
        )
        parser.add_argument(
            "--season",
            action="append",
            dest="seasons",
            help="Season start year to inspect (repeatable). Defaults to detected seasons.",
        )
        parser.add_argument(
            "--team",
            action="append",
            dest="teams",
            help="Optional team name to verify against each widget source (repeatable).",
        )

    def handle(self, *args, **options):
        leagues = options.get("leagues") or list(DEFAULT_LEAGUES)
        explicit_seasons: list[str] | None = options.get("seasons")
        teams: list[str] = options.get("teams") or []

        match_path = _select_existing_path(MERGED_MATCHES_FILE, LEGACY_MERGED_MATCHES_FILE)
        lineup_path = _select_existing_path(FEATURES_CSV)
        availability_path = _select_existing_path(PLAYERS_CSV_PATH)

        self.stdout.write(self.style.NOTICE("Prediction Widget Coverage Diagnostics"))
        self.stdout.write(f"- match source: {match_path or 'MISSING'}")
        self.stdout.write(f"- lineup source: {lineup_path or 'MISSING'}")
        self.stdout.write(f"- availability source: {availability_path or 'MISSING'}")

        match_df = _read_csv_or_empty(
            match_path,
            ["league", "season", "home_team", "away_team"],
        )
        lineup_df = _read_csv_or_empty(
            lineup_path,
            ["league", "season", "team_name"],
        )
        availability_df = _read_csv_or_empty(
            availability_path,
            ["league", "season", "team"],
        )

        if not match_df.empty:
            match_df["league"] = match_df["league"].astype(str)
            match_df["season"] = match_df["season"].map(_normalize_season)
            match_df["home_team"] = match_df["home_team"].astype(str)
            match_df["away_team"] = match_df["away_team"].astype(str)

        if not lineup_df.empty:
            lineup_df["league"] = lineup_df["league"].astype(str)
            lineup_df["season"] = lineup_df["season"].map(_normalize_season)
            lineup_df["team_name"] = lineup_df["team_name"].astype(str)

        if not availability_df.empty:
            availability_df["league"] = availability_df["league"].astype(str)
            availability_df["season"] = availability_df["season"].map(_normalize_season)
            availability_df["team"] = availability_df["team"].astype(str)

        detected_seasons = sorted(
            set(match_df.get("season", pd.Series(dtype=str)).unique().tolist())
            | set(lineup_df.get("season", pd.Series(dtype=str)).unique().tolist())
            | set(availability_df.get("season", pd.Series(dtype=str)).unique().tolist())
        )

        seasons = explicit_seasons or detected_seasons
        if not seasons:
            self.stdout.write(self.style.WARNING("No seasons detected in any source."))
            return

        rows: list[CoverageRow] = []

        for league in leagues:
            for season in seasons:
                match_teams: set[str] = set()
                lineup_teams: set[str] = set()
                availability_teams: set[str] = set()

                if not match_df.empty:
                    m = match_df[
                        (match_df["league"] == league)
                        & (match_df["season"] == season)
                    ]
                    match_teams = set(m["home_team"].tolist()) | set(m["away_team"].tolist())

                if not lineup_df.empty:
                    l = lineup_df[
                        (lineup_df["league"] == league)
                        & (lineup_df["season"] == season)
                    ]
                    lineup_teams = set(l["team_name"].tolist())

                if not availability_df.empty:
                    a = availability_df[
                        (availability_df["league"] == league)
                        & (availability_df["season"] == season)
                    ]
                    availability_teams = set(a["team"].tolist())

                full_stack_teams = match_teams & lineup_teams & availability_teams

                rows.append(
                    CoverageRow(
                        league=league,
                        season=season,
                        match_teams=len(match_teams),
                        lineup_teams=len(lineup_teams),
                        availability_teams=len(availability_teams),
                        full_stack_teams=len(full_stack_teams),
                    )
                )

        if not rows:
            self.stdout.write(self.style.WARNING("No coverage rows computed."))
            return

        rows.sort(key=lambda r: (r.league, r.season), reverse=False)

        header = (
            "league       season   match_teams   lineup_teams   "
            "availability_teams   full_stack_teams"
        )
        self.stdout.write("\n" + header)
        self.stdout.write("-" * len(header))

        for row in rows:
            self.stdout.write(
                f"{row.league:<12} {row.season:<8} "
                f"{row.match_teams:>11} {row.lineup_teams:>14} "
                f"{row.availability_teams:>20} {row.full_stack_teams:>18}"
            )

        self.stdout.write("\nLatest season by component and league:")
        for league in leagues:
            latest_match = self._latest_season(match_df, "league", league)
            latest_lineup = self._latest_season(lineup_df, "league", league)
            latest_availability = self._latest_season(availability_df, "league", league)
            self.stdout.write(
                f"- {league}: match={latest_match or '-'} | "
                f"lineup={latest_lineup or '-'} | availability={latest_availability or '-'}"
            )

        if teams:
            self.stdout.write("\nTeam presence checks:")
            for team in teams:
                self.stdout.write(f"- {team}")
                for league in leagues:
                    for season in seasons:
                        has_match = self._team_in_match_source(match_df, team, league, season)
                        has_lineup = self._team_in_column_source(
                            lineup_df, team, league, season, "team_name"
                        )
                        has_availability = self._team_in_column_source(
                            availability_df, team, league, season, "team"
                        )
                        if has_match or has_lineup or has_availability:
                            self.stdout.write(
                                f"  {league} {season}: "
                                f"match={'yes' if has_match else 'no'}, "
                                f"lineup={'yes' if has_lineup else 'no'}, "
                                f"availability={'yes' if has_availability else 'no'}"
                            )

        self._print_recommendations(
            leagues=leagues,
            seasons=seasons,
            rows=rows,
            match_df=match_df,
            lineup_df=lineup_df,
            availability_df=availability_df,
        )

    @staticmethod
    def _latest_season(df: pd.DataFrame, league_column: str, league: str) -> str | None:
        if df.empty:
            return None
        subset = df[df[league_column] == league]
        if subset.empty:
            return None
        seasons = [s for s in subset["season"].astype(str).tolist() if s]
        if not seasons:
            return None
        seasons_sorted = sorted(seasons, key=lambda s: int(s) if s.isdigit() else -1)
        return seasons_sorted[-1]

    @staticmethod
    def _team_in_match_source(
        df: pd.DataFrame,
        team: str,
        league: str,
        season: str,
    ) -> bool:
        if df.empty:
            return False
        subset = df[(df["league"] == league) & (df["season"] == season)]
        if subset.empty:
            return False
        return bool(
            (subset["home_team"].str.lower() == team.lower()).any()
            or (subset["away_team"].str.lower() == team.lower()).any()
        )

    @staticmethod
    def _team_in_column_source(
        df: pd.DataFrame,
        team: str,
        league: str,
        season: str,
        team_column: str,
    ) -> bool:
        if df.empty:
            return False
        subset = df[(df["league"] == league) & (df["season"] == season)]
        if subset.empty:
            return False
        return bool((subset[team_column].str.lower() == team.lower()).any())

    def _print_recommendations(
        self,
        *,
        leagues: list[str],
        seasons: list[str],
        rows: list[CoverageRow],
        match_df: pd.DataFrame,
        lineup_df: pd.DataFrame,
        availability_df: pd.DataFrame,
    ) -> None:
        self.stdout.write("\nRecommended next actions:")

        action_lines: list[str] = []

        for league in leagues:
            latest_match = self._latest_season(match_df, "league", league)
            latest_lineup = self._latest_season(lineup_df, "league", league)
            latest_availability = self._latest_season(availability_df, "league", league)

            latest_by_component = {
                "match": latest_match,
                "lineup": latest_lineup,
                "availability": latest_availability,
            }
            latest_values = [
                self._as_int_season(value)
                for value in latest_by_component.values()
                if self._as_int_season(value) is not None
            ]
            if not latest_values:
                continue
            expected_latest = max(latest_values)

            # Match source lag recommendations
            if self._as_int_season(latest_match) is None or self._as_int_season(latest_match) < expected_latest:
                action_lines.append(
                    f"- {league}: match source lags latest season; sync and rebuild merged matches:\n"
                    f"  python3 manage.py sync_understat_league_season --league-code {league} --season {expected_latest}\n"
                    "  python3 manage.py export_merged_views --layer processed --dataset matches"
                )

            # Availability source lag recommendations
            if self._as_int_season(latest_availability) is None or self._as_int_season(latest_availability) < expected_latest:
                action_lines.append(
                    f"- {league}: availability source lags latest season; refresh player merges:\n"
                    f"  python3 manage.py sync_understat_league_season --league-code {league} --season {expected_latest}\n"
                    "  python3 manage.py export_merged_views --layer processed --dataset players"
                )

            # Lineup source lag recommendations
            if self._as_int_season(latest_lineup) is None or self._as_int_season(latest_lineup) < expected_latest:
                action_lines.append(
                    f"- {league}: lineup source lags latest season; rebuild lineup features/model:\n"
                    "  python3 -m apps.predictions.ml.models.lineup.train\n"
                    "  python3 manage.py bootstrap_predictions_snapshot"
                )

        # Check explicit season slices for zero full-stack coverage and suggest end-to-end steps.
        for league in leagues:
            for season in seasons:
                row = next(
                    (r for r in rows if r.league == league and r.season == season),
                    None,
                )
                if row is None:
                    continue
                if row.full_stack_teams == 0 and (
                    row.match_teams > 0 or row.lineup_teams > 0 or row.availability_teams > 0
                ):
                    action_lines.append(
                        f"- {league} {season}: zero full-stack coverage across widgets. Run a focused refresh:\n"
                        f"  python3 manage.py sync_understat_league_season --league-code {league} --season {season}\n"
                        "  python3 manage.py export_merged_views --layer processed --dataset matches --dataset players\n"
                        "  python3 -m apps.predictions.ml.models.lineup.train\n"
                        "  python3 manage.py bootstrap_predictions_snapshot"
                    )

        if not action_lines:
            self.stdout.write("- No seasonal lag detected between match/lineup/availability sources.")
            return

        # Deduplicate while preserving order.
        seen: set[str] = set()
        for line in action_lines:
            if line in seen:
                continue
            seen.add(line)
            self.stdout.write(line)

    @staticmethod
    def _as_int_season(season: str | None) -> int | None:
        if season is None:
            return None
        value = str(season).strip()
        if not value.isdigit():
            return None
        return int(value)
