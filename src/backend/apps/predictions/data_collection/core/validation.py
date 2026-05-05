from typing import Any, Mapping

from .enums import (
    DATASET_MATCHES,
    DATASET_PLAYERS,
    DATASET_TEAMS,
    DATASET_TEAM_SUMMARIES,
)
from ..schemas import (
    MATCH_ALL_COLUMNS,
    MATCH_CORE_REQUIRED_COLUMNS,
    PLAYER_ALL_COLUMNS,
    PLAYER_CORE_REQUIRED_COLUMNS,
    TEAM_ALL_COLUMNS,
    TEAM_CORE_REQUIRED_COLUMNS,
    TEAM_SUMMARY_ALL_COLUMNS,
    TEAM_SUMMARY_CORE_REQUIRED_COLUMNS,
)


DATASET_REQUIRED_COLUMNS = {
    DATASET_MATCHES: MATCH_CORE_REQUIRED_COLUMNS,
    DATASET_PLAYERS: PLAYER_CORE_REQUIRED_COLUMNS,
    DATASET_TEAMS: TEAM_CORE_REQUIRED_COLUMNS,
    DATASET_TEAM_SUMMARIES: TEAM_SUMMARY_CORE_REQUIRED_COLUMNS,
}

DATASET_ALL_COLUMNS = {
    DATASET_MATCHES: MATCH_ALL_COLUMNS,
    DATASET_PLAYERS: PLAYER_ALL_COLUMNS,
    DATASET_TEAMS: TEAM_ALL_COLUMNS,
    DATASET_TEAM_SUMMARIES: TEAM_SUMMARY_ALL_COLUMNS,
}


def get_required_columns(dataset: str) -> list[str]:
    try:
        return DATASET_REQUIRED_COLUMNS[dataset]
    except KeyError as exc:
        raise ValueError(f"Unsupported dataset: {dataset}") from exc


def get_all_columns(dataset: str) -> list[str]:
    try:
        return DATASET_ALL_COLUMNS[dataset]
    except KeyError as exc:
        raise ValueError(f"Unsupported dataset: {dataset}") from exc


def find_missing_required_columns(
    row: Mapping[str, Any],
    required_columns: list[str],
) -> list[str]:
    return [
        column
        for column in required_columns
        if column not in row or row[column] is None
    ]


def find_unknown_columns(
    row: Mapping[str, Any],
    allowed_columns: list[str],
) -> list[str]:
    allowed = set(allowed_columns)
    return [column for column in row.keys() if column not in allowed]


def validate_row(
    row: Mapping[str, Any],
    dataset: str,
) -> list[str]:
    errors: list[str] = []
    required_columns = get_required_columns(dataset)
    allowed_columns = get_all_columns(dataset)

    missing_columns = find_missing_required_columns(row, required_columns)
    if missing_columns:
        errors.append(f"missing_required_columns:{','.join(missing_columns)}")

    unknown_columns = find_unknown_columns(row, allowed_columns)
    if unknown_columns:
        errors.append(f"unknown_columns:{','.join(unknown_columns)}")

    return errors


def validate_rows(
    rows: list[Mapping[str, Any]],
    dataset: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    valid_rows: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        row_errors = validate_row(row, dataset)

        if row_errors:
            error_rows.append(
                {
                    "row_index": index,
                    "dataset": dataset,
                    "errors": " | ".join(row_errors),
                    "row": dict(row),
                }
            )
        else:
            valid_rows.append(dict(row))

    return valid_rows, error_rows


def build_validation_report_rows(
    error_rows: list[dict[str, Any]],
    *,
    source: str,
    dataset: str,
    league: str,
    season: str,
) -> list[dict[str, Any]]:
    report_rows: list[dict[str, Any]] = []

    for error in error_rows:
        report_rows.append(
            {
                "source": source,
                "dataset": dataset,
                "league": league,
                "season": season,
                "row_index": error["row_index"],
                "errors": error["errors"],
            }
        )

    return report_rows