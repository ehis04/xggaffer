from __future__ import annotations

import argparse
import inspect
import json
import sys
import traceback
from dataclasses import asdict, is_dataclass
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
    from data_collection.reconcilers import matches as matches_reconciler_module
except ImportError as exc:
    raise ImportError(
        "Could not import data_collection.reconcilers.matches. "
        "Phase 11 match reconciliation must exist before reconcile_all.py can run."
    ) from exc

try:
    from data_collection.core.paths import PROCESSED_MATCHES_ROOT, RECONCILIATION_ROOT
    _DEFAULT_CANONICAL_ROOT = PROCESSED_MATCHES_ROOT
    _DEFAULT_AUDIT_ROOT = RECONCILIATION_ROOT / "matches"
except ImportError:
    _DEFAULT_CANONICAL_ROOT = Path("data_collection/output/canonical_processed/matches")
    _DEFAULT_AUDIT_ROOT = Path("data_collection/output/reconciliation_audit/matches")


DEFAULT_SOURCES = [SOURCE_UNDERSTAT, SOURCE_SOFASCORE]
DEFAULT_CANONICAL_ROOT = _DEFAULT_CANONICAL_ROOT
DEFAULT_AUDIT_ROOT = _DEFAULT_AUDIT_ROOT


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Thin orchestration entrypoint for canonical match reconciliation."
    )
    parser.add_argument(
        "--leagues",
        nargs="+",
        default=SUPPORTED_LEAGUES,
        help="League codes to reconcile.",
    )
    parser.add_argument(
        "--seasons",
        nargs="+",
        required=True,
        help='Season values to reconcile, e.g. "2023" "2024".',
    )
    parser.add_argument(
        "--sources",
        nargs=2,
        default=DEFAULT_SOURCES,
        help="Exactly two canonical sources to reconcile.",
    )
    parser.add_argument(
        "--canonical-root",
        default=str(DEFAULT_CANONICAL_ROOT),
        help="Root folder where canonical match CSVs are stored.",
    )
    parser.add_argument(
        "--audit-root",
        default=str(DEFAULT_AUDIT_ROOT),
        help="Root folder where reconciliation audit outputs should be written.",
    )
    parser.add_argument(
        "--source-a-path",
        default=None,
        help="Optional explicit path for the first source canonical CSV.",
    )
    parser.add_argument(
        "--source-b-path",
        default=None,
        help="Optional explicit path for the second source canonical CSV.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop immediately on the first failed reconciliation job.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Alias for --stop-on-error.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed failure traces and resolved file paths.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    stop_on_error = args.stop_on_error or args.fail_fast

    requested_leagues = _normalise_text_list(args.leagues)
    requested_seasons = _normalise_text_list(args.seasons)
    requested_sources = _normalise_text_list(args.sources)

    config_errors = _validate_requested_values(requested_sources)
    if config_errors:
        for error in config_errors:
            print(f"[config-error] {error}", file=sys.stderr)
        return 2

    canonical_root = Path(args.canonical_root)
    audit_root = Path(args.audit_root)

    jobs = _build_jobs(
        leagues=requested_leagues,
        seasons=requested_seasons,
        source_a=requested_sources[0],
        source_b=requested_sources[1],
        source_a_path=args.source_a_path,
        source_b_path=args.source_b_path,
    )

    if not jobs:
        print("No reconciliation jobs were produced from the supplied filters.", file=sys.stderr)
        return 2

    print(
        "Starting reconciliation run for "
        f"{len(jobs)} job(s) across "
        f"{len(requested_leagues)} league(s) and "
        f"{len(requested_seasons)} season(s)."
    )

    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for index, job in enumerate(jobs, start=1):
        league = job["league"]
        season = job["season"]
        source_a = job["source_a"]
        source_b = job["source_b"]

        print(
            f"\n[{index}/{len(jobs)}] "
            f"league={league} season={season} "
            f"sources={source_a},{source_b}"
        )

        try:
            source_a_path = (
                Path(job["source_a_path"])
                if job.get("source_a_path")
                else _discover_canonical_match_file(
                    canonical_root=canonical_root,
                    source=source_a,
                    league=league,
                    season=season,
                )
            )
            source_b_path = (
                Path(job["source_b_path"])
                if job.get("source_b_path")
                else _discover_canonical_match_file(
                    canonical_root=canonical_root,
                    source=source_b,
                    league=league,
                    season=season,
                )
            )

            if args.verbose:
                print(f"Resolved {source_a} file: {source_a_path}")
                print(f"Resolved {source_b} file: {source_b_path}")

            source_a_df = _read_csv(source_a_path)
            source_b_df = _read_csv(source_b_path)

            result = _run_reconciliation(
                source_a=source_a,
                source_b=source_b,
                source_a_df=source_a_df,
                source_b_df=source_b_df,
                league=league,
                season=season,
                source_a_path=source_a_path,
                source_b_path=source_b_path,
            )

            normalised_result = _normalise_reconciliation_result(
                result=result,
                source_a=source_a,
                source_b=source_b,
            )

            output_paths = _write_reconciliation_outputs(
                payload=normalised_result,
                audit_root=audit_root,
                source_a=source_a,
                source_b=source_b,
                league=league,
                season=season,
            )

            manifest_payload = {
                "script": "reconcile_all.py",
                "dataset": DATASET_MATCHES,
                "league": league,
                "season": season,
                "sources": [source_a, source_b],
                "input_paths": {
                    source_a: str(source_a_path),
                    source_b: str(source_b_path),
                },
                "output_paths": output_paths,
                "summary": normalised_result.get("summary", {}),
            }
            manifest_path = _maybe_write_manifest(
                manifest_payload=manifest_payload,
                audit_root=audit_root,
                source_a=source_a,
                source_b=source_b,
                league=league,
                season=season,
            )
            if manifest_path:
                output_paths["manifest_path"] = str(manifest_path)

            success = {
                **job,
                "source_a_path": str(source_a_path),
                "source_b_path": str(source_b_path),
                **output_paths,
                "summary": normalised_result.get("summary", {}),
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
                f"[failed] league={league} season={season} "
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
    leagues: Iterable[str],
    seasons: Iterable[str],
    source_a: str,
    source_b: str,
    source_a_path: str | None,
    source_b_path: str | None,
) -> list[dict[str, str | None]]:
    jobs: list[dict[str, str | None]] = []

    for league in leagues:
        for season in seasons:
            jobs.append(
                {
                    "league": league,
                    "season": season,
                    "source_a": source_a,
                    "source_b": source_b,
                    "source_a_path": source_a_path,
                    "source_b_path": source_b_path,
                }
            )

    return jobs


def _validate_requested_values(sources: list[str]) -> list[str]:
    errors: list[str] = []

    if len(sources) != 2:
        errors.append("reconcile_all.py requires exactly two sources.")

    if len(set(sources)) != len(sources):
        errors.append("The two reconciliation sources must be different.")

    return errors


def _discover_canonical_match_file(
    canonical_root: Path,
    source: str,
    league: str,
    season: str,
) -> Path:
    if not canonical_root.exists():
        raise FileNotFoundError(
            f"Canonical match root does not exist: {canonical_root}"
        )

    candidates = list(canonical_root.rglob("*.csv"))

    if not candidates:
        raise FileNotFoundError(
            f"No canonical match CSV files were found under {canonical_root}"
        )

    filtered = [
        path
        for path in candidates
        if _path_matches_filters(path=path, source=source, league=league, season=season)
    ]

    if not filtered:
        raise FileNotFoundError(
            f'Could not find canonical match CSV for source="{source}", '
            f'league="{league}", season="{season}" under {canonical_root}'
        )

    scored = sorted(
        filtered,
        key=lambda path: _candidate_score(path, source=source, league=league, season=season),
        reverse=True,
    )

    return scored[0]


def _path_matches_filters(path: Path, source: str, league: str, season: str) -> bool:
    haystack = _normalise_token(str(path))
    checks = [
        _normalise_token(source),
        _normalise_token(league),
        _normalise_token(season),
        _normalise_token(DATASET_MATCHES),
    ]
    return all(token in haystack for token in checks)


def _candidate_score(path: Path, source: str, league: str, season: str) -> int:
    stem = _normalise_token(path.stem)
    score = 0

    if _normalise_token(source) in stem:
        score += 5
    if _normalise_token(league) in stem:
        score += 5
    if _normalise_token(season) in stem:
        score += 5
    if _normalise_token(DATASET_MATCHES) in stem:
        score += 3
    if "canonical_processed" in _normalise_token(str(path.parent)):
        score += 2

    return score


def _read_csv(path: Path) -> pd.DataFrame:
    if project_read_csv is not None:
        return project_read_csv(path)

    return pd.read_csv(path)


def _run_reconciliation(
    source_a: str,
    source_b: str,
    source_a_df: pd.DataFrame,
    source_b_df: pd.DataFrame,
    league: str,
    season: str,
    source_a_path: Path,
    source_b_path: Path,
) -> Any:
    reconcile_func = _resolve_reconcile_function()

    candidate_kwargs = {
        "source_a": source_a,
        "source_b": source_b,
        "source_a_df": source_a_df,
        "source_b_df": source_b_df,
        "left_source": source_a,
        "right_source": source_b,
        "left_df": source_a_df,
        "right_df": source_b_df,
        "understat_df": source_a_df if source_a == SOURCE_UNDERSTAT else None,
        "sofascore_df": source_b_df if source_b == SOURCE_SOFASCORE else None,
        "league": league,
        "season": season,
        "source_a_path": str(source_a_path),
        "source_b_path": str(source_b_path),
        "understat_path": str(source_a_path) if source_a == SOURCE_UNDERSTAT else None,
        "sofascore_path": str(source_b_path) if source_b == SOURCE_SOFASCORE else None,
    }

    accepted_kwargs = _filter_supported_kwargs(
        func=reconcile_func,
        kwargs={key: value for key, value in candidate_kwargs.items() if value is not None},
    )

    if not accepted_kwargs:
        raise TypeError(
            "Could not map any supported arguments onto the match reconciler function."
        )

    return reconcile_func(**accepted_kwargs)


def _resolve_reconcile_function() -> Any:
    candidate_names = [
        "reconcile_matches",
        "reconcile_match_datasets",
        "reconcile_match_files",
        "reconcile_understat_and_sofascore_matches",
    ]

    for name in candidate_names:
        func = getattr(matches_reconciler_module, name, None)
        if callable(func):
            return func

    raise AttributeError(
        "No supported reconciliation function was found in data_collection.reconcilers.matches."
    )


def _filter_supported_kwargs(func: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    signature = inspect.signature(func)
    accepted = set(signature.parameters.keys())

    return {
        key: value
        for key, value in kwargs.items()
        if key in accepted
    }


def _normalise_reconciliation_result(
    result: Any,
    source_a: str,
    source_b: str,
) -> dict[str, Any]:
    if result is None:
        return {
            "matched_df": pd.DataFrame(),
            f"{source_a}_unmatched_df": pd.DataFrame(),
            f"{source_b}_unmatched_df": pd.DataFrame(),
            "summary": {},
        }

    if isinstance(result, tuple):
        if len(result) == 4:
            matched_df, source_a_unmatched_df, source_b_unmatched_df, summary = result
            return {
                "matched_df": _coerce_df(matched_df),
                f"{source_a}_unmatched_df": _coerce_df(source_a_unmatched_df),
                f"{source_b}_unmatched_df": _coerce_df(source_b_unmatched_df),
                "summary": _coerce_dict(summary),
            }
        raise TypeError(
            "Tuple reconciliation results must contain exactly four items."
        )

    result_dict = _result_to_dict(result)

    matched_df = _first_present_df(
        result_dict,
        [
            "matched_df",
            "matched",
            "matches_df",
        ],
    )
    source_a_unmatched_df = _first_present_df(
        result_dict,
        [
            f"{source_a}_unmatched_df",
            f"{source_a}_unmatched",
            "left_unmatched_df",
            "left_unmatched",
            "understat_unmatched_df" if source_a == SOURCE_UNDERSTAT else None,
            "understat_unmatched" if source_a == SOURCE_UNDERSTAT else None,
        ],
    )
    source_b_unmatched_df = _first_present_df(
        result_dict,
        [
            f"{source_b}_unmatched_df",
            f"{source_b}_unmatched",
            "right_unmatched_df",
            "right_unmatched",
            "sofascore_unmatched_df" if source_b == SOURCE_SOFASCORE else None,
            "sofascore_unmatched" if source_b == SOURCE_SOFASCORE else None,
        ],
    )
    summary = _first_present_dict(
        result_dict,
        [
            "summary",
            "audit_summary",
            "metrics",
            "summary_dict",
        ],
    )

    return {
        "matched_df": _coerce_df(matched_df),
        f"{source_a}_unmatched_df": _coerce_df(source_a_unmatched_df),
        f"{source_b}_unmatched_df": _coerce_df(source_b_unmatched_df),
        "summary": _coerce_dict(summary),
    }


def _write_reconciliation_outputs(
    payload: dict[str, Any],
    audit_root: Path,
    source_a: str,
    source_b: str,
    league: str,
    season: str,
) -> dict[str, str]:
    base_dir = audit_root / league / str(season)
    base_dir.mkdir(parents=True, exist_ok=True)

    matched_path = base_dir / f"{source_a}_{source_b}_{league}_{season}_matched.csv"
    source_a_unmatched_path = base_dir / f"{source_a}_{league}_{season}_unmatched.csv"
    source_b_unmatched_path = base_dir / f"{source_b}_{league}_{season}_unmatched.csv"
    summary_json_path = base_dir / f"{source_a}_{source_b}_{league}_{season}_summary.json"
    summary_txt_path = base_dir / f"{source_a}_{source_b}_{league}_{season}_summary.txt"

    _write_df(payload.get("matched_df"), matched_path)
    _write_df(payload.get(f"{source_a}_unmatched_df"), source_a_unmatched_path)
    _write_df(payload.get(f"{source_b}_unmatched_df"), source_b_unmatched_path)
    _write_summary_json(payload.get("summary", {}), summary_json_path)
    _write_summary_txt(payload.get("summary", {}), summary_txt_path)

    return {
        "matched_path": str(matched_path),
        f"{source_a}_unmatched_path": str(source_a_unmatched_path),
        f"{source_b}_unmatched_path": str(source_b_unmatched_path),
        "summary_json_path": str(summary_json_path),
        "summary_txt_path": str(summary_txt_path),
    }


def _write_df(df: pd.DataFrame, path: Path) -> None:
    if project_write_df_to_csv is not None:
        project_write_df_to_csv(df, path)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _write_summary_json(summary: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_summary_txt(summary: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    ordered_keys = [
        "total_understat_rows",
        "total_sofascore_rows",
        "matched_count",
        "understat_unmatched_count",
        "sofascore_unmatched_count",
        "match_rate_percentage",
    ]

    lines: list[str] = ["Match reconciliation summary", ""]

    for key in ordered_keys:
        if key in summary:
            lines.append(f"{key}: {summary[key]}")

    remaining_keys = [
        key
        for key in summary.keys()
        if key not in ordered_keys
    ]
    for key in sorted(remaining_keys):
        lines.append(f"{key}: {summary[key]}")

    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _maybe_write_manifest(
    manifest_payload: dict[str, Any],
    audit_root: Path,
    source_a: str,
    source_b: str,
    league: str,
    season: str,
) -> Path | None:
    if project_write_manifest is None:
        return None

    manifest_dir = audit_root / league / str(season)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{source_a}_{source_b}_{league}_{season}_manifest.json"

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


def _result_to_dict(result: Any) -> dict[str, Any]:
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


def _coerce_df(value: Any) -> pd.DataFrame:
    if value is None:
        return pd.DataFrame()

    if isinstance(value, pd.DataFrame):
        return value

    if isinstance(value, list):
        return pd.DataFrame(value)

    if isinstance(value, dict):
        return pd.DataFrame([value])

    raise TypeError(f"Expected DataFrame-like reconciliation output, got {type(value).__name__}.")


def _coerce_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    if is_dataclass(value):
        return asdict(value)

    if hasattr(value, "__dict__"):
        return {
            key: value
            for key, value in vars(value).items()
            if not key.startswith("_")
        }

    return {"value": value}


def _first_present_df(payload: dict[str, Any], keys: list[str | None]) -> pd.DataFrame:
    for key in keys:
        if key and key in payload and payload[key] is not None:
            return _coerce_df(payload[key])
    return pd.DataFrame()


def _first_present_dict(payload: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    for key in keys:
        if key in payload and payload[key] is not None:
            return _coerce_dict(payload[key])
    return {}


def _format_success_summary(success: dict[str, Any], verbose: bool) -> str:
    summary = success.get("summary", {})

    matched_count = _first_present_value(
        summary,
        ["matched_count", "matched_rows", "matched"],
    )
    source_a_unmatched_count = _first_present_value(
        summary,
        ["understat_unmatched_count", "left_unmatched_count", "source_a_unmatched_count"],
    )
    source_b_unmatched_count = _first_present_value(
        summary,
        ["sofascore_unmatched_count", "right_unmatched_count", "source_b_unmatched_count"],
    )
    match_rate = _first_present_value(
        summary,
        ["match_rate_percentage", "match_rate"],
    )

    message = (
        "[ok] "
        f"matched={matched_count if matched_count is not None else '?'} "
        f"source_a_unmatched={source_a_unmatched_count if source_a_unmatched_count is not None else '?'} "
        f"source_b_unmatched={source_b_unmatched_count if source_b_unmatched_count is not None else '?'} "
        f"match_rate={match_rate if match_rate is not None else '?'}"
    )

    if verbose:
        interesting_keys = [
            "matched_path",
            "summary_json_path",
            "summary_txt_path",
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


def _first_present_value(payload: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _print_final_summary(
    successes: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    total_jobs: int,
) -> None:
    print("\n" + "=" * 72)
    print("Reconciliation run complete")
    print("=" * 72)
    print(f"Total jobs:   {total_jobs}")
    print(f"Succeeded:    {len(successes)}")
    print(f"Failed:       {len(failures)}")

    if failures:
        print("\nFailed jobs:")
        for failure in failures:
            print(
                "- "
                f"{failure['league']}/{failure['season']} "
                f"{failure['source_a']} vs {failure['source_b']} -> "
                f"{failure['error_type']}: {failure['error_message']}"
            )

    if successes:
        total_matched = 0
        total_source_a_unmatched = 0
        total_source_b_unmatched = 0

        for success in successes:
            summary = success.get("summary", {})
            total_matched += _safe_int(
                _first_present_value(summary, ["matched_count", "matched_rows", "matched"])
            )
            total_source_a_unmatched += _safe_int(
                _first_present_value(summary, ["understat_unmatched_count", "left_unmatched_count"])
            )
            total_source_b_unmatched += _safe_int(
                _first_present_value(summary, ["sofascore_unmatched_count", "right_unmatched_count"])
            )

        print("\nAggregate reconciliation counts:")
        print(f"- Matched:              {total_matched}")
        print(f"- Source A unmatched:   {total_source_a_unmatched}")
        print(f"- Source B unmatched:   {total_source_b_unmatched}")


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


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
    return "".join(ch for ch in value.lower().strip() if ch.isalnum())


if __name__ == "__main__":
    raise SystemExit(main())