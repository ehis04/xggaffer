from __future__ import annotations

from unittest.mock import patch

import pandas as pd
from django.test import SimpleTestCase, override_settings

from apps.livefootball.services.simulation import (
    DEFAULT_SIMULATION_COUNT,
    _build_context,
    _prepare_simulation_data,
    simulate_league_scenario,
    simulate_league_season,
)


TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}


def _dynamic_lambdas(prepared):
    count = len(prepared.remaining_fixtures)
    return ([1.4] * count, [1.1] * count)


def _sample_matches() -> pd.DataFrame:
    rows = [
        {
            "match_id": 1,
            "date": "2023-08-10",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "home_goals": 2,
            "away_goals": 1,
            "home_xg": 1.8,
            "away_xg": 0.9,
            "home_xa": 1.2,
            "away_xa": 0.7,
            "home_shots": 15,
            "away_shots": 8,
            "home_key_passes": 11,
            "away_key_passes": 6,
            "home_xpts": 2.3,
            "away_xpts": 0.5,
            "league": "EPL",
            "season": "2023",
        },
        {
            "match_id": 2,
            "date": "2023-08-11",
            "home_team": "Liverpool",
            "away_team": "Manchester City",
            "home_goals": 1,
            "away_goals": 1,
            "home_xg": 1.1,
            "away_xg": 1.4,
            "home_xa": 0.8,
            "away_xa": 1.0,
            "home_shots": 10,
            "away_shots": 12,
            "home_key_passes": 7,
            "away_key_passes": 9,
            "home_xpts": 1.1,
            "away_xpts": 1.5,
            "league": "EPL",
            "season": "2023",
        },
        {
            "match_id": 3,
            "date": "2024-08-10",
            "home_team": "Arsenal",
            "away_team": "Liverpool",
            "home_goals": 2,
            "away_goals": 0,
            "home_xg": 1.9,
            "away_xg": 0.8,
            "home_xa": 1.1,
            "away_xa": 0.5,
            "home_shots": 16,
            "away_shots": 7,
            "home_key_passes": 10,
            "away_key_passes": 5,
            "home_xpts": 2.4,
            "away_xpts": 0.4,
            "league": "EPL",
            "season": "2024",
        },
        {
            "match_id": 4,
            "date": "2024-08-11",
            "home_team": "Chelsea",
            "away_team": "Manchester City",
            "home_goals": 0,
            "away_goals": 3,
            "home_xg": 0.7,
            "away_xg": 2.0,
            "home_xa": 0.4,
            "away_xa": 1.3,
            "home_shots": 6,
            "away_shots": 18,
            "home_key_passes": 4,
            "away_key_passes": 13,
            "home_xpts": 0.3,
            "away_xpts": 2.6,
            "league": "EPL",
            "season": "2024",
        },
    ]
    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


def _sample_matches_with_explicit_remaining() -> pd.DataFrame:
    rows = [
        {
            "match_id": 1,
            "date": "2023-08-10",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "home_goals": 2,
            "away_goals": 1,
            "home_xg": 1.8,
            "away_xg": 0.9,
            "home_xa": 1.2,
            "away_xa": 0.7,
            "home_shots": 15,
            "away_shots": 8,
            "home_key_passes": 11,
            "away_key_passes": 6,
            "home_xpts": 2.3,
            "away_xpts": 0.5,
            "league": "EPL",
            "season": "2023",
        },
        {
            "match_id": 2,
            "date": "2024-08-10",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "home_goals": 1,
            "away_goals": 0,
            "home_xg": 1.2,
            "away_xg": 0.8,
            "home_xa": 0.9,
            "away_xa": 0.5,
            "home_shots": 12,
            "away_shots": 7,
            "home_key_passes": 8,
            "away_key_passes": 4,
            "home_xpts": 2.0,
            "away_xpts": 0.7,
            "league": "EPL",
            "season": "2024",
        },
        {
            "match_id": 3,
            "date": "2024-08-20",
            "home_team": "Chelsea",
            "away_team": "Arsenal",
            "home_goals": None,
            "away_goals": None,
            "home_xg": None,
            "away_xg": None,
            "home_xa": None,
            "away_xa": None,
            "home_shots": None,
            "away_shots": None,
            "home_key_passes": None,
            "away_key_passes": None,
            "home_xpts": None,
            "away_xpts": None,
            "league": "EPL",
            "season": "2024",
        },
    ]
    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


@override_settings(CACHES=TEST_CACHES)
class SimulationServiceTests(SimpleTestCase):
    @patch(
        "apps.livefootball.services.simulation._predict_score_lambdas",
        side_effect=_dynamic_lambdas,
    )
    @patch(
        "apps.livefootball.services.simulation._build_fixture_outcome_probabilities",
        return_value=[
            {
                "home_team": "Arsenal",
                "away_team": "Liverpool",
                "prediction": "Home",
                "probabilities": {"home": 0.5, "draw": 0.25, "away": 0.25},
            },
            {
                "home_team": "Chelsea",
                "away_team": "Manchester City",
                "prediction": "Away",
                "probabilities": {"home": 0.2, "draw": 0.2, "away": 0.6},
            },
        ],
    )
    @patch(
        "apps.livefootball.services.simulation._resolve_engine_versions",
        return_value={
            "elo": "v1",
            "outcome": "v2",
            "score": "score-test",
            "simulation": "v1",
        },
    )
    @patch(
        "apps.livefootball.services.simulation._load_simulation_match_history",
        return_value=_sample_matches(),
    )
    def test_returns_expected_top_level_shape(
        self,
        _mock_loader,
        _mock_versions,
        _mock_outcomes,
        _mock_lambdas,
    ) -> None:
        result = simulate_league_season("EPL", "2024", "pre_season", simulation_count=100)

        self.assertEqual(result["league"], "EPL")
        self.assertEqual(result["season"], "2024")
        self.assertEqual(result["mode"], "pre_season")
        self.assertEqual(result["simulation_count"], 100)
        self.assertEqual(result["based_on_matchweek"], 0)
        self.assertEqual(result["data_cutoff_date"], "2024-08-10")

        self.assertIn("expected_table", result)
        self.assertEqual(len(result["expected_table"]), 4)

        metadata = result["metadata"]
        self.assertEqual(metadata["remaining_fixtures"], 12)
        self.assertEqual(metadata["total_fixtures_simulated"], 1200)
        self.assertEqual(metadata["remaining_fixtures_source"], "synthetic_round_robin_full_season")
        self.assertIn("engine_versions", metadata)

    @patch(
        "apps.livefootball.services.simulation._predict_score_lambdas",
        side_effect=_dynamic_lambdas,
    )
    @patch(
        "apps.livefootball.services.simulation._build_fixture_outcome_probabilities",
        return_value=[],
    )
    @patch(
        "apps.livefootball.services.simulation._resolve_engine_versions",
        return_value={
            "elo": "v1",
            "outcome": "v2",
            "score": "score-test",
            "simulation": "v1",
        },
    )
    @patch(
        "apps.livefootball.services.simulation._load_simulation_match_history",
        return_value=_sample_matches(),
    )
    def test_uses_default_simulation_count(
        self,
        _mock_loader,
        _mock_versions,
        _mock_outcomes,
        _mock_lambdas,
    ) -> None:
        result = simulate_league_season("EPL", "2024", "current_expected")
        self.assertEqual(result["simulation_count"], DEFAULT_SIMULATION_COUNT)

    def test_rejects_invalid_mode(self) -> None:
        with self.assertRaises(ValueError):
            simulate_league_season("EPL", "2024", "not_a_real_mode")

    def test_rejects_blank_league(self) -> None:
        with self.assertRaises(ValueError):
            simulate_league_season("", "2024", "pre_season")

    def test_rejects_blank_season(self) -> None:
        with self.assertRaises(ValueError):
            simulate_league_season("EPL", "", "pre_season")

    def test_rejects_non_positive_simulation_count(self) -> None:
        with self.assertRaises(ValueError):
            simulate_league_season("EPL", "2024", "pre_season", simulation_count=0)

    @patch(
        "apps.livefootball.services.simulation._load_simulation_match_history",
        return_value=_sample_matches(),
    )
    def test_pre_season_mode_does_not_use_target_season_history(self, _mock_loader) -> None:
        context = _build_context("EPL", "2024", "pre_season", 100)
        prepared = _prepare_simulation_data(context)

        historical_seasons = sorted(prepared.historical_matches_df["season"].astype(str).unique().tolist())
        self.assertEqual(historical_seasons, ["2023"])
        self.assertEqual(len(prepared.actual_results), 0)
        self.assertEqual(len(prepared.remaining_fixtures), 12)
        self.assertEqual(prepared.remaining_fixtures_source, "synthetic_round_robin_full_season")
        self.assertEqual(prepared.data_cutoff_date, "2024-08-10")

    @patch(
        "apps.livefootball.services.simulation._load_simulation_match_history",
        return_value=_sample_matches(),
    )
    def test_pre_season_full_season_synthesizes_round_robin_for_partial_schedule(self, _mock_loader) -> None:
        context = _build_context("EPL", "2024", "pre_season", 100, projection_window="full_season")
        prepared = _prepare_simulation_data(context)

        expected_fixture_count = 4 * 3
        self.assertEqual(len(prepared.remaining_fixtures), expected_fixture_count)
        self.assertEqual(prepared.remaining_fixtures_source, "synthetic_round_robin_full_season")

    @patch(
        "apps.livefootball.services.simulation._load_simulation_match_history",
        return_value=_sample_matches(),
    )
    def test_current_expected_mode_uses_available_target_season_matches(self, _mock_loader) -> None:
        context = _build_context("EPL", "2024", "current_expected", 100)
        prepared = _prepare_simulation_data(context)

        self.assertEqual(len(prepared.actual_results), 2)
        self.assertEqual(len(prepared.remaining_fixtures), 10)
        self.assertEqual(prepared.remaining_fixtures_source, "synthetic_round_robin")
        self.assertEqual(prepared.data_cutoff_date, "2024-08-12")

    @patch(
        "apps.livefootball.services.simulation._load_simulation_match_history",
        return_value=_sample_matches_with_explicit_remaining(),
    )
    def test_current_expected_mode_uses_explicit_remaining_fixtures(self, _mock_loader) -> None:
        context = _build_context("EPL", "2024", "current_expected", 100)
        prepared = _prepare_simulation_data(context)

        self.assertEqual(len(prepared.actual_results), 1)
        self.assertEqual(len(prepared.remaining_fixtures), 1)
        self.assertEqual(prepared.remaining_fixtures_source, "historical_schedule")
        self.assertEqual(
            prepared.remaining_fixtures[0],
            {"home_team": "Chelsea", "away_team": "Arsenal"},
        )

    @patch(
        "apps.livefootball.services.simulation._load_simulation_match_history",
        return_value=_sample_matches(),
    )
    def test_strength_snapshot_contains_all_target_teams(self, _mock_loader) -> None:
        context = _build_context("EPL", "2024", "pre_season", 100)
        prepared = _prepare_simulation_data(context)

        self.assertEqual(
            sorted(prepared.strength_snapshot.keys()),
            ["Arsenal", "Chelsea", "Liverpool", "Manchester City"],
        )
        for team_payload in prepared.strength_snapshot.values():
            self.assertIn("elo", team_payload)
            self.assertIn("rolling_features", team_payload)

    @patch(
        "apps.livefootball.services.simulation._predict_score_lambdas",
        side_effect=_dynamic_lambdas,
    )
    @patch(
        "apps.livefootball.services.simulation._build_fixture_outcome_probabilities",
        return_value=[],
    )
    @patch(
        "apps.livefootball.services.simulation._resolve_engine_versions",
        return_value={
            "elo": "v1",
            "outcome": "v2",
            "score": "score-test",
            "simulation": "v1",
        },
    )
    @patch(
        "apps.livefootball.services.simulation._load_simulation_match_history",
        return_value=_sample_matches(),
    )
    def test_pre_season_expected_table_contains_all_teams_and_probability_shape(
        self,
        _mock_loader,
        _mock_versions,
        _mock_outcomes,
        _mock_lambdas,
    ) -> None:
        result = simulate_league_season("EPL", "2024", "pre_season", simulation_count=100)
        expected_table = result["expected_table"]

        self.assertEqual(len(expected_table), 4)

        seen_teams = sorted(item["team"] for item in expected_table)
        self.assertEqual(seen_teams, ["Arsenal", "Chelsea", "Liverpool", "Manchester City"])

        for row in expected_table:
            self.assertIn("predicted_points", row)
            self.assertIn("predicted_position", row)
            self.assertIn("position_probabilities", row)
            self.assertIn("title_probability", row)
            self.assertIn("top_4_probability", row)
            self.assertIn("relegation_probability", row)
            self.assertIn("simulated_wins", row)
            self.assertIn("simulated_draws", row)
            self.assertIn("simulated_losses", row)
            self.assertIn("simulated_goals_for", row)
            self.assertIn("simulated_goals_against", row)

            total_probability = sum(row["position_probabilities"].values())
            self.assertAlmostEqual(total_probability, 1.0, places=3)

    @patch(
        "apps.livefootball.services.simulation._build_fixture_outcome_probabilities",
        return_value=[],
    )
    @patch(
        "apps.livefootball.services.simulation._resolve_engine_versions",
        return_value={
            "elo": "v1",
            "outcome": "v2",
            "score": "score-test",
            "simulation": "v1",
        },
    )
    @patch(
        "apps.livefootball.services.simulation._load_simulation_match_history",
        return_value=_sample_matches(),
    )
    def test_completed_season_returns_full_table_without_remaining_fixtures(
        self,
        _mock_loader,
        _mock_versions,
        _mock_outcomes,
    ) -> None:
        result = simulate_league_season("EPL", "2024", "current_expected", simulation_count=20)

        self.assertEqual(result["metadata"]["remaining_fixtures"], 10)
        self.assertEqual(result["metadata"]["total_fixtures_simulated"], 200)
        self.assertEqual(len(result["expected_table"]), 4)

        for row in result["expected_table"]:
            self.assertAlmostEqual(sum(row["position_probabilities"].values()), 1.0, places=3)

    def test_as_of_matchweek_requires_matchweek(self) -> None:
        with self.assertRaises(ValueError):
            simulate_league_season("EPL", "2023", "as_of_matchweek")

    @patch(
        "apps.livefootball.services.simulation._load_simulation_match_history",
        return_value=_sample_matches(),
    )
    def test_as_of_matchweek_latest_available_season_is_supported(self, _mock_loader) -> None:
        result = simulate_league_season("EPL", "2024", "as_of_matchweek", matchweek=1)

        self.assertEqual(result["mode"], "as_of_matchweek")
        self.assertEqual(result["based_on_matchweek"], 1)

    @patch(
        "apps.livefootball.services.simulation._predict_score_lambdas",
        return_value=([], []),
    )
    @patch(
        "apps.livefootball.services.simulation._build_fixture_outcome_probabilities",
        return_value=[],
    )
    @patch(
        "apps.livefootball.services.simulation._resolve_engine_versions",
        return_value={
            "elo": "v1",
            "outcome": "v2",
            "score": "score-test",
            "simulation": "v1",
        },
    )
    @patch(
        "apps.livefootball.services.simulation._load_simulation_match_history",
        return_value=_sample_matches(),
    )
    def test_as_of_matchweek_historical_season_returns_cutoff_metadata(
        self,
        _mock_loader,
        _mock_versions,
        _mock_outcomes,
        _mock_lambdas,
    ) -> None:
        result = simulate_league_season(
            "EPL",
            "2023",
            "as_of_matchweek",
            simulation_count=20,
            matchweek=1,
        )

        self.assertEqual(result["mode"], "as_of_matchweek")
        self.assertEqual(result["based_on_matchweek"], 1)
        self.assertEqual(result["data_cutoff_date"], "2023-08-11")
        self.assertEqual(result["metadata"]["total_matchweeks"], 1)

    @patch(
        "apps.livefootball.services.simulation._predict_score_lambdas",
        side_effect=_dynamic_lambdas,
    )
    @patch(
        "apps.livefootball.services.simulation._build_fixture_outcome_probabilities",
        return_value=[],
    )
    @patch(
        "apps.livefootball.services.simulation._resolve_engine_versions",
        return_value={
            "elo": "v1",
            "outcome": "v2",
            "score": "score-test",
            "simulation": "v1",
        },
    )
    @patch(
        "apps.livefootball.services.simulation._load_simulation_match_history",
        return_value=_sample_matches(),
    )
    def test_simulate_league_scenario_accepts_locked_results(
        self,
        _mock_loader,
        _mock_versions,
        _mock_outcomes,
        _mock_lambdas,
    ) -> None:
        result = simulate_league_scenario(
            "EPL",
            "2024",
            "pre_season",
            simulation_count=20,
            locked_results=[
                {
                    "fixture_key": "Arsenal__Liverpool",
                    "home_goals": 2,
                    "away_goals": 1,
                }
            ],
        )

        self.assertEqual(result["mode"], "pre_season")
        self.assertEqual(len(result["remaining_fixtures"]), 12)
        self.assertEqual(len(result["locked_results"]), 1)
        self.assertEqual(result["locked_results"][0]["fixture_key"], "Arsenal__Liverpool")
        self.assertEqual(result["metadata"]["remaining_fixtures_before_lock"], 12)
        self.assertEqual(result["metadata"]["remaining_fixtures_after_lock"], 11)

    @patch(
        "apps.livefootball.services.simulation._load_simulation_match_history",
        return_value=_sample_matches(),
    )
    def test_simulate_league_scenario_rejects_unknown_fixture_key(self, _mock_loader) -> None:
        with self.assertRaises(ValueError):
            simulate_league_scenario(
                "EPL",
                "2024",
                "pre_season",
                locked_results=[
                    {
                        "fixture_key": "Unknown__Fixture",
                        "home_goals": 1,
                        "away_goals": 0,
                    }
                ],
            )
