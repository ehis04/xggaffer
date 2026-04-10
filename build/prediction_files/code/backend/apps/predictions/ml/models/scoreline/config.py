from __future__ import annotations

from ml.models.match_outcome.config import (
    DATA_DIR,
    MODELS_DIR,
    PROCESSED_DIR,
    RANDOM_SEED,
    TEST_SEASONS,
)


SCORE_ENGINE_LEAGUES: list[str] = [
    "EPL", "La_Liga", "Bundesliga", "Serie_A", "Ligue_1",
]

SCORE_ENGINE_SEASONS: list[str] = [str(y) for y in range(2014, 2025)]

MAX_GOALS = 6
DEFAULT_TIME_DECAY_RATE = 0.01
DEFAULT_RHO_BOUNDS = (-0.3, 0.3)
NAIVE_HOME_GOALS_RATE = 1.5
NAIVE_AWAY_GOALS_RATE = 1.2

HOME_GOALS_FEATURES: list[str] = [
    "home_rolling_xg_10",
    "away_rolling_xga_10",
    "elo_difference",
]

AWAY_GOALS_FEATURES: list[str] = [
    "away_rolling_xg_10",
    "home_rolling_xga_10",
    "elo_difference",
]