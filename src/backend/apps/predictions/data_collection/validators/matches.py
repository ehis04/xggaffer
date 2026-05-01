import re
from typing import Any, Mapping

from ..models.records import MatchRow
from ..schemas import MATCH_ALL_COLUMNS, MATCH_CORE_REQUIRED_COLUMNS
from .utils import (
    build_validation_report_path,
    build_validation_summary,
    cleaned_rows_to_df,
    resolve_context_value,
    write_validation_report,
)


FINAL_STATUS_VALUES = {"final", "finished", "ft", "full_time", "full-time"}

NEGATIVE_VALUE_FIELDS = [
    "home_goals",
    "away_goals",
    "home_own_goals",
    "away_own_goals",
    "home_shots",
    "away_shots",
    "home_missed_shots",
    "away_missed_shots",
    "home_blocked_shots",
    "away_blocked_shots",
    "home_saved_shots",
    "away_saved_shots",
    "home_shots_on_post",
    "away_shots_on_post",
    "home_shots_six_yard",
    "away_shots_six_yard",
    "home_shots_penalty_area",
    "away_shots_penalty_area",
    "home_shots_outside_box",
    "away_shots_outside_box",
    "home_shots_open_play",
    "away_shots_open_play",
    "home_shots_set_piece",
    "away_shots_set_piece",
    "home_shots_from_corner",
    "away_shots_from_corner",
    "home_shots_direct_freekick",
    "away_shots_direct_freekick",
    "home_shots_penalty",
    "away_shots_penalty",
    "home_shots_left_foot",
    "away_shots_left_foot",
    "home_shots_right_foot",
    "away_shots_right_foot",
    "home_shots_head",
    "away_shots_head",
    "home_xg",
    "away_xg",
    "home_xa",
    "away_xa",
    "home_key_passes",
    "away_key_passes",
    "home_assists",
    "away_assists",
    "home_xpts",
    "away_xpts",
    "home_possession_pct",
    "away_possession_pct",
    "home_total_passes",
    "away_total_passes",
    "home_accurate_passes",
    "away_accurate_passes",
    "home_pass_accuracy_pct",
    "away_pass_accuracy_pct",
    "home_corners",
    "away_corners",
    "home_fouls",
    "away_fouls",
    "home_yellow_cards",
    "away_yellow_cards",
    "home_red_cards",
    "away_red_cards",
    "home_offsides",
    "away_offsides",
    "home_saves",
    "away_saves",
    "home_tackles",
    "away_tackles",
    "home_interceptions",
    "away_interceptions",
    "home_clearances",
    "away_clearances",
    "home_blocks",
    "away_blocks",
    "home_ball_recoveries",
    "away_ball_recoveries",
    "home_aerial_duels_won",
    "away_aerial_duels_won",
    "home_ground_duels_won",
    "away_ground_duels_won",
    "home_total_duels_won",
    "away_total_duels_won",
]

GOAL_MINUTES_PATTERN = re.compile(r"^\d+(,\d+)*$")


def normalize_blank_to_none(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    return value


def clean_match_row(row: Mapping[str, Any]) -> MatchRow:
    cleaned = {column: None for column in MATCH_ALL_COLUMNS}

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


def make_match_row_key(row: Mapping[str, Any]) -> str:
    source = row.get("source")
    source_match_id = row.get("source_match_id")
    return f"{source}|{source_match_id}"


def is_final_status(value: Any) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in FINAL_STATUS_VALUES


def is_finished_match(row: Mapping[str, Any]) -> bool:
    is_finished_value = row.get("is_finished")
    if isinstance(is_finished_value, bool):
        return is_finished_value
    if isinstance(is_finished_value, str):
        lowered = is_finished_value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return is_final_status(row.get("match_status"))


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_blank_team_name(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def goal_minutes_malformed(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    if text == "":
        return False
    return GOAL_MINUTES_PATTERN.fullmatch(text) is None


def validate_required_fields(
    row: Mapping[str, Any],
    row_index: int,
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []

    for column in MATCH_CORE_REQUIRED_COLUMNS:
        if row.get(column) is None:
            errors.append(
                build_issue(
                    "error",
                    "missing_required_field",
                    f"Missing required field: {column}",
                    row_index=row_index,
                    row_key=make_match_row_key(row),
                )
            )

    if is_blank_team_name(row.get("home_team")):
        errors.append(
            build_issue(
                "error",
                "blank_home_team",
                "home_team is blank",
                row_index=row_index,
                row_key=make_match_row_key(row),
            )
        )

    if is_blank_team_name(row.get("away_team")):
        errors.append(
            build_issue(
                "error",
                "blank_away_team",
                "away_team is blank",
                row_index=row_index,
                row_key=make_match_row_key(row),
            )
        )

    if is_finished_match(row):
        if row.get("home_goals") is None:
            errors.append(
                build_issue(
                    "error",
                    "missing_home_goals_for_finished_match",
                    "Finished match is missing home_goals",
                    row_index=row_index,
                    row_key=make_match_row_key(row),
                )
            )
        if row.get("away_goals") is None:
            errors.append(
                build_issue(
                    "error",
                    "missing_away_goals_for_finished_match",
                    "Finished match is missing away_goals",
                    row_index=row_index,
                    row_key=make_match_row_key(row),
                )
            )

    return errors


def validate_warnings(
    row: Mapping[str, Any],
    row_index: int,
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    row_key = make_match_row_key(row)

    home_team = row.get("home_team")
    away_team = row.get("away_team")

    if home_team is not None and away_team is not None:
        if str(home_team).strip().lower() == str(away_team).strip().lower():
            warnings.append(
                build_issue(
                    "warning",
                    "same_home_and_away_team",
                    "home_team and away_team are identical",
                    row_index=row_index,
                    row_key=row_key,
                )
            )

    for field in NEGATIVE_VALUE_FIELDS:
        numeric_value = safe_float(row.get(field))
        if numeric_value is not None and numeric_value < 0:
            warnings.append(
                build_issue(
                    "warning",
                    "negative_value",
                    f"Negative value detected for {field}",
                    row_index=row_index,
                    row_key=row_key,
                )
            )

    home_possession = safe_float(row.get("home_possession_pct"))
    away_possession = safe_float(row.get("away_possession_pct"))
    if home_possession is not None and away_possession is not None:
        total = home_possession + away_possession
        if abs(total - 100.0) > 2.0:
            warnings.append(
                build_issue(
                    "warning",
                    "possession_not_near_100",
                    f"Possession totals {total:.2f}, which is not near 100",
                    row_index=row_index,
                    row_key=row_key,
                )
            )

    if goal_minutes_malformed(row.get("home_goal_minutes")):
        warnings.append(
            build_issue(
                "warning",
                "malformed_home_goal_minutes",
                "home_goal_minutes is malformed",
                row_index=row_index,
                row_key=row_key,
            )
        )

    if goal_minutes_malformed(row.get("away_goal_minutes")):
        warnings.append(
            build_issue(
                "warning",
                "malformed_away_goal_minutes",
                "away_goal_minutes is malformed",
                row_index=row_index,
                row_key=row_key,
            )
        )

    return warnings


def validate_match_rows(
    rows: list[Mapping[str, Any]],
    *,
    source: str | None = None,
    league: str | None = None,
    season: str | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    cleaned_rows: list[MatchRow] = []
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    seen_source_ids: dict[tuple[Any, Any], int] = {}
    seen_canonical_keys: dict[str, int] = {}

    for row_index, row in enumerate(rows):
        cleaned_row = clean_match_row(row)
        cleaned_rows.append(cleaned_row)

        errors.extend(validate_required_fields(cleaned_row, row_index))
        warnings.extend(validate_warnings(cleaned_row, row_index))

        duplicate_key = (
            cleaned_row.get("source"),
            cleaned_row.get("source_match_id"),
        )
        if duplicate_key in seen_source_ids:
            errors.append(
                build_issue(
                    "error",
                    "duplicate_source_match_id",
                    f"Duplicate row for source + source_match_id. First seen at row {seen_source_ids[duplicate_key]}",
                    row_index=row_index,
                    row_key=make_match_row_key(cleaned_row),
                )
            )
        else:
            seen_source_ids[duplicate_key] = row_index

        canonical_match_key = cleaned_row.get("canonical_match_key")
        if canonical_match_key is not None:
            canonical_match_key = str(canonical_match_key)
            if canonical_match_key in seen_canonical_keys:
                warnings.append(
                    build_issue(
                        "warning",
                        "duplicate_canonical_match_key",
                        f"Duplicate canonical_match_key. First seen at row {seen_canonical_keys[canonical_match_key]}",
                        row_index=row_index,
                        row_key=make_match_row_key(cleaned_row),
                    )
                )
            else:
                seen_canonical_keys[canonical_match_key] = row_index

    cleaned_df = cleaned_rows_to_df(cleaned_rows, MATCH_ALL_COLUMNS)
    summary = build_validation_summary("matches", cleaned_rows, errors, warnings)

    source_value = resolve_context_value(source, cleaned_rows, "source")
    league_value = resolve_context_value(league, cleaned_rows, "league")
    season_value = resolve_context_value(season, cleaned_rows, "season")

    if write_report:
        report_path = build_validation_report_path(
            source_value,
            league_value,
            season_value,
            "matches",
        )
        write_validation_report(report_path, summary, errors, warnings)
        summary["report_path"] = str(report_path)

    return {
        "cleaned_df": cleaned_df,
        "errors": errors,
        "warnings": warnings,
        "summary": summary,
    }


def validate_matches(df: Any) -> dict[str, Any]:
    """
    Validate a DataFrame of match data.
    """
    rows = df.to_dict("records") if hasattr(df, "to_dict") else df
    return validate_match_rows(rows, write_report=False)