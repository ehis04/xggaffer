from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from ml.engines.elo import INITIAL_RATING
from ml.features.rolling import (
    build_features,
    load_match_history,
    to_team_match_rows,
)
from ml.models.match_outcome.config import (
    DEFAULT_LEAGUES,
    DEFAULT_SEASONS,
    INTERPRETABLE_MODEL_TYPE,
    PROCESSED_DIR,
    resolve_latest_model_path,
)
from ml.models.match_outcome.prepare_data import FEATURE_COLUMNS


ELO_RATINGS_PATH = PROCESSED_DIR / "elo_ratings.csv"

_current_elo_cache: dict[str, float] | None = None


def _load_current_elo_ratings() -> dict[str, float]:
    global _current_elo_cache
    if _current_elo_cache is not None:
        return _current_elo_cache

    if not ELO_RATINGS_PATH.exists():
        _current_elo_cache = {}
        return _current_elo_cache

    elo = pd.read_csv(ELO_RATINGS_PATH)

    ratings: dict[str, float] = {}

    for _, row in elo.iterrows():
        ratings[row["home_team"]] = row["home_elo_after"]
        ratings[row["away_team"]] = row["away_elo_after"]

    _current_elo_cache = ratings
    return _current_elo_cache


def get_current_elo(team: str) -> float:
    ratings = _load_current_elo_ratings()
    return ratings.get(team, float(INITIAL_RATING))


def _load_cached_features(match_id: str) -> dict | None:
    try:
        from predictions.models import MatchFeature
        row = MatchFeature.objects.filter(match_id=str(match_id)).first()
        if row is not None:
            return row.features
    except Exception:
        pass
    return None


def _save_cached_features(
    match_id: str,
    features: dict,
    home_team: str,
    away_team: str,
    league: str,
    season: str,
    date: str | None = None,
) -> None:
    try:
        from predictions.models import MatchFeature
        MatchFeature.objects.update_or_create(
            match_id=str(match_id),
            defaults={
                "season": str(season),
                "league": str(league),
                "date": date,
                "home_team": home_team,
                "away_team": away_team,
                "features": features,
            },
        )
    except Exception:
        pass


class FeatureService:
    def __init__(
        self,
        leagues: list[str] | None = None,
        seasons: list[str] | None = None,
    ):
        self.leagues = [str(lg) for lg in (leagues or DEFAULT_LEAGUES)]
        self.seasons = [str(s) for s in (seasons or DEFAULT_SEASONS)]
        self._matches: pd.DataFrame | None = None
        self._team_matches: pd.DataFrame | None = None

    def _ensure_loaded(self) -> None:
        if self._matches is None:
            self._matches = load_match_history(self.leagues, self.seasons)
            self._team_matches = to_team_match_rows(self._matches)

    @property
    def matches(self) -> pd.DataFrame:
        self._ensure_loaded()
        return self._matches

    @property
    def team_matches(self) -> pd.DataFrame:
        self._ensure_loaded()
        return self._team_matches

    def reload(
        self,
        leagues: list[str] | None = None,
        seasons: list[str] | None = None,
    ) -> None:
        self.leagues = [str(lg) for lg in (leagues or self.leagues)]
        self.seasons = [str(s) for s in (seasons or self.seasons)]
        self._matches = None
        self._team_matches = None

    def get_available_teams(
        self,
        league: str | None = None,
        season: str | None = None,
    ) -> list[str]:
        df = self.matches
        if league is not None:
            df = df[df["league"] == str(league)]
        if season is not None:
            df = df[df["season"] == str(season)]
        return sorted(
            set(df["home_team"].tolist() + df["away_team"].tolist())
        )

    def build_prediction_features(
        self,
        home_team: str,
        away_team: str,
        league: str,
        season: str,
        as_of: datetime | pd.Timestamp | None = None,
        match_id: str | int | None = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        league = str(league)
        season = str(season)

        if home_team == away_team:
            raise ValueError("Home and away teams must be different.")

        if use_cache and match_id is not None:
            cached = _load_cached_features(match_id)
            if cached is not None:
                available = [c for c in FEATURE_COLUMNS if c in cached]
                if len(available) == len(FEATURE_COLUMNS):
                    return pd.DataFrame([{c: cached[c] for c in FEATURE_COLUMNS}])

        self._ensure_loaded()

        if as_of is None:
            as_of = pd.Timestamp.now(tz=None)
        elif isinstance(as_of, datetime):
            as_of = pd.Timestamp(as_of).tz_localize(None)
        else:
            as_of = pd.Timestamp(as_of)
            if as_of.tzinfo is not None:
                as_of = as_of.tz_localize(None)

        available_teams = self.get_available_teams(league=league, season=season)
        if home_team not in available_teams:
            raise ValueError(
                f"No data for {home_team} in {league} {season}. "
                f"Available: {available_teams[:10]}"
            )
        if away_team not in available_teams:
            raise ValueError(
                f"No data for {away_team} in {league} {season}. "
                f"Available: {available_teams[:10]}"
            )

        feature_dict = build_features(
            match_id=match_id or 0,
            home_team=home_team,
            away_team=away_team,
            kickoff=as_of,
            all_matches=self._matches,
            all_team_matches=self._team_matches,
        )

        home_elo = get_current_elo(home_team)
        away_elo = get_current_elo(away_team)
        feature_dict["home_elo"] = home_elo
        feature_dict["away_elo"] = away_elo
        feature_dict["elo_difference"] = home_elo - away_elo

        missing = [c for c in FEATURE_COLUMNS if c not in feature_dict]
        if missing:
            raise ValueError(
                f"Could not compute the full feature set. Missing: {missing}"
            )

        features = pd.DataFrame([{c: feature_dict[c] for c in FEATURE_COLUMNS}])

        if features.isnull().any().any():
            null_cols = features.columns[features.isnull().any()].tolist()
            raise ValueError(
                f"Prediction features contain null values: {null_cols}"
            )

        if use_cache and match_id is not None:
            _save_cached_features(
                match_id=match_id,
                features=feature_dict,
                home_team=home_team,
                away_team=away_team,
                league=league,
                season=season,
            )

        return features


_service_cache: dict[tuple[tuple[str, ...], tuple[str, ...]], FeatureService] = {}


def _cache_key(
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return (
        tuple(str(lg) for lg in (leagues or DEFAULT_LEAGUES)),
        tuple(str(s) for s in (seasons or DEFAULT_SEASONS)),
    )


def get_feature_service(
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
    *,
    force_reload: bool = False,
) -> FeatureService:
    key = _cache_key(leagues, seasons)

    if force_reload or key not in _service_cache:
        _service_cache[key] = FeatureService(
            leagues=list(key[0]),
            seasons=list(key[1]),
        )

    return _service_cache[key]


def predict_match(
    home_team: str,
    away_team: str,
    league: str,
    season: str,
) -> dict:
    from ml.models.match_outcome.predict import get_predictor

    service = get_feature_service(leagues=[league], seasons=[season])
    features = service.build_prediction_features(
        home_team, away_team, league, season,
    )

    model_path = resolve_latest_model_path(INTERPRETABLE_MODEL_TYPE)
    predictor = get_predictor(model_path=model_path)
    result = predictor.predict(features)

    result["home_team"] = home_team
    result["away_team"] = away_team
    result["league"] = str(league)
    result["season"] = str(season)

    return result