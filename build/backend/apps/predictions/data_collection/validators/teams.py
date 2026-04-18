from typing import Any, Mapping

from ..models.records import TeamRow
from ..schemas import TEAM_ALL_COLUMNS, TEAM_CORE_REQUIRED_COLUMNS
from .utils import (
    build_validation_report_path,
    build_validation_summary,
    cleaned_rows_to_df,
    resolve_context_value,
    write_validation_report,
)


NEGATIVE_AGGREGATE_FIELDS = [
    "matches_played",
    "wins",
    "draws",
    "losses",
    "goals_for",
    "goals_against",
    "xg_for",
    "xg_against",
    "npxg_for",
    "npxg_against",
    "xpts",
    "deep_completions_for",
    "deep_completions_against",
    "ppda_att",
    "ppda_def",
    "oppda_att",
    "oppda_def",
    "ppda",
    "oppda",
    "possession_pct",
    "clean_sheets",
    "corners",
    "offsides",
    "fouls",
    "yellow_cards",
    "red_cards",
    "shots",
    "shots_on_target",
    "big_chances",
    "big_chances_missed",
    "successful_dribbles",
    "tackles",
    "interceptions",
    "clearances",
    "blocks",
    "saves",
    "accurate_passes",
    "total_passes",
    "pass_accuracy_pct",
    "accurate_long_balls",
    "total_long_balls",
    "long_ball_accuracy_pct",
    "accurate_crosses",
    "total_crosses",
    "cross_accuracy_pct",
    "duels_won",
    "duels_total",
    "duel_win_pct",
    "aerial_duels_won",
    "aerial_duels_total",
    "aerial_duel_win_pct",
    "ball_recoveries",
]


def normalize_blank_to_none(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    return value


def clean_team_row(row: Mapping[str, Any]) -> TeamRow:
    cleaned = {column: None for column in TEAM_ALL_COLUMNS}

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


def make_team_row_key(row: Mapping[str, Any]) -> str:
    source = row.get("source")
    source_team_id = row.get("source_team_id")
    season = row.get("season")
    return f"{source}|{source_team_id}|{season}"


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
    row_key = make_team_row_key(row)

    for column in TEAM_CORE_REQUIRED_COLUMNS:
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

    for column in ["source", "source_team_id", "season", "league", "team"]:
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
    row_key = make_team_row_key(row)

    for field in NEGATIVE_AGGREGATE_FIELDS:
        numeric_value = safe_float(row.get(field))
        if numeric_value is not None and numeric_value < 0:
            warnings.append(
                build_issue(
                    "warning",
                    "negative_aggregate_value",
                    f"Negative aggregate value detected for {field}",
                    row_index=row_index,
                    row_key=row_key,
                )
            )

    return warnings


def validate_team_rows(
    rows: list[Mapping[str, Any]],
    *,
    source: str | None = None,
    league: str | None = None,
    season: str | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    cleaned_rows: list[TeamRow] = []
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    seen_source_team_keys: dict[tuple[Any, Any, Any], int] = {}

    for row_index, row in enumerate(rows):
        cleaned_row = clean_team_row(row)
        cleaned_rows.append(cleaned_row)

        errors.extend(validate_required_fields(cleaned_row, row_index))
        warnings.extend(validate_warnings(cleaned_row, row_index))

        duplicate_key = (
            cleaned_row.get("source"),
            cleaned_row.get("source_team_id"),
            cleaned_row.get("season"),
        )

        if duplicate_key in seen_source_team_keys:
            warnings.append(
                build_issue(
                    "warning",
                    "duplicate_source_team_season",
                    f"Duplicate row for source + source_team_id + season. First seen at row {seen_source_team_keys[duplicate_key]}",
                    row_index=row_index,
                    row_key=make_team_row_key(cleaned_row),
                )
            )
        else:
            seen_source_team_keys[duplicate_key] = row_index

    cleaned_df = cleaned_rows_to_df(cleaned_rows, TEAM_ALL_COLUMNS)
    summary = build_validation_summary("teams", cleaned_rows, errors, warnings)

    source_value = resolve_context_value(source, cleaned_rows, "source")
    league_value = resolve_context_value(league, cleaned_rows, "league")
    season_value = resolve_context_value(season, cleaned_rows, "season")

    if write_report:
        report_path = build_validation_report_path(
            source_value,
            league_value,
            season_value,
            "teams",
        )
        write_validation_report(report_path, summary, errors, warnings)
        summary["report_path"] = str(report_path)

    return {
        "cleaned_df": cleaned_df,
        "errors": errors,
        "warnings": warnings,
        "summary": summary,
    }


def validate_teams(df: Any) -> dict[str, Any]:
    """
    Validate a DataFrame of team data.
    """
    rows = df.to_dict("records") if hasattr(df, "to_dict") else df
    return validate_team_rows(rows, write_report=False)