from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

try:
    from data_collection.config.sources import get_enabled_sources, source_supports_dataset
except ImportError:
    get_enabled_sources = None
    source_supports_dataset = None

try:
    from data_collection.core.enums import (
        DATASET_MATCHES,
        DATASET_PLAYERS,
        DATASET_TEAMS,
        DATASET_TEAM_SUMMARIES,
        SOURCE_SOFASCORE,
        SOURCE_UNDERSTAT,
    )
except ImportError:
    DATASET_MATCHES = "matches"
    DATASET_PLAYERS = "players"
    DATASET_TEAMS = "teams"
    DATASET_TEAM_SUMMARIES = "team_summaries"
    SOURCE_SOFASCORE = "sofascore"
    SOURCE_UNDERSTAT = "understat"

try:
    from data_collection.core.paths import (
        ensure_core_directories,
        get_processed_dataset_dir,
        get_processed_merged_csv_path,
        get_processed_merged_dir,
        get_raw_merged_csv_path,
        get_raw_merged_dir,
        get_raw_source_dir,
    )
except ImportError as exc:
    raise ImportError(
        "Could not import data_collection.core.paths. "
        "Run this script from backend/apps/predictions or ensure the predictions package is on PYTHONPATH."
    ) from exc

try:
    from data_collection.io.csv_reader import read_many_csv
    from data_collection.io.csv_writer import write_df_to_csv
    from data_collection.io.manifest import build_manifest, write_manifest
except ImportError as exc:
    raise ImportError(
        "Could not import data_collection.io helpers required for merged exports."
    ) from exc


LAYER_RAW = "raw"
LAYER_PROCESSED = "processed"

DEFAULT_SOURCES = (
    list(get_enabled_sources())
    if callable(get_enabled_sources)
    else [SOURCE_UNDERSTAT, SOURCE_SOFASCORE]
)

DEFAULT_DATASETS = [
    DATASET_MATCHES,
    DATASET_PLAYERS,
    DATASET_TEAMS,
    DATASET_TEAM_SUMMARIES,
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create all-leagues merged CSV exports from the new data layout. "
            "Raw exports are written per source, while processed exports are written "
            "per dataset across the selected canonical sources."
        )
    )
    parser.add_argument(
        "--layers",
        nargs="+",
        default=[LAYER_RAW, LAYER_PROCESSED],
        choices=[LAYER_RAW, LAYER_PROCESSED],
        help="Which data layers to export. Defaults to both raw and processed.",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        default=DEFAULT_SOURCES,
        help=f"Sources to include. Defaults to: {', '.join(DEFAULT_SOURCES)}",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=DEFAULT_DATASETS,
        help=f"Datasets to export. Defaults to: {', '.join(DEFAULT_DATASETS)}",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print resolved files and stack traces on failures.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop immediately on the first failed export.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    return run_export_jobs(
        layers=args.layers,
        sources=args.sources,
        datasets=args.datasets,
        verbose=args.verbose,
        stop_on_error=args.stop_on_error,
    )


def run_export_jobs(
    *,
    layers: Iterable[str],
    sources: Iterable[str],
    datasets: Iterable[str],
    verbose: bool = False,
    stop_on_error: bool = False,
) -> int:
    ensure_core_directories()

    sources = _normalise_text_list(sources)
    datasets = _normalise_text_list(datasets)
    layers = _normalise_text_list(layers)

    jobs = _build_jobs(layers=layers, sources=sources, datasets=datasets)
    if not jobs:
        print("No merged export jobs were produced from the supplied filters.", file=sys.stderr)
        return 2

    print(f"Starting merged export run for {len(jobs)} job(s).")

    failures: list[dict[str, Any]] = []

    for index, job in enumerate(jobs, start=1):
        layer = job["layer"]
        dataset = job["dataset"]
        source = job.get("source")

        if layer == LAYER_RAW:
            label = f"layer={layer} source={source} dataset={dataset}"
        else:
            label = f"layer={layer} dataset={dataset} sources={','.join(job['sources'])}"

        print(f"\n[{index}/{len(jobs)}] {label}")

        try:
            if layer == LAYER_RAW:
                result = export_raw_merged_view(
                    source=str(source),
                    dataset=dataset,
                    verbose=verbose,
                )
            else:
                result = export_processed_merged_view(
                    dataset=dataset,
                    sources=list(job["sources"]),
                    verbose=verbose,
                )

            print(
                f"[ok] rows={result['row_count']} files={result['source_file_count']} "
                f"output={result['output_csv_path']}"
            )
        except Exception as exc:
            failure = {
                **job,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
            failures.append(failure)
            print(f"[failed] {label} -> {type(exc).__name__}: {exc}", file=sys.stderr)
            if verbose:
                traceback.print_exc()
            if stop_on_error:
                break

    print(
        f"\nMerged export summary: succeeded={len(jobs) - len(failures)} "
        f"failed={len(failures)} total={len(jobs)}"
    )

    return 1 if failures else 0


def export_raw_merged_view(source: str, dataset: str, verbose: bool = False) -> dict[str, Any]:
    started_at = datetime.utcnow()
    source_dir = get_raw_source_dir(source)
    merged_dir = get_raw_merged_dir(source)
    input_paths = _discover_raw_input_paths(source=source, dataset=dataset, source_dir=source_dir)

    if not input_paths:
        raise FileNotFoundError(
            f"No raw CSVs found for source={source} dataset={dataset} under {source_dir}"
        )

    if verbose:
        for path in input_paths:
            print(f"  raw input: {path}")

    merged_df = read_many_csv(input_paths)
    merged_df = _finalize_merged_dataframe(merged_df)

    output_csv_path = get_raw_merged_csv_path(source, dataset)
    manifest_path = _build_manifest_path(
        merged_dir=merged_dir,
        filename=output_csv_path.stem + "_manifest.json",
    )

    write_df_to_csv(merged_df, output_csv_path)
    manifest = build_manifest(
        source=source,
        dataset=dataset,
        league="all",
        season="all",
        started_at=started_at,
        finished_at=datetime.utcnow(),
        row_count_raw=len(merged_df),
        row_count_canonical=0,
        validation_errors_count=0,
        validation_warnings_count=0,
        output_paths=[output_csv_path, manifest_path],
        extra={
            "layer": LAYER_RAW,
            "status": "success",
            "source_file_count": len(input_paths),
            "input_paths": [str(path) for path in input_paths],
        },
    )
    write_manifest(manifest, manifest_path)

    return {
        "layer": LAYER_RAW,
        "source": source,
        "dataset": dataset,
        "row_count": int(len(merged_df)),
        "source_file_count": len(input_paths),
        "output_csv_path": str(output_csv_path),
        "manifest_path": str(manifest_path),
    }


def export_processed_merged_view(dataset: str, sources: list[str], verbose: bool = False) -> dict[str, Any]:
    started_at = datetime.utcnow()
    dataset_dir = get_processed_dataset_dir(dataset)
    merged_dir = get_processed_merged_dir(dataset)
    input_paths = _discover_processed_input_paths(
        dataset=dataset,
        dataset_dir=dataset_dir,
        sources=sources,
    )

    if not input_paths:
        raise FileNotFoundError(
            f"No processed CSVs found for dataset={dataset} sources={sources} under {dataset_dir}"
        )

    if verbose:
        for path in input_paths:
            print(f"  processed input: {path}")

    merged_df = read_many_csv(input_paths)
    merged_df = _ensure_source_column(merged_df, input_paths)
    merged_df = _finalize_merged_dataframe(merged_df)

    output_csv_path = get_processed_merged_csv_path(dataset)
    manifest_path = _build_manifest_path(
        merged_dir=merged_dir,
        filename=output_csv_path.stem + "_manifest.json",
    )

    write_df_to_csv(merged_df, output_csv_path)
    manifest = build_manifest(
        source="+".join(sorted(sources)),
        dataset=dataset,
        league="all",
        season="all",
        started_at=started_at,
        finished_at=datetime.utcnow(),
        row_count_raw=0,
        row_count_canonical=len(merged_df),
        validation_errors_count=0,
        validation_warnings_count=0,
        output_paths=[output_csv_path, manifest_path],
        extra={
            "layer": LAYER_PROCESSED,
            "status": "success",
            "source_file_count": len(input_paths),
            "sources_included": sorted(sources),
            "input_paths": [str(path) for path in input_paths],
        },
    )
    write_manifest(manifest, manifest_path)

    return {
        "layer": LAYER_PROCESSED,
        "dataset": dataset,
        "sources": sorted(sources),
        "row_count": int(len(merged_df)),
        "source_file_count": len(input_paths),
        "output_csv_path": str(output_csv_path),
        "manifest_path": str(manifest_path),
    }


def _build_jobs(
    layers: Iterable[str],
    sources: Iterable[str],
    datasets: Iterable[str],
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    source_list = list(sources)

    for layer in layers:
        if layer == LAYER_RAW:
            for source in source_list:
                for dataset in datasets:
                    if not _supports_dataset(source, dataset):
                        continue
                    jobs.append(
                        {
                            "layer": layer,
                            "source": source,
                            "dataset": dataset,
                        }
                    )
            continue

        for dataset in datasets:
            supported_sources = [source for source in source_list if _supports_dataset(source, dataset)]
            if not supported_sources:
                continue
            jobs.append(
                {
                    "layer": layer,
                    "dataset": dataset,
                    "sources": supported_sources,
                }
            )

    return jobs


def _discover_raw_input_paths(source: str, dataset: str, source_dir: Path) -> list[Path]:
    pattern = f"{source}_{dataset}_*_raw.csv"
    return sorted(
        path
        for path in source_dir.glob("*/*.csv")
        if path.parent.name != "merged" and path.match(f"*/{pattern}")
    )


def _discover_processed_input_paths(dataset: str, dataset_dir: Path, sources: list[str]) -> list[Path]:
    paths = [path for path in dataset_dir.glob("*/*.csv") if path.parent.name != "merged"]
    filtered_paths: list[Path] = []

    for path in sorted(paths):
        if any(f"_{source}_" in path.name for source in sources):
            filtered_paths.append(path)

    return filtered_paths


def _ensure_source_column(df: pd.DataFrame, input_paths: list[Path]) -> pd.DataFrame:
    if "source" in df.columns:
        return df

    path_by_marker = {
        path.name: _infer_source_from_filename(path)
        for path in input_paths
    }

    if not path_by_marker:
        return df

    enriched = df.copy()

    if "source_file" in enriched.columns:
        enriched["source"] = enriched["source_file"].map(path_by_marker)
        return enriched

    sources_found = sorted({value for value in path_by_marker.values() if value})
    if len(sources_found) == 1:
        enriched["source"] = sources_found[0]

    return enriched


def _infer_source_from_filename(path: Path) -> str | None:
    name = path.name.lower()
    for source in DEFAULT_SOURCES:
        if f"_{source.lower()}_" in name:
            return source
    return None


def _finalize_merged_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    merged_df = df.copy()

    for column in ["season", "league", "date", "source"]:
        if column in merged_df.columns:
            merged_df[column] = merged_df[column].astype("string")

    sort_columns = [column for column in ["season", "league", "date", "source"] if column in merged_df.columns]
    if sort_columns:
        merged_df = merged_df.sort_values(sort_columns, kind="stable", na_position="last")

    return merged_df.reset_index(drop=True)


def _build_manifest_path(merged_dir: Path, filename: str) -> Path:
    merged_dir.mkdir(parents=True, exist_ok=True)
    return merged_dir / filename


def _supports_dataset(source: str, dataset: str) -> bool:
    if callable(source_supports_dataset):
        return bool(source_supports_dataset(source, dataset))

    if source == SOURCE_SOFASCORE and dataset == DATASET_TEAM_SUMMARIES:
        return False

    return True


def _normalise_text_list(values: Iterable[str]) -> list[str]:
    return [str(value).strip() for value in values if str(value).strip()]


if __name__ == "__main__":
    raise SystemExit(main())