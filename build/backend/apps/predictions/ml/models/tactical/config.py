from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from apps.predictions.ml.models.lineup.config import DATA_DIR, MODELS_DIR, RANDOM_SEED


RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

STATSBOMB_RAW_DIR = RAW_DIR / "statsbomb"
STATSBOMB_CHECKPOINT_DIR = STATSBOMB_RAW_DIR / "checkpoints"
WHOSCORED_RAW_DIR = RAW_DIR / "whoscored"
WHOSCORED_CHECKPOINT_DIR = WHOSCORED_RAW_DIR / "checkpoints"

PASS_EVENTS_PATH = PROCESSED_DIR / "pass_events.csv"
ZONE_PROFILES_PATH = PROCESSED_DIR / "team_zone_profiles.csv"
ZONE_STATS_PATH = PROCESSED_DIR / "zone_stats.csv"

ZONE_COLS = 6
ZONE_ROWS = 4
ZONE_COUNT = ZONE_COLS * ZONE_ROWS

PITCH_LENGTH = 120.0
PITCH_WIDTH = 80.0
ZONE_COL_WIDTH = PITCH_LENGTH / ZONE_COLS
ZONE_ROW_HEIGHT = PITCH_WIDTH / ZONE_ROWS

MIN_PASSES_FOR_ZONE = 3

MAX_GOAL_DIFF_CLIP = 2

PASS_EVENT_TYPE = "Pass"

INCOMPLETE_PASS_OUTCOMES = {
    "Incomplete",
    "Out",
    "Unknown",
    "Pass Offside",
    "Injury Clearance",
}

PASS_HEIGHT_ENCODING = {
    "Ground Pass": 0,
    "Low Pass": 1,
    "High Pass": 2,
}

RARE_TECHNIQUE_THRESHOLD = 0.01
RARE_CATEGORY_LABEL = "Other"

STATSBOMB_COMPETITIONS = [
    {"competition_id": 11, "competition_name": "La Liga"},
    {"competition_id": 16, "competition_name": "Champions League"},
]

PASS_FEATURES = [
    "zone_id",
    "zone_col",
    "zone_row",
    "end_zone_id",
    "pass_length",
    "pass_angle",
    "is_forward_pass",
    "under_pressure",
    "pass_height_encoded",
    "game_state_goal_diff",
    "match_period",
    "minute",
]

PASS_CATEGORICAL_BODY_PART = "body_part"
PASS_CATEGORICAL_TECHNIQUE = "pass_technique"

TARGET = "pass_completed"

XGBOOST_PARAMS = {
    "max_depth": 4,
    "n_estimators": 200,
    "learning_rate": 0.05,
    "min_child_weight": 10,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "tree_method": "hist",
    "n_jobs": -1,
    "random_state": RANDOM_SEED,
}

KMEANS_CANDIDATE_K = [3, 5, 7]
KMEANS_DEFAULT_K = 5
KMEANS_N_INIT = 20
KMEANS_NMI_SEEDS = 10
KMEANS_NMI_N_INIT = 10

SILHOUETTE_TARGET = 0.35
SILHOUETTE_SOFT_MINIMUM = 0.25
NMI_STABILITY_TARGET = 0.5

PASS_MODEL_PREFIX = "pass_xgboost"
CLUSTER_MODEL_PREFIX = "style_kmeans"
MODEL_VERSION = "v1"


def compute_zone_id(x: float, y: float) -> int:
    col = min(int(x / ZONE_COL_WIDTH), ZONE_COLS - 1)
    row = min(int(y / ZONE_ROW_HEIGHT), ZONE_ROWS - 1)
    if col < 0:
        col = 0
    if row < 0:
        row = 0
    return col * ZONE_ROWS + row


def compute_zone_col_row(zone_id: int) -> tuple[int, int]:
    col = zone_id // ZONE_ROWS
    row = zone_id % ZONE_ROWS
    return col, row

TEAM_SEASON_PROFILES_PATH = PROCESSED_DIR / "team_season_zone_profiles.csv"
TEAM_MATCH_CLUSTERS_PATH = PROCESSED_DIR / "team_match_clusters.csv"

MIN_PASSES_FOR_DIRECTIONAL = 5
MIN_MATCHES_FOR_TEAM_SEASON = 5

def _current_whoscored_season() -> str:
    now = datetime.now(timezone.utc)
    start_year = now.year if now.month >= 7 else now.year - 1
    season_str = str(start_year)
    if len(season_str) == 4 and season_str.isdigit():
        return f"{season_str}-{str(int(season_str) + 1)[-2:]}"
    return season_str


WHOSCORED_LEAGUE_SEASONS = [
    {"league": "ENG-Premier League", "season": _current_whoscored_season(), "competition_name": "Premier League"},
    {"league": "ESP-La Liga", "season": _current_whoscored_season(), "competition_name": "La Liga"},
    {"league": "GER-Bundesliga", "season": _current_whoscored_season(), "competition_name": "Bundesliga"},
    {"league": "ITA-Serie A", "season": _current_whoscored_season(), "competition_name": "Serie A"},
    {"league": "FRA-Ligue 1", "season": _current_whoscored_season(), "competition_name": "Ligue 1"},
]

WHOSCORED_PITCH_LENGTH = 100.0
WHOSCORED_PITCH_WIDTH = 100.0