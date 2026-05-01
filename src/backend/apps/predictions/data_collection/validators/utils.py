import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from ..core.paths import VALIDATION_ROOT, ensure_dir


def slugify_token(value: Any) -> str:
    text = "" if value is None else str(value).strip().lower()
    if not text:
        return "unknown"
    return "_".join(text.split())


def resolve_context_value(
    explicit_value: Any,
    cleaned_rows: Sequence[Mapping[str, Any]],
    field_name: str,
) -> Any:
    if explicit_value not in (None, ""):
        return explicit_value

    for row in cleaned_rows:
        value = row.get(field_name)
        if value not in (None, ""):
            return value

    return "unknown"


def cleaned_rows_to_df(
    cleaned_rows: list[dict[str, Any]],
    columns: Sequence[str],
) -> pd.DataFrame:
    return pd.DataFrame(cleaned_rows, columns=list(columns))


def build_validation_summary(
    dataset: str,
    cleaned_rows: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    errored_row_indices = sorted(
        {
            issue["row_index"]
            for issue in errors
            if issue.get("row_index") is not None
        }
    )

    return {
        "dataset": dataset,
        "row_count": len(cleaned_rows),
        "cleaned_row_count": len(cleaned_rows),
        "valid_row_count": len(cleaned_rows) - len(errored_row_indices),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errored_row_indices": errored_row_indices,
    }


def build_validation_report_path(
    source: Any,
    league: Any,
    season: Any,
    dataset: str,
) -> Path:
    filename = (
        f"{slugify_token(source)}_"
        f"{slugify_token(league)}_"
        f"{slugify_token(season)}_"
        f"{slugify_token(dataset)}_validation.txt"
    )
    return ensure_dir(VALIDATION_ROOT) / filename


def write_validation_report(
    path: Path,
    summary: dict[str, Any],
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> Path:
    content = "\n".join(
        [
            "SUMMARY",
            json.dumps(summary, indent=2, ensure_ascii=False),
            "",
            "ERRORS",
            json.dumps(errors, indent=2, ensure_ascii=False),
            "",
            "WARNINGS",
            json.dumps(warnings, indent=2, ensure_ascii=False),
            "",
        ]
    )

    path.write_text(content, encoding="utf-8")
    return path