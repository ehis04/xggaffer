import importlib
import inspect

import pandas as pd


def _load_reconciliation_module():
    return importlib.import_module("data_collection.reconcilers.matches")


def _resolve_callable(module, names, required=True):
    for name in names:
        func = getattr(module, name, None)
        if callable(func):
            return func
    if required:
        raise AssertionError(f"Could not resolve any callable from: {names}")
    return None


def _call_with_supported_kwargs(func, kwargs):
    signature = inspect.signature(func)
    accepted = set(signature.parameters.keys())
    return func(**{key: value for key, value in kwargs.items() if key in accepted})


def _choose_alias_pair():
    try:
        mappings_module = importlib.import_module("data_collection.config.team_name_mappings")
    except ImportError:
        return (" Manchester United ", "Manchester United")

    candidate_dicts = []
    for attr_name in dir(mappings_module):
        if attr_name.startswith("_"):
            continue
        value = getattr(mappings_module, attr_name)
        if isinstance(value, dict) and value:
            candidate_dicts.append(value)

    for mapping in candidate_dicts:
        first_alias = next(iter(mapping.keys()))
        canonical = mapping[first_alias]
        if isinstance(first_alias, str) and isinstance(canonical, str):
            return (first_alias, canonical)

    return (" Manchester United ", "Manchester United")


def _extract_matched_count(result):
    if isinstance(result, tuple):
        if len(result) == 4:
            matched_df = result[0]
            return len(matched_df)
        raise AssertionError("Unexpected tuple reconciliation shape")

    if isinstance(result, dict):
        if "matched_df" in result and isinstance(result["matched_df"], pd.DataFrame):
            return len(result["matched_df"])
        if "matched" in result and isinstance(result["matched"], pd.DataFrame):
            return len(result["matched"])
        if "summary" in result and isinstance(result["summary"], dict):
            summary = result["summary"]
            for key in ("matched_count", "matched_rows", "matched"):
                if key in summary:
                    return int(summary[key])

    if isinstance(result, pd.DataFrame):
        return len(result)

    raise AssertionError(f"Unexpected reconciliation result type: {type(result).__name__}")


def _build_match_rows(home_understat, home_sofascore, date_understat, date_sofascore):
    understat_df = pd.DataFrame(
        [
            {
                "source": "understat",
                "source_match_id": "u1",
                "league": "EPL",
                "season": "2024",
                "date": date_understat,
                "home_team": home_understat,
                "away_team": "Chelsea",
                "home_goals": 2,
                "away_goals": 1,
                "match_status": "final",
            }
        ]
    )
    sofascore_df = pd.DataFrame(
        [
            {
                "source": "sofascore",
                "source_match_id": "s1",
                "league": "EPL",
                "season": "2024",
                "date": date_sofascore,
                "home_team": home_sofascore,
                "away_team": "Chelsea",
                "home_goals": 2,
                "away_goals": 1,
                "match_status": "final",
            }
        ]
    )
    return understat_df, sofascore_df


def test_team_name_mapping_produces_expected_canonical_match_key():
    module = _load_reconciliation_module()
    alias_name, canonical_name = _choose_alias_pair()

    normalise_team = _resolve_callable(
        module,
        (
            "normalise_team_name",
            "normalize_team_name",
            "canonicalise_team_name",
            "canonicalize_team_name",
        ),
        required=False,
    )
    build_key = _resolve_callable(
        module,
        (
            "build_canonical_match_key",
            "make_canonical_match_key",
            "create_match_key",
            "build_match_key",
        ),
        required=False,
    )

    if normalise_team is not None:
        alias_normalised = _call_with_supported_kwargs(normalise_team, {"value": alias_name, "team_name": alias_name, "name": alias_name})
        canonical_normalised = _call_with_supported_kwargs(normalise_team, {"value": canonical_name, "team_name": canonical_name, "name": canonical_name})
        assert str(alias_normalised) == str(canonical_normalised)
        return

    if build_key is not None:
        row_a = {
            "league": "EPL",
            "season": "2024",
            "date": "2024-08-16",
            "home_team": alias_name,
            "away_team": "Chelsea",
        }
        row_b = {
            "league": "EPL",
            "season": "2024",
            "date": "2024-08-16",
            "home_team": canonical_name,
            "away_team": "Chelsea",
        }
        key_a = _call_with_supported_kwargs(build_key, {"row": row_a, "record": row_a, "match_row": row_a})
        key_b = _call_with_supported_kwargs(build_key, {"row": row_b, "record": row_b, "match_row": row_b})
        assert str(key_a) == str(key_b)
        return

    reconcile = _resolve_callable(
        module,
        (
            "reconcile_matches",
            "reconcile_match_datasets",
            "reconcile_match_files",
            "reconcile_understat_and_sofascore_matches",
        ),
    )
    understat_df, sofascore_df = _build_match_rows(
        home_understat=canonical_name,
        home_sofascore=alias_name,
        date_understat="2024-08-16",
        date_sofascore="2024-08-16",
    )
    result = _call_with_supported_kwargs(
        reconcile,
        {
            "understat_df": understat_df,
            "sofascore_df": sofascore_df,
            "source_a_df": understat_df,
            "source_b_df": sofascore_df,
            "left_df": understat_df,
            "right_df": sofascore_df,
            "league": "EPL",
            "season": "2024",
        },
    )
    assert _extract_matched_count(result) == 1


def test_date_normalization_works_for_equivalent_dates():
    module = _load_reconciliation_module()

    normalise_date = _resolve_callable(
        module,
        (
            "normalise_date",
            "normalize_date",
            "coerce_date",
            "normalise_match_date",
            "normalize_match_date",
        ),
        required=False,
    )

    if normalise_date is not None:
        value_a = _call_with_supported_kwargs(normalise_date, {"value": "2024-08-16", "date_value": "2024-08-16"})
        value_b = _call_with_supported_kwargs(normalise_date, {"value": "2024/08/16", "date_value": "2024/08/16"})
        assert str(value_a) == str(value_b)
        return

    reconcile = _resolve_callable(
        module,
        (
            "reconcile_matches",
            "reconcile_match_datasets",
            "reconcile_match_files",
            "reconcile_understat_and_sofascore_matches",
        ),
    )
    understat_df, sofascore_df = _build_match_rows(
        home_understat="Arsenal",
        home_sofascore="Arsenal",
        date_understat="2024-08-16",
        date_sofascore="2024/08/16",
    )
    result = _call_with_supported_kwargs(
        reconcile,
        {
            "understat_df": understat_df,
            "sofascore_df": sofascore_df,
            "source_a_df": understat_df,
            "source_b_df": sofascore_df,
            "left_df": understat_df,
            "right_df": sofascore_df,
            "league": "EPL",
            "season": "2024",
        },
    )
    assert _extract_matched_count(result) == 1


def test_known_matching_rows_reconcile_correctly():
    module = _load_reconciliation_module()
    reconcile = _resolve_callable(
        module,
        (
            "reconcile_matches",
            "reconcile_match_datasets",
            "reconcile_match_files",
            "reconcile_understat_and_sofascore_matches",
        ),
    )

    understat_df = pd.DataFrame(
        [
            {
                "source": "understat",
                "source_match_id": "u1",
                "league": "EPL",
                "season": "2024",
                "date": "2024-08-16",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "home_goals": 2,
                "away_goals": 1,
                "match_status": "final",
            }
        ]
    )
    sofascore_df = pd.DataFrame(
        [
            {
                "source": "sofascore",
                "source_match_id": "s1",
                "league": "EPL",
                "season": "2024",
                "date": "2024-08-16",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "home_goals": 2,
                "away_goals": 1,
                "match_status": "final",
            }
        ]
    )

    result = _call_with_supported_kwargs(
        reconcile,
        {
            "understat_df": understat_df,
            "sofascore_df": sofascore_df,
            "source_a_df": understat_df,
            "source_b_df": sofascore_df,
            "left_df": understat_df,
            "right_df": sofascore_df,
            "league": "EPL",
            "season": "2024",
        },
    )

    assert _extract_matched_count(result) == 1