from typing import Any, Mapping

from ..models.records import PlayerRow
from ..schemas import PLAYER_ALL_COLUMNS, PLAYER_CORE_REQUIRED_COLUMNS
from .utils import (
    build_validation_report_path,
    build_validation_summary,
    cleaned_rows_to_df,
    resolve_context_value,
    write_validation_report,
)


PER_90_FIELDS = [
    "g90",
    "xg90",
    "npxg90",
    "xa90",
    "sh90",
    "kp90",
    "xg90_xa90",
    "npxg90_xa90",
]


def normalize_blank_to_none(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    return value


def clean_player_row(row: Mapping[str, Any]) -> PlayerRow:
    cleaned = {column: None for column in PLAYER_ALL_COLUMNS}

    for key, value in row.items():
        if key in cleaned:
            cleaned[key] = normalize_blank_to_none(value)

    return cleaned


def build_issue(
    level: str,
    code: str,
    message: str,
    row_index: int | None = None,
    row_key: str | None = None,
) -> dict[str, Any]:
    return {
        "level": level,
        "code": code,
        "message": message,
        "row_index": row_index,
        "row_key": row_key,
    }


def make_player_row_key(row: Mapping[str, Any]) -> str:
    source = row.get("source")
    source_player_id = row.get("source_player_id")
    season = row.get("season")
    team = row.get("team")
    return f"{source}|{source_player_id}|{season}|{team}"


def is_blank_text(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate_required_fields(
    row: Mapping[str, Any],
    row_index: int,
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    row_key = make_player_row_key(row)

    for column in PLAYER_CORE_REQUIRED_COLUMNS:
        if row.get(column) is None:
            errors.append(
                build_issue(
                    "error",
                    "missing_required_field",
                    f"Missing required field: {column}",
                    row_index=row_index,
                    row_key=row_key,
                )
            )

    for column in ["source", "source_player_id", "season", "league", "name", "team"]:
        if is_blank_text(row.get(column)):
            errors.append(
                build_issue(
                    "error",
                    f"blank_{column}",
                    f"{column} is blank",
                    row_index=row_index,
                    row_key=row_key,
                )
            )

    return errors


def validate_warnings(
    row: Mapping[str, Any],
    row_index: int,
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    row_key = make_player_row_key(row)

    minutes = safe_float(row.get("minutes"))
    games = safe_float(row.get("games"))

    if minutes is not None and minutes < 0:
        warnings.append(
            build_issue(
                "warning",
                "negative_minutes",
                "minutes is negative",
                row_index=row_index,
                row_key=row_key,
            )
        )

    if games is not None and games < 0:
        warnings.append(
            build_issue(
                "warning",
                "negative_games",
                "games is negative",
                row_index=row_index,
                row_key=row_key,
            )
        )

    if minutes is not None and minutes == 0:
        populated_per_90_fields = []
        for field in PER_90_FIELDS:
            value = safe_float(row.get(field))
            if value is not None and value != 0:
                populated_per_90_fields.append(field)

        if populated_per_90_fields:
            warnings.append(
                build_issue(
                    "warning",
                    "per_90_present_with_zero_minutes",
                    f"Per-90 fields populated despite minutes == 0: {', '.join(populated_per_90_fields)}",
                    row_index=row_index,
                    row_key=row_key,
                )
            )

    return warnings


def validate_player_rows(
    rows: list[Mapping[str, Any]],
    *,
    source: str | None = None,
    league: str | None = None,
    season: str | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    cleaned_rows: list[PlayerRow] = []
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    seen_source_player_keys: dict[tuple[Any, Any, Any, Any], int] = {}

    for row_index, row in enumerate(rows):
        cleaned_row = clean_player_row(row)
        cleaned_rows.append(cleaned_row)

        errors.extend(validate_required_fields(cleaned_row, row_index))
        warnings.extend(validate_warnings(cleaned_row, row_index))

        duplicate_key = (
            cleaned_row.get("source"),
            cleaned_row.get("source_player_id"),
            cleaned_row.get("season"),
            cleaned_row.get("team"),
        )

        if duplicate_key in seen_source_player_keys:
            warnings.append(
                build_issue(
                    "warning",
                    "duplicate_source_player_season_team",
                    f"Duplicate row for source + source_player_id + season + team. First seen at row {seen_source_player_keys[duplicate_key]}",
                    row_index=row_index,
                    row_key=make_player_row_key(cleaned_row),
                )
            )
        else:
            seen_source_player_keys[duplicate_key] = row_index

    cleaned_df = cleaned_rows_to_df(cleaned_rows, PLAYER_ALL_COLUMNS)
    summary = build_validation_summary("players", cleaned_rows, errors, warnings)

    source_value = resolve_context_value(source, cleaned_rows, "source")
    league_value = resolve_context_value(league, cleaned_rows, "league")
    season_value = resolve_context_value(season, cleaned_rows, "season")

    if write_report:
        report_path = build_validation_report_path(
            source_value,
            league_value,
            season_value,
            "players",
        )
        write_validation_report(report_path, summary, errors, warnings)
        summary["report_path"] = str(report_path)

    return {
        "cleaned_df": cleaned_df,
        "errors": errors,
        "warnings": warnings,
        "summary": summary,
    }


def validate_players(df: Any) -> dict[str, Any]:
    """
    Validate a DataFrame of player data.
    """
    rows = df.to_dict("records") if hasattr(df, "to_dict") else df
    return validate_player_rows(rows, write_report=False)