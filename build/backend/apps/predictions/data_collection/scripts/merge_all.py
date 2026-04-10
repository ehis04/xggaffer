from __future__ import annotations

import argparse
import inspect
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

try:
    from data_collection.config.sources import SOURCE_UNDERSTAT, SOURCE_SOFASCORE
except ImportError:
    SOURCE_UNDERSTAT = "understat"
    SOURCE_SOFASCORE = "sofascore"

try:
    from data_collection.core.enums import DATASET_MATCHES
except ImportError:
    DATASET_MATCHES = "matches"

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

try:
    from data_collection.io.csv_reader import read_csv as project_read_csv
except ImportError:
    project_read_csv = None

try:
    from data_collection.io.csv_writer import write_df_to_csv as project_write_df_to_csv
except ImportError:
    project_write_df_to_csv = None

try:
    from data_collection.io.manifest import write_manifest as project_write_manifest
except ImportError:
    project_write_manifest = None

try:
    from data_collection.pipelines import merge_processed as merge_processed_module
except ImportError:
    merge_processed_module = None

try:
    from data_collection.core.paths import PROCESSED_ROOT, RECONCILIATION_ROOT, DB_LOAD_ROOT
    _DEFAULT_CANONICAL_ROOT = PROCESSED_ROOT
    _DEFAULT_AUDIT_ROOT = RECONCILIATION_ROOT
    _DEFAULT_MERGED_ROOT = DB_LOAD_ROOT
except ImportError:
    _DEFAULT_CANONICAL_ROOT = Path("data_collection/output/canonical_processed")
    _DEFAULT_AUDIT_ROOT = Path("data_collection/output/reconciliation_audit")
    _DEFAULT_MERGED_ROOT = Path("data_collection/output/future_database_load")


DEFAULT_SOURCES = [SOURCE_UNDERSTAT, SOURCE_SOFASCORE]
DEFAULT_DATASETS = [DATASET_MATCHES]
DEFAULT_CANONICAL_ROOT = _DEFAULT_CANONICAL_ROOT
DEFAULT_AUDIT_ROOT = _DEFAULT_AUDIT_ROOT
DEFAULT_MERGED_ROOT = _DEFAULT_MERGED_ROOT


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Thin orchestration entrypoint for processed merged outputs."
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=DEFAULT_DATASETS,
        help="Datasets to merge. For now, only matches are supported safely.",
    )
    parser.add_argument(
        "--leagues",
        nargs="+",
        default=SUPPORTED_LEAGUES,
        help="League codes to merge.",
    )
    parser.add_argument(
        "--seasons",
        nargs="+",
        required=True,
        help='Season values to merge, e.g. "2023" "2024".',
    )
    parser.add_argument(
        "--sources",
        nargs=2,
        default=DEFAULT_SOURCES,
        help="Exactly two sources to merge after reconciliation.",
    )
    parser.add_argument(
        "--canonical-root",
        default=str(DEFAULT_CANONICAL_ROOT),
        help="Root folder containing canonical processed outputs.",
    )
    parser.add_argument(
        "--audit-root",
        default=str(DEFAULT_AUDIT_ROOT),
        help="Root folder containing reconciliation audit outputs.",
    )
    parser.add_argument(
        "--merged-root",
        default=str(DEFAULT_MERGED_ROOT),
        help="Root folder where merged processed outputs should be written.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop immediately on the first failed merge job.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Alias for --stop-on-error.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed failure traces and resolved paths.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    stop_on_error = args.stop_on_error or args.fail_fast

    requested_datasets = _normalise_text_list(args.datasets)
    requested_leagues = _normalise_text_list(args.leagues)
    requested_seasons = _normalise_text_list(args.seasons)
    requested_sources = _normalise_text_list(args.sources)

    config_errors = _validate_requested_values(
        datasets=requested_datasets,
        sources=requested_sources,
    )
    if config_errors:
        for error in config_errors:
            print(f"[config-error] {error}", file=sys.stderr)
        return 2

    canonical_root = Path(args.canonical_root)
    audit_root = Path(args.audit_root)
    merged_root = Path(args.merged_root)

    jobs = _build_jobs(
        datasets=requested_datasets,
        leagues=requested_leagues,
        seasons=requested_seasons,
        source_a=requested_sources[0],
        source_b=requested_sources[1],
    )

    if not jobs:
        print("No merge jobs were produced from the supplied filters.", file=sys.stderr)
        return 2

    print(
        "Starting merged-output run for "
        f"{len(jobs)} job(s) across "
        f"{len(requested_datasets)} dataset(s), "
        f"{len(requested_leagues)} league(s), "
        f"and {len(requested_seasons)} season(s)."
    )

    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for index, job in enumerate(jobs, start=1):
        dataset = job["dataset"]
        league = job["league"]
        season = job["season"]
        source_a = job["source_a"]
        source_b = job["source_b"]

        print(
            f"\n[{index}/{len(jobs)}] "
            f"dataset={dataset} league={league} season={season} "
            f"sources={source_a},{source_b}"
        )

        try:
            if dataset != DATASET_MATCHES:
                raise ValueError(
                    f'Merged dataset "{dataset}" is not supported yet. '
                    "Only matches have an explicit reconciliation contract so far."
                )

            source_a_canonical_path = _discover_canonical_file(
                canonical_root=canonical_root,
                dataset=dataset,
                source=source_a,
                league=league,
                season=season,
            )
            source_b_canonical_path = _discover_canonical_file(
                canonical_root=canonical_root,
                dataset=dataset,
                source=source_b,
                league=league,
                season=season,
            )
            matched_audit_path = _discover_matched_audit_file(
                audit_root=audit_root,
                dataset=dataset,
                source_a=source_a,
                source_b=source_b,
                league=league,
                season=season,
            )

            if args.verbose:
                print(f"Resolved {source_a} canonical file: {source_a_canonical_path}")
                print(f"Resolved {source_b} canonical file: {source_b_canonical_path}")
                print(f"Resolved matched audit file: {matched_audit_path}")

            source_a_df = _read_csv(source_a_canonical_path)
            source_b_df = _read_csv(source_b_canonical_path)
            matched_df = _read_csv(matched_audit_path)

            merged_df = _run_merge(
                dataset=dataset,
                source_a=source_a,
                source_b=source_b,
                source_a_df=source_a_df,
                source_b_df=source_b_df,
                matched_df=matched_df,
                league=league,
                season=season,
            )

            output_paths = _write_merged_outputs(
                merged_df=merged_df,
                merged_root=merged_root,
                dataset=dataset,
                source_a=source_a,
                source_b=source_b,
                league=league,
                season=season,
            )

            manifest_payload = {
                "script": "merge_all.py",
                "dataset": dataset,
                "league": league,
                "season": season,
                "sources": [source_a, source_b],
                "input_paths": {
                    source_a: str(source_a_canonical_path),
                    source_b: str(source_b_canonical_path),
                    "matched_audit": str(matched_audit_path),
                },
                "output_paths": output_paths,
                "row_count_merged": int(len(merged_df)),
            }
            manifest_path = _maybe_write_manifest(
                manifest_payload=manifest_payload,
                merged_root=merged_root,
                dataset=dataset,
                source_a=source_a,
                source_b=source_b,
                league=league,
                season=season,
            )
            if manifest_path:
                output_paths["manifest_path"] = str(manifest_path)

            success = {
                **job,
                "source_a_canonical_path": str(source_a_canonical_path),
                "source_b_canonical_path": str(source_b_canonical_path),
                "matched_audit_path": str(matched_audit_path),
                "merged_rows": int(len(merged_df)),
                **output_paths,
            }
            successes.append(success)

            print(_format_success_summary(success, verbose=args.verbose))
        except Exception as exc:
            failure = {
                **job,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
            failures.append(failure)

            print(
                f"[failed] dataset={dataset} league={league} season={season} "
                f"sources={source_a},{source_b} -> {type(exc).__name__}: {exc}",
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
    datasets: Iterable[str],
    leagues: Iterable[str],
    seasons: Iterable[str],
    source_a: str,
    source_b: str,
) -> list[dict[str, str]]:
    jobs: list[dict[str, str]] = []

    for dataset in datasets:
        for league in leagues:
            for season in seasons:
                jobs.append(
                    {
                        "dataset": dataset,
                        "league": league,
                        "season": season,
                        "source_a": source_a,
                        "source_b": source_b,
                    }
                )

    return jobs


def _validate_requested_values(
    datasets: list[str],
    sources: list[str],
) -> list[str]:
    errors: list[str] = []

    if len(sources) != 2:
        errors.append("merge_all.py requires exactly two sources.")

    if len(set(sources)) != len(sources):
        errors.append("The two merge sources must be different.")

    for dataset in datasets:
        if dataset != DATASET_MATCHES:
            errors.append(
                f'Merged dataset "{dataset}" is not supported yet. '
                "Only matches have an explicit reconciliation contract today."
            )

    return errors


def _discover_canonical_file(
    canonical_root: Path,
    dataset: str,
    source: str,
    league: str,
    season: str,
) -> Path:
    dataset_root = canonical_root / dataset

    if not dataset_root.exists():
        raise FileNotFoundError(
            f"Canonical dataset root does not exist: {dataset_root}"
        )

    candidates = list(dataset_root.rglob("*.csv"))
    if not candidates:
        raise FileNotFoundError(
            f"No canonical CSV files were found under {dataset_root}"
        )

    filtered = [
        path
        for path in candidates
        if _path_matches_filters(
            path=path,
            source=source,
            dataset=dataset,
            league=league,
            season=season,
        )
    ]

    if not filtered:
        raise FileNotFoundError(
            f'Could not find canonical CSV for source="{source}", dataset="{dataset}", '
            f'league="{league}", season="{season}" under {dataset_root}'
        )

    scored = sorted(
        filtered,
        key=lambda path: _candidate_score(
            path=path,
            source=source,
            dataset=dataset,
            league=league,
            season=season,
        ),
        reverse=True,
    )

    return scored[0]


def _discover_matched_audit_file(
    audit_root: Path,
    dataset: str,
    source_a: str,
    source_b: str,
    league: str,
    season: str,
) -> Path:
    dataset_root = audit_root / dataset

    if not dataset_root.exists():
        raise FileNotFoundError(
            f"Reconciliation audit dataset root does not exist: {dataset_root}"
        )

    candidates = list(dataset_root.rglob("*.csv"))
    if not candidates:
        raise FileNotFoundError(
            f"No reconciliation audit CSV files were found under {dataset_root}"
        )

    filtered = [
        path
        for path in candidates
        if _path_matches_filters(
            path=path,
            source=source_a,
            dataset=dataset,
            league=league,
            season=season,
        )
        and _normalise_token(source_b) in _normalise_token(str(path))
        and "matched" in _normalise_token(str(path))
    ]

    if not filtered:
        raise FileNotFoundError(
            f'Could not find matched audit CSV for sources="{source_a},{source_b}", '
            f'dataset="{dataset}", league="{league}", season="{season}" under {dataset_root}'
        )

    scored = sorted(
        filtered,
        key=lambda path: _candidate_score(
            path=path,
            source=source_a,
            dataset=dataset,
            league=league,
            season=season,
        ),
        reverse=True,
    )

    return scored[0]


def _run_merge(
    dataset: str,
    source_a: str,
    source_b: str,
    source_a_df: pd.DataFrame,
    source_b_df: pd.DataFrame,
    matched_df: pd.DataFrame,
    league: str,
    season: str,
) -> pd.DataFrame:
    merge_func = _resolve_merge_function()

    if merge_func is not None:
        candidate_kwargs = {
            "dataset": dataset,
            "source_a": source_a,
            "source_b": source_b,
            "source_a_df": source_a_df,
            "source_b_df": source_b_df,
            "left_source": source_a,
            "right_source": source_b,
            "left_df": source_a_df,
            "right_df": source_b_df,
            "matched_df": matched_df,
            "reconciliation_df": matched_df,
            "league": league,
            "season": season,
        }

        accepted_kwargs = _filter_supported_kwargs(
            func=merge_func,
            kwargs=candidate_kwargs,
        )

        if accepted_kwargs:
            result = merge_func(**accepted_kwargs)
            return _coerce_df(result)

    return _fallback_merge_matches(
        source_a=source_a,
        source_b=source_b,
        source_a_df=source_a_df,
        source_b_df=source_b_df,
        matched_df=matched_df,
    )


def _resolve_merge_function() -> Any | None:
    if merge_processed_module is not None:
        for name in [
            "merge_processed_matches",
            "merge_processed_dataset",
            "merge_matches",
            "merge_dataset",
        ]:
            func = getattr(merge_processed_module, name, None)
            if callable(func):
                return func

    return None


def _fallback_merge_matches(
    source_a: str,
    source_b: str,
    source_a_df: pd.DataFrame,
    source_b_df: pd.DataFrame,
    matched_df: pd.DataFrame,
) -> pd.DataFrame:
    left_id_column = _find_first_existing_column(
        matched_df,
        [
            f"{source_a}_source_match_id",
            f"{source_a}__source_match_id",
            "understat_source_match_id" if source_a == SOURCE_UNDERSTAT else None,
            "left_source_match_id",
        ],
    )
    right_id_column = _find_first_existing_column(
        matched_df,
        [
            f"{source_b}_source_match_id",
            f"{source_b}__source_match_id",
            "sofascore_source_match_id" if source_b == SOURCE_SOFASCORE else None,
            "right_source_match_id",
        ],
    )

    if left_id_column is None or right_id_column is None:
        raise KeyError(
            "Matched audit file does not contain the source_match_id columns needed "
            "for a safe processed merge."
        )

    left_prefixed = _prefix_source_columns(
        df=source_a_df,
        source=source_a,
        dataset=DATASET_MATCHES,
    )
    right_prefixed = _prefix_source_columns(
        df=source_b_df,
        source=source_b,
        dataset=DATASET_MATCHES,
    )

    left_join_key = f"{source_a}_source_match_id"
    right_join_key = f"{source_b}_source_match_id"

    merged = matched_df.copy()

    if left_id_column != left_join_key:
        merged = merged.rename(columns={left_id_column: left_join_key})

    if right_id_column != right_join_key:
        merged = merged.rename(columns={right_id_column: right_join_key})

    merged = merged.merge(
        left_prefixed,
        how="left",
        on=left_join_key,
    )

    merged = merged.merge(
        right_prefixed,
        how="left",
        on=right_join_key,
    )

    merged["merged_source_a"] = source_a
    merged["merged_source_b"] = source_b
    merged["merged_from_reconciliation"] = True

    merged["league"] = _coalesce_series(
        merged,
        [
            f"{source_a}_league",
            f"{source_b}_league",
            "league",
        ],
    )
    merged["season"] = _coalesce_series(
        merged,
        [
            f"{source_a}_season",
            f"{source_b}_season",
            "season",
        ],
    )
    merged["date"] = _coalesce_series(
        merged,
        [
            f"{source_a}_date",
            f"{source_b}_date",
            "date_understat",
            "date_sofascore",
        ],
    )
    merged["home_team"] = _coalesce_series(
        merged,
        [
            f"{source_a}_home_team",
            f"{source_b}_home_team",
            "home_team_understat",
            "home_team_sofascore",
        ],
    )
    merged["away_team"] = _coalesce_series(
        merged,
        [
            f"{source_a}_away_team",
            f"{source_b}_away_team",
            "away_team_understat",
            "away_team_sofascore",
        ],
    )
    merged["home_goals"] = _coalesce_series(
        merged,
        [
            f"{source_a}_home_goals",
            f"{source_b}_home_goals",
        ],
    )
    merged["away_goals"] = _coalesce_series(
        merged,
        [
            f"{source_a}_away_goals",
            f"{source_b}_away_goals",
        ],
    )
    merged["match_status"] = _coalesce_series(
        merged,
        [
            f"{source_a}_match_status",
            f"{source_b}_match_status",
            f"{source_a}_status",
            f"{source_b}_status",
        ],
    )

    merged["understat_source_match_id"] = _coalesce_series(
        merged,
        [
            "understat_source_match_id",
            f"{SOURCE_UNDERSTAT}_source_match_id",
        ],
    )
    merged["sofascore_source_match_id"] = _coalesce_series(
        merged,
        [
            "sofascore_source_match_id",
            f"{SOURCE_SOFASCORE}_source_match_id",
        ],
    )

    preferred_column_order = [
        "canonical_match_key",
        "league",
        "season",
        "date",
        "home_team",
        "away_team",
        "home_goals",
        "away_goals",
        "match_status",
        "understat_source_match_id",
        "sofascore_source_match_id",
        "merged_source_a",
        "merged_source_b",
        "merged_from_reconciliation",
    ]

    remaining_columns = [
        column
        for column in merged.columns
        if column not in preferred_column_order
    ]

    merged = merged[preferred_column_order + remaining_columns]

    if "canonical_match_key" in merged.columns:
        merged = merged.drop_duplicates(subset=["canonical_match_key"], keep="first")

    return merged.reset_index(drop=True)


def _prefix_source_columns(
    df: pd.DataFrame,
    source: str,
    dataset: str,
) -> pd.DataFrame:
    renamed = df.copy()

    column_map: dict[str, str] = {}

    for column in renamed.columns:
        if column == "source_match_id" and dataset == DATASET_MATCHES:
            column_map[column] = f"{source}_source_match_id"
        elif column == "source":
            column_map[column] = f"{source}_source"
        else:
            column_map[column] = f"{source}_{column}"

    renamed = renamed.rename(columns=column_map)

    return renamed


def _write_merged_outputs(
    merged_df: pd.DataFrame,
    merged_root: Path,
    dataset: str,
    source_a: str,
    source_b: str,
    league: str,
    season: str,
) -> dict[str, str]:
    dataset_root = merged_root / dataset
    dataset_root.mkdir(parents=True, exist_ok=True)

    merged_csv_path = dataset_root / f"{league.lower()}_{season}_{dataset}_{source_a}_{source_b}_merged.csv"
    summary_json_path = dataset_root / f"{league.lower()}_{season}_{dataset}_{source_a}_{source_b}_merged_summary.json"

    _write_df(merged_df, merged_csv_path)
    _write_summary_json(
        {
            "dataset": dataset,
            "league": league,
            "season": season,
            "sources": [source_a, source_b],
            "row_count_merged": int(len(merged_df)),
            "columns": list(merged_df.columns),
        },
        summary_json_path,
    )

    return {
        "merged_csv_path": str(merged_csv_path),
        "summary_json_path": str(summary_json_path),
    }


def _maybe_write_manifest(
    manifest_payload: dict[str, Any],
    merged_root: Path,
    dataset: str,
    source_a: str,
    source_b: str,
    league: str,
    season: str,
) -> Path | None:
    if project_write_manifest is None:
        return None

    manifest_dir = merged_root / dataset
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{league.lower()}_{season}_{dataset}_{source_a}_{source_b}_merged_manifest.json"

    supported_kwargs = _filter_supported_kwargs(
        func=project_write_manifest,
        kwargs={
            "manifest_data": manifest_payload,
            "manifest": manifest_payload,
            "path": manifest_path,
            "output_path": manifest_path,
        },
    )

    if not supported_kwargs:
        return None

    result = project_write_manifest(**supported_kwargs)

    if isinstance(result, (str, Path)):
        return Path(result)

    return manifest_path


def _write_df(df: pd.DataFrame, path: Path) -> None:
    if project_write_df_to_csv is not None:
        project_write_df_to_csv(df, path)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _write_summary_json(summary: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_csv(path: Path) -> pd.DataFrame:
    if project_read_csv is not None:
        return project_read_csv(path)

    return pd.read_csv(path)


def _filter_supported_kwargs(func: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    signature = inspect.signature(func)
    accepted = set(signature.parameters.keys())

    return {
        key: value
        for key, value in kwargs.items()
        if key in accepted
    }


def _coerce_df(value: Any) -> pd.DataFrame:
    if value is None:
        return pd.DataFrame()

    if isinstance(value, pd.DataFrame):
        return value

    if isinstance(value, list):
        return pd.DataFrame(value)

    if isinstance(value, dict):
        return pd.DataFrame([value])

    raise TypeError(f"Expected DataFrame-like merge output, got {type(value).__name__}.")


def _find_first_existing_column(
    df: pd.DataFrame,
    candidates: list[str | None],
) -> str | None:
    for candidate in candidates:
        if candidate and candidate in df.columns:
            return candidate
    return None


def _coalesce_series(
    df: pd.DataFrame,
    candidates: list[str | None],
) -> pd.Series:
    existing = [column for column in candidates if column and column in df.columns]

    if not existing:
        return pd.Series(pd.NA, index=df.index, dtype="object")

    merged = df[existing].copy()
    merged = merged.replace({"": pd.NA})

    if len(existing) == 1:
        return merged.iloc[:, 0]

    return merged.bfill(axis=1).iloc[:, 0]


def _discover_token_candidates(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return list(root.rglob("*.csv"))


def _path_matches_filters(
    path: Path,
    source: str,
    dataset: str,
    league: str,
    season: str,
) -> bool:
    haystack = _normalise_token(str(path))
    checks = [
        _normalise_token(source),
        _normalise_token(dataset),
        _normalise_token(league),
        _normalise_token(season),
    ]
    return all(token in haystack for token in checks)


def _candidate_score(
    path: Path,
    source: str,
    dataset: str,
    league: str,
    season: str,
) -> int:
    stem = _normalise_token(path.stem)
    score = 0

    if _normalise_token(source) in stem:
        score += 5
    if _normalise_token(dataset) in stem:
        score += 5
    if _normalise_token(league) in stem:
        score += 5
    if _normalise_token(season) in stem:
        score += 5
    if "matched" in stem:
        score += 2
    if "merged" in stem:
        score += 1

    return score


def _format_success_summary(success: dict[str, Any], verbose: bool) -> str:
    message = f"[ok] merged_rows={success.get('merged_rows', '?')}"

    if verbose:
        interesting_keys = [
            "merged_csv_path",
            "summary_json_path",
            "manifest_path",
        ]
        extras = [
            f"{key}={success[key]}"
            for key in interesting_keys
            if key in success and success[key]
        ]
        if extras:
            message += "\n    " + "\n    ".join(extras)

    return message


def _print_final_summary(
    successes: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    total_jobs: int,
) -> None:
    print("\n" + "=" * 72)
    print("Merged-output run complete")
    print("=" * 72)
    print(f"Total jobs:   {total_jobs}")
    print(f"Succeeded:    {len(successes)}")
    print(f"Failed:       {len(failures)}")

    if failures:
        print("\nFailed jobs:")
        for failure in failures:
            print(
                "- "
                f"{failure['dataset']}/{failure['league']}/{failure['season']} "
                f"{failure['source_a']} vs {failure['source_b']} -> "
                f"{failure['error_type']}: {failure['error_message']}"
            )

    if successes:
        total_rows = sum(int(item.get("merged_rows", 0)) for item in successes)
        print("\nAggregate merged rows:")
        print(f"- Merged rows:  {total_rows}")


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


def _normalise_token(value: str) -> str:
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


if __name__ == "__main__":
    raise SystemExit(main())