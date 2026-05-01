from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from data_collection.core.enums import (
        SOURCE_UNDERSTAT,
        SOURCE_SOFASCORE,
        SOURCE_WHOSCORED,
        DATASET_MATCHES,
        DATASET_PLAYERS,
        DATASET_TEAMS,
        DATASET_TEAM_SUMMARIES,
    )
except ImportError:
    SOURCE_UNDERSTAT = "understat"
    SOURCE_SOFASCORE = "sofascore"
    SOURCE_WHOSCORED = "whoscored"
    DATASET_MATCHES = "matches"
    DATASET_PLAYERS = "players"
    DATASET_TEAMS = "teams"
    DATASET_TEAM_SUMMARIES = "team_summaries"


@dataclass(frozen=True)
class SourceCapability:
    name: str
    display_name: str
    supported_datasets: tuple[str, ...]
    strengths: tuple[str, ...]
    id_quality: str
    primary_stat_ownership_families: tuple[str, ...]
    writes_raw_first: bool
    transforms_to_canonical_schema: bool
    cross_source_join_requires_reconciliation: bool
    source_ids_are_universal: bool
    notes: str = ""
    enabled: bool = True


SOURCE_CAPABILITIES: dict[str, SourceCapability] = {
    SOURCE_UNDERSTAT: SourceCapability(
        name=SOURCE_UNDERSTAT,
        display_name="Understat",
        supported_datasets=(
            DATASET_MATCHES,
            DATASET_PLAYERS,
            DATASET_TEAMS,
            DATASET_TEAM_SUMMARIES,
        ),
        strengths=(
            "xg",
            "npxg",
            "xa",
            "xpts",
            "shots",
            "shot locations",
            "shot types",
            "attacking context",
            "chance quality",
            "team summary context",
        ),
        id_quality="source-specific",
        primary_stat_ownership_families=(
            "xg-family",
            "shot-detail-family",
            "attacking-context-family",
            "team-summary-context-family",
        ),
        writes_raw_first=True,
        transforms_to_canonical_schema=True,
        cross_source_join_requires_reconciliation=True,
        source_ids_are_universal=False,
        notes=(
            "Primary analytics source for xG-family, shot-detail, and attacking-context "
            "metrics. Team summaries remain Understat-owned for now."
        ),
    ),
    SOURCE_SOFASCORE: SourceCapability(
        name=SOURCE_SOFASCORE,
        display_name="Sofascore",
        supported_datasets=(
            DATASET_MATCHES,
            DATASET_PLAYERS,
            DATASET_TEAMS,
        ),
        strengths=(
            "broader match stats",
            "possession",
            "corners",
            "fouls",
            "cards",
            "saves",
            "tackles",
            "interceptions",
            "clearances",
            "duels",
            "aerial duels",
            "defensive contributions",
            "control metrics",
        ),
        id_quality="source-specific",
        primary_stat_ownership_families=(
            "possession-family",
            "defensive-family",
            "control-metrics-family",
            "broader-match-stats-family",
        ),
        writes_raw_first=True,
        transforms_to_canonical_schema=True,
        cross_source_join_requires_reconciliation=True,
        source_ids_are_universal=False,
        notes=(
            "Secondary source used to expand beyond Understat where broader match, team, "
            "and player defensive/control metrics are useful."
        ),
    ),
    SOURCE_WHOSCORED: SourceCapability(
        name=SOURCE_WHOSCORED,
        display_name="WhoScored",
        supported_datasets=(
            DATASET_MATCHES,
            DATASET_PLAYERS,
            DATASET_TEAMS,
        ),
        strengths=(
            "match events",
            "key passes",
            "dribbles",
            "touches",
            "aerial duels",
            "player ratings",
            "defensive actions",
            "attacking contributions",
        ),
        id_quality="source-specific",
        primary_stat_ownership_families=(
            "match-events-family",
            "player-ratings-family",
            "defensive-actions-family",
        ),
        writes_raw_first=True,
        transforms_to_canonical_schema=True,
        cross_source_join_requires_reconciliation=True,
        source_ids_are_universal=False,
        notes=(
            "Match events and detailed player ratings from WhoScored via soccerdata. "
            "Supplements Understat xG and SofaScore broader stats."
        ),
        enabled=True,
    ),
    "fbref": SourceCapability(
        name="fbref",
        display_name="FBref",
        supported_datasets=(),
        strengths=(),
        id_quality="source-specific",
        primary_stat_ownership_families=(),
        writes_raw_first=True,
        transforms_to_canonical_schema=True,
        cross_source_join_requires_reconciliation=True,
        source_ids_are_universal=False,
        notes="Reserved future source placeholder.",
        enabled=False,
    ),
}


def get_source_capability(source: str) -> SourceCapability:
    key = normalise_source_name(source)

    if key not in SOURCE_CAPABILITIES:
        raise KeyError(f"Unsupported source: {source}")

    return SOURCE_CAPABILITIES[key]


def get_enabled_sources() -> list[str]:
    return sorted(
        source_name
        for source_name, capability in SOURCE_CAPABILITIES.items()
        if capability.enabled
    )


def get_all_sources() -> list[str]:
    return sorted(SOURCE_CAPABILITIES.keys())


def get_supported_datasets_for_source(source: str) -> list[str]:
    capability = get_source_capability(source)
    return list(capability.supported_datasets)


def source_supports_dataset(source: str, dataset: str) -> bool:
    capability = get_source_capability(source)
    dataset_name = normalise_dataset_name(dataset)
    return dataset_name in {
        normalise_dataset_name(item)
        for item in capability.supported_datasets
    }


def get_source_strengths(source: str) -> list[str]:
    capability = get_source_capability(source)
    return list(capability.strengths)


def get_primary_stat_ownership_families(source: str) -> list[str]:
    capability = get_source_capability(source)
    return list(capability.primary_stat_ownership_families)


def get_sources_for_dataset(dataset: str, enabled_only: bool = True) -> list[str]:
    dataset_name = normalise_dataset_name(dataset)

    sources: list[str] = []

    for source_name, capability in SOURCE_CAPABILITIES.items():
        if enabled_only and not capability.enabled:
            continue

        supported = {
            normalise_dataset_name(item)
            for item in capability.supported_datasets
        }
        if dataset_name in supported:
            sources.append(source_name)

    return sorted(sources)


def get_enabled_source_capabilities() -> dict[str, SourceCapability]:
    return {
        source_name: capability
        for source_name, capability in SOURCE_CAPABILITIES.items()
        if capability.enabled
    }


def build_source_capability_summary() -> dict[str, Any]:
    enabled_capabilities = get_enabled_source_capabilities()

    return {
        "enabled_sources": sorted(enabled_capabilities.keys()),
        "all_sources": get_all_sources(),
        "datasets_by_source": {
            source_name: list(capability.supported_datasets)
            for source_name, capability in enabled_capabilities.items()
        },
        "strengths_by_source": {
            source_name: list(capability.strengths)
            for source_name, capability in enabled_capabilities.items()
        },
        "primary_stat_ownership_by_source": {
            source_name: list(capability.primary_stat_ownership_families)
            for source_name, capability in enabled_capabilities.items()
        },
    }


def validate_source_capabilities() -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    for source_name, capability in SOURCE_CAPABILITIES.items():
        if capability.enabled and not capability.supported_datasets:
            warnings.append(
                f'Enabled source "{source_name}" has no supported datasets configured.'
            )

        if capability.source_ids_are_universal:
            errors.append(
                f'Source "{source_name}" incorrectly treats source IDs as universal.'
            )

        if not capability.writes_raw_first:
            errors.append(
                f'Source "{source_name}" does not enforce raw-first output.'
            )

        if not capability.transforms_to_canonical_schema:
            errors.append(
                f'Source "{source_name}" does not enforce canonical transformation.'
            )

        if not capability.cross_source_join_requires_reconciliation:
            errors.append(
                f'Source "{source_name}" allows cross-source joins without reconciliation.'
            )

        if capability.enabled and not capability.primary_stat_ownership_families:
            warnings.append(
                f'Enabled source "{source_name}" has no primary stat ownership families listed.'
            )

    return {
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total_sources": len(SOURCE_CAPABILITIES),
            "enabled_sources": get_enabled_sources(),
        },
    }


def normalise_source_name(source: str) -> str:
    return str(source).strip().lower()


def normalise_dataset_name(dataset: str) -> str:
    return str(dataset).strip().lower()