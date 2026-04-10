from __future__ import annotations

from pathlib import Path

import pandas as pd

try:
    import soccerdata as sd
except ImportError:
    sd = None


SOFASCORE_LEAGUE_MAP = {
    "EPL": "ENG-Premier League",
    "La_Liga": "ESP-La Liga",
    "Bundesliga": "GER-Bundesliga",
    "Serie_A": "ITA-Serie A",
    "Ligue_1": "FRA-Ligue 1",
    "RFPL": "RUS-Premier League",
}


def _resolve_sofascore_league(league: str) -> str:
    value = str(league).strip()
    return SOFASCORE_LEAGUE_MAP.get(value, value)


def _resolve_sofascore_season(season: str | int) -> str | int:
    value = str(season).strip()

    if value.isdigit() and len(value) == 4:
        return int(value)

    if "-" in value and value[:4].isdigit():
        return int(value[:4])

    if "/" in value and value[:4].isdigit():
        return int(value[:4])

    return value


def _materialize_index(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.index, pd.MultiIndex):
        return df.reset_index()

    if any(name is not None for name in df.index.names):
        return df.reset_index()

    return df.copy()


def get_sofascore_client(
    league: str,
    season: str | int,
    *,
    no_cache: bool = False,
    no_store: bool = False,
    data_dir: str | Path | None = None,
):
    if sd is None:
        raise ImportError(
            "soccerdata is not installed. Install it with `python3 -m pip install soccerdata`."
        )

    kwargs: dict[str, object] = {
        "leagues": [_resolve_sofascore_league(league)],
        "seasons": [_resolve_sofascore_season(season)],
        "no_cache": no_cache,
        "no_store": no_store,
    }

    if data_dir is not None:
        kwargs["data_dir"] = Path(data_dir)

    return sd.Sofascore(**kwargs)


def fetch_sofascore_teams(
    league: str,
    season: str | int,
    *,
    force_cache: bool = False,
    no_cache: bool = False,
    no_store: bool = False,
    data_dir: str | Path | None = None,
) -> pd.DataFrame:
    client = get_sofascore_client(
        league,
        season,
        no_cache=no_cache,
        no_store=no_store,
        data_dir=data_dir,
    )

    raw_df = client.read_league_table(force_cache=force_cache)

    if not isinstance(raw_df, pd.DataFrame):
        raise TypeError(
            f"Sofascore read_league_table() returned unsupported type: {type(raw_df)!r}"
        )

    return _materialize_index(raw_df)


__all__ = [
    "SOFASCORE_LEAGUE_MAP",
    "fetch_sofascore_teams",
    "get_sofascore_client",
]