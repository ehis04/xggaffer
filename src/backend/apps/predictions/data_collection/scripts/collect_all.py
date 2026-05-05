from __future__ import annotations

import argparse
import sys
import traceback
from dataclasses import asdict, is_dataclass
from typing import Any, Iterable

try:
    from data_collection.pipelines.collect_source_dataset import collect_source_dataset
except ImportError as exc:
    raise ImportError(
        "Could not import collect_source_dataset from "
        "data_collection.pipelines.collect_source_dataset. "
        "Make sure Phase I pipeline wiring exists before running collect_all.py."
    ) from exc

try:
    from data_collection.config.sources import (
        SOURCE_UNDERSTAT,
        SOURCE_SOFASCORE,
        get_enabled_sources,
        source_supports_dataset,
    )
except ImportError:
    SOURCE_UNDERSTAT = "understat"
    SOURCE_SOFASCORE = "sofascore"
    get_enabled_sources = None
    source_supports_dataset = None

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

try:
    from data_collection.config.leagues import SUPPORTED_LEAGUES
except ImportError:
    SUPPORTED_LEAGUES = [
        "EPL",
        "La_Liga",
        "Bundesliga",
        "Serie_A",
        "Ligue_1",
        "RFPL",
    ]


DEFAULT_SOURCES = [
    SOURCE_UNDERSTAT,
    SOURCE_SOFASCORE,
]

DEFAULT_DATASETS = [
    DATASET_MATCHES,
    DATASET_PLAYERS,
    DATASET_TEAMS,
    DATASET_TEAM_SUMMARIES,
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Thin orchestration entrypoint for collecting source datasets into the "
            "raw and canonical scraper pipeline."
        )
    )

    parser.add_argument(
        "--sources",
        nargs="+",
        default=DEFAULT_SOURCES,
        help=f"Sources to collect. Defaults to: {', '.join(DEFAULT_SOURCES)}",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=DEFAULT_DATASETS,
        help=f"Datasets to collect. Defaults to: {', '.join(DEFAULT_DATASETS)}",
    )
    parser.add_argument(
        "--leagues",
        nargs="+",
        default=SUPPORTED_LEAGUES,
        help="League codes to collect.",
    )
    parser.add_argument(
        "--seasons",
        nargs="+",
        required=True,
        help='Season values to collect, e.g. "2019" "2020" "2021".',
    )

    parser.add_argument(
        "--skip-save",
        action="store_true",
        help="Run extraction/transformation without persisting outputs where supported.",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip validator execution where supported by the pipeline.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop immediately on the first failed collection job.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Alias for --stop-on-error.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print more detailed per-job output.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    stop_on_error = args.stop_on_error or args.fail_fast

    requested_sources = _normalise_text_list(args.sources)
    requested_datasets = _normalise_text_list(args.datasets)
    requested_leagues = _normalise_text_list(args.leagues)
    requested_seasons = _normalise_text_list(args.seasons)

    validation_errors = _validate_requested_values(
        sources=requested_sources,
        datasets=requested_datasets,
    )
    if validation_errors:
        for error in validation_errors:
            print(f"[config-error] {error}", file=sys.stderr)
        return 2

    jobs = _build_jobs(
        sources=requested_sources,
        datasets=requested_datasets,
        leagues=requested_leagues,
        seasons=requested_seasons,
    )

    if not jobs:
        print("No valid jobs were produced from the supplied filters.", file=sys.stderr)
        return 2

    print(
        "Starting collection run for "
        f"{len(jobs)} job(s) across "
        f"{len(requested_sources)} source(s), "
        f"{len(requested_datasets)} dataset(s), "
        f"{len(requested_leagues)} league(s), "
        f"and {len(requested_seasons)} season(s)."
    )

    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for index, job in enumerate(jobs, start=1):
        source = job["source"]
        dataset = job["dataset"]
        league = job["league"]
        season = job["season"]

        print(
            f"\n[{index}/{len(jobs)}] "
            f"source={source} dataset={dataset} league={league} season={season}"
        )

        try:
            result = _run_single_job(
                source=source,
                dataset=dataset,
                league=league,
                season=season,
                skip_save=args.skip_save,
                skip_validation=args.skip_validation,
            )
            result_dict = _result_to_dict(result)
            result_dict.update(job)

            successes.append(result_dict)

            print(_format_success_summary(result_dict, verbose=args.verbose))
        except Exception as exc:
            failure = {
                **job,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
            failures.append(failure)

            print(
                f"[failed] {source}/{dataset}/{league}/{season} -> "
                f"{type(exc).__name__}: {exc}",
                file=sys.stderr,
            )

            if args.verbose:
                traceback.print_exc()

            if stop_on_error:
                break

    _print_final_summary(
        successes=successes,
        failures=failures,
        total_jobs=len(jobs),
    )

    return 1 if failures else 0


def _build_jobs(
    sources: Iterable[str],
    datasets: Iterable[str],
    leagues: Iterable[str],
    seasons: Iterable[str],
) -> list[dict[str, str]]:
    jobs: list[dict[str, str]] = []

    for source in sources:
        for dataset in datasets:
            if source_supports_dataset is not None and not source_supports_dataset(source, dataset):
                print(
                    f"[skip] source={source} does not support dataset={dataset} "
                    "per SOURCE_CAPABILITIES config."
                )
                continue

            for league in leagues:
                for season in seasons:
                    jobs.append(
                        {
                            "source": source,
                            "dataset": dataset,
                            "league": league,
                            "season": season,
                        }
                    )

    return jobs


def _run_single_job(
    source: str,
    dataset: str,
    league: str,
    season: str,
    skip_save: bool,
    skip_validation: bool,
) -> Any:
    """
    Thin wrapper over the generic pipeline.

    This keeps Phase 15A aligned with the reform rule:
    scripts orchestrate; pipelines perform the actual work.
    """
    pipeline_kwargs = {
        "source": source,
        "dataset": dataset,
        "league": league,
        "season": season,
    }

    supported_kwargs = _filter_supported_kwargs(
        func=collect_source_dataset,
        kwargs={
            **pipeline_kwargs,
            "save": not skip_save,
            "run_validation": not skip_validation,
            "validate": not skip_validation,
        },
    )

    return collect_source_dataset(**supported_kwargs)


def _filter_supported_kwargs(func: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    import inspect

    signature = inspect.signature(func)
    accepted = set(signature.parameters.keys())

    return {
        key: value
        for key, value in kwargs.items()
        if key in accepted
    }


def _result_to_dict(result: Any) -> dict[str, Any]:
    if result is None:
        return {}

    if isinstance(result, dict):
        return result

    if is_dataclass(result):
        return asdict(result)

    if hasattr(result, "__dict__"):
        return {
            key: value
            for key, value in vars(result).items()
            if not key.startswith("_")
        }

    return {"result": result}


def _format_success_summary(result: dict[str, Any], verbose: bool) -> str:
    raw_rows = _first_present(
        result,
        ["raw_row_count", "raw_rows", "raw_count", "extracted_rows"],
    )
    canonical_rows = _first_present(
        result,
        ["canonical_row_count", "canonical_rows", "processed_rows", "transformed_rows"],
    )
    validation_errors = _safe_len(
        _first_present(
            result,
            ["validation_errors", "errors"],
        )
    )
    validation_warnings = _safe_len(
        _first_present(
            result,
            ["validation_warnings", "warnings"],
        )
    )

    summary = (
        "[ok] "
        f"raw_rows={raw_rows if raw_rows is not None else '?'} "
        f"canonical_rows={canonical_rows if canonical_rows is not None else '?'} "
        f"errors={validation_errors} "
        f"warnings={validation_warnings}"
    )

    if verbose:
        interesting_keys = [
            "raw_output_path",
            "canonical_output_path",
            "validation_report_path",
            "manifest_path",
            "status",
        ]
        extras = [
            f"{key}={result[key]}"
            for key in interesting_keys
            if key in result and result[key]
        ]
        if extras:
            summary += "\n    " + "\n    ".join(extras)

    return summary


def _print_final_summary(
    successes: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    total_jobs: int,
) -> None:
    print("\n" + "=" * 72)
    print("Collection run complete")
    print("=" * 72)
    print(f"Total jobs:   {total_jobs}")
    print(f"Succeeded:    {len(successes)}")
    print(f"Failed:       {len(failures)}")

    if failures:
        print("\nFailed jobs:")
        for failure in failures:
            print(
                "- "
                f"{failure['source']}/{failure['dataset']}/"
                f"{failure['league']}/{failure['season']} -> "
                f"{failure['error_type']}: {failure['error_message']}"
            )

    if successes:
        total_raw_rows = _sum_present(
            successes,
            ["raw_row_count", "raw_rows", "raw_count", "extracted_rows"],
        )
        total_canonical_rows = _sum_present(
            successes,
            ["canonical_row_count", "canonical_rows", "processed_rows", "transformed_rows"],
        )

        print("\nAggregate row counts:")
        print(f"- Raw rows:        {total_raw_rows}")
        print(f"- Canonical rows:  {total_canonical_rows}")


def _validate_requested_values(
    sources: list[str],
    datasets: list[str],
) -> list[str]:
    errors: list[str] = []

    allowed_sources = set(get_enabled_sources()) if get_enabled_sources is not None else {SOURCE_UNDERSTAT, SOURCE_SOFASCORE}
    for source in sources:
        if source not in allowed_sources:
            errors.append(
                f'Unsupported source "{source}". '
                f"Allowed values: {sorted(allowed_sources)}"
            )

    allowed_datasets = set(DEFAULT_DATASETS)
    for dataset in datasets:
        if dataset not in allowed_datasets:
            errors.append(
                f'Unsupported dataset "{dataset}". '
                f"Allowed values: {sorted(allowed_datasets)}"
            )

    return errors


def _normalise_text_list(values: Iterable[str]) -> list[str]:
    normalised: list[str] = []
    seen: set[str] = set()

    for value in values:
        cleaned = str(value).strip()
        if not cleaned:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        normalised.append(cleaned)

    return normalised


def _first_present(payload: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _sum_present(rows: list[dict[str, Any]], keys: list[str]) -> int:
    total = 0
    for row in rows:
        value = _first_present(row, keys)
        if value is None:
            continue
        try:
            total += int(value)
        except (TypeError, ValueError):
            continue
    return total


def _safe_len(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (list, tuple, set, dict)):
        return len(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())