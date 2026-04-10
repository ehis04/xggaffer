from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd

from ml.engines.elo import (
    DEFAULT_HOME_ADVANTAGE,
    DEFAULT_K_FACTOR,
    compute_elo_history,
    elo_to_probabilities,
    save_elo_history,
)
from ml.features.rolling import ALL_LEAGUES, ALL_SEASONS, load_match_history
from ml.models.match_outcome.config import PROCESSED_DIR


DEFAULT_OUTPUT = PROCESSED_DIR / "elo_ratings.csv"

TUNE_K_VALUES = [20, 25, 30, 35, 40]
TUNE_HOME_ADV_VALUES = [60, 80, 100, 120]
VALIDATION_SEASON = "2023"
ECE_N_BINS = 10



def _result_to_index(home_goals: float, away_goals: float) -> int:
    if home_goals > away_goals:
        return 0
    if home_goals < away_goals:
        return 2
    return 1


def _compute_log_loss(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    clipped = np.clip(y_prob, 1e-15, 1.0 - 1e-15)
    n = len(y_true)
    loss = 0.0
    for i in range(n):
        loss -= np.log(clipped[i, y_true[i]])
    return loss / n


def _compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = ECE_N_BINS) -> float:
    n_classes = y_prob.shape[1]
    total_predictions = len(y_true) * n_classes
    ece = 0.0

    for cls in range(n_classes):
        probs = y_prob[:, cls]
        actuals = (y_true == cls).astype(float)

        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
        for b in range(n_bins):
            mask = (probs >= bin_edges[b]) & (probs < bin_edges[b + 1])
            if b == n_bins - 1:
                mask = (probs >= bin_edges[b]) & (probs <= bin_edges[b + 1])

            count = mask.sum()
            if count == 0:
                continue

            avg_predicted = probs[mask].mean()
            avg_actual = actuals[mask].mean()
            ece += count * abs(avg_predicted - avg_actual)

    return ece / total_predictions


def _evaluate_params(
    history: list[dict],
    matches_df: pd.DataFrame,
    home_advantage: float,
    validation_season: str,
) -> dict[str, float]:
    hist_df = pd.DataFrame(history)
    val_mask = hist_df["season"] == validation_season

    if val_mask.sum() == 0:
        return {"log_loss": float("inf"), "ece": float("inf"), "accuracy": 0.0, "n_matches": 0}

    val_hist = hist_df[val_mask]

    y_true = np.array([
        _result_to_index(row.actual_home, row.actual_away)
        for row in val_hist.itertuples(index=False)
    ])

    y_prob = np.array([
        [p["H"], p["D"], p["A"]]
        for _, row in val_hist.iterrows()
        for p in [elo_to_probabilities(row["home_elo_before"], row["away_elo_before"], home_advantage)]
    ])

    predictions = np.argmax(y_prob, axis=1)
    accuracy = (predictions == y_true).mean()
    log_loss_val = _compute_log_loss(y_true, y_prob)
    ece_val = _compute_ece(y_true, y_prob)

    return {
        "log_loss": log_loss_val,
        "ece": ece_val,
        "accuracy": accuracy,
        "n_matches": len(val_hist),
    }



def _print_league_rankings(history: list[dict], current_ratings: dict[str, float]) -> None:
    hist_df = pd.DataFrame(history)
    leagues = sorted(hist_df["league"].unique())

    for league in leagues:
        league_hist = hist_df[hist_df["league"] == league]
        latest_season = league_hist["season"].max()
        season_hist = league_hist[league_hist["season"] == latest_season]

        team_ratings: dict[str, float] = {}
        for _, row in season_hist.iterrows():
            team_ratings[row["home_team"]] = row["home_elo_after"]
            team_ratings[row["away_team"]] = row["away_elo_after"]

        ranked = sorted(team_ratings.items(), key=lambda x: x[1], reverse=True)

        print(f"\n  {league} (season {latest_season}):")
        for i, (team, elo) in enumerate(ranked[:5]):
            print(f"    {i + 1:2d}. {team:30s} {elo:7.2f}")
        if len(ranked) > 5:
            print(f"    {'...':>34s}")
            for i, (team, elo) in enumerate(ranked[-3:], start=len(ranked) - 2):
                print(f"    {i:2d}. {team:30s} {elo:7.2f}")



def compute(
    leagues: list[str],
    seasons: list[str],
    k_factor: float,
    home_advantage: float,
    output_path: str,
) -> tuple[list[dict], dict[str, float]]:
    print("Loading match history...")
    matches = load_match_history(leagues, seasons)
    print(f"  {len(matches)} matches across {len(leagues)} leagues")

    print(f"Computing Elo ratings (K={k_factor}, HA={home_advantage})...")
    start = time.time()
    history, current_ratings = compute_elo_history(matches, k_factor, home_advantage)
    elapsed = time.time() - start
    print(f"  Processed {len(history)} matches in {elapsed:.2f}s")
    print(f"  {len(current_ratings)} teams rated")

    hist_df = pd.DataFrame(history)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    save_elo_history(hist_df, output_path)
    print(f"  Saved to {output_path}")

    _print_league_rankings(history, current_ratings)

    rating_values = list(current_ratings.values())
    print(f"\n  Rating range: {min(rating_values):.2f} – {max(rating_values):.2f}")
    print(f"  Rating mean:  {np.mean(rating_values):.2f}")
    print(f"  Rating std:   {np.std(rating_values):.2f}")

    return history, current_ratings


def tune(
    leagues: list[str],
    seasons: list[str],
    validation_season: str = VALIDATION_SEASON,
) -> dict:
    print("Loading match history...")
    matches = load_match_history(leagues, seasons)
    print(f"  {len(matches)} matches across {len(leagues)} leagues")

    combos = [
        (k, ha) for k in TUNE_K_VALUES for ha in TUNE_HOME_ADV_VALUES
    ]
    print(f"\nTuning {len(combos)} parameter combinations...")
    print(f"  K-factor values:      {TUNE_K_VALUES}")
    print(f"  Home advantage values: {TUNE_HOME_ADV_VALUES}")
    print(f"  Validation season:    {validation_season}")

    results: list[dict] = []

    for k, ha in combos:
        history, _ = compute_elo_history(matches, k_factor=k, home_advantage=ha)
        metrics = _evaluate_params(history, matches, ha, validation_season)

        results.append({
            "k_factor": k,
            "home_advantage": ha,
            **metrics,
        })

    results_df = pd.DataFrame(results).sort_values("log_loss")

    print(f"\n{'K':>5s} {'HA':>5s} {'LogLoss':>9s} {'ECE':>8s} {'Acc':>7s} {'N':>6s}")
    print("-" * 45)
    for _, row in results_df.iterrows():
        print(
            f"{row['k_factor']:5.0f} {row['home_advantage']:5.0f} "
            f"{row['log_loss']:9.4f} {row['ece']:8.4f} "
            f"{row['accuracy']:7.3f} {row['n_matches']:6.0f}"
        )

    best = results_df.iloc[0]
    print(f"\nBest combination (by log loss):")
    print(f"  K-factor:       {best['k_factor']:.0f}")
    print(f"  Home advantage: {best['home_advantage']:.0f}")
    print(f"  Log loss:       {best['log_loss']:.4f}")
    print(f"  ECE:            {best['ece']:.4f}")
    print(f"  Accuracy:       {best['accuracy']:.3f}")

    return {
        "best_k": int(best["k_factor"]),
        "best_ha": int(best["home_advantage"]),
        "best_log_loss": best["log_loss"],
        "best_ece": best["ece"],
        "best_accuracy": best["accuracy"],
        "all_results": results_df,
    }



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="xgGaffer Engine 1 — Compute Elo ratings from match history.",
    )
    parser.add_argument("--leagues", nargs="+", default=ALL_LEAGUES)
    parser.add_argument("--seasons", nargs="+", default=ALL_SEASONS)
    parser.add_argument("--k-factor", type=float, default=DEFAULT_K_FACTOR)
    parser.add_argument("--home-advantage", type=float, default=DEFAULT_HOME_ADVANTAGE)
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))
    parser.add_argument("--tune", action="store_true", help="Run grid search to find optimal K and home advantage.")
    parser.add_argument("--validation-season", type=str, default=VALIDATION_SEASON)

    args = parser.parse_args()

    if args.tune:
        best = tune(
            leagues=args.leagues,
            seasons=args.seasons,
            validation_season=args.validation_season,
        )
        print(f"\nRe-computing with best parameters (K={best['best_k']}, HA={best['best_ha']})...")
        compute(
            leagues=args.leagues,
            seasons=args.seasons,
            k_factor=best["best_k"],
            home_advantage=best["best_ha"],
            output_path=args.output,
        )
    else:
        compute(
            leagues=args.leagues,
            seasons=args.seasons,
            k_factor=args.k_factor,
            home_advantage=args.home_advantage,
            output_path=args.output,
        )