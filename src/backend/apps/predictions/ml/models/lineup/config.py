from __future__ import annotations

from apps.predictions.data_paths import DATA_ROOT


DATA_DIR = DATA_ROOT

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
    '4-5-1': {'GK': 1, 'DEF': 4, 'MID': 5, 'FWD': 1},
    '3-4-3': {'GK': 1, 'DEF': 3, 'MID': 4, 'FWD': 3},
    '4-1-4-1': {'GK': 1, 'DEF': 4, 'MID': 5, 'FWD': 1},
    '5-3-2': {'GK': 1, 'DEF': 5, 'MID': 3, 'FWD': 2},
    '5-4-1': {'GK': 1, 'DEF': 5, 'MID': 4, 'FWD': 1},
    '3-5-1-1': {'GK': 1, 'DEF': 3, 'MID': 6, 'FWD': 1},
    '4-3-2-1': {'GK': 1, 'DEF': 4, 'MID': 5, 'FWD': 1},
    '4-4-1-1': {'GK': 1, 'DEF': 4, 'MID': 5, 'FWD': 1},
}
