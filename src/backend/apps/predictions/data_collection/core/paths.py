from pathlib import Path

from apps.predictions.data_paths import DATA_ROOT

from .enums import (
    DATASET_MATCHES,
    DATASET_PLAYERS,
    DATASET_TEAMS,
    DATASET_TEAM_SUMMARIES,
    SOURCE_SOFASCORE,
    SOURCE_UNDERSTAT,
    SOURCE_WHOSCORED,
)


RAW_ROOT = DATA_ROOT / "raw"
PROCESSED_ROOT = DATA_ROOT / "processed"
AUDITS_ROOT = DATA_ROOT / "audits"
DB_LOAD_ROOT = DATA_ROOT / "db_load"

RAW_UNDERSTAT_ROOT = RAW_ROOT / SOURCE_UNDERSTAT
RAW_SOFASCORE_ROOT = RAW_ROOT / SOURCE_SOFASCORE
RAW_WHOSCORED_ROOT = RAW_ROOT / SOURCE_WHOSCORED

RAW_UNDERSTAT_MERGED_ROOT = RAW_UNDERSTAT_ROOT / "merged"
RAW_SOFASCORE_MERGED_ROOT = RAW_SOFASCORE_ROOT / "merged"
RAW_WHOSCORED_MERGED_ROOT = RAW_WHOSCORED_ROOT / "merged"

PROCESSED_MATCHES_ROOT = PROCESSED_ROOT / DATASET_MATCHES
PROCESSED_PLAYERS_ROOT = PROCESSED_ROOT / DATASET_PLAYERS
PROCESSED_TEAMS_ROOT = PROCESSED_ROOT / DATASET_TEAMS
PROCESSED_TEAM_SUMMARIES_ROOT = PROCESSED_ROOT / DATASET_TEAM_SUMMARIES

PROCESSED_MATCHES_MERGED_ROOT = PROCESSED_MATCHES_ROOT / "merged"
PROCESSED_PLAYERS_MERGED_ROOT = PROCESSED_PLAYERS_ROOT / "merged"
PROCESSED_TEAMS_MERGED_ROOT = PROCESSED_TEAMS_ROOT / "merged"
PROCESSED_TEAM_SUMMARIES_MERGED_ROOT = PROCESSED_TEAM_SUMMARIES_ROOT / "merged"

RECONCILIATION_ROOT = AUDITS_ROOT / "reconciliation"
VALIDATION_ROOT = AUDITS_ROOT / "validation"

DATASET_TO_PROCESSED_ROOT = {
    DATASET_MATCHES: PROCESSED_MATCHES_ROOT,
    DATASET_PLAYERS: PROCESSED_PLAYERS_ROOT,
    DATASET_TEAMS: PROCESSED_TEAMS_ROOT,
    DATASET_TEAM_SUMMARIES: PROCESSED_TEAM_SUMMARIES_ROOT,
}

SOURCE_TO_RAW_ROOT = {
    SOURCE_UNDERSTAT: RAW_UNDERSTAT_ROOT,
    SOURCE_SOFASCORE: RAW_SOFASCORE_ROOT,
    SOURCE_WHOSCORED: RAW_WHOSCORED_ROOT,
}

SOURCE_TO_RAW_MERGED_ROOT = {
    SOURCE_UNDERSTAT: RAW_UNDERSTAT_MERGED_ROOT,
    SOURCE_SOFASCORE: RAW_SOFASCORE_MERGED_ROOT,
    SOURCE_WHOSCORED: RAW_WHOSCORED_MERGED_ROOT,
}

DATASET_TO_PROCESSED_MERGED_ROOT = {
    DATASET_MATCHES: PROCESSED_MATCHES_MERGED_ROOT,
    DATASET_PLAYERS: PROCESSED_PLAYERS_MERGED_ROOT,
    DATASET_TEAMS: PROCESSED_TEAMS_MERGED_ROOT,
    DATASET_TEAM_SUMMARIES: PROCESSED_TEAM_SUMMARIES_MERGED_ROOT,
}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_core_directories() -> None:
    directories = [
        RAW_ROOT,
        PROCESSED_ROOT,
        AUDITS_ROOT,
        DB_LOAD_ROOT,
        RAW_UNDERSTAT_ROOT,
        RAW_SOFASCORE_ROOT,
        RAW_UNDERSTAT_MERGED_ROOT,
        RAW_SOFASCORE_MERGED_ROOT,
        PROCESSED_MATCHES_ROOT,
        PROCESSED_PLAYERS_ROOT,
        PROCESSED_TEAMS_ROOT,
        PROCESSED_TEAM_SUMMARIES_ROOT,
        PROCESSED_MATCHES_MERGED_ROOT,
        PROCESSED_PLAYERS_MERGED_ROOT,
        PROCESSED_TEAMS_MERGED_ROOT,
        PROCESSED_TEAM_SUMMARIES_MERGED_ROOT,
        RECONCILIATION_ROOT,
        VALIDATION_ROOT,
    ]

    for directory in directories:
        ensure_dir(directory)


def get_raw_source_dir(source: str) -> Path:
    try:
        return SOURCE_TO_RAW_ROOT[source]
    except KeyError as exc:
        raise ValueError(f"Unsupported source: {source}") from exc


def get_processed_dataset_dir(dataset: str) -> Path:
    try:
        return DATASET_TO_PROCESSED_ROOT[dataset]
    except KeyError as exc:
        raise ValueError(f"Unsupported dataset: {dataset}") from exc


def get_raw_merged_dir(source: str) -> Path:
    try:
        return SOURCE_TO_RAW_MERGED_ROOT[source]
    except KeyError as exc:
        raise ValueError(f"Unsupported source: {source}") from exc


def get_processed_merged_dir(dataset: str) -> Path:
    try:
        return DATASET_TO_PROCESSED_MERGED_ROOT[dataset]
    except KeyError as exc:
        raise ValueError(f"Unsupported dataset: {dataset}") from exc


def get_raw_season_dir(source: str, season: str) -> Path:
    return get_raw_source_dir(source) / str(season)


def get_processed_season_dir(dataset: str, season: str) -> Path:
    return get_processed_dataset_dir(dataset) / str(season)


def build_raw_filename(source: str, dataset: str, league: str, season: str) -> str:
    return f"{source}_{dataset}_{league}_{season}_raw.csv"


def build_processed_filename(dataset: str, source: str, league: str, season: str) -> str:
    return f"{dataset}_{source}_{league}_{season}_canonical.csv"


def build_validation_filename(dataset: str, source: str, league: str, season: str) -> str:
    return f"{dataset}_{source}_{league}_{season}_validation.csv"


def build_reconciliation_filename(dataset: str, primary_source: str, secondary_source: str, league: str, season: str) -> str:
    return f"{dataset}_{primary_source}_{secondary_source}_{league}_{season}_reconciliation.csv"


def build_raw_merged_filename(dataset: str) -> str:
    return f"all_leagues_all_seasons_{dataset}.csv"


def build_processed_merged_filename(dataset: str) -> str:
    return f"all_leagues_all_seasons_{dataset}_merged.csv"


def get_raw_csv_path(source: str, dataset: str, league: str, season: str) -> Path:
    return get_raw_season_dir(source, season) / build_raw_filename(source, dataset, league, season)


def get_processed_csv_path(dataset: str, source: str, league: str, season: str) -> Path:
    return get_processed_season_dir(dataset, season) / build_processed_filename(dataset, source, league, season)


def get_raw_merged_csv_path(source: str, dataset: str) -> Path:
    return get_raw_merged_dir(source) / build_raw_merged_filename(dataset)


def get_processed_merged_csv_path(dataset: str) -> Path:
    return get_processed_merged_dir(dataset) / build_processed_merged_filename(dataset)


def get_validation_csv_path(dataset: str, source: str, league: str, season: str) -> Path:
    return ensure_dir(VALIDATION_ROOT / dataset / str(season)) / build_validation_filename(dataset, source, league, season)


def get_reconciliation_csv_path(dataset: str, primary_source: str, secondary_source: str, league: str, season: str) -> Path:
    return ensure_dir(RECONCILIATION_ROOT / dataset / str(season)) / build_reconciliation_filename(
        dataset,
        primary_source,
        secondary_source,
        league,
        season,
    )
