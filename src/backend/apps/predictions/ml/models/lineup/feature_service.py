from __future__ import annotations

import ast
import json
import logging
import threading
from pathlib import Path

import pandas as pd

from .config import DATA_DIR, DEFAULT_LEAGUES, DEFAULT_SEASONS

logger = logging.getLogger(__name__)

FEATURES_CSV = DATA_DIR / 'processed' / 'lineup_features.csv'
RAW_UNDERSTAT_DIR = DATA_DIR / 'raw' / 'understat'

_cache: dict = {}
_cache_lock = threading.Lock()


def _load_features() -> pd.DataFrame:
    if 'df' in _cache:
        return _cache['df']

    with _cache_lock:
        if 'df' in _cache:
            return _cache['df']

        if not FEATURES_CSV.exists():
            raise FileNotFoundError(
                f'Lineup features cache not found at {FEATURES_CSV}. '
                'Run build_lineup_dataset(save=True) first.'
            )

        logger.info("Loading lineup_features.csv (~500 MB) — this happens once per process")
        df = pd.read_csv(FEATURES_CSV, parse_dates=['date'])
        _cache['df'] = df
        logger.info("lineup_features.csv loaded: %d rows", len(df))
        return df


def _load_team_id_lookup() -> dict[tuple[str, int, str], int]:
    """Return {(league, season_int, team_name): team_id} from Understat raw teams CSVs."""
    if 'team_id_lookup' in _cache:
        return _cache['team_id_lookup']

    lookup: dict[tuple[str, int, str], int] = {}
    if not RAW_UNDERSTAT_DIR.exists():
        return lookup

    for season_dir in RAW_UNDERSTAT_DIR.iterdir():
        if not season_dir.is_dir():
            continue
        try:
            season_int = int(season_dir.name)
        except ValueError:
            continue
        for path in season_dir.glob('understat_teams_*_raw.csv'):
            parts = path.stem.split('_')  # ['understat','teams','La','Liga','2025','raw']
            league = '_'.join(parts[2:-2])
            try:
                df = pd.read_csv(path)
                for _, row in df.iterrows():
                    try:
                        team_id = int(row['source_team_id'])
                        raw = row['team_info']
                        if isinstance(raw, dict):
                            d = raw
                        else:
                            try:
                                d = ast.literal_eval(str(raw))
                            except Exception:
                                continue
                        name = d.get('title', '')
                        if name:
                            lookup[(league, season_int, name)] = team_id
                    except Exception:
                        continue
            except Exception:
                continue

    _cache['team_id_lookup'] = lookup
    return lookup


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

    # The pipeline can swap team names in the features CSV when the home/away
    # heuristic is wrong.  Cross-check: if the most common team_id for the
    # matched rows doesn't match the canonical team_id from Understat, re-query
    # by team_id instead so we always return the correct players.
    lookup = _load_team_id_lookup()
    canonical_id = lookup.get((league, season_int, team_name))
    if canonical_id is not None:
        actual_id = int(team_data['team_id'].mode().iloc[0])
        if actual_id != canonical_id:
            logger.warning(
                'team_name "%s" maps to team_id %d in features but canonical is %d; '
                'falling back to team_id lookup',
                team_name, actual_id, canonical_id,
            )
            team_data = df[
                (df['team_id'] == canonical_id) &
                (df['league'] == league) &
                (df['season'] == season_int)
            ]
            if team_data.empty:
                raise ValueError(
                    f'No data found for team "{team_name}" (id={canonical_id}) '
                    f'in {league} {season}'
                )

    latest_match_id = team_data.sort_values('date').iloc[-1]['match_id']
    latest_features = team_data[team_data['match_id'] == latest_match_id].copy()

    # Normalise team_name so predict_match_lineups keys on the requested name.
    latest_features['team_name'] = team_name

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