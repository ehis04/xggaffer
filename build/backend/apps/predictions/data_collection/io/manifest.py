from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from .csv_writer import ensure_parent_dir


MANIFEST_FIELD_ORDER = [
    "source",
    "dataset",
    "league",
    "season",
    "started_at",
    "finished_at",
    "row_count_raw",
    "row_count_canonical",
    "validation_errors_count",
    "validation_warnings_count",
    "output_paths",
]


def _to_iso(value: str | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _normalize_output_paths(output_paths: Sequence[str | Path] | None) -> list[str]:
    if not output_paths:
        return []
    return [str(Path(path)) for path in output_paths]


def build_manifest(
    *,
    source: str,
    dataset: str,
    league: str,
    season: str,
    started_at: str | datetime | None,
    finished_at: str | datetime | None,
    row_count_raw: int = 0,
    row_count_canonical: int = 0,
    validation_errors_count: int = 0,
    validation_warnings_count: int = 0,
    output_paths: Sequence[str | Path] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "source": source,
        "dataset": dataset,
        "league": league,
        "season": season,
        "started_at": _to_iso(started_at),
        "finished_at": _to_iso(finished_at),
        "row_count_raw": int(row_count_raw),
        "row_count_canonical": int(row_count_canonical),
        "validation_errors_count": int(validation_errors_count),
        "validation_warnings_count": int(validation_warnings_count),
        "output_paths": _normalize_output_paths(output_paths),
    }

    if extra:
        manifest.update(extra)

    return manifest


def write_manifest_json(manifest: dict[str, Any], path: str | Path) -> Path:
    output_path = ensure_parent_dir(path)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2, ensure_ascii=False)

    return output_path


def write_manifest_txt(manifest: dict[str, Any], path: str | Path) -> Path:
    output_path = ensure_parent_dir(path)

    ordered_keys = [key for key in MANIFEST_FIELD_ORDER if key in manifest]
    remaining_keys = [key for key in manifest.keys() if key not in MANIFEST_FIELD_ORDER]
    all_keys = ordered_keys + remaining_keys

    lines: list[str] = []

    for key in all_keys:
        value = manifest[key]

        if key == "output_paths":
            lines.append(f"{key}:")
            if value:
                lines.extend(f"- {item}" for item in value)
            else:
                lines.append("-")
            continue

        lines.append(f"{key}: {value}")

    with output_path.open("w", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")

    return output_path


def write_manifest(manifest: dict[str, Any], path: str | Path) -> Path:
    output_path = Path(path)

    if output_path.suffix.lower() == ".json":
        return write_manifest_json(manifest, output_path)

    if output_path.suffix.lower() == ".txt":
        return write_manifest_txt(manifest, output_path)

    raise ValueError("Manifest path must end with .json or .txt")


__all__ = [
    "MANIFEST_FIELD_ORDER",
    "build_manifest",
    "write_manifest",
    "write_manifest_json",
    "write_manifest_txt",
]