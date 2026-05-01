from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import LEGACY_UNDERSTAT_MATCHES_CSV, MATCHES_CSV


def load_match_index(path: Path | None = None) -> pd.DataFrame:
    primary_path = path or MATCHES_CSV

    if primary_path.exists():
        matches = pd.read_csv(primary_path, low_memory=False)
        return _normalize_processed_merged_matches(matches)

    if LEGACY_UNDERSTAT_MATCHES_CSV.exists():
        return pd.read_csv(LEGACY_UNDERSTAT_MATCHES_CSV)

    raise FileNotFoundError(
        f"No merged match index found. Checked: {primary_path}, {LEGACY_UNDERSTAT_MATCHES_CSV}"
    )


def _normalize_processed_merged_matches(matches: pd.DataFrame) -> pd.DataFrame:
    normalized = matches.copy()

    if "source" in normalized.columns:
        normalized = normalized[normalized["source"] == "understat"].copy()

    if "source_match_id" in normalized.columns and "match_id" not in normalized.columns:
        normalized = normalized.rename(columns={"source_match_id": "match_id"})

    if "season" in normalized.columns:
        normalized["season"] = pd.to_numeric(normalized["season"], errors="coerce")

    dedupe_columns = [column for column in ["match_id", "date", "home_team", "away_team"] if column in normalized.columns]
    if dedupe_columns:
        normalized = normalized.drop_duplicates(subset=dedupe_columns, keep="first")

    return normalized.reset_index(drop=True)