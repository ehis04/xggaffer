from __future__ import annotations

from dataclasses import dataclass
import importlib
from typing import Any

try:
    from data_collection.config.sources import SOURCE_UNDERSTAT, SOURCE_SOFASCORE, SOURCE_WHOSCORED
except ImportError:
    SOURCE_UNDERSTAT = "understat"
    SOURCE_SOFASCORE = "sofascore"
    SOURCE_WHOSCORED = "whoscored"

try:
    from data_collection.core.enums import (
        DATASET_MATCHES,
        DATASET_PLAYERS,
        DATASET_TEAMS,
        DATASET_TEAM_SUMMARIES,
    )
except ImportError:
    DATASET_MATCHES = "matches"
    DATASET_PLAYERS = "players"
    DATASET_TEAMS = "teams"
    DATASET_TEAM_SUMMARIES = "team_summaries"


@dataclass(frozen=True)
class SourceDatasetContract:
    source: str
    dataset: str
    extractor_import_path: str
    transformer_import_path: str
    writes_raw_first: bool = True
    transforms_to_canonical_schema: bool = True
    cross_source_join_requires_reconciliation: bool = True
    source_ids_are_universal: bool = False
    source_specific_stats_optional: bool = True


SOURCE_DATASET_CONTRACTS: dict[tuple[str, str], SourceDatasetContract] = {
    (SOURCE_UNDERSTAT, DATASET_MATCHES): SourceDatasetContract(
        source=SOURCE_UNDERSTAT,
        dataset=DATASET_MATCHES,
        extractor_import_path=(
            "data_collection.extractors.understat.matches:fetch_understat_matches"
        ),
        transformer_import_path=(
            "data_collection.transformers.understat.matches:transform_understat_matches"
        ),
    ),
    (SOURCE_UNDERSTAT, DATASET_PLAYERS): SourceDatasetContract(
        source=SOURCE_UNDERSTAT,
        dataset=DATASET_PLAYERS,
        extractor_import_path=(
            "data_collection.extractors.understat.players:fetch_understat_players"
        ),
        transformer_import_path=(
            "data_collection.transformers.understat.players:transform_understat_players"
        ),
    ),
    (SOURCE_UNDERSTAT, DATASET_TEAMS): SourceDatasetContract(
        source=SOURCE_UNDERSTAT,
        dataset=DATASET_TEAMS,
        extractor_import_path=(
            "data_collection.extractors.understat.teams:fetch_understat_teams"
        ),
        transformer_import_path=(
            "data_collection.transformers.understat.teams:transform_understat_teams"
        ),
    ),
    (SOURCE_UNDERSTAT, DATASET_TEAM_SUMMARIES): SourceDatasetContract(
        source=SOURCE_UNDERSTAT,
        dataset=DATASET_TEAM_SUMMARIES,
        extractor_import_path=(
            "data_collection.extractors.understat.team_summaries:"
            "fetch_understat_team_summaries"
        ),
        transformer_import_path=(
            "data_collection.transformers.understat.team_summaries:"
            "transform_understat_team_summaries"
        ),
    ),
    (SOURCE_SOFASCORE, DATASET_MATCHES): SourceDatasetContract(
        source=SOURCE_SOFASCORE,
        dataset=DATASET_MATCHES,
        extractor_import_path=(
            "data_collection.extractors.sofascore.matches:fetch_sofascore_matches"
        ),
        transformer_import_path=(
            "data_collection.transformers.sofascore.matches:transform_sofascore_matches"
        ),
    ),
    (SOURCE_SOFASCORE, DATASET_PLAYERS): SourceDatasetContract(
        source=SOURCE_SOFASCORE,
        dataset=DATASET_PLAYERS,
        extractor_import_path=(
            "data_collection.extractors.sofascore.players:fetch_sofascore_players"
        ),
        transformer_import_path=(
            "data_collection.transformers.sofascore.players:transform_sofascore_players"
        ),
    ),
    (SOURCE_SOFASCORE, DATASET_TEAMS): SourceDatasetContract(
        source=SOURCE_SOFASCORE,
        dataset=DATASET_TEAMS,
        extractor_import_path=(
            "data_collection.extractors.sofascore.teams:fetch_sofascore_teams"
        ),
        transformer_import_path=(
            "data_collection.transformers.sofascore.teams:transform_sofascore_teams"
        ),
    ),
    (SOURCE_WHOSCORED, DATASET_MATCHES): SourceDatasetContract(
        source=SOURCE_WHOSCORED,
        dataset=DATASET_MATCHES,
        extractor_import_path=(
            "data_collection.extractors.whoscored.matches:fetch_whoscored_matches"
        ),
        transformer_import_path=(
            "data_collection.transformers.whoscored.matches:transform_whoscored_matches"
        ),
    ),
    (SOURCE_WHOSCORED, DATASET_PLAYERS): SourceDatasetContract(
        source=SOURCE_WHOSCORED,
        dataset=DATASET_PLAYERS,
        extractor_import_path=(
            "data_collection.extractors.whoscored.players:fetch_whoscored_players"
        ),
        transformer_import_path=(
            "data_collection.transformers.whoscored.players:transform_whoscored_players"
        ),
    ),
    (SOURCE_WHOSCORED, DATASET_TEAMS): SourceDatasetContract(
        source=SOURCE_WHOSCORED,
        dataset=DATASET_TEAMS,
        extractor_import_path=(
            "data_collection.extractors.whoscored.teams:fetch_whoscored_teams"
        ),
        transformer_import_path=(
            "data_collection.transformers.whoscored.teams:transform_whoscored_teams"
        ),
    ),
}


def get_supported_sources() -> list[str]:
    return sorted({contract.source for contract in SOURCE_DATASET_CONTRACTS.values()})


def get_supported_datasets(source: str | None = None) -> list[str]:
    if source is None:
        return sorted({contract.dataset for contract in SOURCE_DATASET_CONTRACTS.values()})

    normalised_source = normalise_source(source)

    return sorted(
        {
            contract.dataset
            for contract in SOURCE_DATASET_CONTRACTS.values()
            if contract.source == normalised_source
        }
    )


def list_contracts(source: str | None = None) -> list[SourceDatasetContract]:
    if source is None:
        return sorted(
            SOURCE_DATASET_CONTRACTS.values(),
            key=lambda contract: (contract.source, contract.dataset),
        )

    normalised_source = normalise_source(source)

    return sorted(
        [
            contract
            for contract in SOURCE_DATASET_CONTRACTS.values()
            if contract.source == normalised_source
        ],
        key=lambda contract: contract.dataset,
    )


def source_supports_dataset(source: str, dataset: str) -> bool:
    key = (normalise_source(source), normalise_dataset(dataset))
    return key in SOURCE_DATASET_CONTRACTS


def get_contract(source: str, dataset: str) -> SourceDatasetContract:
    key = (normalise_source(source), normalise_dataset(dataset))

    if key not in SOURCE_DATASET_CONTRACTS:
        raise KeyError(
            f"Unsupported source/dataset combination: source={source}, dataset={dataset}"
        )

    return SOURCE_DATASET_CONTRACTS[key]


def get_extractor_import_path(source: str, dataset: str) -> str:
    return get_contract(source, dataset).extractor_import_path


def get_transformer_import_path(source: str, dataset: str) -> str:
    return get_contract(source, dataset).transformer_import_path


def load_extractor(source: str, dataset: str) -> Any:
    return _import_callable(get_extractor_import_path(source, dataset))


def load_transformer(source: str, dataset: str) -> Any:
    return _import_callable(get_transformer_import_path(source, dataset))


def build_registry_summary() -> dict[str, Any]:
    sources = get_supported_sources()

    return {
        "sources": sources,
        "datasets_by_source": {
            source: get_supported_datasets(source)
            for source in sources
        },
        "total_contracts": len(SOURCE_DATASET_CONTRACTS),
    }


def validate_registry() -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    for key, contract in SOURCE_DATASET_CONTRACTS.items():
        if not contract.writes_raw_first:
            errors.append(
                f"{key} does not enforce raw-first output."
            )

        if not contract.transforms_to_canonical_schema:
            errors.append(
                f"{key} does not transform into canonical schema."
            )

        if not contract.cross_source_join_requires_reconciliation:
            errors.append(
                f"{key} allows cross-source joins without reconciliation."
            )

        if contract.source_ids_are_universal:
            errors.append(
                f"{key} incorrectly treats source IDs as universal."
            )

        if not contract.extractor_import_path:
            errors.append(f"{key} is missing extractor_import_path.")

        if not contract.transformer_import_path:
            errors.append(f"{key} is missing transformer_import_path.")

    return {
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total_contracts": len(SOURCE_DATASET_CONTRACTS),
            "supported_sources": get_supported_sources(),
        },
    }


def normalise_source(source: str) -> str:
    return str(source).strip().lower()


def normalise_dataset(dataset: str) -> str:
    return str(dataset).strip().lower()


def _import_callable(import_path: str) -> Any:
    if ":" not in import_path:
        raise ValueError(
            f'Invalid import path "{import_path}". Expected "module.submodule:callable_name".'
        )

    module_path, callable_name = import_path.split(":", 1)
    module = importlib.import_module(module_path)
    obj = getattr(module, callable_name, None)

    if not callable(obj):
        raise AttributeError(
            f'Import path "{import_path}" did not resolve to a callable.'
        )

    return obj