"""
Helper functions for the playerdata service layer.

Handles cleaning values, formatting numbers and dates, building standard API payloads, and supporting player and club comparisons.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from common.utils import latest_datetime, serialise_numeric  # noqa: F401 – re-exported for callers

# Numeric fields available on PlayerSeasonEnrichment that can receive percentile ranks
_PERCENTILE_FIELDS: list[str] = [
    "goals",
    "assists",
    "shots",
    "xg",
    "xa",
    "npg",
    "npxg",
    "key_passes",
    "minutes_played",
    "matches_played",
]


def compute_league_percentiles(
    *,
    player_id: int,
    season_label: str | None,
    competition_code: str | None,
) -> dict[str, float | None]:
    """Return a dict mapping metric key → percentile rank (0-100) for the given player.

    Percentile rank is computed against all PlayerSeasonEnrichment rows that share
    the same season_label and competition_code.  Returns an empty dict if fewer
    than two rows are found (percentiles are meaningless with a single data point).
    """
    from apps.playerdata.models import PlayerSeasonEnrichment  # local import to avoid circular

    qs = PlayerSeasonEnrichment.objects.all()
    if season_label:
        qs = qs.filter(season_label=season_label)
    if competition_code:
        qs = qs.filter(competition_code=competition_code)

    rows = list(qs.values("player_id", *_PERCENTILE_FIELDS))
    if len(rows) < 2:
        return {}

    # Build per-metric sorted value lists
    metric_values: dict[str, list[float]] = {}
    for field in _PERCENTILE_FIELDS:
        vals = [float(r[field]) for r in rows if r.get(field) is not None]
        if vals:
            metric_values[field] = sorted(vals)

    # Find the current player's row(s); pick the first match
    player_rows = [r for r in rows if r["player_id"] == player_id]
    if not player_rows:
        return {}
    player_row = player_rows[0]

    percentiles: dict[str, float | None] = {}
    for field in _PERCENTILE_FIELDS:
        raw = player_row.get(field)
        if raw is None or field not in metric_values:
            percentiles[field] = None
            continue
        val = float(raw)
        sorted_vals = metric_values[field]
        n = len(sorted_vals)
        # Count how many values are strictly below this one
        below = sum(1 for v in sorted_vals if v < val)
        percentiles[field] = (below / n) * 100.0

    return percentiles


# ---------------------------------------------------------------------------
# String utilities
# ---------------------------------------------------------------------------

# Trim a string and return None if it is empty
def clean_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None

# Pick the season label from either season_label or season
def normalise_season_label(
    *,
    season_label: str | None = None,
    season: str | None = None,
) -> str | None:

    return clean_optional_str(season_label) or clean_optional_str(season)

# Pick the ordering field from order_by, ordering, or the default value
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

#  Return the best display label for a competition using its name(preferable) or code
def competition_label(
    competition_name: str | None,
    competition_code: str | None,
) -> str:
    if competition_name:
        return competition_name
    if competition_code:
        return competition_code
    return "this competition"


# ---------------------------------------------------------------------------
# Numeric formatting
# ---------------------------------------------------------------------------

# Format an integer with commas, or return '0' when the value is missing
def format_int(value: int | None) -> str:
    return f"{value:,}" if value is not None else "0"

# Format a number for display, with support for decimals, integers, and missing values
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

# Format a decimal number to a fixed number of places
def format_decimal(
    value: Decimal | float | None,
    *,
    decimal_places: int = 1,
) -> str | None:
    if value is None:
        return None
    return f"{value:.{decimal_places}f}"

# Format a datetime as a UTC display string
def format_datetime_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M UTC")


# ---------------------------------------------------------------------------
# Ordering resolution
# ---------------------------------------------------------------------------

# Build the ORM ordering list from an allowed field and sort direction
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


# ---------------------------------------------------------------------------
# Metric payload construction
# ---------------------------------------------------------------------------

# Build a standard metric dictionary for API responses
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


# ---------------------------------------------------------------------------
# Provider coverage payload construction
# ---------------------------------------------------------------------------

# Build a dictionary showing provider freshness and coverage details
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


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

# Return the difference between two metric values
def metric_difference(
    left_value: Decimal | int,
    right_value: Decimal | int,
) -> Decimal | int:
    return left_value - right_value

# Decide which side wins a metric comparison and return the result detai
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

# Return True when both values are equal
def values_equal(left: Any, right: Any) -> bool:
    return left == right
