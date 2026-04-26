from __future__ import annotations

import os
from pathlib import Path



_BUILD_ROOT = Path(__file__).resolve().parents[6]
_env_data_dir = os.environ.get('XGGAFFER_DATA_DIR')
DATA_DIR = Path(_env_data_dir) if _env_data_dir else _BUILD_ROOT / 'data'

RAW_DIR = DATA_DIR / 'raw' / 'understat'
PROCESSED_DIR = DATA_DIR / 'processed'
MODELS_DIR = DATA_DIR / 'models'


RANDOM_SEED = 42

DEFAULT_LEAGUES: list[str] = ['EPL', 'La_Liga', 'Bundesliga', 'Serie_A', 'Ligue_1']

DEFAULT_SEASONS: list[str] = [
    '2014', '2015', '2016', '2017', '2018', '2019',
    '2020', '2021', '2022', '2023', '2024', '2025',
]

TEST_SEASONS: list[str] = ['2025']
DEMO_LEAGUE = 'EPL'
DEMO_SEASON = '2025'


MODEL_VERSION = 'v2'
DEFAULT_MODEL_TYPE = 'logistic_regression'
INTERPRETABLE_MODEL_TYPE = 'logistic_regression'
FRONTEND_CONTRACT_VERSION = 'v1'
DEFAULT_TOP_FACTORS = 5

PREDICTION_LABEL_MAP = {
    'H': 'Home',
    'D': 'Draw',
    'A': 'Away',
}

PROBABILITY_KEY_MAP = {
    'H': 'home',
    'D': 'draw',
    'A': 'away',
}

ARTIFACT_REQUIRED_KEYS = [
    'model',
    'feature_columns',
    'model_type',
    'metrics',
    'training_info',
    'version',
]



def model_artifact_glob(model_type: str | None = None) -> str:
    if model_type:
        return f'match_outcome_{model_type}_*.joblib'
    return 'match_outcome_*.joblib'


def resolve_latest_model_path(
    model_type: str | None = None,
    *,
    strict: bool = True,
) -> Path | None:
    pattern = model_artifact_glob(model_type)
    model_files = sorted(MODELS_DIR.glob(pattern), key=lambda f: f.stat().st_mtime)

    if model_type and '_with_odds' not in model_type:
        model_files = [
            path for path in model_files
            if '_with_odds_' not in path.name
        ]

    if model_files:
        return model_files[-1]

    if strict:
        if model_type:
            raise FileNotFoundError(
                f"No {model_type} model artifacts found in {MODELS_DIR}. "
                f"Train {model_type} first."
            )
        raise FileNotFoundError(f"No model artifacts found in {MODELS_DIR}")

    return None


def is_interpretable_model_type(model_type: str) -> bool:
    return model_type == INTERPRETABLE_MODEL_TYPE
