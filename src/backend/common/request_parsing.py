from __future__ import annotations

from rest_framework.exceptions import ValidationError


TRUTHY_VALUES = {"1", "true", "yes", "y"}
FALSY_VALUES = {"0", "false", "no", "n"}


def parse_optional_int(value, *, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({field_name: "Must be an integer."}) from exc


def parse_positive_int_or_default(value, *, default: int, field_name: str) -> int:
    if value in (None, ""):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({field_name: "Must be an integer."}) from exc
    if parsed <= 0:
        raise ValidationError({field_name: "Must be greater than 0."})
    return parsed


def parse_bool_or_default(value, *, default: bool, field_name: str) -> bool:
    if value in (None, ""):
        return default

    normalized = str(value).strip().lower()
    if normalized in TRUTHY_VALUES:
        return True
    if normalized in FALSY_VALUES:
        return False

    raise ValidationError({field_name: "Must be a boolean."})