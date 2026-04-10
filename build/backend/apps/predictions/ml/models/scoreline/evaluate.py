from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import poisson as poisson_dist

from ml.models.scoreline.config import MAX_GOALS
from ml.models.scoreline.train import (
    derive_probabilities,
    dixon_coles_tau,
    fit_naive_poisson,
    scoreline_matrix,
)



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


def compute_naive_nll(test_df: pd.DataFrame) -> float:
    mean_home = test_df["home_goals"].mean()
    mean_away = test_df["away_goals"].mean()

    hg = test_df["home_goals"].values.astype(int)
    ag = test_df["away_goals"].values.astype(int)

    p = poisson_dist.pmf(hg, mean_home) * poisson_dist.pmf(ag, mean_away)
    return float(-np.mean(np.log(np.maximum(p, 1e-10))))



def compute_exact_score_accuracy(
    test_df: pd.DataFrame,
    lambda_home: np.ndarray,
    lambda_away: np.ndarray,
    rho: float,
) -> float:
    hg = test_df["home_goals"].values.astype(int)
    ag = test_df["away_goals"].values.astype(int)

    correct = 0
    for i in range(len(test_df)):
        matrix = scoreline_matrix(lambda_home[i], lambda_away[i], rho)
        predicted = divmod(np.argmax(matrix), matrix.shape[1])
        if predicted[0] == hg[i] and predicted[1] == ag[i]:
            correct += 1

    return correct / len(test_df)



def compute_derived_wdl(
    test_df: pd.DataFrame,
    lambda_home: np.ndarray,
    lambda_away: np.ndarray,
    rho: float,
) -> dict:
    hg = test_df["home_goals"].values.astype(int)
    ag = test_df["away_goals"].values.astype(int)

    actual_outcomes = np.where(hg > ag, "H", np.where(ag > hg, "A", "D"))

    predicted_outcomes = []
    predicted_probs = {"H": [], "D": [], "A": []}

    for i in range(len(test_df)):
        matrix = scoreline_matrix(lambda_home[i], lambda_away[i], rho)
        probs = derive_probabilities(matrix)

        best = max(("H", probs["home_win"]), ("D", probs["draw"]), ("A", probs["away_win"]),
                    key=lambda x: x[1])
        predicted_outcomes.append(best[0])

        predicted_probs["H"].append(probs["home_win"])
        predicted_probs["D"].append(probs["draw"])
        predicted_probs["A"].append(probs["away_win"])

    predicted_outcomes = np.array(predicted_outcomes)
    accuracy = float((predicted_outcomes == actual_outcomes).mean())

    per_class = {}
    for cls in ("H", "D", "A"):
        mask = actual_outcomes == cls
        total = int(mask.sum())
        correct = int((predicted_outcomes[mask] == cls).sum()) if total > 0 else 0
        recall = correct / total if total > 0 else 0.0

        pred_mask = predicted_outcomes == cls
        pred_total = int(pred_mask.sum())
        pred_correct = int((actual_outcomes[pred_mask] == cls).sum()) if pred_total > 0 else 0
        precision = pred_correct / pred_total if pred_total > 0 else 0.0

        per_class[cls] = {
            "support": total,
            "predicted": pred_total,
            "recall": recall,
            "precision": precision,
        }

    return {
        "accuracy": accuracy,
        "per_class": per_class,
        "predicted_probs": predicted_probs,
    }



def compute_over_under_accuracy(
    test_df: pd.DataFrame,
    lambda_home: np.ndarray,
    lambda_away: np.ndarray,
    rho: float,
    threshold: float = 2.5,
) -> float:
    hg = test_df["home_goals"].values.astype(int)
    ag = test_df["away_goals"].values.astype(int)
    actual_total = hg + ag

    correct = 0
    for i in range(len(test_df)):
        matrix = scoreline_matrix(lambda_home[i], lambda_away[i], rho)
        probs = derive_probabilities(matrix)
        predicted_over = probs[f"over_{threshold}"] > 0.5
        actual_over = actual_total[i] > threshold
        if predicted_over == actual_over:
            correct += 1

    return correct / len(test_df)



def compute_btts_accuracy(
    test_df: pd.DataFrame,
    lambda_home: np.ndarray,
    lambda_away: np.ndarray,
    rho: float,
) -> float:
    hg = test_df["home_goals"].values.astype(int)
    ag = test_df["away_goals"].values.astype(int)

    correct = 0
    for i in range(len(test_df)):
        matrix = scoreline_matrix(lambda_home[i], lambda_away[i], rho)
        probs = derive_probabilities(matrix)
        predicted_btts = probs["btts_yes"] > 0.5
        actual_btts = (hg[i] > 0) and (ag[i] > 0)
        if predicted_btts == actual_btts:
            correct += 1

    return correct / len(test_df)



def compute_draw_analysis(
    test_df: pd.DataFrame,
    lambda_home: np.ndarray,
    lambda_away: np.ndarray,
    rho: float,
) -> dict:
    hg = test_df["home_goals"].values.astype(int)
    ag = test_df["away_goals"].values.astype(int)
    actual_draws = hg == ag

    draw_probs = []
    predicted_draws = 0

    for i in range(len(test_df)):
        matrix = scoreline_matrix(lambda_home[i], lambda_away[i], rho)
        probs = derive_probabilities(matrix)
        draw_probs.append(probs["draw"])

        if probs["draw"] > probs["home_win"] and probs["draw"] > probs["away_win"]:
            predicted_draws += 1

    draw_probs = np.array(draw_probs)

    return {
        "mean_predicted_draw_prob": float(draw_probs.mean()),
        "actual_draw_rate": float(actual_draws.mean()),
        "matches_predicted_draw": predicted_draws,
        "draw_prediction_rate": predicted_draws / len(test_df),
        "draw_recall": (
            float(((draw_probs == draw_probs.max()) & actual_draws).sum() / actual_draws.sum())
            if actual_draws.sum() > 0 else 0.0
        ),
    }



def compute_rho_impact(
    test_df: pd.DataFrame,
    lambda_home: np.ndarray,
    lambda_away: np.ndarray,
    rho: float,
) -> dict:
    nll_with = compute_nll(test_df, lambda_home, lambda_away, rho)
    nll_without = compute_nll(test_df, lambda_home, lambda_away, 0.0)
    return {
        "nll_with_rho": nll_with,
        "nll_without_rho": nll_without,
        "nll_delta": nll_without - nll_with,
    }



def run_score_evaluation(results: dict) -> dict:
    test_df = results["test_df"]
    lh = results["test_lambda_home"]
    la = results["test_lambda_away"]
    rho = results["rho"]
    naive_home = results["naive_home"]
    naive_away = results["naive_away"]

    print("=" * 60)
    print("ENGINE 3 — SCORE ENGINE EVALUATION")
    print("=" * 60)

    naive_nll = compute_naive_nll(test_df)
    covariate_nll = compute_nll(test_df, lh, la, rho)
    print(f"\n--- Negative Log-Likelihood ---")
    print(f"  Naive baseline:   {naive_nll:.4f}")
    print(f"  Covariate model:  {covariate_nll:.4f}")
    print(f"  Improvement:      {naive_nll - covariate_nll:.4f}")

    rho_impact = compute_rho_impact(test_df, lh, la, rho)
    print(f"\n--- Dixon-Coles Impact ---")
    print(f"  NLL with rho:     {rho_impact['nll_with_rho']:.4f}")
    print(f"  NLL without rho:  {rho_impact['nll_without_rho']:.4f}")
    print(f"  Delta:            {rho_impact['nll_delta']:.4f}")

    exact_acc = compute_exact_score_accuracy(test_df, lh, la, rho)
    print(f"\n--- Exact Score Accuracy ---")
    print(f"  Accuracy:         {exact_acc:.1%}")
    print(f"  Random baseline:  ~4%")

    wdl = compute_derived_wdl(test_df, lh, la, rho)
    print(f"\n--- Derived W/D/L ---")
    print(f"  Accuracy:         {wdl['accuracy']:.1%}")
    for cls in ("H", "D", "A"):
        c = wdl["per_class"][cls]
        print(f"  {cls}: recall={c['recall']:.1%}  precision={c['precision']:.1%}  "
              f"support={c['support']}  predicted={c['predicted']}")

    over_under = compute_over_under_accuracy(test_df, lh, la, rho, 2.5)
    print(f"\n--- Over/Under 2.5 ---")
    print(f"  Accuracy:         {over_under:.1%}")

    btts = compute_btts_accuracy(test_df, lh, la, rho)
    print(f"\n--- BTTS ---")
    print(f"  Accuracy:         {btts:.1%}")

    draw = compute_draw_analysis(test_df, lh, la, rho)
    print(f"\n--- Draw Analysis ---")
    print(f"  Mean predicted P(draw):  {draw['mean_predicted_draw_prob']:.1%}")
    print(f"  Actual draw rate:        {draw['actual_draw_rate']:.1%}")
    print(f"  Matches predicted draw:  {draw['matches_predicted_draw']}/{len(test_df)}")
    print(f"  Draw prediction rate:    {draw['draw_prediction_rate']:.1%}")

    print(f"\n--- Engine 2 Comparison ---")
    print(f"  Engine 2 accuracy:      53.2%")
    print(f"  Engine 2 draw recall:   0%")
    print(f"  Engine 3 W/D/L acc:     {wdl['accuracy']:.1%}")
    print(f"  Engine 3 draw recall:   {wdl['per_class']['D']['recall']:.1%}")

    print("\n" + "=" * 60)

    return {
        "naive_nll": naive_nll,
        "covariate_nll": covariate_nll,
        "rho_impact": rho_impact,
        "exact_score_accuracy": exact_acc,
        "wdl": wdl,
        "over_under_2_5": over_under,
        "btts": btts,
        "draw_analysis": draw,
    }


if __name__ == "__main__":
    from ml.models.scoreline.train import train_score_model

    results = train_score_model(save=False)
    metrics = run_score_evaluation(results)