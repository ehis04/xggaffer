from __future__ import annotations

import pandas as pd

from apps.predictions.ml.engines.elo import compute_elo_history, get_elo_at_date
from apps.predictions.ml.features.rolling import (
    build_all_features,
    compute_team_rolling_features,
    load_match_history,
    to_team_match_rows,
)
from apps.predictions.ml.models.scoreline.config import (
    AWAY_GOALS_FEATURES,
    HOME_GOALS_FEATURES,
)
from apps.predictions.ml.models.simulation.config import MATCHES_PER_MATCHWEEK


SCORE_FEATURE_COLUMNS = sorted(
    set(HOME_GOALS_FEATURES + AWAY_GOALS_FEATURES)
)

FALLBACK_XG = 1.35
FALLBACK_XGA = 1.35


def split_season(
    all_matches_df: pd.DataFrame,
    season: str,
    league: str,
    freeze_matchweek: int | None = None,
    freeze_date: pd.Timestamp | None = None,
) -> tuple[list[dict], list[dict], pd.DataFrame]:
    season_matches = all_matches_df[
        (all_matches_df["season"].astype(str) == str(season))
        & (all_matches_df["league"] == league)
    ].sort_values("date").reset_index(drop=True)

    if freeze_date is not None:
        played = season_matches[season_matches["date"] < freeze_date]
        remaining = season_matches[season_matches["date"] >= freeze_date]
    elif freeze_matchweek is not None:
        cutoff_idx = freeze_matchweek * MATCHES_PER_MATCHWEEK
        played = season_matches.iloc[:cutoff_idx]
        remaining = season_matches.iloc[cutoff_idx:]
    else:
        raise ValueError("Must specify freeze_date or freeze_matchweek")

    actual_results = played[
        ["home_team", "away_team", "home_goals", "away_goals"]
    ].to_dict("records")

    remaining_fixtures = remaining[
        ["home_team", "away_team"]
    ].to_dict("records")

    return actual_results, remaining_fixtures, remaining


def prepare_fixture_features(
    all_matches_df: pd.DataFrame,
    remaining_df: pd.DataFrame,
    freeze_date: pd.Timestamp,
) -> pd.DataFrame:
    historical = all_matches_df[
        all_matches_df["date"] < freeze_date
    ].copy()

    historical_sorted = historical.sort_values("date")
    elo_history_list, current_elos = compute_elo_history(historical_sorted)
    elo_history_df = pd.DataFrame(elo_history_list)
    if "date" in elo_history_df.columns:
        elo_history_df["date"] = pd.to_datetime(elo_history_df["date"])

    team_matches = to_team_match_rows(historical)

    rows = []
    for _, fixture in remaining_df.iterrows():
        home = fixture["home_team"]
        away = fixture["away_team"]

        home_history = team_matches[
            team_matches["team"] == home
        ].sort_values("date")
        away_history = team_matches[
            team_matches["team"] == away
        ].sort_values("date")

        home_feats = compute_team_rolling_features(home_history, freeze_date)
        away_feats = compute_team_rolling_features(away_history, freeze_date)

        home_elo = current_elos.get(home, 1500)
        away_elo = current_elos.get(away, 1500)

        rows.append({
            "home_team": home,
            "away_team": away,
            "home_rolling_xg_10": home_feats.get(
                "rolling_xg_10", FALLBACK_XG,
            ),
            "away_rolling_xga_10": away_feats.get(
                "rolling_xga_10", FALLBACK_XGA,
            ),
            "away_rolling_xg_10": away_feats.get(
                "rolling_xg_10", FALLBACK_XG,
            ),
            "home_rolling_xga_10": home_feats.get(
                "rolling_xga_10", FALLBACK_XGA,
            ),
            "elo_difference": home_elo - away_elo,
        })

    return pd.DataFrame(rows)


def prepare_fixture_features_fast(
    precomputed_features: pd.DataFrame,
    elo_history_df: pd.DataFrame,
    remaining_df: pd.DataFrame,
    freeze_date: pd.Timestamp,
) -> pd.DataFrame:
    pre = precomputed_features[
        precomputed_features["date"] < freeze_date
    ].copy()

    latest_home = {}
    latest_away = {}

    for team in set(remaining_df["home_team"]).union(remaining_df["away_team"]):
        home_rows = pre[pre["home_team"] == team].sort_values("date")
        if not home_rows.empty:
            latest_home[team] = home_rows.iloc[-1]

        away_rows = pre[pre["away_team"] == team].sort_values("date")
        if not away_rows.empty:
            latest_away[team] = away_rows.iloc[-1]

    rows = []
    for _, fixture in remaining_df.iterrows():
        home = fixture["home_team"]
        away = fixture["away_team"]

        home_as_home = latest_home.get(home)
        away_as_away = latest_away.get(away)

        home_xg_10 = (
            float(home_as_home["home_rolling_xg_10"])
            if home_as_home is not None
            and "home_rolling_xg_10" in home_as_home.index
            and pd.notna(home_as_home["home_rolling_xg_10"])
            else FALLBACK_XG
        )

        home_xga_10 = (
            float(home_as_home["home_rolling_xga_10"])
            if home_as_home is not None
            and "home_rolling_xga_10" in home_as_home.index
            and pd.notna(home_as_home["home_rolling_xga_10"])
            else FALLBACK_XGA
        )

        away_xg_10 = (
            float(away_as_away["away_rolling_xg_10"])
            if away_as_away is not None
            and "away_rolling_xg_10" in away_as_away.index
            and pd.notna(away_as_away["away_rolling_xg_10"])
            else FALLBACK_XG
        )

        away_xga_10 = (
            float(away_as_away["away_rolling_xga_10"])
            if away_as_away is not None
            and "away_rolling_xga_10" in away_as_away.index
            and pd.notna(away_as_away["away_rolling_xga_10"])
            else FALLBACK_XGA
        )

        home_elo = get_elo_at_date(elo_history_df, home, freeze_date)
        away_elo = get_elo_at_date(elo_history_df, away, freeze_date)

        rows.append({
            "home_team": home,
            "away_team": away,
            "home_rolling_xg_10": home_xg_10,
            "away_rolling_xga_10": away_xga_10,
            "away_rolling_xg_10": away_xg_10,
            "home_rolling_xga_10": home_xga_10,
            "elo_difference": home_elo - away_elo,
        })

    return pd.DataFrame(rows)


def prepare_remaining_fixtures(
    all_matches_df: pd.DataFrame,
    season: str,
    league: str,
    freeze_matchweek: int | None = None,
    freeze_date: pd.Timestamp | None = None,
) -> tuple[list[dict], list[dict], pd.DataFrame]:
    actual_results, remaining_fixtures, remaining_df = split_season(
        all_matches_df, season, league,
        freeze_matchweek=freeze_matchweek,
        freeze_date=freeze_date,
    )

    if remaining_df.empty:
        return actual_results, remaining_fixtures, pd.DataFrame()

    effective_freeze = (
        freeze_date
        if freeze_date is not None
        else remaining_df["date"].iloc[0]
    )

    features = prepare_fixture_features(
        all_matches_df, remaining_df, effective_freeze,
    )

    return actual_results, remaining_fixtures, features