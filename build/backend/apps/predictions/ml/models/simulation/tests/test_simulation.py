from __future__ import annotations

import numpy as np
import pytest

from apps.predictions.ml.models.simulation.config import POINTS_DRAW, POINTS_WIN
from apps.predictions.ml.models.simulation.simulate import (
    aggregate_results,
    compute_league_table,
    simulate_season,
    simulate_with_locked_results,
)


class TestComputeLeagueTable:

    def test_basic_four_teams(self):
        matches = [
            {"home_team": "A", "away_team": "B", "home_goals": 2, "away_goals": 1},
            {"home_team": "C", "away_team": "D", "home_goals": 0, "away_goals": 0},
            {"home_team": "A", "away_team": "C", "home_goals": 1, "away_goals": 1},
            {"home_team": "B", "away_team": "D", "home_goals": 3, "away_goals": 0},
            {"home_team": "A", "away_team": "D", "home_goals": 1, "away_goals": 0},
            {"home_team": "B", "away_team": "C", "home_goals": 0, "away_goals": 2},
        ]
        table = compute_league_table(matches)

        assert table.iloc[0]["team"] == "A"
        assert table.iloc[0]["points"] == 7
        assert table.iloc[1]["team"] == "C"
        assert table.iloc[1]["points"] == 5
        assert table.iloc[2]["team"] == "B"
        assert table.iloc[2]["points"] == 3
        assert table.iloc[3]["team"] == "D"
        assert table.iloc[3]["points"] == 1

    def test_tiebreaker_goal_difference(self):
        matches = [
            {"home_team": "A", "away_team": "B", "home_goals": 3, "away_goals": 0},
            {"home_team": "B", "away_team": "A", "home_goals": 2, "away_goals": 0},
        ]
        table = compute_league_table(matches)

        assert table.iloc[0]["team"] == "A"
        assert table.iloc[0]["goal_difference"] == 1
        assert table.iloc[1]["team"] == "B"
        assert table.iloc[1]["goal_difference"] == -1

    def test_tiebreaker_goals_scored(self):
        matches = [
            {"home_team": "A", "away_team": "B", "home_goals": 3, "away_goals": 2},
            {"home_team": "B", "away_team": "A", "home_goals": 2, "away_goals": 1},
        ]
        table = compute_league_table(matches)

        assert table.iloc[0]["points"] == table.iloc[1]["points"]
        assert table.iloc[0]["goal_difference"] == table.iloc[1]["goal_difference"]
        assert table.iloc[0]["team"] == "A"
        assert table.iloc[0]["goals_for"] == 4

    def test_all_draws(self):
        matches = [
            {"home_team": "A", "away_team": "B", "home_goals": 1, "away_goals": 1},
            {"home_team": "A", "away_team": "C", "home_goals": 0, "away_goals": 0},
            {"home_team": "B", "away_team": "C", "home_goals": 2, "away_goals": 2},
        ]
        table = compute_league_table(matches)

        assert all(table["points"] == 2)
        assert all(table["goal_difference"] == 0)

    def test_position_column_sequential(self):
        matches = [
            {"home_team": "X", "away_team": "Y", "home_goals": 1, "away_goals": 0},
            {"home_team": "Y", "away_team": "Z", "home_goals": 1, "away_goals": 0},
            {"home_team": "Z", "away_team": "X", "home_goals": 1, "away_goals": 0},
        ]
        table = compute_league_table(matches)
        assert table["position"].tolist() == [1, 2, 3]


class TestSimulateSeason:

    @pytest.fixture()
    def four_team_setup(self):
        actual = [
            {"home_team": "A", "away_team": "B", "home_goals": 1, "away_goals": 0},
        ]
        remaining = [
            {"home_team": "C", "away_team": "D"},
            {"home_team": "A", "away_team": "C"},
            {"home_team": "B", "away_team": "D"},
        ]
        lam_h = np.array([1.5, 1.8, 1.2])
        lam_a = np.array([1.2, 1.0, 1.4])
        return actual, remaining, lam_h, lam_a

    def test_all_teams_present(self, four_team_setup):
        actual, remaining, lam_h, lam_a = four_team_setup
        result = simulate_season(actual, remaining, lam_h, lam_a, n_simulations=100)
        assert result["team_list"] == ["A", "B", "C", "D"]

    def test_position_counts_row_sums(self, four_team_setup):
        actual, remaining, lam_h, lam_a = four_team_setup
        n = 500
        result = simulate_season(actual, remaining, lam_h, lam_a, n_simulations=n)
        row_sums = result["position_counts"].sum(axis=1)
        assert all(row_sums == n)

    def test_position_counts_col_sums(self, four_team_setup):
        actual, remaining, lam_h, lam_a = four_team_setup
        n = 500
        result = simulate_season(actual, remaining, lam_h, lam_a, n_simulations=n)
        col_sums = result["position_counts"].sum(axis=0)
        assert all(col_sums == n)

    def test_deterministic_with_same_seed(self, four_team_setup):
        actual, remaining, lam_h, lam_a = four_team_setup
        r1 = simulate_season(actual, remaining, lam_h, lam_a, n_simulations=100, seed=99)
        r2 = simulate_season(actual, remaining, lam_h, lam_a, n_simulations=100, seed=99)
        np.testing.assert_array_equal(r1["position_counts"], r2["position_counts"])
        np.testing.assert_array_equal(r1["points_per_sim"], r2["points_per_sim"])

    def test_different_seeds_differ(self, four_team_setup):
        actual, remaining, lam_h, lam_a = four_team_setup
        r1 = simulate_season(actual, remaining, lam_h, lam_a, n_simulations=500, seed=1)
        r2 = simulate_season(actual, remaining, lam_h, lam_a, n_simulations=500, seed=2)
        assert not np.array_equal(r1["position_counts"], r2["position_counts"])

    def test_no_remaining_fixtures(self):
        actual = [
            {"home_team": "A", "away_team": "B", "home_goals": 2, "away_goals": 0},
            {"home_team": "B", "away_team": "A", "home_goals": 1, "away_goals": 1},
        ]
        result = simulate_season(actual, [], np.array([]), np.array([]), n_simulations=100)

        assert all(result["position_counts"].sum(axis=1) == 100)
        a_idx = result["team_list"].index("A")
        assert result["position_counts"][a_idx, 0] == 100

    def test_points_within_valid_range(self, four_team_setup):
        actual, remaining, lam_h, lam_a = four_team_setup
        result = simulate_season(actual, remaining, lam_h, lam_a, n_simulations=200)
        total_matches = len(actual) + len(remaining)
        max_possible = total_matches * POINTS_WIN
        assert result["points_per_sim"].max() <= max_possible
        assert result["points_per_sim"].min() >= 0


class TestAggregateResults:

    def test_all_teams_present(self):
        actual = [{"home_team": "A", "away_team": "B", "home_goals": 1, "away_goals": 0}]
        remaining = [{"home_team": "A", "away_team": "B"}]
        sim = simulate_season(actual, remaining, np.array([1.5]), np.array([1.0]), n_simulations=100)
        agg = aggregate_results(sim)
        assert set(agg["team"]) == {"A", "B"}

    def test_probabilities_sum_to_one(self):
        actual = [
            {"home_team": "A", "away_team": "B", "home_goals": 1, "away_goals": 0},
            {"home_team": "C", "away_team": "D", "home_goals": 0, "away_goals": 2},
        ]
        remaining = [
            {"home_team": "A", "away_team": "C"},
            {"home_team": "B", "away_team": "D"},
        ]
        sim = simulate_season(actual, remaining, np.array([1.5, 1.2]), np.array([1.0, 1.3]), n_simulations=500)
        agg = aggregate_results(sim)

        for _, row in agg.iterrows():
            total = sum(row["position_probs"].values())
            assert abs(total - 1.0) < 1e-9

    def test_sorted_by_projected_points(self):
        actual = [{"home_team": "A", "away_team": "B", "home_goals": 5, "away_goals": 0}]
        remaining = [{"home_team": "B", "away_team": "A"}]
        sim = simulate_season(actual, remaining, np.array([0.5]), np.array([2.0]), n_simulations=200)
        agg = aggregate_results(sim)
        points = agg["projected_points_mean"].tolist()
        assert points == sorted(points, reverse=True)

    def test_projected_points_reasonable(self):
        actual = [{"home_team": "A", "away_team": "B", "home_goals": 1, "away_goals": 1}]
        remaining = [{"home_team": "B", "away_team": "A"}]
        sim = simulate_season(actual, remaining, np.array([1.5]), np.array([1.5]), n_simulations=500)
        agg = aggregate_results(sim)

        for _, row in agg.iterrows():
            assert 0 <= row["projected_points_mean"] <= 6
            assert 0 <= row["projected_points_5th"] <= row["projected_points_95th"]


class TestWhatIf:

    def test_locked_result_removed_from_remaining(self):
        actual = [{"home_team": "A", "away_team": "B", "home_goals": 1, "away_goals": 0}]
        remaining = [
            {"home_team": "A", "away_team": "C"},
            {"home_team": "B", "away_team": "C"},
        ]
        lam_h = np.array([1.5, 1.2])
        lam_a = np.array([1.0, 1.3])
        locked = [{"home_team": "A", "away_team": "C", "home_goals": 3, "away_goals": 0}]

        result = simulate_with_locked_results(
            actual, remaining, lam_h, lam_a, locked, n_simulations=100,
        )

        a_idx = result["team_list"].index("A")
        min_a_points = result["points_per_sim"][:, a_idx].min()
        assert min_a_points >= POINTS_WIN * 2

    def test_locked_boosts_probability(self):
        actual = [{"home_team": "A", "away_team": "B", "home_goals": 1, "away_goals": 1}]
        remaining = [
            {"home_team": "A", "away_team": "C"},
            {"home_team": "B", "away_team": "C"},
        ]
        lam_h = np.array([1.5, 1.5])
        lam_a = np.array([1.5, 1.5])

        base = simulate_season(actual, remaining, lam_h, lam_a, n_simulations=2000, seed=42)
        base_agg = aggregate_results(base)

        locked = [{"home_team": "A", "away_team": "C", "home_goals": 5, "away_goals": 0}]
        whatif = simulate_with_locked_results(
            actual, remaining, lam_h, lam_a, locked, n_simulations=2000, seed=42,
        )
        whatif_agg = aggregate_results(whatif)

        base_a = base_agg[base_agg["team"] == "A"]["p_title"].iloc[0]
        whatif_a = whatif_agg[whatif_agg["team"] == "A"]["p_title"].iloc[0]
        assert whatif_a > base_a