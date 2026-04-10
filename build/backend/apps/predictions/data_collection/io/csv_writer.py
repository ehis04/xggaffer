from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping, Any

import pandas as pd


def ensure_parent_dir(path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def write_df_to_csv(df: pd.DataFrame, path: str | Path) -> Path:
    output_path = ensure_parent_dir(path)
    df.to_csv(output_path, index=False)
    return output_path


def write_rows_to_csv(rows: Iterable[Mapping[str, Any]], path: str | Path) -> Path:
    row_list = list(rows)

    if not row_list:
        df = pd.DataFrame()
        return write_df_to_csv(df, path)

    columns: list[str] = []
    seen: set[str] = set()

    for row in row_list:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                columns.append(key)

    df = pd.DataFrame(row_list, columns=columns)
    return write_df_to_csv(df, path)


__all__ = [
    "ensure_parent_dir",
    "write_df_to_csv",
    "write_rows_to_csv",
]