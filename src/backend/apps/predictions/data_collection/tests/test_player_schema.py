import importlib
import inspect

import pandas as pd


def _load_schema_module():
    return importlib.import_module("data_collection.schemas.player_schema")


def _load_validator_module():
    return importlib.import_module("data_collection.validators.players")


def _resolve_validator():
    module = _load_validator_module()
    for name in ("validate_players", "validate_dataset", "validate", "run"):
        func = getattr(module, name, None)
        if callable(func):
            return func
    raise AssertionError("No callable player validator found in data_collection.validators.players")


def _call_with_supported_kwargs(func, kwargs):
    signature = inspect.signature(func)
    accepted = set(signature.parameters.keys())
    return func(**{key: value for key, value in kwargs.items() if key in accepted})


def _normalise_validation_result(result):
    if isinstance(result, tuple) and len(result) == 4:
        cleaned_df, errors, warnings, summary = result
        return {
            "cleaned_df": cleaned_df,
            "errors": list(errors or []),
            "warnings": list(warnings or []),
            "summary": dict(summary or {}),
        }

    if isinstance(result, dict):
        return {
            "cleaned_df": result.get("cleaned_df"),
            "errors": list(result.get("errors", []) or []),
            "warnings": list(result.get("warnings", []) or []),
            "summary": dict(result.get("summary", {}) or {}),
        }

    raise AssertionError(f"Unexpected validator result type: {type(result).__name__}")


def _get_schema_columns():
    module = _load_schema_module()
    required = tuple(getattr(module, "REQUIRED_COLUMNS", ()))
    optional = tuple(getattr(module, "OPTIONAL_COLUMNS", ()))
    assert required, "REQUIRED_COLUMNS is missing or empty in player schema"
    return set(required), set(optional)


def _run_validator(df):
    validator = _resolve_validator()
    result = _call_with_supported_kwargs(
        validator,
        {
            "df": df,
            "dataframe": df,
            "dataset": "players",
            "source": "understat",
            "league": "EPL",
            "season": "2024",
        },
    )
    return _normalise_validation_result(result)


def test_player_schema_required_columns_include_core_identity_fields():
    required, _ = _get_schema_columns()
    expected = {
        "source",
        "source_player_id",
        "season",
        "league",
        "name",
        "team",
    }
    assert expected.issubset(required)


def test_player_schema_allowed_columns_include_expected_known_fields():
    required, optional = _get_schema_columns()
    allowed = required | optional
    expected_known_fields = {
        "minutes",
        "games",
        "rating",
        "tackles_won",
        "interceptions",
    }
    assert expected_known_fields.issubset(allowed)


def test_player_validator_catches_missing_required_fields():
    df = pd.DataFrame(
        [
            {
                "source": "understat",
                "season": "2024",
                "league": "EPL",
                "name": "Declan Rice",
                "team": "Arsenal",
            }
        ]
    )

    result = _run_validator(df)
    combined_issues = " | ".join(
        [str(item) for item in result["errors"] + result["warnings"]]
    ).lower()

    assert result["errors"], "Expected validator to flag missing required player fields"
    assert "source_player_id" in combined_issues or "required" in combined_issues


def test_player_validator_catches_duplicate_source_ids():
    df = pd.DataFrame(
        [
            {
                "source": "understat",
                "source_player_id": "501",
                "season": "2024",
                "league": "EPL",
                "name": "Declan Rice",
                "team": "Arsenal",
                "minutes": 900,
                "games": 10,
            },
            {
                "source": "understat",
                "source_player_id": "501",
                "season": "2024",
                "league": "EPL",
                "name": "Declan Rice",
                "team": "Arsenal",
                "minutes": 900,
                "games": 10,
            },
        ]
    )

    result = _run_validator(df)
    combined_issues = " | ".join(
        [str(item) for item in result["errors"] + result["warnings"]]
    ).lower()

    assert result["errors"] or result["warnings"], "Expected duplicate player IDs to be caught"
    assert "duplicate" in combined_issues or "source_player_id" in combined_issues