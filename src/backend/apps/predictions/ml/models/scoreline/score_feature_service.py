from __future__ import annotations

import pandas as pd

from apps.predictions.ml.engines.elo import compute_elo_history, get_elo_at_date
from apps.predictions.ml.features.rolling import (
    build_features,
    load_match_history,
    to_team_match_rows,
)
from apps.predictions.ml.models.scoreline.config import SCORE_ENGINE_LEAGUES, SCORE_ENGINE_SEASONS


class ScoreFeatureService:

    def __init__(
        self,
        leagues: list[str] | None = None,
        seasons: list[str] | None = None,
    ):
        self.leagues = leagues or SCORE_ENGINE_LEAGUES
        self.seasons = seasons or SCORE_ENGINE_SEASONS
        self._matches: pd.DataFrame | None = None
        self._team_matches: pd.DataFrame | None = None
        self._elo_history_df: pd.DataFrame | None = None

    def _ensure_loaded(self) -> None:
        if self._matches is None:
            self._matches = load_match_history(self.leagues, self.seasons)
            self._team_matches = to_team_match_rows(self._matches)
            elo_history, _ = compute_elo_history(self._matches)
            self._elo_history_df = pd.DataFrame(elo_history)
            self._elo_history_df["date"] = pd.to_datetime(self._elo_history_df["date"])

    def build_prediction_features(
        self,
        home_team: str,
        away_team: str,
        league: str,
        season: str,
    ) -> pd.DataFrame:
        self._ensure_loaded()

        kickoff = pd.Timestamp.now().normalize()

        match_features = build_features(
            match_id=-1,
            home_team=home_team,
            away_team=away_team,
            kickoff=kickoff,
            all_matches=self._matches,
            all_team_matches=self._team_matches,
        )

        home_elo = get_elo_at_date(self._elo_history_df, home_team, kickoff)
        away_elo = get_elo_at_date(self._elo_history_df, away_team, kickoff)
        match_features["elo_difference"] = home_elo - away_elo

        return pd.DataFrame([match_features])

    def get_available_teams(
        self,
        league: str | None = None,
        season: str | None = None,
    ) -> list[str]:
        self._ensure_loaded()
        df = self._matches
        if league is not None:
            df = df[df["league"] == league]
        if season is not None:
            df = df[df["season"] == str(season)]
        teams = set(df["home_team"].unique()) | set(df["away_team"].unique())
        return sorted(teams)


_cache: dict[tuple, ScoreFeatureService] = {}


def get_score_feature_service(
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
    force_reload: bool = False,
) -> ScoreFeatureService:
    key = (
        tuple(leagues or SCORE_ENGINE_LEAGUES),
        tuple(seasons or SCORE_ENGINE_SEASONS),
    )
    if force_reload or key not in _cache:
        _cache[key] = ScoreFeatureService(leagues=list(key[0]), seasons=list(key[1]))
    return _cache[key]