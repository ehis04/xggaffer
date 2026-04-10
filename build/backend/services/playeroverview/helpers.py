from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any


GENERAL_METRIC_KEYS = ["matches_played", "minutes_played"]

DEFAULT_FOCUS_KEYS = [
    "goals",
    "assists",
    "xg",
    "xa",
    "shots",
    "key_passes",
    "npg",
    "npxg",
]

FORWARD_FOCUS_KEYS = [
    "goals",
    "xg",
    "shots",
    "npg",
    "npxg",
    "assists",
    "xa",
    "key_passes",
]

MIDFIELDER_FOCUS_KEYS = [
    "assists",
    "xa",
    "key_passes",
    "minutes_played",
    "matches_played",
    "xg",
    "goals",
    "shots",
    "npg",
    "npxg",
]

DEFENDER_FOCUS_KEYS = [
    "minutes_played",
    "matches_played",
    "clean_sheets",
    "tackles",
    "interceptions",
    "blocks",
    "clearances",
    "aerial_duels_won",
    "duels_won",
    "assists",
    "key_passes",
    "goals",
    "xg",
    "xa",
    "shots",
]

GOALKEEPER_FOCUS_KEYS = [
    "minutes_played",
    "matches_played",
    "clean_sheets",
    "saves",
    "save_percentage",
    "goals_conceded",
]

ADDITIONAL_METRIC_FALLBACK_KEYS = [
    "yellow_cards",
    "red_cards",
    "fouls",
    "offsides",
    "dribbles",
    "touches",
    "passes",
    "pass_accuracy",
]

FORWARD_TOKENS = {"FW", "FWD", "CF", "ST", "SS", "LW", "RW", "LF", "RF", "ATT", "FORWARD", "STRIKER", "WINGER"}
MIDFIELDER_TOKENS = {"MF", "MID", "CM", "DM", "AM", "CAM", "CDM", "LM", "RM", "MIDFIELDER"}
DEFENDER_TOKENS = {"DF", "DEF", "CB", "LB", "RB", "LWB", "RWB", "WB", "DEFENDER", "CENTRE-BACK", "CENTER-BACK", "FULL-BACK"}
GOALKEEPER_TOKENS = {"GK", "GOALKEEPER", "KEEPER"}

METRIC_SOURCE_RULES = {
    "matches_played": {
        "metric_key": "matches_played",
        "concept": "usage",
        "primary_source": "playerdata",
        "preferred_provider": None,
        "reason": "Use one main displayed value for basic usage metrics in the merged overview.",
    },
    "minutes_played": {
        "metric_key": "minutes_played",
        "concept": "usage",
        "primary_source": "playerdata",
        "preferred_provider": None,
        "reason": "Use one main displayed value for basic usage metrics in the merged overview.",
    },
    "goals": {
        "metric_key": "goals",
        "concept": "end_product",
        "primary_source": "playerdata",
        "preferred_provider": None,
        "reason": "Keep one primary end-product value rather than duplicating provider blocks.",
    },
    "assists": {
        "metric_key": "assists",
        "concept": "end_product",
        "primary_source": "playerdata",
        "preferred_provider": None,
        "reason": "Keep one primary end-product value rather than duplicating provider blocks.",
    },
    "shots": {
        "metric_key": "shots",
        "concept": "advanced_attacking",
        "primary_source": "playerdata",
        "preferred_provider": "understat",
        "reason": "Prefer Understat-backed advanced attacking metrics where clearly stronger.",
    },
    "xg": {
        "metric_key": "xg",
        "concept": "advanced_attacking",
        "primary_source": "playerdata",
        "preferred_provider": "understat",
        "reason": "Prefer Understat-backed advanced attacking metrics where clearly stronger.",
    },
    "xa": {
        "metric_key": "xa",
        "concept": "advanced_attacking",
        "primary_source": "playerdata",
        "preferred_provider": "understat",
        "reason": "Prefer Understat-backed advanced attacking metrics where clearly stronger.",
    },
    "npg": {
        "metric_key": "npg",
        "concept": "advanced_attacking",
        "primary_source": "playerdata",
        "preferred_provider": "understat",
        "reason": "Prefer Understat-backed advanced attacking metrics where clearly stronger.",
    },
    "npxg": {
        "metric_key": "npxg",
        "concept": "advanced_attacking",
        "primary_source": "playerdata",
        "preferred_provider": "understat",
        "reason": "Prefer Understat-backed advanced attacking metrics where clearly stronger.",
    },
    "key_passes": {
        "metric_key": "key_passes",
        "concept": "creative_output",
        "primary_source": "playerdata",
        "preferred_provider": "understat",
        "reason": "Prefer the stronger attacking and creative event source where available.",
    },
}

OVERVIEW_SOURCE_PREFERENCE_RULES = [
    {
        "key": "context",
        "primary_source": "livefootball",
        "preferred_provider": "football-data",
        "reason": "Use livefootball for competition, team, and player discovery context.",
    },
    {
        "key": "advanced_attacking_metrics",
        "primary_source": "playerdata",
        "preferred_provider": "understat",
        "reason": "Prefer Understat-backed advanced attacking metrics where clearly appropriate.",
    },
    {
        "key": "primary_metric_display",
        "primary_source": "merged",
        "preferred_provider": None,
        "reason": "Use one main displayed value per concept where possible.",
    },
    {
        "key": "coverage_and_gaps",
        "primary_source": "merged",
        "preferred_provider": None,
        "reason": "Expose coverage, freshness, and missing-data honesty rather than hiding gaps.",
    },
]


def clean_optional_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def first_non_empty_str(*values: Any) -> str | None:
    for value in values:
        cleaned = clean_optional_str(value)
        if cleaned:
            return cleaned
    return None


def serialise_numeric(value: Decimal | int | float | None) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


def format_number(value: Decimal | int | float | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        value = value.normalize()
        text = format(value, "f")
        return text.rstrip("0").rstrip(".") if "." in text else text
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{value:,}"


def latest_datetime(*values: datetime | None) -> datetime | None:
    available_values = [value for value in values if value is not None]
    return max(available_values) if available_values else None


def get_player_display_name(player: Any) -> str:
    for attribute in ("display_name", "full_name"):
        value = clean_optional_str(getattr(player, attribute, ""))
        if value:
            return value

    first_name = clean_optional_str(getattr(player, "first_name", ""))
    last_name = clean_optional_str(getattr(player, "last_name", ""))
    full_name = f"{first_name} {last_name}".strip()
    if full_name:
        return full_name
    return f"Player {player.id}"


def get_player_age(player: Any, *, fallback_date_of_birth: date | None = None) -> int | None:
    date_of_birth = getattr(player, "date_of_birth", None) or fallback_date_of_birth
    if not date_of_birth:
        return None

    today = date.today()
    years = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return years


def normalise_position(value: str | None) -> str:
    raw = clean_optional_str(value)
    if not raw:
        return "unknown"

    upper = raw.upper().replace("_", " ").replace("/", " ").replace("-", " ")
    tokens = {token for token in upper.split() if token}
    tokens.add(upper)

    if tokens & GOALKEEPER_TOKENS:
        return "goalkeeper"
    if tokens & DEFENDER_TOKENS:
        return "defender"
    if tokens & MIDFIELDER_TOKENS:
        return "midfielder"
    if tokens & FORWARD_TOKENS:
        return "forward"
    return "unknown"


def get_position_metric_priority(position: str | None) -> list[str]:
    normalised_position = normalise_position(position)

    if normalised_position == "forward":
        return [*GENERAL_METRIC_KEYS, *FORWARD_FOCUS_KEYS, *ADDITIONAL_METRIC_FALLBACK_KEYS]
    if normalised_position == "midfielder":
        return [*GENERAL_METRIC_KEYS, *MIDFIELDER_FOCUS_KEYS, *ADDITIONAL_METRIC_FALLBACK_KEYS]
    if normalised_position == "defender":
        return [*GENERAL_METRIC_KEYS, *DEFENDER_FOCUS_KEYS, *ADDITIONAL_METRIC_FALLBACK_KEYS]
    if normalised_position == "goalkeeper":
        return [*GENERAL_METRIC_KEYS, *GOALKEEPER_FOCUS_KEYS, *ADDITIONAL_METRIC_FALLBACK_KEYS]
    return [*GENERAL_METRIC_KEYS, *DEFAULT_FOCUS_KEYS, *ADDITIONAL_METRIC_FALLBACK_KEYS]


def get_focus_group_spec(position: str | None) -> tuple[str, list[str]]:
    normalised_position = normalise_position(position)

    if normalised_position == "forward":
        return "Attacking output", FORWARD_FOCUS_KEYS
    if normalised_position == "midfielder":
        return "Creative and possession output", MIDFIELDER_FOCUS_KEYS
    if normalised_position == "defender":
        return "Usage and contribution", DEFENDER_FOCUS_KEYS
    if normalised_position == "goalkeeper":
        return "Goalkeeper overview", GOALKEEPER_FOCUS_KEYS
    return "Primary metrics", DEFAULT_FOCUS_KEYS


def sort_metric_dicts(metrics: list[dict[str, Any]], *, position: str | None) -> list[dict[str, Any]]:
    priority_keys = get_position_metric_priority(position)
    priority_index = {key: index for index, key in enumerate(priority_keys)}

    def sort_key(item: dict[str, Any]) -> tuple[int, str]:
        metric_key = clean_optional_str(item.get("key"))
        return (
            priority_index.get(metric_key, len(priority_index) + 1000),
            metric_key,
        )

    return sorted(metrics, key=sort_key)


def group_metric_dicts(metrics: list[dict[str, Any]], *, position: str | None) -> list[dict[str, Any]]:
    if not metrics:
        return []

    ordered_metrics = sort_metric_dicts(metrics, position=position)
    metric_map = {metric["key"]: metric for metric in ordered_metrics if metric.get("key")}
    focus_label, focus_keys = get_focus_group_spec(position)

    groups: list[dict[str, Any]] = []

    general_metrics = [metric_map[key] for key in GENERAL_METRIC_KEYS if key in metric_map]
    if general_metrics:
        groups.append(
            {
                "key": "general",
                "label": "General overview",
                "metrics": general_metrics,
            }
        )

    focus_metrics = [
        metric_map[key]
        for key in focus_keys
        if key in metric_map and key not in GENERAL_METRIC_KEYS
    ]
    if focus_metrics:
        groups.append(
            {
                "key": "role_focus",
                "label": focus_label,
                "metrics": focus_metrics,
            }
        )

    used_keys = set(GENERAL_METRIC_KEYS) | set(focus_keys)
    additional_metrics = [
        metric for metric in ordered_metrics if metric.get("key") not in used_keys
    ]
    if additional_metrics:
        groups.append(
            {
                "key": "additional",
                "label": "Additional metrics",
                "metrics": additional_metrics,
            }
        )

    return groups


def derive_freshness_label(
    *,
    has_data: bool,
    last_synced_at: datetime | None = None,
    source_updated_at: datetime | None = None,
) -> str:
    if not has_data:
        return "unknown"
    if last_synced_at is not None:
        return "synced"
    if source_updated_at is not None:
        return "updated"
    return "stored"


def build_no_data_provider_block(*, source: str, coverage_notes: list[str] | None = None) -> dict[str, Any]:
    return {
        "source": source,
        "has_data": False,
        "coverage_status": "missing",
        "freshness_label": "unknown",
        "source_updated_at": None,
        "last_synced_at": None,
        "matches_sampled": None,
        "minutes_sampled": None,
        "coverage_notes": coverage_notes or [],
    }


def build_source_detail_block(
    *,
    source: str,
    has_data: bool,
    provider: str | None = None,
    providers: list[str] | None = None,
    source_updated_at: datetime | None = None,
    last_synced_at: datetime | None = None,
    matches_sampled: int | None = None,
    minutes_sampled: int | None = None,
    coverage_notes: list[str] | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    detail = {
        "source": source,
        "provider": provider,
        "has_data": has_data,
        "coverage_status": "available" if has_data else "missing",
        "freshness_label": derive_freshness_label(
            has_data=has_data,
            last_synced_at=last_synced_at,
            source_updated_at=source_updated_at,
        ),
        "source_updated_at": source_updated_at,
        "last_synced_at": last_synced_at,
        "matches_sampled": matches_sampled,
        "minutes_sampled": minutes_sampled,
        "coverage_notes": coverage_notes or [],
    }
    if providers:
        detail["providers"] = providers
    if extra_fields:
        detail.update(extra_fields)
    return detail


def build_provider_coverage_block(
    source_details: dict[str, dict[str, Any]],
    *,
    matches_sampled: int | None = None,
    minutes_sampled: int | None = None,
) -> dict[str, Any]:
    available_sources = [
        source_name
        for source_name, detail in source_details.items()
        if detail.get("has_data")
    ]
    missing_sources = [
        source_name
        for source_name, detail in source_details.items()
        if not detail.get("has_data")
    ]

    latest_synced_at = latest_datetime(
        *(detail.get("last_synced_at") for detail in source_details.values())
    )
    latest_updated_at = latest_datetime(
        *(detail.get("source_updated_at") for detail in source_details.values())
    )

    if len(available_sources) == len(source_details) and source_details:
        coverage_status = "available"
    elif available_sources:
        coverage_status = "partial"
    else:
        coverage_status = "missing"

    freshness_label = derive_freshness_label(
        has_data=bool(available_sources),
        last_synced_at=latest_synced_at,
        source_updated_at=latest_updated_at,
    )

    coverage_notes: list[str] = []
    seen_notes: set[str] = set()
    for detail in source_details.values():
        for note in detail.get("coverage_notes", []):
            cleaned_note = clean_optional_str(note)
            if cleaned_note and cleaned_note not in seen_notes:
                seen_notes.add(cleaned_note)
                coverage_notes.append(cleaned_note)

    return {
        "provider": "merged",
        "has_data": bool(available_sources),
        "coverage_status": coverage_status,
        "freshness_label": freshness_label,
        "source_updated_at": latest_updated_at,
        "last_synced_at": latest_synced_at,
        "matches_sampled": matches_sampled,
        "minutes_sampled": minutes_sampled,
        "coverage_notes": coverage_notes,
        "available_sources": available_sources,
        "missing_sources": missing_sources,
        "source_count": len(source_details),
        "available_source_count": len(available_sources),
        "missing_source_count": len(missing_sources),
        "source_details": source_details,
    }


def get_metric_source_rule(metric_key: str | None) -> dict[str, Any]:
    key = clean_optional_str(metric_key)
    rule = METRIC_SOURCE_RULES.get(key)
    if rule is not None:
        return dict(rule)

    return {
        "metric_key": key or None,
        "concept": "general",
        "primary_source": "playerdata",
        "preferred_provider": None,
        "reason": "Use one deterministic merged value per concept where possible.",
    }


def apply_metric_source_preference(
    metric: dict[str, Any],
    *,
    available_provider: str | None = None,
) -> dict[str, Any]:
    metric_copy = dict(metric)
    rule = get_metric_source_rule(metric_copy.get("key"))

    preferred_provider = available_provider or rule.get("preferred_provider")
    metric_copy["source"] = rule.get("primary_source")
    metric_copy["preferred_provider"] = preferred_provider
    metric_copy["source_preference"] = {
        "concept": rule.get("concept"),
        "primary_source": rule.get("primary_source"),
        "preferred_provider": rule.get("preferred_provider"),
        "reason": rule.get("reason"),
    }
    return metric_copy


def build_source_preference_block(*, available_sources: list[str] | None = None) -> dict[str, Any]:
    available_sources = available_sources or []

    return {
        "available_sources": available_sources,
        "rules": [dict(rule) for rule in OVERVIEW_SOURCE_PREFERENCE_RULES],
        "metric_rules": [dict(rule) for rule in METRIC_SOURCE_RULES.values()],
    }