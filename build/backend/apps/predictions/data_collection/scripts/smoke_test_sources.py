from __future__ import annotations

import argparse
import importlib
import inspect
import json
import sys
import traceback
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from data_collection.io.csv_writer import write_df_to_csv as project_write_df_to_csv
except ImportError:
    project_write_df_to_csv = None

try:
    from data_collection.io.manifest import write_manifest as project_write_manifest
except ImportError:
    project_write_manifest = None

DEFAULT_RAW_ROOT = Path("data_collection/output/raw")
DEFAULT_CANONICAL_ROOT = Path("data_collection/output/canonical_processed")
DEFAULT_SMOKE_ROOT = Path("data_collection/output/smoke_tests")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Development smoke test for one source/dataset/league/season. "
            "Runs the extractor directly, prints raw columns and row counts, "
            "and optionally runs transformer/validator and saves outputs."
        )
    )
    parser.add_argument("--source", required=True, help='Example: "understat" or "sofascore"')
    parser.add_argument("--dataset", required=True, help='Example: "matches", "players", "teams"')
    parser.add_argument("--league", required=True, help='Example: "EPL"')
    parser.add_argument("--season", required=True, help='Example: "2024"')
    parser.add_argument(
        "--raw-only",
        action="store_true",
        help="Only run the extractor and inspect raw output.",
    )
    parser.add_argument(
        "--skip-save",
        action="store_true",
        help="Do not save raw or canonical smoke-test outputs.",
    )
    parser.add_argument(
        "--run-validator",
        action="store_true",
        help="Run dataset validator if one exists and a transformed frame is available.",
    )
    parser.add_argument(
        "--head",
        type=int,
        default=5,
        help="Number of preview rows to print. Default: 5",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed tracebacks and extra metadata.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    source = args.source.strip()
    dataset = args.dataset.strip()
    league = args.league.strip()
    season = args.season.strip()

    print(
        "Running smoke test for "
        f"source={source} dataset={dataset} league={league} season={season}"
    )

    try:
        extractor_module = _import_module(
            f"data_collection.extractors.{source}.{dataset}"
        )
        extractor_func = _resolve_extractor_function(
            module=extractor_module,
            source=source,
            dataset=dataset,
        )

        raw_result = _call_with_supported_kwargs(
            func=extractor_func,
            kwargs={
                "league": league,
                "season": season,
                "source": source,
                "dataset": dataset,
            },
        )
        raw_df = _coerce_to_dataframe(raw_result)

        print("\n" + "=" * 72)
        print("RAW OUTPUT")
        print("=" * 72)
        _print_dataframe_summary(
            df=raw_df,
            label="raw",
            head=args.head,
        )

        saved_paths: dict[str, str] = {}

        if not args.skip_save:
            raw_path = _build_raw_output_path(
                source=source,
                dataset=dataset,
                league=league,
                season=season,
            )
            _write_df(raw_df, raw_path)
            saved_paths["raw_output_path"] = str(raw_path)
            print(f"\nSaved raw smoke-test output to: {raw_path}")

        transformed_df: pd.DataFrame | None = None
        validator_summary: dict[str, Any] | None = None

        if not args.raw_only:
            transformer_module = _import_module_optional(
                f"data_collection.transformers.{source}.{dataset}"
            )

            if transformer_module is None:
                print(
                    "\nNo transformer module found. "
                    "Stopping after raw inspection, which is still valid for a smoke test."
                )
            else:
                transformer_func = _resolve_transformer_function(
                    module=transformer_module,
                    source=source,
                    dataset=dataset,
                )
                transformed_result = _call_with_supported_kwargs(
                    func=transformer_func,
                    kwargs={
                        "raw_df": raw_df,
                        "df": raw_df,
                        "league": league,
                        "season": season,
                        "source": source,
                        "dataset": dataset,
                    },
                )
                transformed_df = _coerce_to_dataframe(transformed_result)

                print("\n" + "=" * 72)
                print("TRANSFORMED OUTPUT")
                print("=" * 72)
                _print_dataframe_summary(
                    df=transformed_df,
                    label="canonical",
                    head=args.head,
                )

                if not args.skip_save:
                    canonical_path = _build_canonical_output_path(
                        source=source,
                        dataset=dataset,
                        league=league,
                        season=season,
                    )
                    _write_df(transformed_df, canonical_path)
                    saved_paths["canonical_output_path"] = str(canonical_path)
                    print(f"\nSaved canonical smoke-test output to: {canonical_path}")

                if args.run_validator:
                    validator_summary = _run_validator_if_available(
                        dataset=dataset,
                        transformed_df=transformed_df,
                        source=source,
                        league=league,
                        season=season,
                    )

        if not args.skip_save:
            manifest_path = _write_smoke_manifest(
                source=source,
                dataset=dataset,
                league=league,
                season=season,
                raw_df=raw_df,
                transformed_df=transformed_df,
                validator_summary=validator_summary,
                saved_paths=saved_paths,
            )
            if manifest_path:
                print(f"Saved smoke-test manifest to: {manifest_path}")

        print("\nSmoke test completed successfully.")
        return 0

    except Exception as exc:
        print(f"\nSmoke test failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc()
        return 1


def _import_module(module_path: str) -> Any:
    return importlib.import_module(module_path)


def _import_module_optional(module_path: str) -> Any | None:
    try:
        return importlib.import_module(module_path)
    except ImportError:
        return None


def _resolve_extractor_function(module: Any, source: str, dataset: str) -> Any:
    candidates = [
        f"fetch_{source}_{dataset}",
        f"extract_{source}_{dataset}",
        f"get_{source}_{dataset}",
        f"fetch_{dataset}",
        f"extract_{dataset}",
        f"get_{dataset}",
        "fetch_data",
        "extract_data",
        "run",
    ]
    return _resolve_callable(module, candidates, "extractor")


def _resolve_transformer_function(module: Any, source: str, dataset: str) -> Any:
    candidates = [
        f"transform_{source}_{dataset}",
        f"map_{source}_{dataset}",
        f"transform_{dataset}",
        f"map_{dataset}",
        "transform",
        "run",
    ]
    return _resolve_callable(module, candidates, "transformer")


def _resolve_callable(module: Any, candidates: list[str], label: str) -> Any:
    for name in candidates:
        func = getattr(module, name, None)
        if callable(func):
            return func

    available = sorted(
        name
        for name in dir(module)
        if callable(getattr(module, name)) and not name.startswith("_")
    )
    raise AttributeError(
        f"Could not resolve {label} function. Tried {candidates}. "
        f"Available callables: {available}"
    )


def _call_with_supported_kwargs(func: Any, kwargs: dict[str, Any]) -> Any:
    signature = inspect.signature(func)
    accepted = set(signature.parameters.keys())

    supported_kwargs = {
        key: value
        for key, value in kwargs.items()
        if key in accepted
    }

    return func(**supported_kwargs)


def _coerce_to_dataframe(value: Any) -> pd.DataFrame:
    if value is None:
        return pd.DataFrame()

    if isinstance(value, pd.DataFrame):
        return value

    if isinstance(value, list):
        return pd.DataFrame(value)

    if isinstance(value, dict):
        return pd.DataFrame([value])

    if hasattr(value, "__dict__"):
        return pd.DataFrame([vars(value)])

    raise TypeError(
        f"Could not coerce value of type {type(value).__name__} into a DataFrame."
    )


def _print_dataframe_summary(df: pd.DataFrame, label: str, head: int) -> None:
    print(f"{label.title()} row count: {len(df)}")
    print(f"{label.title()} column count: {len(df.columns)}")

    if df.empty:
        print(f"{label.title()} columns: []")
        print(f"{label.title()} preview: DataFrame is empty.")
        return

    print(f"{label.title()} columns:")
    for column in df.columns:
        print(f"- {column}")

    print(f"\nFirst {min(head, len(df))} {label} row(s):")
    with pd.option_context(
        "display.max_columns", None,
        "display.width", 200,
        "display.max_colwidth", 80,
    ):
        print(df.head(head).to_string(index=False))


def _run_validator_if_available(
    dataset: str,
    transformed_df: pd.DataFrame,
    source: str,
    league: str,
    season: str,
) -> dict[str, Any] | None:
    validator_module = _import_module_optional(f"data_collection.validators.{dataset}")

    if validator_module is None:
        print("\nNo validator module found for this dataset.")
        return None

    validator_func = _resolve_validator_function(validator_module)

    print("\n" + "=" * 72)
    print("VALIDATION")
    print("=" * 72)

    result = _call_with_supported_kwargs(
        func=validator_func,
        kwargs={
            "df": transformed_df,
            "dataframe": transformed_df,
            "dataset": dataset,
            "source": source,
            "league": league,
            "season": season,
        },
    )

    summary = _normalise_validator_result(result)

    print(f"Validation errors: {len(summary.get('errors', []))}")
    print(f"Validation warnings: {len(summary.get('warnings', []))}")

    if summary.get("summary"):
        print("Validation summary:")
        print(json.dumps(summary["summary"], indent=2, ensure_ascii=False))

    if summary.get("errors"):
        print("Validation error details:")
        for error in summary["errors"]:
            print(f"- {error}")

    if summary.get("warnings"):
        print("Validation warning details:")
        for warning in summary["warnings"]:
            print(f"- {warning}")

    return summary


def _resolve_validator_function(module: Any) -> Any:
    candidates = [
        "validate_matches",
        "validate_players",
        "validate_teams",
        "validate_team_summaries",
        "validate_dataset",
        "validate",
        "run",
    ]
    return _resolve_callable(module, candidates, "validator")


def _normalise_validator_result(result: Any) -> dict[str, Any]:
    if result is None:
        return {"errors": [], "warnings": [], "summary": {}}

    if isinstance(result, tuple):
        if len(result) == 4:
            cleaned_df, errors, warnings, summary = result
            return {
                "cleaned_df": _coerce_to_dataframe(cleaned_df),
                "errors": list(errors or []),
                "warnings": list(warnings or []),
                "summary": dict(summary or {}),
            }

    if isinstance(result, dict):
        normalised = {
            "errors": list(result.get("errors", []) or []),
            "warnings": list(result.get("warnings", []) or []),
            "summary": dict(result.get("summary", {}) or {}),
        }
        if result.get("cleaned_df") is not None:
            normalised["cleaned_df"] = _coerce_to_dataframe(result["cleaned_df"])
        return normalised

    return {"errors": [], "warnings": [], "summary": {"raw_result": str(result)}}


def _build_raw_output_path(
    source: str,
    dataset: str,
    league: str,
    season: str,
) -> Path:
    output_dir = DEFAULT_RAW_ROOT / source / dataset
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / (
        f"{league.lower()}_{season}_{dataset}_{source}_smoke_test_raw.csv"
    )


def _build_canonical_output_path(
    source: str,
    dataset: str,
    league: str,
    season: str,
) -> Path:
    output_dir = DEFAULT_CANONICAL_ROOT / dataset
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / (
        f"{league.lower()}_{season}_{dataset}_{source}_smoke_test_canonical.csv"
    )


def _write_df(df: pd.DataFrame, path: Path) -> None:
    if project_write_df_to_csv is not None:
        supported_kwargs = _filter_supported_kwargs(
            func=project_write_df_to_csv,
            kwargs={
                "df": df,
                "dataframe": df,
                "path": path,
                "output_path": path,
            },
        )
        if supported_kwargs:
            project_write_df_to_csv(**supported_kwargs)
            return

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _write_smoke_manifest(
    source: str,
    dataset: str,
    league: str,
    season: str,
    raw_df: pd.DataFrame,
    transformed_df: pd.DataFrame | None,
    validator_summary: dict[str, Any] | None,
    saved_paths: dict[str, str],
) -> Path | None:
    manifest_dir = DEFAULT_SMOKE_ROOT
    manifest_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = manifest_dir / (
        f"{league.lower()}_{season}_{dataset}_{source}_smoke_test_manifest.json"
    )

    serialisable_validator_summary = {
        key: value
        for key, value in (validator_summary or {}).items()
        if not isinstance(value, pd.DataFrame)
    }

    manifest_payload = {
        "script": "smoke_test_sources.py",
        "source": source,
        "dataset": dataset,
        "league": league,
        "season": season,
        "raw_row_count": int(len(raw_df)),
        "raw_columns": list(raw_df.columns),
        "canonical_row_count": int(len(transformed_df)) if transformed_df is not None else None,
        "canonical_columns": list(transformed_df.columns) if transformed_df is not None else None,
        "saved_paths": saved_paths,
        "validator_summary": serialisable_validator_summary,
    }

    if project_write_manifest is not None:
        supported_kwargs = _filter_supported_kwargs(
            func=project_write_manifest,
            kwargs={
                "manifest_data": manifest_payload,
                "manifest": manifest_payload,
                "path": manifest_path,
                "output_path": manifest_path,
            },
        )
        if supported_kwargs:
            result = project_write_manifest(**supported_kwargs)
            if isinstance(result, (str, Path)):
                return Path(result)
            return manifest_path

    manifest_path.write_text(
        json.dumps(manifest_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest_path


def _filter_supported_kwargs(func: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    signature = inspect.signature(func)
    accepted = set(signature.parameters.keys())
    return {
        key: value
        for key, value in kwargs.items()
        if key in accepted
    }


if __name__ == "__main__":
    raise SystemExit(main())