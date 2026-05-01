from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from data_collection.core.enums import (
    DATASET_MATCHES,
    DATASET_PLAYERS,
    DATASET_TEAMS,
    DATASET_TEAM_SUMMARIES,
)
from data_collection.core.paths import (
    get_processed_csv_path,
    get_raw_csv_path,
    get_validation_csv_path,
)
from data_collection.core.source_registry import load_extractor, load_transformer
from data_collection.io.csv_writer import write_df_to_csv, write_rows_to_csv
from data_collection.io.manifest import build_manifest, write_manifest
from data_collection.validators.matches import validate_match_rows as validate_matches_df
from data_collection.validators.players import validate_player_rows as validate_players_df
from data_collection.validators.team_summaries import validate_team_summary_rows as validate_team_summaries_df
from data_collection.validators.teams import validate_team_rows as validate_teams_df

ExtractorFn = Callable[[str, str], Any]
TransformerFn = Callable[[Any, str, str], pd.DataFrame | list[dict[str, Any]]]
ValidatorFn = Callable[..., tuple[pd.DataFrame, list[Any], list[Any], dict[str, Any]]]


VALIDATOR_REGISTRY: dict[str, ValidatorFn] = {
    DATASET_MATCHES: validate_matches_df,
    DATASET_PLAYERS: validate_players_df,
    DATASET_TEAMS: validate_teams_df,
    DATASET_TEAM_SUMMARIES: validate_team_summaries_df,
}


def _require_validator(dataset: str) -> ValidatorFn:
    validator = VALIDATOR_REGISTRY.get(dataset)
    if validator is None:
        raise ValueError(f"No validator registered for dataset='{dataset}'")
    return validator


def _coerce_to_dataframe(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, list):
        return pd.DataFrame(data)
    if data is None:
        return pd.DataFrame()
    raise TypeError(f"Unsupported data type for dataframe coercion: {type(data)!r}")


def _build_manifest_path(source: str, dataset: str, league: str, season: str) -> Path:
    validation_path = Path(
        get_validation_csv_path(
            source=source,
            dataset=dataset,
            league=league,
            season=season,
        )
    )
    return validation_path.with_name(
        validation_path.stem.replace("_validation", "_manifest") + ".json"
    )


def _write_raw_output(raw_data: Any, raw_path: str | Path) -> Path:
    if isinstance(raw_data, pd.DataFrame):
        return write_df_to_csv(raw_data, raw_path)
    if isinstance(raw_data, list):
        return write_rows_to_csv(raw_data, raw_path)
    raise TypeError(f"Unsupported raw output type for saving: {type(raw_data)!r}")


def _run_validator(
    *,
    validator: ValidatorFn,
    canonical_df: pd.DataFrame,
    source: str,
    dataset: str,
    league: str,
    season: str,
) -> tuple[pd.DataFrame, list[Any], list[Any], dict[str, Any], Path | None]:
    rows = canonical_df.to_dict(orient="records")

    result = validator(
        rows,
        league=league,
        season=season,
        source=source,
        write_report=True,
    )

    validated_df = result.get("cleaned_df", canonical_df)
    errors = result.get("errors", [])
    warnings = result.get("warnings", [])
    summary = result.get("summary", {})

    report_path = None
    if isinstance(summary, dict) and summary.get("report_path"):
        report_path = Path(summary["report_path"])
    else:
        report_path = Path(
            get_validation_csv_path(
                source=source,
                dataset=dataset,
                league=league,
                season=season,
            )
        )
        if report_path.suffix.lower() == ".csv":
            report_path = report_path.with_suffix(".txt")

    return validated_df, errors, warnings, summary, report_path


def collect_source_dataset(
    source: str,
    dataset: str,
    league: str,
    season: str,
    save_raw: bool = True,
    save_canonical: bool = True,
    save_manifest: bool = True,
) -> dict[str, Any]:
    started_at = datetime.utcnow()

    extractor = load_extractor(source, dataset)
    transformer = load_transformer(source, dataset)
    validator = _require_validator(dataset)

    raw_data = extractor(league, season)
    raw_df = _coerce_to_dataframe(raw_data)

    output_paths: list[str] = []

    if save_raw:
        raw_path = get_raw_csv_path(
            source=source,
            dataset=dataset,
            league=league,
            season=season,
        )
        saved_raw_path = _write_raw_output(raw_data, raw_path)
        output_paths.append(str(saved_raw_path))

    transformed = transformer(raw_data, league, season)
    canonical_df = _coerce_to_dataframe(transformed)

    validated_df, errors, warnings, summary, validation_report_path = _run_validator(
        validator=validator,
        canonical_df=canonical_df,
        source=source,
        dataset=dataset,
        league=league,
        season=season,
    )

    if validation_report_path is not None:
        output_paths.append(str(validation_report_path))

    if save_canonical:
        canonical_path = get_processed_csv_path(
            source=source,
            dataset=dataset,
            league=league,
            season=season,
        )
        saved_canonical_path = write_df_to_csv(validated_df, canonical_path)
        output_paths.append(str(saved_canonical_path))

    finished_at = datetime.utcnow()

    manifest_path = None
    manifest_output_paths = list(output_paths)

    if save_manifest:
        manifest_path = _build_manifest_path(
            source=source,
            dataset=dataset,
            league=league,
            season=season,
        )
        manifest_output_paths.append(str(manifest_path))

    manifest = build_manifest(
        source=source,
        dataset=dataset,
        league=league,
        season=season,
        started_at=started_at,
        finished_at=finished_at,
        row_count_raw=len(raw_df),
        row_count_canonical=len(validated_df),
        validation_errors_count=len(errors),
        validation_warnings_count=len(warnings),
        output_paths=manifest_output_paths,
        extra={
            "status": "success",
            "summary": summary,
        },
    )

    if save_manifest and manifest_path is not None:
        write_manifest(manifest, manifest_path)
        output_paths = manifest_output_paths

    return {
        "source": source,
        "dataset": dataset,
        "league": league,
        "season": season,
        "raw_df": raw_df,
        "canonical_df": validated_df,
        "errors": errors,
        "warnings": warnings,
        "summary": summary,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "validation_report_path": validation_report_path,
        "output_paths": output_paths,
    }