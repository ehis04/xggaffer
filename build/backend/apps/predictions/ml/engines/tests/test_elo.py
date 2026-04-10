import numpy as np
import pandas as pd
import pytest

from ml.engines.elo import (
    INITIAL_RATING,
    PROMOTED_TEAM_OFFSET,
    SEASON_MEAN_REVERSION_WEIGHT,
    actual_score,
    apply_season_reset,
    compute_elo_history,
    elo_to_probabilities,
    expected_score,
    get_elo_at_date,
    update_ratings,
)



def _make_matches(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df["season"] = df["season"].astype(str)
    return df


FOUR_MATCH_FIXTURE = _make_matches([
    {"match_id": 1, "date": "2020-08-15", "home_team": "A", "away_team": "B",
     "home_goals": 2, "away_goals": 0, "league": "EPL", "season": "2020"},
    {"match_id": 2, "date": "2020-09-01", "home_team": "B", "away_team": "A",
     "home_goals": 1, "away_goals": 1, "league": "EPL", "season": "2020"},
    {"match_id": 3, "date": "2021-08-15", "home_team": "A", "away_team": "C",
     "home_goals": 3, "away_goals": 1, "league": "EPL", "season": "2021"},
    {"match_id": 4, "date": "2021-09-01", "home_team": "B", "away_team": "C",
     "home_goals": 0, "away_goals": 1, "league": "EPL", "season": "2021"},
])

TEN_MATCH_FIXTURE = _make_matches([
    {"match_id": i, "date": f"2020-{8 + i // 4:02d}-{1 + (i % 4) * 7:02d}",
     "home_team": "A" if i % 2 == 0 else "B",
     "away_team": "B" if i % 2 == 0 else "A",
     "home_goals": (i % 3), "away_goals": ((i + 1) % 3),
     "league": "EPL", "season": "2020"}
    for i in range(1, 11)
])



class TestExpectedScore:

    def test_equal_teams_no_home_advantage(self):
        assert abs(expected_score(1500, 1500, 0) - 0.5) < 0.001

    def test_equal_teams_with_home_advantage(self):
        result = expected_score(1500, 1500, 100)
        assert result > 0.5
        assert abs(result - 0.64) < 0.02

    def test_strong_favourite(self):
        assert expected_score(1800, 1400, 100) > 0.85

    def test_symmetry(self):
        home_exp = expected_score(1500, 1600, 0)
        away_exp = expected_score(1600, 1500, 0)
        assert abs(home_exp + away_exp - 1.0) < 0.001

    def test_home_and_away_sum_to_one(self):
        for h, a, ha in [(1500, 1500, 100), (1700, 1300, 60), (1200, 1800, 120)]:
            exp = expected_score(h, a, ha)
            assert abs(exp + (1.0 - exp) - 1.0) < 0.001



class TestActualScore:

    def test_home_win(self):
        assert actual_score(2, 1) == (1.0, 0.0)

    def test_away_win(self):
        assert actual_score(0, 3) == (0.0, 1.0)

    def test_draw(self):
        assert actual_score(1, 1) == (0.5, 0.5)

    def test_high_scoring_draw(self):
        assert actual_score(4, 4) == (0.5, 0.5)

    def test_goalless_draw(self):
        assert actual_score(0, 0) == (0.5, 0.5)



class TestUpdateRatings:

    def test_home_win_from_equal(self):
        h, a = update_ratings(1500, 1500, 2, 1)
        assert h > 1500
        assert a < 1500

    def test_zero_sum(self):
        h, a = update_ratings(1500, 1500, 2, 1)
        assert abs((h + a) - 3000) < 0.001

    def test_draw_from_equal_no_home_advantage(self):
        h, a = update_ratings(1500, 1500, 1, 1, home_advantage=0)
        assert abs(h - 1500) < 0.001
        assert abs(a - 1500) < 0.001

    def test_draw_with_home_advantage_costs_home(self):
        h, a = update_ratings(1500, 1500, 1, 1, home_advantage=100)
        assert h < 1500
        assert a > 1500

    def test_upset_gives_bigger_swing(self):
        fav_h, _ = update_ratings(1600, 1400, 2, 1)
        und_h, _ = update_ratings(1400, 1600, 2, 1)
        fav_gain = fav_h - 1600
        und_gain = und_h - 1400
        assert und_gain > fav_gain

    def test_larger_k_gives_larger_update(self):
        h_small, _ = update_ratings(1500, 1500, 2, 1, k_factor=20)
        h_large, _ = update_ratings(1500, 1500, 2, 1, k_factor=40)
        assert abs(h_large - 1500) > abs(h_small - 1500)



class TestSeasonReset:

    def test_both_move_toward_mean(self):
        reset = apply_season_reset({"A": 1700, "B": 1300})
        assert reset["A"] < 1700
        assert reset["B"] > 1300

    def test_exact_values(self):
        reset = apply_season_reset({"A": 1700, "B": 1300})
        mean = 1500
        weight = SEASON_MEAN_REVERSION_WEIGHT
        assert abs(reset["A"] - (1700 * (1 - weight) + mean * weight)) < 0.01
        assert abs(reset["B"] - (1300 * (1 - weight) + mean * weight)) < 0.01

    def test_empty_dict(self):
        assert apply_season_reset({}) == {}

    def test_custom_league_mean(self):
        reset = apply_season_reset({"A": 1600}, league_mean=1400)
        weight = SEASON_MEAN_REVERSION_WEIGHT
        assert abs(reset["A"] - (1600 * (1 - weight) + 1400 * weight)) < 0.01



class TestComputeEloHistory:

    def test_first_match_both_start_at_initial(self):
        history, _ = compute_elo_history(FOUR_MATCH_FIXTURE)
        assert history[0]["home_elo_before"] == INITIAL_RATING
        assert history[0]["away_elo_before"] == INITIAL_RATING

    def test_history_length_matches_match_count(self):
        history, _ = compute_elo_history(FOUR_MATCH_FIXTURE)
        assert len(history) == len(FOUR_MATCH_FIXTURE)

    def test_all_required_columns_present(self):
        history, _ = compute_elo_history(FOUR_MATCH_FIXTURE)
        required = [
            "match_id", "date", "home_team", "away_team", "league", "season",
            "home_elo_before", "away_elo_before", "home_elo_after", "away_elo_after",
            "elo_difference", "expected_home", "expected_away",
            "actual_home", "actual_away",
        ]
        for col in required:
            assert col in history[0], f"Missing column: {col}"

    def test_zero_sum_all_matches(self):
        history, _ = compute_elo_history(FOUR_MATCH_FIXTURE)
        for h in history:
            delta = (h["home_elo_after"] - h["home_elo_before"]) + (
                h["away_elo_after"] - h["away_elo_before"]
            )
            assert abs(delta) < 0.02

    def test_elo_difference_consistent(self):
        history, _ = compute_elo_history(FOUR_MATCH_FIXTURE)
        for h in history:
            computed = round(h["home_elo_before"] - h["away_elo_before"], 2)
            assert h["elo_difference"] == computed

    def test_expected_scores_sum_to_one(self):
        history, _ = compute_elo_history(FOUR_MATCH_FIXTURE)
        for h in history:
            assert abs(h["expected_home"] + h["expected_away"] - 1.0) < 0.001



class TestBatchSeasonReset:

    def test_season_boundary_triggers_reset(self):
        history, _ = compute_elo_history(FOUR_MATCH_FIXTURE)
        pre_reset_a = history[1]["away_elo_after"]
        pre_reset_b = history[1]["home_elo_after"]
        league_mean = (pre_reset_a + pre_reset_b) / 2
        weight = SEASON_MEAN_REVERSION_WEIGHT
        expected_a = pre_reset_a * (1 - weight) + league_mean * weight
        actual_a = history[2]["home_elo_before"]
        assert abs(actual_a - round(expected_a, 2)) < 0.02



class TestPromotedTeams:

    def test_promoted_team_gets_below_mean_rating(self):
        history, _ = compute_elo_history(FOUR_MATCH_FIXTURE)
        pre_reset_a = history[1]["away_elo_after"]
        pre_reset_b = history[1]["home_elo_after"]
        league_mean = (pre_reset_a + pre_reset_b) / 2
        weight = SEASON_MEAN_REVERSION_WEIGHT
        reset_a = pre_reset_a * (1 - weight) + league_mean * weight
        reset_b = pre_reset_b * (1 - weight) + league_mean * weight
        reset_mean = (round(reset_a, 2) + round(reset_b, 2)) / 2
        expected_c = reset_mean + PROMOTED_TEAM_OFFSET
        actual_c = history[2]["away_elo_before"]
        assert abs(actual_c - expected_c) < 0.02

    def test_two_new_teams_same_match_both_get_initial(self):
        matches = _make_matches([{
            "match_id": 1, "date": "2020-08-15",
            "home_team": "X", "away_team": "Y",
            "home_goals": 1, "away_goals": 0,
            "league": "EPL", "season": "2020",
        }])
        history, _ = compute_elo_history(matches)
        assert history[0]["home_elo_before"] == INITIAL_RATING
        assert history[0]["away_elo_before"] == INITIAL_RATING



class TestTemporalContract:

    def test_match_n_uses_only_prior_results(self):
        history, _ = compute_elo_history(TEN_MATCH_FIXTURE)

        for i in range(1, len(history)):
            current = history[i]
            prior_history = history[:i]

            home_team = current["home_team"]
            home_appearances = [
                h for h in prior_history
                if h["home_team"] == home_team or h["away_team"] == home_team
            ]

            if home_appearances:
                last = home_appearances[-1]
                if last["home_team"] == home_team:
                    expected_elo = last["home_elo_after"]
                else:
                    expected_elo = last["away_elo_after"]
                assert abs(current["home_elo_before"] - expected_elo) < 0.02, (
                    f"Match {current['match_id']}: {home_team} expected "
                    f"{expected_elo}, got {current['home_elo_before']}"
                )

    def test_ratings_evolve_across_matches(self):
        history, _ = compute_elo_history(TEN_MATCH_FIXTURE)
        first_a_elo = history[0]["home_elo_before"]
        last_row_with_a = [
            h for h in history if h["home_team"] == "A" or h["away_team"] == "A"
        ][-1]
        last_a_elo = (
            last_row_with_a["home_elo_after"]
            if last_row_with_a["home_team"] == "A"
            else last_row_with_a["away_elo_after"]
        )
        assert first_a_elo != last_a_elo



class TestMultiLeagueIsolation:

    def test_leagues_do_not_contaminate_each_other(self):
        matches = _make_matches([
            {"match_id": 1, "date": "2020-08-15", "home_team": "X", "away_team": "Y",
             "home_goals": 5, "away_goals": 0, "league": "La_Liga", "season": "2020"},
            {"match_id": 2, "date": "2020-08-16", "home_team": "A", "away_team": "B",
             "home_goals": 1, "away_goals": 0, "league": "EPL", "season": "2020"},
        ])
        history, _ = compute_elo_history(matches)
        assert history[0]["home_elo_before"] == INITIAL_RATING
        assert history[1]["home_elo_before"] == INITIAL_RATING



class TestEloProbabilities:

    def test_probabilities_sum_to_one(self):
        test_cases = [
            (1500, 1500, 100),
            (1700, 1300, 60),
            (1300, 1700, 120),
            (1500, 1500, 0),
            (1800, 1200, 80),
        ]
        for h, a, ha in test_cases:
            probs = elo_to_probabilities(h, a, ha)
            total = sum(probs.values())
            assert abs(total - 1.0) < 0.001, f"Sum={total} for ({h}, {a}, {ha})"

    def test_all_probabilities_non_negative(self):
        for diff in range(-400, 401, 50):
            probs = elo_to_probabilities(1500 + diff, 1500)
            for cls, val in probs.items():
                assert val >= 0, f"Negative probability: {cls}={val} at diff={diff}"

    def test_stronger_team_favoured(self):
        probs = elo_to_probabilities(1700, 1300, 100)
        assert probs["H"] > probs["A"]

    def test_much_stronger_team_heavily_favoured(self):
        probs = elo_to_probabilities(1700, 1300, 100)
        assert probs["H"] > 0.7

    def test_draw_probability_highest_for_equal_teams(self):
        equal = elo_to_probabilities(1500, 1500, 0)
        unequal = elo_to_probabilities(1700, 1300, 0)
        assert equal["D"] > unequal["D"]

    def test_has_all_three_classes(self):
        probs = elo_to_probabilities(1500, 1500, 100)
        assert "H" in probs and "D" in probs and "A" in probs



class TestGetEloAtDate:

    @pytest.fixture()
    def elo_history_df(self):
        history, _ = compute_elo_history(FOUR_MATCH_FIXTURE)
        return pd.DataFrame(history)

    def test_returns_initial_before_any_history(self, elo_history_df):
        elo = get_elo_at_date(elo_history_df, "A", pd.Timestamp("2019-01-01"))
        assert elo == INITIAL_RATING

    def test_returns_correct_post_match_rating(self, elo_history_df):
        elo = get_elo_at_date(elo_history_df, "A", pd.Timestamp("2020-08-20"))
        expected = elo_history_df.iloc[0]["home_elo_after"]
        assert elo == expected

    def test_returns_float(self, elo_history_df):
        elo = get_elo_at_date(elo_history_df, "A", pd.Timestamp("2022-01-01"))
        assert isinstance(elo, float)