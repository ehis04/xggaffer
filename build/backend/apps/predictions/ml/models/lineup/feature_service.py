from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .config import DATA_DIR, DEFAULT_LEAGUES, DEFAULT_SEASONS

logger = logging.getLogger(__name__)

FEATURES_CSV = DATA_DIR / 'processed' / 'lineup_features.csv'

_cache: dict = {}


def _load_features() -> pd.DataFrame:
    if 'df' in _cache:
        return _cache['df']

    if not FEATURES_CSV.exists():
        raise FileNotFoundError(
            f'Lineup features cache not found at {FEATURES_CSV}. '
            'Run build_lineup_dataset(save=True) first.'
        )

    df = pd.read_csv(FEATURES_CSV, parse_dates=['date'])
    _cache['df'] = df
    return df


def clear_cache() -> None:
    _cache.clear()


def get_available_teams(league: str, season: str) -> list[str]:
    df = _load_features()
    season_int = int(season)
    subset = df[(df['league'] == league) & (df['season'] == season_int)]
    teams = sorted(subset['team_name'].dropna().unique().tolist())
    return teams


def get_latest_team_features(
    team_name: str,
    league: str,
    season: str,
) -> pd.DataFrame:
    df = _load_features()
    season_int = int(season)

    team_data = df[
        (df['team_name'] == team_name) &
        (df['league'] == league) &
        (df['season'] == season_int)
    ]

    if team_data.empty:
        raise ValueError(
            f'No data found for team "{team_name}" in {league} {season}'
        )

    latest_match_id = team_data.sort_values('date').iloc[-1]['match_id']
    latest_features = team_data[team_data['match_id'] == latest_match_id].copy()

    return latest_features


def get_team_match_features(
    team_name: str,
    match_id: int,
) -> pd.DataFrame:
    df = _load_features()

    match_data = df[
        (df['team_name'] == team_name) &
        (df['match_id'] == match_id)
    ]

    if match_data.empty:
        raise ValueError(
            f'No data found for team "{team_name}" in match {match_id}'
        )

    return match_data.copy()