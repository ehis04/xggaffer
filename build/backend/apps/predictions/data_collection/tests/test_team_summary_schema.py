import importlib
import inspect

import pandas as pd


def _load_schema_module():
    return importlib.import_module("data_collection.schemas.team_summary_schema")


def _load_validator_module():
    return importlib.import_module("data_collection.validators.team_summaries")


def _resolve_validator():
    module = _load_validator_module()
    for name in ("validate_team_summaries", "validate_dataset", "validate", "run"):
        func = getattr(module, name, None)
        if callable(func):
            return func
    raise AssertionError(
        "No callable team summary validator found in data_collection.validators.team_summaries"
    )


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
    assert required, "REQUIRED_COLUMNS is missing or empty in team summary schema"
    return set(required), set(optional)


def _run_validator(df):
    validator = _resolve_validator()
    result = _call_with_supported_kwargs(
        validator,
        {
            "df": df,
            "dataframe": df,
            "dataset": "team_summaries",
            "source": "understat",
            "league": "EPL",
            "season": "2024",
        },
    )
    return _normalise_validation_result(result)


def test_team_summary_schema_required_columns_include_core_identity_fields():
    required, _ = _get_schema_columns()
    expected = {
        "source",
        "season",
        "league",
        "team",
    }
    assert expected.issubset(required)


def test_team_summary_schema_allowed_columns_include_expected_known_fields():
    required, optional = _get_schema_columns()
    allowed = required | optional
    expected_known_fields = {
        "xpts",
        "tackles",
        "interceptions",
    }
    assert expected_known_fields.issubset(allowed)


def test_team_summary_validator_catches_missing_required_fields():
    df = pd.DataFrame(
        [
            {
                "source": "understat",
                "season": "2024",
                "league": "EPL",
                "formation": "4-3-3",
            }
        ]
    )

    result = _run_validator(df)
    combined_issues = " | ".join(
        [str(item) for item in result["errors"] + result["warnings"]]
    ).lower()

    assert result["errors"], "Expected validator to flag missing required team summary fields"
    assert "team" in combined_issues or "required" in combined_issues