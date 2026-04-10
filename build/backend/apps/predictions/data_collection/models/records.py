from typing import Any, Iterable, Mapping, TypeAlias


Row: TypeAlias = dict[str, Any]
MatchRow: TypeAlias = dict[str, Any]
PlayerRow: TypeAlias = dict[str, Any]
TeamRow: TypeAlias = dict[str, Any]
TeamSummaryRow: TypeAlias = dict[str, Any]


def build_row(
    all_columns: Iterable[str],
    values: Mapping[str, Any],
    *,
    allow_extra: bool = False,
) -> Row:
    column_list = list(all_columns)
    row = {column: None for column in column_list}

    extra_keys = [key for key in values.keys() if key not in row]
    if extra_keys and not allow_extra:
        raise ValueError(f"Unexpected keys for row: {extra_keys}")

    row.update(values)
    return row


def filter_row_to_columns(
    row: Mapping[str, Any],
    allowed_columns: Iterable[str],
) -> Row:
    allowed = set(allowed_columns)
    return {key: value for key, value in row.items() if key in allowed}


def merge_rows(
    base_row: Mapping[str, Any],
    incoming_row: Mapping[str, Any],
    *,
    overwrite_non_null: bool = False,
) -> Row:
    merged = dict(base_row)

    for key, value in incoming_row.items():
        if key not in merged:
            merged[key] = value
            continue

        if overwrite_non_null:
            merged[key] = value
            continue

        if merged[key] is None and value is not None:
            merged[key] = value

    return merged


def row_missing_required(
    row: Mapping[str, Any],
    required_columns: Iterable[str],
) -> list[str]:
    missing = []
    for column in required_columns:
        if column not in row or row[column] is None:
            missing.append(column)
    return missing