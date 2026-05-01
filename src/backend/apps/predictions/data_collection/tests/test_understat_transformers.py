import importlib
import inspect

import pandas as pd


def _load_transformer_module():
    return importlib.import_module("data_collection.transformers.understat.matches")


def _resolve_transformer():
    module = _load_transformer_module()
    for name in (
        "transform_understat_matches",
        "transform_matches",
        "transform",
        "run",
    ):
        func = getattr(module, name, None)
        if callable(func):
            return func
    raise AssertionError("No callable Understat match transformer found")


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


def test_understat_match_transformer_returns_canonical_core_fields():
    raw_df = pd.DataFrame(
        [
            {
                "id": 1001,
                "match_id": 1001,
                "source_match_id": 1001,
                "datetime": "2024-08-16 20:00:00",
                "date": "2024-08-16",
                "league": "EPL",
                "season": "2024",
                "h_title": "Arsenal",
                "a_title": "Chelsea",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "h": {"title": "Arsenal"},
                "a": {"title": "Chelsea"},
                "goals": {"h": 2, "a": 1},
                "goals__h": 2,
                "goals__a": 1,
                "home_goals": 2,
                "away_goals": 1,
                "xG": {"h": 1.9, "a": 1.1},
                "xG__h": 1.9,
                "xG__a": 1.1,
                "forecast": {"w": 0.5, "d": 0.3, "l": 0.2},
                "isResult": True,
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
            "source": "understat",
            "dataset": "matches",
        },
    )
    canonical_df = _coerce_dataframe(result)

    assert not canonical_df.empty
    assert "source" in canonical_df.columns
    assert "source_match_id" in canonical_df.columns
    assert canonical_df.iloc[0]["source"] == "understat"
    assert pd.notna(canonical_df.iloc[0]["source_match_id"])
    assert "home_team" in canonical_df.columns
    assert "away_team" in canonical_df.columns