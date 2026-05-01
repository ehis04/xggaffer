"""
Shared utility functions used across service modules.

Functions here are pure, stdlib-only helpers with no project-level imports, so
they can be safely imported from any service layer without risk of circular
dependencies.
"""

from __future__ import annotations

import re
import unicodedata
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

def upsert_record(model_class, lookup_kwargs, field_values):
    """Generic ORM upsert. Returns (instance, created, updated).

    Looks up a record by lookup_kwargs. If missing, creates it with both
    lookup_kwargs and field_values set. If found, diffs field_values against
    current values and saves only changed fields.
    """
    instance = model_class.objects.filter(**lookup_kwargs).first()

    if not instance:
        instance = model_class(**lookup_kwargs)
        for k, v in field_values.items():
            setattr(instance, k, v)
        instance.save()
        return instance, True, False

    changed = [k for k, v in field_values.items() if getattr(instance, k) != v]
    for k in changed:
        setattr(instance, k, field_values[k])
    if changed:
        instance.save(update_fields=changed)
        return instance, False, True

    return instance, False, False


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


def normalise_lookup_name(value: str | None) -> str:
    """Normalise free-text names for deterministic matching.

    Uses Unicode decomposition + accent removal, case folding, punctuation
    stripping, and whitespace collapsing.
    """
    text = unicodedata.normalize("NFKD", (value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())