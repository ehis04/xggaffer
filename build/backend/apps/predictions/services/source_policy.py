from __future__ import annotations

from pathlib import Path

import pandas as pd

SOURCE_PRIORITY = [
    "sofascore",
    "understat",
    "whoscored",
    "football_data",
    "native_stats_api",
]

SOURCE_PRIORITY_RANK = {source: idx for idx, source in enumerate(SOURCE_PRIORITY)}

DATA_ROOT = Path(__file__).resolve().parents[4] / "data" / "processed"

MERGED_TEAMS_CSV = DATA_ROOT / "teams" / "merged" / "all_leagues_all_seasons_teams_merged.csv"
MERGED_PLAYERS_CSV = DATA_ROOT / "players" / "merged" / "all_leagues_all_seasons_players_merged.csv"
MERGED_MATCHES_CSV = DATA_ROOT / "matches" / "merged" / "all_leagues_all_seasons_matches_merged.csv"


def latest_available_season(df: pd.DataFrame, season_col: str = "season", default: str = "2024") -> str:
    seasons = pd.to_numeric(df.get(season_col), errors="coerce").dropna().astype(int)
    if seasons.empty:
        return default
    return str(int(seasons.max()))


def season_tokens(season: str | int | None) -> set[str]:
    if season is None:
        return set()

    text = str(season).strip()
    if not text:
        return set()

    tokens = {text}
    digits = "".join(ch for ch in text if ch.isdigit())

    if len(text) == 4 and text.isdigit():
        year = int(text)
        start_short = str(year)[-2:]
        end_short = str(year + 1)[-2:]
        tokens.update(
            {
                f"{text}{end_short}",
                f"{text}-{end_short}",
                f"{text}/{end_short}",
                f"{start_short}{end_short}",
                f"{start_short}/{end_short}",
                f"{start_short}-{end_short}",
            }
        )

    if len(digits) == 6:
        start_full = digits[:4]
        end_short = digits[4:]
        tokens.update({
            digits,
            start_full,
            end_short,
            f"{start_full}-{end_short}",
            f"{start_full}/{end_short}",
            start_full[2:] + end_short,
        })

    if len(digits) == 8:
        start_full = digits[:4]
        end_full = digits[4:]
        tokens.update({digits, f"{start_full}-{end_full[-2:]}", f"{start_full}/{end_full[-2:]}", start_full})

    return {token for token in tokens if token}


def season_group_key(season: str | int | None) -> str:
    if season is None:
        return ""

    text = str(season).strip()
    if not text:
        return ""

    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 4:
        return digits[:4]
    return text


def filter_by_season_tokens(df: pd.DataFrame, season: str | int | None, *, season_col: str = "season") -> pd.DataFrame:
    if df.empty or season is None or season_col not in df.columns:
        return df

    tokens = season_tokens(season)
    if not tokens:
        return df

    season_values = df[season_col].astype(str).str.strip()
    return df[season_values.isin(tokens)]


def apply_source_priority(
    df: pd.DataFrame,
    *,
    dedupe_keys: list[str],
    source_col: str = "source",
) -> tuple[pd.DataFrame, list[str]]:
    if df.empty or source_col not in df.columns:
        return df, []

    preferred = df.copy()
    preferred[source_col] = preferred[source_col].astype(str).str.strip().str.lower()
    preferred["_src_rank"] = preferred[source_col].map(SOURCE_PRIORITY_RANK).fillna(len(SOURCE_PRIORITY))
    preferred = preferred.sort_values("_src_rank").drop_duplicates(subset=dedupe_keys, keep="first")
    used_sources = sorted(preferred[source_col].dropna().unique().tolist())
    preferred = preferred.drop(columns=["_src_rank"])
    return preferred, used_sources


def fuse_source_rows(
    df: pd.DataFrame,
    *,
    dedupe_keys: list[str],
    source_col: str = "source",
) -> tuple[pd.DataFrame, list[str]]:
    if df.empty:
        return df, []

    fused = df.copy()
    group_keys = list(dedupe_keys)

    if "season" in fused.columns and "season" in dedupe_keys:
        fused["_season_group_key"] = fused["season"].map(season_group_key)
        group_keys = ["_season_group_key" if key == "season" else key for key in dedupe_keys]

    if source_col in fused.columns:
        fused[source_col] = fused[source_col].astype(str).str.strip().str.lower()
        fused["_src_rank"] = fused[source_col].map(SOURCE_PRIORITY_RANK).fillna(len(SOURCE_PRIORITY))
        used_sources = sorted(fused[source_col].dropna().unique().tolist())
        fused = fused.sort_values(group_keys + ["_src_rank"])
    else:
        used_sources = []
        fused["_src_rank"] = len(SOURCE_PRIORITY)

    def _combine(group: pd.DataFrame) -> pd.Series:
        group = group.sort_values("_src_rank")
        result: dict[str, object] = {}
        for column in group.columns:
            if column == "_src_rank":
                continue
            if column == source_col:
                result[column] = ",".join(sorted(group[column].dropna().astype(str).unique().tolist()))
                continue
            non_null = group[column].dropna()
            result[column] = non_null.iloc[0] if not non_null.empty else pd.NA
        return pd.Series(result)

    fused = fused.groupby(group_keys, dropna=False, as_index=False).apply(_combine)
    if isinstance(fused.index, pd.MultiIndex):
        fused = fused.reset_index(drop=True)
    fused = fused.drop(columns=["_season_group_key"], errors="ignore")
    return fused, used_sources


def source_coverage_metadata(
    *,
    intent: str,
    used_sources: list[str],
    required_sources: list[str] | None = None,
) -> dict:
    required = required_sources or SOURCE_PRIORITY
    used_set = {s.lower() for s in used_sources}
    missing = [s for s in required if s.lower() not in used_set]
    return {
        "intent": intent,
        "source_priority": SOURCE_PRIORITY,
        "used_sources": sorted(used_sources),
        "missing_sources": missing,
        "source_count": len(used_sources),
        "coverage_status": "full" if not missing else "partial",
    }
