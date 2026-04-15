from __future__ import annotations

import numpy as np
import pytest

from apps.predictions.ml.models.scoreline.config import (
    AWAY_GOALS_FEATURES,
    HOME_GOALS_FEATURES,
    MAX_GOALS,
)
from apps.predictions.ml.models.scoreline.train import (
    derive_probabilities,
    dixon_coles_tau,
    fit_naive_poisson,
    scoreline_matrix,
)

TOLERANCE = 1e-6


class TestDixonColesTau:

    def test_no_effect_on_high_scores(self):
        for hg, ag in [(2, 0), (0, 2), (2, 1), (3, 2), (4, 1), (5, 3)]:
            assert dixon_coles_tau(hg, ag, 1.5, 1.2, -0.1) == 1.0

    def test_modifies_low_scores_when_rho_nonzero(self):
        rho = -0.1
        lambda_h, lambda_a = 1.5, 1.2

        assert dixon_coles_tau(0, 0, lambda_h, lambda_a, rho) != 1.0
        assert dixon_coles_tau(1, 0, lambda_h, lambda_a, rho) != 1.0
        assert dixon_coles_tau(0, 1, lambda_h, lambda_a, rho) != 1.0
        assert dixon_coles_tau(1, 1, lambda_h, lambda_a, rho) != 1.0

    def test_no_effect_when_rho_zero(self):
        for hg, ag in [(0, 0), (1, 0), (0, 1), (1, 1)]:
            assert dixon_coles_tau(hg, ag, 1.5, 1.2, 0.0) == 1.0

    def test_tau_00_formula(self):
        lh, la, rho = 1.5, 1.2, -0.1
        expected = 1.0 + lh * la * rho
        assert dixon_coles_tau(0, 0, lh, la, rho) == pytest.approx(expected)

    def test_tau_11_formula(self):
        rho = -0.1
        expected = 1.0 + rho
        assert dixon_coles_tau(1, 1, 1.5, 1.2, rho) == pytest.approx(expected)


class TestScorelineMatrix:

    def test_shape(self):
        matrix = scoreline_matrix(1.5, 1.2, rho=0.0)
        assert matrix.shape == (MAX_GOALS + 1, MAX_GOALS + 1)

    def test_sums_to_one(self):
        for lh, la, rho in [(1.5, 1.2, 0.0), (2.0, 0.8, -0.1), (0.5, 0.5, 0.05)]:
            matrix = scoreline_matrix(lh, la, rho)
            assert abs(matrix.sum() - 1.0) < TOLERANCE

    def test_all_non_negative(self):
        for lh, la, rho in [(1.5, 1.2, -0.15), (2.5, 0.5, -0.1), (1.0, 1.0, 0.1)]:
            matrix = scoreline_matrix(lh, la, rho)
            assert (matrix >= 0).all()

    def test_higher_home_lambda_shifts_mass(self):
        matrix_strong = scoreline_matrix(2.5, 0.8, rho=0.0)
        matrix_weak = scoreline_matrix(0.8, 2.5, rho=0.0)

        home_win_strong = np.tril(matrix_strong, -1).sum()
        home_win_weak = np.tril(matrix_weak, -1).sum()

        assert home_win_strong > home_win_weak


class TestDeriveProbabilities:

    def test_wdl_sums_to_one(self):
        matrix = scoreline_matrix(1.5, 1.2, rho=0.0)
        probs = derive_probabilities(matrix)
        total = probs["home_win"] + probs["draw"] + probs["away_win"]
        assert abs(total - 1.0) < TOLERANCE

    def test_home_favoured_when_stronger(self):
        matrix = scoreline_matrix(2.0, 0.8, rho=0.0)
        probs = derive_probabilities(matrix)
        assert probs["home_win"] > probs["away_win"]

    def test_away_favoured_when_stronger(self):
        matrix = scoreline_matrix(0.8, 2.0, rho=0.0)
        probs = derive_probabilities(matrix)
        assert probs["away_win"] > probs["home_win"]

    def test_symmetric_lambdas_similar_probs(self):
        matrix = scoreline_matrix(1.5, 1.5, rho=0.0)
        probs = derive_probabilities(matrix)
        assert abs(probs["home_win"] - probs["away_win"]) < 0.01

    def test_over_under_consistency(self):
        matrix = scoreline_matrix(1.5, 1.2, rho=-0.05)
        probs = derive_probabilities(matrix)
        for threshold in [0.5, 1.5, 2.5, 3.5, 4.5]:
            total = probs[f"over_{threshold}"] + probs[f"under_{threshold}"]
            assert abs(total - 1.0) < TOLERANCE

    def test_btts_consistency(self):
        matrix = scoreline_matrix(1.5, 1.2, rho=0.0)
        probs = derive_probabilities(matrix)
        assert abs(probs["btts_yes"] + probs["btts_no"] - 1.0) < TOLERANCE

    def test_draw_probability_nonzero(self):
        for lh, la in [(0.5, 0.5), (1.5, 1.2), (2.5, 2.0)]:
            matrix = scoreline_matrix(lh, la, rho=0.0)
            probs = derive_probabilities(matrix)
            assert probs["draw"] > 0

    def test_most_likely_score_sensible(self):
        matrix = scoreline_matrix(1.5, 1.0, rho=0.0)
        probs = derive_probabilities(matrix)
        score = probs["most_likely_score"]
        home, away = map(int, score.split("-"))
        assert 0 <= home <= 3
        assert 0 <= away <= 2

    def test_high_lambda_means_more_overs(self):
        matrix_low = scoreline_matrix(0.8, 0.6, rho=0.0)
        matrix_high = scoreline_matrix(2.5, 2.0, rho=0.0)
        probs_low = derive_probabilities(matrix_low)
        probs_high = derive_probabilities(matrix_high)
        assert probs_high["over_2.5"] > probs_low["over_2.5"]

    def test_high_lambda_means_more_btts(self):
        matrix_low = scoreline_matrix(0.5, 0.3, rho=0.0)
        matrix_high = scoreline_matrix(2.0, 2.0, rho=0.0)
        probs_low = derive_probabilities(matrix_low)
        probs_high = derive_probabilities(matrix_high)
        assert probs_high["btts_yes"] > probs_low["btts_yes"]


class TestNaivePoisson:

    def test_returns_positive_rates(self):
        import pandas as pd
        df = pd.DataFrame({"home_goals": [1, 2, 0, 3], "away_goals": [0, 1, 1, 2]})
        naive_h, naive_a = fit_naive_poisson(df)
        assert naive_h > 0
        assert naive_a > 0

    def test_returns_correct_means(self):
        import pandas as pd
        df = pd.DataFrame({"home_goals": [2, 2, 2], "away_goals": [1, 1, 1]})
        naive_h, naive_a = fit_naive_poisson(df)
        assert naive_h == pytest.approx(2.0)
        assert naive_a == pytest.approx(1.0)


class TestPredictLambdasPositive:

    def test_lambdas_always_positive(self):
        matrix = scoreline_matrix(0.01, 0.01, rho=0.0)
        assert matrix.sum() > 0

        matrix = scoreline_matrix(5.0, 5.0, rho=0.0)
        assert matrix.sum() > 0