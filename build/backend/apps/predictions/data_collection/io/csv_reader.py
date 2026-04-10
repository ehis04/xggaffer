from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


def normalize_empty_strings(df: pd.DataFrame) -> pd.DataFrame:
    normalized_df = df.copy()

    object_columns = normalized_df.select_dtypes(include=["object", "string"]).columns
    for column in object_columns:
        normalized_df[column] = normalized_df[column].replace(r"^\s*$", pd.NA, regex=True)

    return normalized_df


def read_csv(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)
    return normalize_empty_strings(df)


def read_many_csv(paths: Iterable[str | Path]) -> pd.DataFrame:
    path_list = list(paths)

    if not path_list:
        return pd.DataFrame()

    dataframes = [read_csv(path) for path in path_list]
    combined_df = pd.concat(dataframes, ignore_index=True, sort=False)

    return normalize_empty_strings(combined_df)


__all__ = [
    "normalize_empty_strings",
    "read_csv",
    "read_many_csv",
]