from __future__ import annotations

from pathlib import Path

import pandas as pd

try:
    import soccerdata as sd
except ImportError:
    sd = None

from data_collection.extractors.whoscored.matches import (
    get_whoscored_client,
    _materialize_index,
)


def fetch_whoscored_teams(
    league: str,
    season: str | int,
    *,
    force_cache: bool = False,
    no_cache: bool = False,
    no_store: bool = False,
    data_dir: str | Path | None = None,
) -> pd.DataFrame:
    client = get_whoscored_client(
        league,
        season,
        no_cache=no_cache,
        no_store=no_store,
        data_dir=data_dir,
    )

    raw_df = client.read_schedule(force_cache=force_cache)

    if not isinstance(raw_df, pd.DataFrame):
        raise TypeError(
            f"WhoScored read_schedule() returned unsupported type: {type(raw_df)!r}"
        )

    return _materialize_index(raw_df)


__all__ = [
    "fetch_whoscored_teams",
]
