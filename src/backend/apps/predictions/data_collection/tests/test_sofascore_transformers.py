import importlib
import inspect

import pandas as pd


def _load_transformer_module():
    return importlib.import_module("data_collection.transformers.sofascore.matches")


def _resolve_transformer():
    module = _load_transformer_module()
    for name in (
        "transform_sofascore_matches",
        "transform_matches",
        "transform",
        "run",
    ):
        func = getattr(module, name, None)
        if callable(func):
            return func
    raise AssertionError("No callable Sofascore match transformer found")


def _call_with_supported_kwargs(func, kwargs):
    signature = inspect.signature(func)
    accepted = set(signature.parameters.keys())
    return func(**{key: value for key, value in kwargs.items() if key in accepted})


def _coerce_dataframe(value):
    if isinstance(value, pd.DataFrame):
        return value
    if isinstance(value, list):
        return pd.DataFrame(value)
    if isinstance(value, dict):
        return pd.DataFrame([value])
    raise AssertionError(f"Unexpected transformer output type: {type(value).__name__}")


def test_sofascore_match_transformer_returns_canonical_core_fields():
    raw_df = pd.DataFrame(
        [
            {
                "id": 2001,
                "match_id": 2001,
                "source_match_id": 2001,
                "date": "2024-08-16",
                "startTimestamp": 1723838400,
                "league": "EPL",
                "season": "2024",
                "tournament": {"name": "Premier League"},
                "uniqueTournament": {"name": "Premier League"},
                "homeTeam": {"name": "Arsenal", "id": 1},
                "awayTeam": {"name": "Chelsea", "id": 2},
                "homeTeam.name": "Arsenal",
                "awayTeam.name": "Chelsea",
                "homeTeam.id": 1,
                "awayTeam.id": 2,
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "homeScore": {"current": 2},
                "awayScore": {"current": 1},
                "homeScore.current": 2,
                "awayScore.current": 1,
                "home_goals": 2,
                "away_goals": 1,
                "status": {"type": "finished", "description": "FT"},
                "status.type": "finished",
                "match_status": "final",
                "is_finished": True,
            }
        ]
    )

    transformer = _resolve_transformer()
    result = _call_with_supported_kwargs(
        transformer,
        {
            "raw_df": raw_df,
            "df": raw_df,
            "league": "EPL",
            "season": "2024",
            "source": "sofascore",
            "dataset": "matches",
        },
    )
    canonical_df = _coerce_dataframe(result)

    assert not canonical_df.empty
    assert "source" in canonical_df.columns
    assert "source_match_id" in canonical_df.columns
    assert canonical_df.iloc[0]["source"] == "sofascore"
    assert pd.notna(canonical_df.iloc[0]["source_match_id"])
    assert "home_team" in canonical_df.columns
    assert "away_team" in canonical_df.columns