from __future__ import annotations

from apps.predictions.data_paths import DATA_ROOT


DATA_DIR = DATA_ROOT

RAW_INJURIES_DIR = DATA_DIR / "raw" / "injuries"
RAW_DOBS_DIR = DATA_DIR / "raw" / "dobs"
LINEUP_DIR = DATA_DIR / "raw" / "lineups"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = DATA_DIR / "models"

PLAYER_ID_MAPPING_PATH = PROCESSED_DIR / "player_id_mapping.csv"
TEAM_ID_MAPPING_PATH = PROCESSED_DIR / "team_id_mapping.csv"
PLAYER_DOBS_PATH = PROCESSED_DIR / "player_dobs.csv"
INJURY_SPELLS_PATH = PROCESSED_DIR / "injury_spells.csv"
SURVIVAL_DATASET_PATH = PROCESSED_DIR / "survival_dataset.csv"
RISK_DATASET_PATH = PROCESSED_DIR / "risk_dataset.csv"

UNDERSTAT_PLAYERS_PATH = PROCESSED_DIR / "players" / "merged" / "all_leagues_all_seasons_players_merged.csv"

MIN_FUZZY_MATCH_SCORE = 85
MIN_TEAM_FUZZY_MATCH_SCORE = 70

LEAGUES = ["EPL", "La_Liga", "Bundesliga", "Serie_A", "Ligue_1"]
DEFAULT_SEASONS = list(range(2014, 2026))

UNDERSTAT_SOURCE_FILTER = "understat"

INJURY_TYPE_KEYWORDS = {
    "LIGAMENT": ["ligament", "acl", "mcl", "cruciate", "tendon", "achilles", "meniscus"],
    "BONE": ["fracture", "bone", "metatarsal", "rib", "broken", "crack"],
    "KNEE": ["knee"],
    "ANKLE": ["ankle"],
    "FOOT": ["foot", "toe", "heel"],
    "HIP": ["hip", "pelvic"],
    "BACK": ["back"],
    "SHOULDER": ["shoulder"],
    "HEAD": ["head", "concussion", "skull", "face", "jaw", "nose"],
    "MUSCLE": ["muscle", "muscular", "hamstring", "thigh", "calf", "strain", "groin", "adductor", "sprain", "overstretching", "contracture"],
    "KNOCK": ["knock", "dead leg", "contusion", "bruise"],
    "ILLNESS": ["ill", "illness", "covid", "virus", "infection", "fever", "flu", "cold", "quarantine", "stomach"],
    "CONDITIONING": ["fitness", "rest", "training", "conditioning"],
}
INJURY_CATEGORY_OTHER = "OTHER"
INJURY_CATEGORIES = [
    "MUSCLE", "LIGAMENT", "KNEE", "ANKLE", "FOOT", "HIP", "BACK",
    "SHOULDER", "HEAD", "BONE", "KNOCK", "ILLNESS", "CONDITIONING",
    INJURY_CATEGORY_OTHER,
]

SUSPENSION_KEYWORDS = ["suspension", "ban", "red card", "suspended"]

DURATION_COL = "duration"
EVENT_COL = "event"
RISK_TARGET = "injury_next_7d"

SURVIVAL_FEATURES = [
    "injury_type_muscle",
    "injury_type_ligament",
    "injury_type_knee",
    "injury_type_ankle",
    "injury_type_foot",
    "injury_type_hip",
    "injury_type_back",
    "injury_type_shoulder",
    "injury_type_head",
    "injury_type_bone",
    "injury_type_knock",
    "injury_type_illness",
    "injury_type_conditioning",
    "player_age",
    "days_since_last_injury",
    "matches_in_prior_30d",
    "minutes_in_prior_30d",
    "is_peak_season",
]

RISK_FEATURES = [
    "minutes_last_7d",
    "minutes_last_14d",
    "minutes_last_30d",
    "matches_last_7d",
    "matches_last_14d",
    "consecutive_starts",
    "days_since_last_rest",
    "age",
    "prior_injuries_count",
    "days_since_last_injury",
    "season_phase_mid",
    "season_phase_late",
    "acwr_7_28",
    "minutes_per_match_30d",
    "workload_zscore_30d",
    "recent_match_density",
    "cumulative_workload_per_week",
]

RISK_FLAG_THRESHOLD = 0.80
