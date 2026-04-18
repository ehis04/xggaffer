from __future__ import annotations

from datetime import datetime

import joblib
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.optimize import minimize_scalar
from scipy.stats import poisson as poisson_dist

from apps.predictions.ml.models.scoreline.config import (
    AWAY_GOALS_FEATURES,
    DEFAULT_RHO_BOUNDS,
    DEFAULT_TIME_DECAY_RATE,
    HOME_GOALS_FEATURES,
    MAX_GOALS,
    MODELS_DIR,
    SCORE_ENGINE_LEAGUES,
    SCORE_ENGINE_SEASONS,
    TEST_SEASONS,
)



def fit_naive_poisson(
    train_df: pd.DataFrame,
) -> tuple[float, float]:
    return float(train_df["home_goals"].mean()), float(train_df["away_goals"].mean())



def fit_poisson_glm(
    train_df: pd.DataFrame,
    home_features: list[str],
    away_features: list[str],
    weights: np.ndarray | None = None,
) -> tuple[sm.GLM, sm.GLM]:
    X_home = sm.add_constant(train_df[home_features].astype(float))
    y_home = train_df["home_goals"]

    X_away = sm.add_constant(train_df[away_features].astype(float))
    y_away = train_df["away_goals"]

    model_home = sm.GLM(
        y_home, X_home,
        family=sm.families.Poisson(),
        freq_weights=weights,
    ).fit()

    model_away = sm.GLM(
        y_away, X_away,
        family=sm.families.Poisson(),
        freq_weights=weights,
    ).fit()

    return model_home, model_away


def predict_lambdas(
    model_home: sm.GLM,
    model_away: sm.GLM,
    df: pd.DataFrame,
    home_features: list[str],
    away_features: list[str],
) -> tuple[np.ndarray, np.ndarray]:
    X_home = sm.add_constant(df[home_features].astype(float))
    X_away = sm.add_constant(df[away_features].astype(float))

    lambda_home = model_home.predict(X_home).values
    lambda_away = model_away.predict(X_away).values

    return lambda_home, lambda_away



def dixon_coles_tau(
    home_goals: int,
    away_goals: int,
    lambda_h: float,
    lambda_a: float,
    rho: float,
) -> float:
    if home_goals == 0 and away_goals == 0:
        return 1.0 + lambda_h * lambda_a * rho
    if home_goals == 1 and away_goals == 0:
        return 1.0 - lambda_a * rho
    if home_goals == 0 and away_goals == 1:
        return 1.0 - lambda_h * rho
    if home_goals == 1 and away_goals == 1:
        return 1.0 + rho
    return 1.0


def fit_rho(
    train_df: pd.DataFrame,
    lambda_home: np.ndarray,
    lambda_away: np.ndarray,
    rho_bounds: tuple[float, float] = DEFAULT_RHO_BOUNDS,
) -> float:
    hg = train_df["home_goals"].values.astype(int)
    ag = train_df["away_goals"].values.astype(int)
    lh = lambda_home
    la = lambda_away

    p_indep = poisson_dist.pmf(hg, lh) * poisson_dist.pmf(ag, la)

    mask_00 = (hg == 0) & (ag == 0)
    mask_10 = (hg == 1) & (ag == 0)
    mask_01 = (hg == 0) & (ag == 1)
    mask_11 = (hg == 1) & (ag == 1)

    def neg_log_likelihood(rho: float) -> float:
        tau = np.ones(len(hg))
        tau[mask_00] = 1.0 + lh[mask_00] * la[mask_00] * rho
        tau[mask_10] = 1.0 - la[mask_10] * rho
        tau[mask_01] = 1.0 - lh[mask_01] * rho
        tau[mask_11] = 1.0 + rho

        p_dc = np.maximum(p_indep * tau, 1e-10)
        return -np.sum(np.log(p_dc))

    result = minimize_scalar(
        neg_log_likelihood,
        bounds=rho_bounds,
        method="bounded",
    )

    return float(result.x)


def compute_nll(
    test_df: pd.DataFrame,
    lambda_home: np.ndarray,
    lambda_away: np.ndarray,
    rho: float,
) -> float:
    hg = test_df["home_goals"].values.astype(int)
    ag = test_df["away_goals"].values.astype(int)

    p_indep = poisson_dist.pmf(hg, lambda_home) * poisson_dist.pmf(ag, lambda_away)

    tau = np.ones(len(hg))
    mask_00 = (hg == 0) & (ag == 0)
    mask_10 = (hg == 1) & (ag == 0)
    mask_01 = (hg == 0) & (ag == 1)
    mask_11 = (hg == 1) & (ag == 1)

    tau[mask_00] = 1.0 + lambda_home[mask_00] * lambda_away[mask_00] * rho
    tau[mask_10] = 1.0 - lambda_away[mask_10] * rho
    tau[mask_01] = 1.0 - lambda_home[mask_01] * rho
    tau[mask_11] = 1.0 + rho

    p_dc = np.maximum(p_indep * tau, 1e-10)
    return float(-np.mean(np.log(p_dc)))



def scoreline_matrix(
    lambda_h: float,
    lambda_a: float,
    rho: float = 0.0,
    max_goals: int = MAX_GOALS,
) -> np.ndarray:
    goals = np.arange(max_goals + 1)
    home_probs = poisson_dist.pmf(goals, lambda_h)
    away_probs = poisson_dist.pmf(goals, lambda_a)

    matrix = np.outer(home_probs, away_probs)

    matrix[0, 0] *= 1.0 + lambda_h * lambda_a * rho
    matrix[1, 0] *= 1.0 - lambda_a * rho
    matrix[0, 1] *= 1.0 - lambda_h * rho
    matrix[1, 1] *= 1.0 + rho

    matrix = np.maximum(matrix, 0.0)
    matrix /= matrix.sum()

    return matrix



OVER_UNDER_THRESHOLDS = [0.5, 1.5, 2.5, 3.5, 4.5]


def derive_probabilities(matrix: np.ndarray) -> dict:
    p_home = float(np.tril(matrix, -1).sum())
    p_draw = float(np.trace(matrix))
    p_away = float(np.triu(matrix, 1).sum())

    n = matrix.shape[0]
    goals_range = np.arange(n)
    total_goals_grid = goals_range[:, None] + goals_range[None, :]

    total_goals_probs = {}
    for threshold in OVER_UNDER_THRESHOLDS:
        p_over = float(matrix[total_goals_grid > threshold].sum())
        total_goals_probs[f"over_{threshold}"] = p_over
        total_goals_probs[f"under_{threshold}"] = 1.0 - p_over

    p_btts = (
        1.0
        - float(matrix[0, :].sum())
        - float(matrix[:, 0].sum())
        + float(matrix[0, 0])
    )

    flat_idx = np.argmax(matrix)
    most_likely = divmod(flat_idx, matrix.shape[1])

    return {
        "home_win": p_home,
        "draw": p_draw,
        "away_win": p_away,
        **total_goals_probs,
        "btts_yes": p_btts,
        "btts_no": 1.0 - p_btts,
        "most_likely_score": f"{most_likely[0]}-{most_likely[1]}",
        "most_likely_score_prob": float(matrix[most_likely]),
    }



def train_score_model(
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
    test_seasons: list[str] | None = None,
    home_features: list[str] | None = None,
    away_features: list[str] | None = None,
    decay_rate: float = DEFAULT_TIME_DECAY_RATE,
    save: bool = True,
) -> dict:
    from apps.predictions.ml.models.scoreline.prepare_data import (
        compute_match_weights,
        get_temporal_split,
        prepare_score_dataset,
    )

    leagues = leagues or SCORE_ENGINE_LEAGUES
    seasons = seasons or SCORE_ENGINE_SEASONS
    test_seasons = test_seasons or TEST_SEASONS
    home_features = home_features or HOME_GOALS_FEATURES
    away_features = away_features or AWAY_GOALS_FEATURES

    all_features = list(set(home_features + away_features))

    print("Loading dataset...")
    df = prepare_score_dataset(leagues=leagues, seasons=seasons)
    print(f"  Total matches: {len(df)}")

    df = df.dropna(subset=all_features)
    print(f"  After dropping feature NaN: {len(df)}")

    train_df, test_df = get_temporal_split(df, test_seasons)
    print(f"  Train: {len(train_df)}  Test: {len(test_df)}")

    weights = compute_match_weights(train_df, decay_rate)

    naive_home, naive_away = fit_naive_poisson(train_df)
    print(f"\nNaive baseline — lambda_home: {naive_home:.3f}, lambda_away: {naive_away:.3f}")

    print("\nFitting Poisson GLMs...")
    model_home, model_away = fit_poisson_glm(
        train_df, home_features, away_features, weights,
    )

    print("\n--- Home goals model ---")
    print(model_home.summary2())
    print("\n--- Away goals model ---")
    print(model_away.summary2())

    print("\nFitting Dixon-Coles rho...")
    train_lambda_h, train_lambda_a = predict_lambdas(
        model_home, model_away, train_df, home_features, away_features,
    )
    rho = fit_rho(train_df, train_lambda_h, train_lambda_a)
    print(f"  rho = {rho:.4f}")

    test_lambda_h, test_lambda_a = predict_lambdas(
        model_home, model_away, test_df, home_features, away_features,
    )
    nll = compute_nll(test_df, test_lambda_h, test_lambda_a, rho)

    artifact_path = None

    artifact = {
        "model_home": model_home,
        "model_away": model_away,
        "rho": rho,
        "nll": nll,
        "home_features": home_features,
        "away_features": away_features,
        "decay_rate": decay_rate,
        "naive_home": naive_home,
        "naive_away": naive_away,
        "trained_at": datetime.now().isoformat(),
        "leagues": leagues,
        "seasons": seasons,
        "test_seasons": test_seasons,
        "train_samples": len(train_df),
        "test_samples": len(test_df),
    }

    if save:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        artifact_path = MODELS_DIR / f"score_poisson_dc_{timestamp}.joblib"
        joblib.dump(artifact, artifact_path)
        print(f"\nSaved to: {artifact_path}")

    return {
        "model_home": model_home,
        "model_away": model_away,
        "rho": rho,
        "nll": nll,
        "model_path": str(artifact_path) if artifact_path is not None else None,
        "home_features": home_features,
        "away_features": away_features,
        "naive_home": naive_home,
        "naive_away": naive_away,
        "test_lambda_home": test_lambda_h,
        "test_lambda_away": test_lambda_a,
        "train_df": train_df,
        "test_df": test_df,
        "artifact": artifact,
    }


if __name__ == "__main__":
    results = train_score_model()

    test_df = results["test_df"]
    lh = results["test_lambda_home"]
    la = results["test_lambda_away"]
    rho = results["rho"]

    print("\n" + "=" * 60)
    print("SAMPLE PREDICTIONS (first 5 test matches)")
    print("=" * 60)

    for i in range(min(5, len(test_df))):
        row = test_df.iloc[i]
        matrix = scoreline_matrix(lh[i], la[i], rho)
        probs = derive_probabilities(matrix)
        actual = f"{int(row['home_goals'])}-{int(row['away_goals'])}"

        print(f"\n{row['home_team']} vs {row['away_team']}")
        print(f"  lambda_h={lh[i]:.2f}  lambda_a={la[i]:.2f}")
        print(f"  H={probs['home_win']:.1%}  D={probs['draw']:.1%}  A={probs['away_win']:.1%}")
        print(f"  Most likely: {probs['most_likely_score']} ({probs['most_likely_score_prob']:.1%})")
        print(f"  Over 2.5: {probs['over_2.5']:.1%}  BTTS: {probs['btts_yes']:.1%}")
        print(f"  Actual: {actual}")