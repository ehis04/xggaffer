from __future__ import annotations

import os
from pathlib import Path


def _resolve_project_root() -> Path:
    current = Path(__file__).resolve()

    # Prefer the repository root layout: <root>/backend and <root>/data.
    # This avoids accidentally selecting nested app-local data folders.
    for parent in current.parents:
        if (parent / 'backend').exists() and (parent / 'data').exists():
            return parent

    for parent in current.parents:
        if (parent / 'data').exists():
            return parent
    fallback_index = min(6, len(current.parents) - 1)
    return current.parents[fallback_index]


_env_data_dir = os.environ.get('XGGAFFER_DATA_DIR')

if _env_data_dir:
    DATA_DIR = Path(_env_data_dir)
else:
    DATA_DIR = _resolve_project_root() / 'data'

RAW_DIR = DATA_DIR / 'raw'
LINEUP_DIR = RAW_DIR / 'lineups'
PROCESSED_DIR = DATA_DIR / 'processed'
MATCHES_CSV = PROCESSED_DIR / 'matches' / 'merged' / 'all_leagues_all_seasons_matches_merged.csv'
LEGACY_UNDERSTAT_MATCHES_CSV = RAW_DIR / 'understat' / 'merged' / 'all_leagues_all_seasons_matches.csv'
MODELS_DIR = DATA_DIR / 'models'

RANDOM_SEED = 42

DEFAULT_LEAGUES: list[str] = ['EPL', 'La_Liga', 'Bundesliga', 'Serie_A', 'Ligue_1']

DEFAULT_SEASONS: list[str] = [
    '2014', '2015', '2016', '2017', '2018', '2019',
    '2020', '2021', '2022', '2023', '2024', '2025',
]

DROPPED_PLAYER_THRESHOLD = 0.60

TEST_SEASONS: list[str] = ['2025']

REQUEST_DELAY_MIN = 0.5
REQUEST_DELAY_MAX = 1.5

LINEUP_COLUMNS: list[str] = [
    'match_id',
    'date',
    'season',
    'league',
    'team',
    'team_id',
    'player_id',
    'player_name',
    'position',
    'started',
    'minutes_played',
]

LINEUP_FEATURES_WORKLOAD: list[str] = [
    'minutes_last_match',
    'minutes_last_3_matches',
    'minutes_last_5_matches',
    'days_since_last_start',
    'days_since_last_appearance',
    'consecutive_starts',
    'started_last_match',
]

LINEUP_FEATURES_CONTEXT: list[str] = [
    'opponent_elo',
    'elo_difference',
    'is_home',
    'days_until_next_match',
    'season_phase',
]

LINEUP_FEATURES_PROFILE: list[str] = [
    'player_age',
    'squad_role',
    'player_quality_proxy',
]

LINEUP_FEATURES_MANAGER: list[str] = [
    'manager_avg_changes',
    'player_start_rate',
]

LINEUP_FEATURES_POSITION: list[str] = [
    'is_gk',
    'is_def',
    'is_mid',
    'is_fwd',
]

TARGET = 'started'

XGBOOST_PARAMS: dict = {
    'max_depth': 5,
    'n_estimators': 200,
    'learning_rate': 0.05,
    'min_child_weight': 5,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'random_state': RANDOM_SEED,
    'eval_metric': 'logloss',
}

POSITION_CATEGORY_MAP: dict[str, str] = {
    'GK': 'GK',
    'DC': 'DEF', 'DR': 'DEF', 'DL': 'DEF',
    'DMC': 'MID', 'MC': 'MID', 'AMC': 'MID', 'AML': 'MID', 'AMR': 'MID', 'ML': 'MID', 'MR': 'MID',
    'FW': 'FWD', 'FWL': 'FWD', 'FWR': 'FWD',
    'Sub': 'SUB',
}

FORMATION_SLOTS: dict[str, dict[str, int]] = {
    '4-3-3': {'GK': 1, 'DEF': 4, 'MID': 3, 'FWD': 3},
    '4-4-2': {'GK': 1, 'DEF': 4, 'MID': 4, 'FWD': 2},
    '3-5-2': {'GK': 1, 'DEF': 3, 'MID': 5, 'FWD': 2},
    '4-2-3-1': {'GK': 1, 'DEF': 4, 'MID': 5, 'FWD': 1},
    '3-4-3': {'GK': 1, 'DEF': 3, 'MID': 4, 'FWD': 3},
    '4-1-4-1': {'GK': 1, 'DEF': 4, 'MID': 5, 'FWD': 1},
    '5-3-2': {'GK': 1, 'DEF': 5, 'MID': 3, 'FWD': 2},
    '5-4-1': {'GK': 1, 'DEF': 5, 'MID': 4, 'FWD': 1},
}