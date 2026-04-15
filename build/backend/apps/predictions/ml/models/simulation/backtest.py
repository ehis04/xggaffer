from __future__ import annotations

import time

import numpy as np
import pandas as pd

from apps.predictions.ml.engines.elo import compute_elo_history
from apps.predictions.ml.features.rolling import load_match_history
from apps.predictions.ml.models.scoreline.predict import ScorePredictor
from apps.predictions.ml.models.simulation.config import (
    BACKTEST_FREEZE_MATCHWEEKS,
    BACKTEST_LEAGUES,
    BACKTEST_SEASONS,
    N_SIMULATIONS,
)
from apps.predictions.ml.models.simulation.prepare_fixtures import (
    prepare_remaining_fixtures,
)
from apps.predictions.ml.models.simulation.simulate import (
    aggregate_results,
    compute_league_table,
    simulate_season,
)


def _get_actual_final_table(
    all_matches: pd.DataFrame,
    season: str,
    league: str,
) -> pd.DataFrame:
    season_matches = all_matches[
        (all_matches["season"].astype(str) == str(season))
        & (all_matches["league"] == league)
    ]
    match_dicts = season_matches[
        ["home_team", "away_team", "home_goals", "away_goals"]
    ].to_dict("records")

    return compute_league_table(match_dicts)


def _position_percentiles(
    position_probs: dict[int, float],
    n_sims: int,
    lower_pct: float,
    upper_pct: float,
) -> tuple[int, int]:
    positions = []
    for pos, prob in sorted(position_probs.items()):
        count = int(round(prob * n_sims))
        positions.extend([pos] * count)

    if not positions:
        return 1, 20

    return (
        int(np.percentile(positions, lower_pct)),
        int(np.percentile(positions, upper_pct)),
    )


def run_backtest(
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
    freeze_matchweeks: list[int] | None = None,
    n_simulations: int = N_SIMULATIONS,
    verbose: bool = True,
) -> pd.DataFrame:
    leagues = leagues or BACKTEST_LEAGUES
    seasons = seasons or BACKTEST_SEASONS
    freeze_matchweeks = freeze_matchweeks or BACKTEST_FREEZE_MATCHWEEKS

    all_seasons = [str(y) for y in range(2014, 2025)]
    all_matches = load_match_history(leagues, all_seasons)

    score_predictor = ScorePredictor()

    results = []

    for league in leagues:
        for season in seasons:
            actual_table = _get_actual_final_table(all_matches, season, league)

            if actual_table.empty:
                if verbose:
                    print(f"  Skipping {league} {season} — no matches found")
                continue

            for mw in freeze_matchweeks:
                t0 = time.time()

                actual, remaining, features = prepare_remaining_fixtures(
                    all_matches, season, league, freeze_matchweek=mw,
                )

                if len(remaining) == 0:
                    continue

                lambda_h, lambda_a = score_predictor.predict_lambdas_batch(
                    features,
                )

                sim = simulate_season(
                    actual, remaining, lambda_h, lambda_a,
                    n_simulations=n_simulations,
                )
                agg = aggregate_results(sim)

                elapsed = time.time() - t0

                for _, row in agg.iterrows():
                    team = row["team"]
                    actual_row = actual_table[actual_table["team"] == team]

                    if actual_row.empty:
                        continue

                    actual_pos = int(actual_row["position"].iloc[0])
                    actual_pts = int(actual_row["points"].iloc[0])

                    pos_5th, pos_95th = _position_percentiles(
                        row["position_probs"],
                        n_simulations,
                        10,
                        90,
                    )

                    results.append({
                        "league": league,
                        "season": season,
                        "matchweek": mw,
                        "team": team,
                        "actual_position": actual_pos,
                        "actual_points": actual_pts,
                        "modal_position": row["modal_position"],
                        "projected_points": row["projected_points_mean"],
                        "points_error": abs(
                            row["projected_points_mean"] - actual_pts
                        ),
                        "p_top_4": row["p_top_4"],
                        "p_relegation": row["p_relegation"],
                        "position_5th": pos_5th,
                        "position_95th": pos_95th,
                        "in_interval": pos_5th <= actual_pos <= pos_95th,
                    })

                if verbose:
                    coverage = np.mean(
                        [r["in_interval"] for r in results if r["matchweek"] == mw and r["season"] == season]
                    )
                    mae = np.mean(
                        [r["points_error"] for r in results if r["matchweek"] == mw and r["season"] == season]
                    )
                    print(
                        f"  {league} {season} MW{mw:2d}: "
                        f"coverage={coverage:.1%}  "
                        f"MAE={mae:.1f}pts  "
                        f"({elapsed:.1f}s)"
                    )

    return pd.DataFrame(results)


if __name__ == "__main__":
    print("Running Engine 4 backtest...")
    print()

    df = run_backtest(
        leagues=["EPL"],
        seasons=["2023"],
        freeze_matchweeks=[10, 20, 30],
        n_simulations=1000,
    )

    if not df.empty:
        print()
        print("Summary by matchweek:")
        summary = df.groupby("matchweek").agg(
            coverage=("in_interval", "mean"),
            points_mae=("points_error", "mean"),
            mean_position_error=(
                "actual_position",
                lambda x: np.mean(
                    np.abs(
                        x.values
                        - df.loc[x.index, "modal_position"].values
                    )
                ),
            ),
        )
        print(summary.to_string())