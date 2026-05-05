from __future__ import annotations

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


def merge_processed_dataset(
    dataset: str,
    source_a: str,
    source_b: str,
    source_a_df: pd.DataFrame,
    source_b_df: pd.DataFrame,
    matched_df: pd.DataFrame,
    league: str | None = None,
    season: str | None = None,
) -> pd.DataFrame:
    dataset_value = str(dataset).strip().lower()

    if dataset_value != DATASET_MATCHES:
        raise ValueError(
            f'Merge pipeline currently supports only "{DATASET_MATCHES}". '
            f'Received "{dataset}".'
        )

    return merge_processed_matches(
        source_a=source_a,
        source_b=source_b,
        source_a_df=source_a_df,
        source_b_df=source_b_df,
        matched_df=matched_df,
        league=league,
        season=season,
    )


def merge_processed_matches(
    source_a: str,
    source_b: str,
    source_a_df: pd.DataFrame,
    source_b_df: pd.DataFrame,
    matched_df: pd.DataFrame,
    league: str | None = None,
    season: str | None = None,
) -> pd.DataFrame:
    source_a_name = _clean_token(source_a)
    source_b_name = _clean_token(source_b)

    if source_a_name == source_b_name:
        raise ValueError("source_a and source_b must be different.")

    left_df = _prepare_canonical_source_df(
        df=source_a_df,
        source_name=source_a_name,
    )
    right_df = _prepare_canonical_source_df(
        df=source_b_df,
        source_name=source_b_name,
    )

    matched = matched_df.copy()

    if matched.empty:
        return _build_empty_merged_matches_frame(
            source_a=source_a_name,
            source_b=source_b_name,
        )

    matched_flag_column = _find_first_existing_column(
        matched,
        ["matched_flag", "is_matched"],
    )
    if matched_flag_column is not None:
        matched = matched[matched[matched_flag_column].fillna(False).astype(bool)].copy()

    source_a_match_id_column = _find_first_existing_column(
        matched,
        [
            f"{source_a_name}_source_match_id",
            f"{source_a_name}__source_match_id",
            "left_source_match_id",
            "understat_source_match_id" if source_a_name == SOURCE_UNDERSTAT else None,
            "sofascore_source_match_id" if source_a_name == SOURCE_SOFASCORE else None,
        ],
    )
    source_b_match_id_column = _find_first_existing_column(
        matched,
        [
            f"{source_b_name}_source_match_id",
            f"{source_b_name}__source_match_id",
            "right_source_match_id",
            "understat_source_match_id" if source_b_name == SOURCE_UNDERSTAT else None,
            "sofascore_source_match_id" if source_b_name == SOURCE_SOFASCORE else None,
        ],
    )

    if source_a_match_id_column is None or source_b_match_id_column is None:
        raise KeyError(
            "Matched reconciliation data does not contain the source_match_id columns "
            "required for processed merging."
        )

    if source_a_match_id_column != f"{source_a_name}_source_match_id":
        matched = matched.rename(
            columns={source_a_match_id_column: f"{source_a_name}_source_match_id"}
        )

    if source_b_match_id_column != f"{source_b_name}_source_match_id":
        matched = matched.rename(
            columns={source_b_match_id_column: f"{source_b_name}_source_match_id"}
        )

    matched = matched.merge(
        left_df,
        how="left",
        on=f"{source_a_name}_source_match_id",
    )
    matched = matched.merge(
        right_df,
        how="left",
        on=f"{source_b_name}_source_match_id",
    )

    merged = _derive_common_match_fields(
        df=matched,
        source_a=source_a_name,
        source_b=source_b_name,
        league=league,
        season=season,
    )

    preferred_columns = _preferred_match_column_order(
        source_a=source_a_name,
        source_b=source_b_name,
    )
    remaining_columns = [
        column
        for column in merged.columns
        if column not in preferred_columns
    ]

    merged = merged[preferred_columns + remaining_columns]

    if "canonical_match_key" in merged.columns:
        merged = merged.drop_duplicates(subset=["canonical_match_key"], keep="first")
    else:
        dedupe_columns = [
            column
            for column in [
                f"{source_a_name}_source_match_id",
                f"{source_b_name}_source_match_id",
            ]
            if column in merged.columns
        ]
        if dedupe_columns:
            merged = merged.drop_duplicates(subset=dedupe_columns, keep="first")

    return merged.reset_index(drop=True)


def merge_matches(
    source_a: str,
    source_b: str,
    source_a_df: pd.DataFrame,
    source_b_df: pd.DataFrame,
    matched_df: pd.DataFrame,
    league: str | None = None,
    season: str | None = None,
) -> pd.DataFrame:
    return merge_processed_matches(
        source_a=source_a,
        source_b=source_b,
        source_a_df=source_a_df,
        source_b_df=source_b_df,
        matched_df=matched_df,
        league=league,
        season=season,
    )


def merge_dataset(
    dataset: str,
    source_a: str,
    source_b: str,
    source_a_df: pd.DataFrame,
    source_b_df: pd.DataFrame,
    matched_df: pd.DataFrame,
    league: str | None = None,
    season: str | None = None,
) -> pd.DataFrame:
    return merge_processed_dataset(
        dataset=dataset,
        source_a=source_a,
        source_b=source_b,
        source_a_df=source_a_df,
        source_b_df=source_b_df,
        matched_df=matched_df,
        league=league,
        season=season,
    )


def _prepare_canonical_source_df(
    df: pd.DataFrame,
    source_name: str,
) -> pd.DataFrame:
    prepared = df.copy()

    source_match_id_column = _find_first_existing_column(
        prepared,
        ["source_match_id", f"{source_name}_source_match_id"],
    )
    if source_match_id_column is None:
        raise KeyError(
            f'Canonical processed match data for source "{source_name}" does not contain '
            '"source_match_id".'
        )

    renamed_columns: dict[str, str] = {}
    for column in prepared.columns:
        if column == source_match_id_column:
            renamed_columns[column] = f"{source_name}_source_match_id"
        elif column == "source":
            renamed_columns[column] = f"{source_name}_source"
        elif column.startswith(f"{source_name}_"):
            renamed_columns[column] = column
        else:
            renamed_columns[column] = f"{source_name}_{column}"

    prepared = prepared.rename(columns=renamed_columns)

    return prepared


def _derive_common_match_fields(
    df: pd.DataFrame,
    source_a: str,
    source_b: str,
    league: str | None,
    season: str | None,
) -> pd.DataFrame:
    merged = df.copy()

    merged["league"] = _coalesce_series(
        merged,
        [
            "league",
            f"{source_a}_league",
            f"{source_b}_league",
        ],
    )
    merged["season"] = _coalesce_series(
        merged,
        [
            "season",
            f"{source_a}_season",
            f"{source_b}_season",
        ],
    )
    merged["date"] = _coalesce_series(
        merged,
        [
            "date",
            "date_understat",
            "date_sofascore",
            f"{source_a}_date",
            f"{source_b}_date",
        ],
    )
    merged["home_team"] = _coalesce_series(
        merged,
        [
            "home_team",
            "home_team_understat",
            "home_team_sofascore",
            f"{source_a}_home_team",
            f"{source_b}_home_team",
        ],
    )
    merged["away_team"] = _coalesce_series(
        merged,
        [
            "away_team",
            "away_team_understat",
            "away_team_sofascore",
            f"{source_a}_away_team",
            f"{source_b}_away_team",
        ],
    )
    merged["home_goals"] = _coalesce_series(
        merged,
        [
            "home_goals",
            f"{source_a}_home_goals",
            f"{source_b}_home_goals",
        ],
    )
    merged["away_goals"] = _coalesce_series(
        merged,
        [
            "away_goals",
            f"{source_a}_away_goals",
            f"{source_b}_away_goals",
        ],
    )
    merged["match_status"] = _coalesce_series(
        merged,
        [
            "match_status",
            f"{source_a}_match_status",
            f"{source_b}_match_status",
            f"{source_a}_status",
            f"{source_b}_status",
        ],
    )
    merged["is_finished"] = _coalesce_series(
        merged,
        [
            "is_finished",
            f"{source_a}_is_finished",
            f"{source_b}_is_finished",
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
    merged["merged_source_a"] = source_a
    merged["merged_source_b"] = source_b
    merged["merged_from_reconciliation"] = True

    if league is not None:
        merged["league"] = merged["league"].fillna(str(league).strip())

    if season is not None:
        merged["season"] = merged["season"].fillna(str(season).strip())

    for numeric_column in [
        "home_goals",
        "away_goals",
    ]:
        if numeric_column in merged.columns:
            merged[numeric_column] = pd.to_numeric(
                merged[numeric_column],
                errors="coerce",
            )

    if "is_finished" in merged.columns:
        merged["is_finished"] = merged["is_finished"].map(_coerce_bool)

    return merged


def _build_empty_merged_matches_frame(
    source_a: str,
    source_b: str,
) -> pd.DataFrame:
    columns = _preferred_match_column_order(
        source_a=source_a,
        source_b=source_b,
    )
    return pd.DataFrame(columns=columns)


def _preferred_match_column_order(
    source_a: str,
    source_b: str,
) -> list[str]:
    return [
        "canonical_match_key",
        "league",
        "season",
        "date",
        "home_team",
        "away_team",
        "home_goals",
        "away_goals",
        "match_status",
        "is_finished",
        "understat_source_match_id",
        "sofascore_source_match_id",
        f"{source_a}_source_match_id",
        f"{source_b}_source_match_id",
        "merged_source_a",
        "merged_source_b",
        "merged_from_reconciliation",
    ]


def _coalesce_series(
    df: pd.DataFrame,
    candidates: Iterable[str | None],
) -> pd.Series:
    existing = [
        column
        for column in candidates
        if column and column in df.columns
    ]

    if not existing:
        return pd.Series(pd.NA, index=df.index, dtype="object")

    merged = df[existing].copy()
    merged = merged.replace({"": pd.NA})

    if len(existing) == 1:
        return merged.iloc[:, 0]

    return merged.bfill(axis=1).iloc[:, 0]


def _find_first_existing_column(
    df: pd.DataFrame,
    candidates: Iterable[str | None],
) -> str | None:
    for candidate in candidates:
        if candidate and candidate in df.columns:
            return candidate
    return None


def _coerce_bool(value: Any) -> Any:
    if pd.isna(value):
        return pd.NA

    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    truthy = {"true", "1", "yes", "y", "final", "finished", "ft"}
    falsy = {"false", "0", "no", "n", "scheduled", "not_started"}

    if text in truthy:
        return True
    if text in falsy:
        return False

    return value


def _clean_token(value: str) -> str:
    return str(value).strip().lower()