"""
Shared utility functions used across service modules.

Functions here are pure, stdlib-only helpers with no project-level imports, so
they can be safely imported from any service layer without risk of circular
dependencies.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from django.utils import timezone


# ---------------------------------------------------------------------------
# Numeric serialisation
# ---------------------------------------------------------------------------

def serialise_numeric(value: Decimal | int | float | None) -> int | float | None:
    """Convert a Decimal or numeric value to a JSON-serialisable Python type.

    Returns float for Decimal values, preserves int/float as-is, and passes
    None through unchanged.
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


# ---------------------------------------------------------------------------
# Datetime utilities
# ---------------------------------------------------------------------------

def latest_datetime(*values: datetime | None) -> datetime | None:
    """Return the most recent non-None datetime from the given arguments.

    Returns None if every argument is None.
    """
    present_values = [v for v in values if v is not None]
    return max(present_values) if present_values else None

def utcnow():
    return timezone.now()


def iso_or_none(value) -> str | None:
    """Return the ISO-8601 string representation of a datetime, or None."""
    if value is None:
        return None
    return value.isoformat()


def age_seconds(dt) -> float:
    if dt is None:
        return float('inf')
    return (utcnow() - dt).total_seconds()


def is_older_than(dt, threshold_seconds: float) -> bool:
    return age_seconds(dt) > threshold_seconds


def latest_of(*datetimes):
    candidates = [d for d in datetimes if d is not None]
    return max(candidates) if candidates else None


# ---------------------------------------------------------------------------
# Football season utilities
# ---------------------------------------------------------------------------

def current_football_season() -> str:
    """Return the starting year of the current football season as a string.

    Seasons run roughly August–May, so before August we are still in the
    season that started the previous calendar year.

    Examples:
        April 2026   → "2025"  (2025/26 season)
        October 2025 → "2025"  (2025/26 season)
        March 2025   → "2024"  (2024/25 season)
    """
    now = utcnow()
    return str(now.year if now.month >= 8 else now.year - 1)