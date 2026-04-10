from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any


def clean_optional_str(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = str(value).strip()
    return cleaned or None


def normalise_season_label(
    *,
    season_label: str | None = None,
    season: str | None = None,
) -> str | None:
    return clean_optional_str(season_label) or clean_optional_str(season)


def normalise_order_by(
    *,
    order_by: str | None = None,
    ordering: str | None = None,
    default: str,
) -> str:
    cleaned_order_by = clean_optional_str(order_by)
    if cleaned_order_by:
        return cleaned_order_by

    cleaned_ordering = clean_optional_str(ordering)
    if cleaned_ordering:
        return cleaned_ordering

    return default


def competition_label(
    competition_name: str | None,
    competition_code: str | None,
) -> str:
    if competition_name:
        return competition_name
    if competition_code:
        return competition_code
    return "this competition"


def format_int(value: int | None) -> str:
    return f"{value:,}" if value is not None else "0"


def format_number(
    value: Decimal | int | float | None,
    *,
    decimal_places: int = 1,
    none_label: str = "N/A",
) -> str:
    if value is None:
        return none_label

    if isinstance(value, Decimal):
        return f"{value:.{decimal_places}f}"

    if isinstance(value, float):
        return f"{value:.{decimal_places}f}"

    return f"{value:,}"


def format_decimal(
    value: Decimal | float | None,
    *,
    decimal_places: int = 1,
) -> str | None:
    if value is None:
        return None
    return f"{value:.{decimal_places}f}"


def format_datetime_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M UTC")


def latest_datetime(*values: datetime | None) -> datetime | None:
    present_values = [value for value in values if value is not None]
    return max(present_values) if present_values else None


def resolve_ordering(
    *,
    allowed_fields: dict[str, tuple[str, ...]],
    order_by: str,
    descending: bool,
) -> list[str]:
    if order_by not in allowed_fields:
        allowed = ", ".join(sorted(allowed_fields.keys()))
        raise ValueError(
            f"Unsupported order_by '{order_by}'. Allowed values: {allowed}"
        )

    prefix = "-" if descending else ""
    return [f"{prefix}{field}" for field in allowed_fields[order_by]]


def serialise_numeric(value: Decimal | int | float | None) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


def build_metric_payload(
    *,
    key: str,
    label: str,
    value: Decimal | int | float | None,
    unit: str | None = None,
    rank: int | None = None,
    percentile: float | None = None,
    sample_size: int | None = None,
) -> dict[str, Any]:
    if isinstance(value, Decimal):
        formatted_value = format_decimal(value)
    else:
        formatted_value = None if value is None else str(value)

    return {
        "key": key,
        "label": label,
        "value": serialise_numeric(value),
        "formatted_value": formatted_value,
        "unit": unit,
        "rank": rank,
        "percentile": percentile,
        "sample_size": sample_size,
        "is_available": value is not None,
    }


def build_provider_coverage_payload(
    *,
    provider: str,
    last_synced_at: datetime | None,
    source_updated_at: datetime | None = None,
    updated_at: datetime | None = None,
    matches_sampled: int | None = None,
    minutes_sampled: int | None = None,
    coverage_notes: list[str] | None = None,
) -> dict[str, Any]:
    notes = list(coverage_notes or [])

    if last_synced_at is not None:
        coverage_status = "available"
        freshness_label = "synced"
    elif updated_at is not None:
        coverage_status = "available"
        freshness_label = "stored"
        notes.append("No explicit sync timestamp is stored; using updated_at instead.")
    else:
        coverage_status = "unknown"
        freshness_label = "unknown"
        notes.append("No sync or updated timestamp is stored.")

    return {
        "provider": provider,
        "has_data": True,
        "coverage_status": coverage_status,
        "freshness_label": freshness_label,
        "source_updated_at": source_updated_at,
        "last_synced_at": last_synced_at,
        "matches_sampled": matches_sampled,
        "minutes_sampled": minutes_sampled,
        "coverage_notes": notes,
    }


def metric_difference(
    left_value: Decimal | int,
    right_value: Decimal | int,
) -> Decimal | int:
    return left_value - right_value


def winner_for_metric(
    *,
    left_name: str,
    right_name: str,
    left_value: Decimal | int | None,
    right_value: Decimal | int | None,
    direction: str,
) -> tuple[str | None, bool, bool, Decimal | int | None]:
    if left_value is None or right_value is None:
        return None, False, False, None

    if left_value == right_value:
        return None, True, True, metric_difference(left_value, right_value)

    if direction == "higher":
        return (
            left_name if left_value > right_value else right_name,
            False,
            True,
            metric_difference(left_value, right_value),
        )

    if direction == "lower":
        return (
            left_name if left_value < right_value else right_name,
            False,
            True,
            metric_difference(left_value, right_value),
        )

    raise ValueError(f"Unsupported comparison direction: {direction}")


def values_equal(left: Any, right: Any) -> bool:
    return left == right