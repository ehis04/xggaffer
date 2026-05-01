from typing import Any, Mapping

from ..models.records import TeamSummaryRow
from ..schemas import TEAM_SUMMARY_ALL_COLUMNS, TEAM_SUMMARY_CORE_REQUIRED_COLUMNS
from .utils import (
    build_validation_report_path,
    build_validation_summary,
    cleaned_rows_to_df,
    resolve_context_value,
    write_validation_report,
)


NEGATIVE_XG_FIELDS = [
    "xg_for",
    "xg_against",
    "npxg_for",
    "npxg_against",
]

POSSIBLE_MINUTE_TOTAL_FIELDS = [
    "minutes_drawing",
    "minutes_winning",
    "minutes_losing",
]

POSSIBLE_FORMATION_LIST_FIELDS = [
    "formations_used",
    "formation_list",
    "formations",
]

POSSIBLE_PRIMARY_FORMATION_FIELDS = [
    "primary_formation",
]


def normalize_blank_to_none(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    return value


def clean_team_summary_row(row: Mapping[str, Any]) -> TeamSummaryRow:
    cleaned = {column: None for column in TEAM_SUMMARY_ALL_COLUMNS}

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


def make_team_summary_row_key(row: Mapping[str, Any]) -> str:
    source = row.get("source")
    season = row.get("season")
    team = row.get("team")
    return f"{source}|{season}|{team}"


def is_blank_text(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def first_present_value(row: Mapping[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in row:
            value = normalize_blank_to_none(row.get(key))
            if value is not None:
                return value
    return None


def parse_formation_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    text = str(value).strip()
    if not text:
        return []

    if "," in text:
        return [part.strip() for part in text.split(",") if part.strip()]

    return [text]


def validate_required_fields(
    row: Mapping[str, Any],
    row_index: int,
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    row_key = make_team_summary_row_key(row)

    for column in TEAM_SUMMARY_CORE_REQUIRED_COLUMNS:
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

    for column in ["source", "season", "league", "team"]:
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
    original_row: Mapping[str, Any],
    cleaned_row: Mapping[str, Any],
    row_index: int,
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    row_key = make_team_summary_row_key(cleaned_row)

    for field in NEGATIVE_XG_FIELDS:
        numeric_value = safe_float(cleaned_row.get(field))
        if numeric_value is not None and numeric_value < 0:
            warnings.append(
                build_issue(
                    "warning",
                    "negative_xg_value",
                    f"Negative xG-style value detected for {field}",
                    row_index=row_index,
                    row_key=row_key,
                )
            )

    minute_values = []
    for field in POSSIBLE_MINUTE_TOTAL_FIELDS:
        value = safe_int(original_row.get(field))
        if value is not None:
            minute_values.append((field, value))

    if minute_values:
        total_minutes = sum(value for _, value in minute_values)
        matches_played = safe_int(cleaned_row.get("matches_played"))

        if total_minutes < 0:
            warnings.append(
                build_issue(
                    "warning",
                    "negative_minute_totals",
                    "Minute totals contain negative values",
                    row_index=row_index,
                    row_key=row_key,
                )
            )

        if matches_played is not None and matches_played > 0:
            upper_bound = matches_played * 110
            lower_bound = matches_played * 60

            if total_minutes > upper_bound:
                warnings.append(
                    build_issue(
                        "warning",
                        "contradictory_minute_totals",
                        f"Minute totals sum to {total_minutes}, which is too high for {matches_played} matches",
                        row_index=row_index,
                        row_key=row_key,
                    )
                )

            if total_minutes < lower_bound:
                warnings.append(
                    build_issue(
                        "warning",
                        "minute_totals_suspiciously_low",
                        f"Minute totals sum to {total_minutes}, which is suspiciously low for {matches_played} matches",
                        row_index=row_index,
                        row_key=row_key,
                    )
                )

    formation_list_value = first_present_value(original_row, POSSIBLE_FORMATION_LIST_FIELDS)
    primary_formation_value = first_present_value(original_row, POSSIBLE_PRIMARY_FORMATION_FIELDS)

    formation_list = parse_formation_list(formation_list_value)
    primary_formation = normalize_blank_to_none(primary_formation_value)

    if formation_list and primary_formation is None:
        warnings.append(
            build_issue(
                "warning",
                "missing_primary_formation",
                "Formation list exists but primary_formation is missing",
                row_index=row_index,
                row_key=row_key,
            )
        )

    return warnings


def validate_team_summary_rows(
    rows: list[Mapping[str, Any]],
    *,
    source: str | None = None,
    league: str | None = None,
    season: str | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    cleaned_rows: list[TeamSummaryRow] = []
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for row_index, row in enumerate(rows):
        cleaned_row = clean_team_summary_row(row)
        cleaned_rows.append(cleaned_row)

        errors.extend(validate_required_fields(cleaned_row, row_index))
        warnings.extend(validate_warnings(row, cleaned_row, row_index))

    cleaned_df = cleaned_rows_to_df(cleaned_rows, TEAM_SUMMARY_ALL_COLUMNS)
    summary = build_validation_summary("team_summaries", cleaned_rows, errors, warnings)

    source_value = resolve_context_value(source, cleaned_rows, "source")
    league_value = resolve_context_value(league, cleaned_rows, "league")
    season_value = resolve_context_value(season, cleaned_rows, "season")

    if write_report:
        report_path = build_validation_report_path(
            source_value,
            league_value,
            season_value,
            "team_summaries",
        )
        write_validation_report(report_path, summary, errors, warnings)
        summary["report_path"] = str(report_path)

    return {
        "cleaned_df": cleaned_df,
        "errors": errors,
        "warnings": warnings,
        "summary": summary,
    }


def validate_team_summaries(df: Any) -> dict[str, Any]:
    """
    Validate a DataFrame of team summary data.
    """
    rows = df.to_dict("records") if hasattr(df, "to_dict") else df
    return validate_team_summary_rows(rows, write_report=False)