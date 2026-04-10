from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

try:
    from data_collection.config.team_name_mappings import TEAM_NAME_MAPPINGS
except ImportError:
    TEAM_NAME_MAPPINGS = {}

try:
    from data_collection.config.league_name_mappings import LEAGUE_NAME_MAPPINGS
except ImportError:
    LEAGUE_NAME_MAPPINGS = {}

try:
    from data_collection.io.csv_writer import ensure_parent_dir
except ImportError:
    def ensure_parent_dir(path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path


DEFAULT_LEAGUE_NAME_MAPPINGS = {
    "eng_premier_league": "EPL",
    "epl": "EPL",
    "premier_league": "EPL",
    "esp_la_liga": "La_Liga",
    "la_liga": "La_Liga",
    "ger_bundesliga": "Bundesliga",
    "bundesliga": "Bundesliga",
    "ita_serie_a": "Serie_A",
    "serie_a": "Serie_A",
    "fra_ligue_1": "Ligue_1",
    "ligue_1": "Ligue_1",
    "rus_premier_league": "RFPL",
    "rfpl": "RFPL",
}

DEFAULT_TEAM_NAME_MAPPINGS = {
    "ac_milan": "AC Milan",
    "ac_milan_1899": "AC Milan",
    "atletico_madrid": "Atletico Madrid",
    "atletico_de_madrid": "Atletico Madrid",
    "bayern_munchen": "Bayern Munich",
    "bayern_munich": "Bayern Munich",
    "borussia_monchengladbach": "Borussia Monchengladbach",
    "cadiz_cf": "Cadiz",
    "internazionale": "Inter",
    "inter_milan": "Inter",
    "losc_lille": "Lille",
    "lille_osc": "Lille",
    "man_city": "Manchester City",
    "manchester_city": "Manchester City",
    "man_utd": "Manchester United",
    "manchester_utd": "Manchester United",
    "manchester_united": "Manchester United",
    "newcastle": "Newcastle United",
    "newcastle_utd": "Newcastle United",
    "newcastle_united": "Newcastle United",
    "paris_saint_germain": "PSG",
    "psg": "PSG",
    "rayo_vallecano_de_madrid": "Rayo Vallecano",
    "real_sociedad_de_futbol": "Real Sociedad",
    "spal": "SPAL 2013",
    "spal_2013": "SPAL 2013",
    "spurs": "Tottenham Hotspur",
    "tottenham": "Tottenham Hotspur",
    "tottenham_hotspur": "Tottenham Hotspur",
    "wolverhampton": "Wolverhampton Wanderers",
    "wolverhampton_wanderers": "Wolverhampton Wanderers",
    "wolves": "Wolverhampton Wanderers",
}

AUDIT_OUTPUT_COLUMNS = [
    "understat_source_match_id",
    "sofascore_source_match_id",
    "canonical_match_key",
    "home_team_understat",
    "home_team_sofascore",
    "away_team_understat",
    "away_team_sofascore",
    "date_understat",
    "date_sofascore",
    "matched_flag",
    "notes",
]


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def clean_text(value: Any) -> str | None:
    if _is_missing(value):
        return None

    text = str(value).strip()
    if not text:
        return None

    return text


def fold_to_ascii(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")


def lowercase_text(value: Any) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    return text.lower()


def trim_whitespace(value: Any) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    return re.sub(r"\s+", " ", text).strip()


def remove_safe_punctuation(value: Any) -> str | None:
    text = trim_whitespace(value)
    if text is None:
        return None

    text = fold_to_ascii(text)
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text or None


def spaces_to_underscores(value: Any) -> str | None:
    text = remove_safe_punctuation(value)
    if text is None:
        return None

    text = text.lower()
    text = re.sub(r"[\s-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")

    return text or None


def normalize_match_date(value: Any) -> str | None:
    if _is_missing(value):
        return None

    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None

    return parsed.strftime("%Y-%m-%d")


def normalize_season(value: Any) -> str | None:
    text = clean_text(value)
    if text is None:
        return None

    if text.isdigit() and len(text) == 4:
        return text

    match = re.match(r"^(\d{4})[/-](\d{2,4})$", text)
    if match:
        return match.group(1)

    if len(text) >= 4 and text[:4].isdigit():
        return text[:4]

    return text


def _merge_mappings(defaults: Mapping[str, str], custom: Mapping[str, str]) -> dict[str, str]:
    merged = dict(defaults)
    merged.update(custom)
    return merged


def normalize_league_name(value: Any) -> str | None:
    token = spaces_to_underscores(value)
    if token is None:
        return None

    mapping = _merge_mappings(DEFAULT_LEAGUE_NAME_MAPPINGS, LEAGUE_NAME_MAPPINGS)
    canonical = mapping.get(token)

    if canonical:
        return canonical

    return clean_text(value)


def normalize_team_name(value: Any) -> str | None:
    token = spaces_to_underscores(value)
    if token is None:
        return None

    mapping = _merge_mappings(DEFAULT_TEAM_NAME_MAPPINGS, TEAM_NAME_MAPPINGS)
    canonical = mapping.get(token)

    if canonical:
        return canonical

    text = remove_safe_punctuation(value)
    if text is None:
        return None

    words: list[str] = []
    for word in text.split():
        upper_word = word.upper()
        if upper_word in {"AC", "FC", "CF", "SC", "SSC", "TSG", "PSG", "RB"}:
            words.append(upper_word)
        else:
            words.append(word.capitalize())

    return " ".join(words)


def normalize_team_token(value: Any) -> str | None:
    canonical_name = normalize_team_name(value)
    if canonical_name is None:
        return None
    return spaces_to_underscores(canonical_name)


def normalize_league_token(value: Any) -> str | None:
    canonical_name = normalize_league_name(value)
    if canonical_name is None:
        return None
    return spaces_to_underscores(canonical_name)


def build_canonical_match_key(
    *,
    league: Any,
    season: Any,
    date: Any,
    home_team: Any,
    away_team: Any,
) -> str | None:
    league_norm = normalize_league_token(league)
    season_norm = normalize_season(season)
    date_norm = normalize_match_date(date)
    home_team_norm = normalize_team_token(home_team)
    away_team_norm = normalize_team_token(away_team)

    parts = [
        league_norm,
        season_norm,
        date_norm,
        home_team_norm,
        away_team_norm,
    ]

    if any(part is None for part in parts):
        return None

    return "|".join(parts)


def build_canonical_match_key_from_row(row: Mapping[str, Any]) -> str | None:
    return build_canonical_match_key(
        league=row.get("league"),
        season=row.get("season"),
        date=row.get("date"),
        home_team=row.get("home_team"),
        away_team=row.get("away_team"),
    )


def add_canonical_match_key(df: pd.DataFrame) -> pd.DataFrame:
    keyed_df = df.copy()
    keyed_df["canonical_match_key"] = keyed_df.apply(
        lambda row: build_canonical_match_key_from_row(row),
        axis=1,
    )
    return keyed_df


def _prepare_source_frame(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    prepared_df = df.copy()

    if "canonical_match_key" not in prepared_df.columns or prepared_df["canonical_match_key"].isna().all():
        prepared_df = add_canonical_match_key(prepared_df)

    prepared_df["canonical_match_key"] = prepared_df["canonical_match_key"].astype(object)

    duplicate_mask = (
        prepared_df["canonical_match_key"].notna()
        & prepared_df["canonical_match_key"].duplicated(keep=False)
    )

    prepared_df[f"{source_name}_source_match_id"] = prepared_df.get("source_match_id")
    prepared_df[f"home_team_{source_name}"] = prepared_df.get("home_team")
    prepared_df[f"away_team_{source_name}"] = prepared_df.get("away_team")
    prepared_df[f"date_{source_name}"] = prepared_df.get("date")
    prepared_df[f"{source_name}_key_missing"] = prepared_df["canonical_match_key"].isna()
    prepared_df[f"{source_name}_key_duplicate"] = duplicate_mask

    columns = [
        "canonical_match_key",
        f"{source_name}_source_match_id",
        f"home_team_{source_name}",
        f"away_team_{source_name}",
        f"date_{source_name}",
        f"{source_name}_key_missing",
        f"{source_name}_key_duplicate",
    ]

    return prepared_df.loc[:, columns]


def _build_note(row: pd.Series) -> str | None:
    notes: list[str] = []

    matched_flag = bool(row.get("matched_flag", False))
    understat_id = row.get("understat_source_match_id")
    sofascore_id = row.get("sofascore_source_match_id")

    if matched_flag:
        notes.append("matched_on_canonical_match_key")
    else:
        if not _is_missing(understat_id) and _is_missing(sofascore_id):
            notes.append("missing_in_sofascore")
        if _is_missing(understat_id) and not _is_missing(sofascore_id):
            notes.append("missing_in_understat")

    if bool(row.get("understat_key_missing", False)):
        notes.append("missing_canonical_match_key_understat")
    if bool(row.get("sofascore_key_missing", False)):
        notes.append("missing_canonical_match_key_sofascore")

    if bool(row.get("understat_key_duplicate", False)):
        notes.append("duplicate_canonical_key_understat")
    if bool(row.get("sofascore_key_duplicate", False)):
        notes.append("duplicate_canonical_key_sofascore")

    if not notes:
        return None

    return ";".join(notes)


def _finalize_audit_frame(df: pd.DataFrame) -> pd.DataFrame:
    audit_df = df.copy()
    audit_df["matched_flag"] = (
        audit_df["understat_source_match_id"].notna()
        & audit_df["sofascore_source_match_id"].notna()
    )
    audit_df["notes"] = audit_df.apply(_build_note, axis=1)

    for column in AUDIT_OUTPUT_COLUMNS:
        if column not in audit_df.columns:
            audit_df[column] = None

    return audit_df.loc[:, AUDIT_OUTPUT_COLUMNS]


def build_reconciliation_summary(
    *,
    understat_df: pd.DataFrame,
    sofascore_df: pd.DataFrame,
    matched_df: pd.DataFrame,
    understat_unmatched_df: pd.DataFrame,
    sofascore_unmatched_df: pd.DataFrame,
) -> dict[str, Any]:
    total_understat_rows = int(len(understat_df))
    total_sofascore_rows = int(len(sofascore_df))
    matched_count = int(len(matched_df))
    understat_unmatched_count = int(len(understat_unmatched_df))
    sofascore_unmatched_count = int(len(sofascore_unmatched_df))

    denominator = max(total_understat_rows, total_sofascore_rows, 1)
    match_rate_percentage = round((matched_count / denominator) * 100, 2)

    return {
        "total_understat_rows": total_understat_rows,
        "total_sofascore_rows": total_sofascore_rows,
        "matched_count": matched_count,
        "understat_unmatched_count": understat_unmatched_count,
        "sofascore_unmatched_count": sofascore_unmatched_count,
        "match_rate_percentage": match_rate_percentage,
    }


def build_reconciliation_summary_text(summary: Mapping[str, Any]) -> str:
    lines = [f"{key}: {value}" for key, value in summary.items()]
    return "\n".join(lines) + "\n"


def write_reconciliation_summary(summary: Mapping[str, Any], path: str | Path) -> Path:
    output_path = ensure_parent_dir(path)

    if output_path.suffix.lower() == ".json":
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(dict(summary), file, indent=2, ensure_ascii=False)
        return output_path

    with output_path.open("w", encoding="utf-8") as file:
        file.write(build_reconciliation_summary_text(summary))
    return output_path


def reconcile_match_dataframes(
    understat_df: pd.DataFrame,
    sofascore_df: pd.DataFrame,
) -> dict[str, Any]:
    prepared_understat_df = _prepare_source_frame(understat_df, "understat")
    prepared_sofascore_df = _prepare_source_frame(sofascore_df, "sofascore")

    merged_df = prepared_understat_df.merge(
        prepared_sofascore_df,
        on="canonical_match_key",
        how="outer",
    )

    audit_df = _finalize_audit_frame(merged_df)

    matched_df = audit_df[audit_df["matched_flag"]].reset_index(drop=True)

    understat_unmatched_df = audit_df[
        audit_df["understat_source_match_id"].notna() & ~audit_df["matched_flag"]
    ].reset_index(drop=True)

    sofascore_unmatched_df = audit_df[
        audit_df["sofascore_source_match_id"].notna() & ~audit_df["matched_flag"]
    ].reset_index(drop=True)

    summary = build_reconciliation_summary(
        understat_df=understat_df,
        sofascore_df=sofascore_df,
        matched_df=matched_df,
        understat_unmatched_df=understat_unmatched_df,
        sofascore_unmatched_df=sofascore_unmatched_df,
    )

    return {
        "matched_df": matched_df,
        "understat_unmatched_df": understat_unmatched_df,
        "sofascore_unmatched_df": sofascore_unmatched_df,
        "audit_summary": summary,
    }


reconcile_matches = reconcile_match_dataframes

__all__ = [
    "AUDIT_OUTPUT_COLUMNS",
    "add_canonical_match_key",
    "build_canonical_match_key",
    "build_canonical_match_key_from_row",
    "build_reconciliation_summary",
    "build_reconciliation_summary_text",
    "clean_text",
    "fold_to_ascii",
    "lowercase_text",
    "normalize_league_name",
    "normalize_league_token",
    "normalize_match_date",
    "normalize_season",
    "normalize_team_name",
    "normalize_team_token",
    "reconcile_match_dataframes",
    "remove_safe_punctuation",
    "spaces_to_underscores",
    "trim_whitespace",
    "write_reconciliation_summary",
]