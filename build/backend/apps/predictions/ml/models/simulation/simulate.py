from __future__ import annotations

import numpy as np
import pandas as pd

from ml.models.simulation.config import (
    CI_LOWER_PERCENTILE,
    CI_UPPER_PERCENTILE,
    MAX_GOALS_PER_MATCH,
    N_SIMULATIONS,
    POINTS_DRAW,
    POINTS_LOSS,
    POINTS_WIN,
    RANDOM_SEED,
)


def compute_league_table(match_results: list[dict]) -> pd.DataFrame:
    stats: dict[str, dict[str, int]] = {}

    for match in match_results:
        home = match["home_team"]
        away = match["away_team"]
        hg = match["home_goals"]
        ag = match["away_goals"]

        for team in (home, away):
            if team not in stats:
                stats[team] = {
                    "played": 0,
                    "won": 0,
                    "drawn": 0,
                    "lost": 0,
                    "gf": 0,
                    "ga": 0,
                }

        stats[home]["played"] += 1
        stats[away]["played"] += 1
        stats[home]["gf"] += hg
        stats[home]["ga"] += ag
        stats[away]["gf"] += ag
        stats[away]["ga"] += hg

        if hg > ag:
            stats[home]["won"] += 1
            stats[away]["lost"] += 1
        elif hg < ag:
            stats[away]["won"] += 1
            stats[home]["lost"] += 1
        else:
            stats[home]["drawn"] += 1
            stats[away]["drawn"] += 1

    rows = []
    for team, s in stats.items():
        gd = s["gf"] - s["ga"]
        pts = s["won"] * POINTS_WIN + s["drawn"] * POINTS_DRAW
        rows.append(
            {
                "team": team,
                "played": s["played"],
                "won": s["won"],
                "drawn": s["drawn"],
                "lost": s["lost"],
                "goals_for": s["gf"],
                "goals_against": s["ga"],
                "goal_difference": gd,
                "points": pts,
            }
        )

    table = pd.DataFrame(rows)
    table = table.sort_values(
        ["points", "goal_difference", "goals_for"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    table["position"] = range(1, len(table) + 1)

    return table


def simulate_season(
    actual_results: list[dict],
    remaining_fixtures: list[dict],
    lambda_home: np.ndarray,
    lambda_away: np.ndarray,
    n_simulations: int = N_SIMULATIONS,
    seed: int = RANDOM_SEED,
) -> dict:
    rng = np.random.default_rng(seed)
    n_remaining = len(remaining_fixtures)

    all_teams: set[str] = set()
    for match in actual_results:
        all_teams.add(match["home_team"])
        all_teams.add(match["away_team"])
    for fix in remaining_fixtures:
        all_teams.add(fix["home_team"])
        all_teams.add(fix["away_team"])

    team_list = sorted(all_teams)
    team_to_idx = {team: i for i, team in enumerate(team_list)}
    n_teams = len(team_list)

    actual_points = np.zeros(n_teams, dtype=int)
    actual_gf = np.zeros(n_teams, dtype=int)
    actual_ga = np.zeros(n_teams, dtype=int)
    actual_wins = np.zeros(n_teams, dtype=int)
    actual_draws = np.zeros(n_teams, dtype=int)
    actual_losses = np.zeros(n_teams, dtype=int)

    for match in actual_results:
        hi = team_to_idx[match["home_team"]]
        ai = team_to_idx[match["away_team"]]
        hg = match["home_goals"]
        ag = match["away_goals"]

        actual_gf[hi] += hg
        actual_ga[hi] += ag
        actual_gf[ai] += ag
        actual_ga[ai] += hg

        if hg > ag:
            actual_points[hi] += POINTS_WIN
            actual_wins[hi] += 1
            actual_losses[ai] += 1
        elif hg < ag:
            actual_points[ai] += POINTS_WIN
            actual_wins[ai] += 1
            actual_losses[hi] += 1
        else:
            actual_points[hi] += POINTS_DRAW
            actual_points[ai] += POINTS_DRAW
            actual_draws[hi] += 1
            actual_draws[ai] += 1

    if n_remaining == 0:
        sim_points = np.tile(actual_points, (n_simulations, 1))
        sim_gf = np.tile(actual_gf, (n_simulations, 1))
        sim_ga = np.tile(actual_ga, (n_simulations, 1))
        sim_wins = np.tile(actual_wins, (n_simulations, 1))
        sim_draws = np.tile(actual_draws, (n_simulations, 1))
        sim_losses = np.tile(actual_losses, (n_simulations, 1))
    else:
        sim_home_goals = rng.poisson(lambda_home, size=(n_simulations, n_remaining))
        sim_away_goals = rng.poisson(lambda_away, size=(n_simulations, n_remaining))
        sim_home_goals = np.minimum(sim_home_goals, MAX_GOALS_PER_MATCH)
        sim_away_goals = np.minimum(sim_away_goals, MAX_GOALS_PER_MATCH)

        fix_home_idx = np.array([team_to_idx[f["home_team"]] for f in remaining_fixtures])
        fix_away_idx = np.array([team_to_idx[f["away_team"]] for f in remaining_fixtures])

        sim_points = np.tile(actual_points, (n_simulations, 1))
        sim_gf = np.tile(actual_gf, (n_simulations, 1))
        sim_ga = np.tile(actual_ga, (n_simulations, 1))
        sim_wins = np.tile(actual_wins, (n_simulations, 1))
        sim_draws = np.tile(actual_draws, (n_simulations, 1))
        sim_losses = np.tile(actual_losses, (n_simulations, 1))

        for fix_idx in range(n_remaining):
            hi = fix_home_idx[fix_idx]
            ai = fix_away_idx[fix_idx]
            hg = sim_home_goals[:, fix_idx]
            ag = sim_away_goals[:, fix_idx]

            sim_gf[:, hi] += hg
            sim_ga[:, hi] += ag
            sim_gf[:, ai] += ag
            sim_ga[:, ai] += hg

            home_win = hg > ag
            away_win = ag > hg
            draw = hg == ag

            sim_points[:, hi] += home_win * POINTS_WIN + draw * POINTS_DRAW
            sim_points[:, ai] += away_win * POINTS_WIN + draw * POINTS_DRAW

            sim_wins[:, hi] += home_win.astype(int)
            sim_wins[:, ai] += away_win.astype(int)
            sim_draws[:, hi] += draw.astype(int)
            sim_draws[:, ai] += draw.astype(int)
            sim_losses[:, hi] += away_win.astype(int)
            sim_losses[:, ai] += home_win.astype(int)

    sim_gd = sim_gf - sim_ga

    position_counts = np.zeros((n_teams, n_teams), dtype=int)
    points_per_sim = np.zeros((n_simulations, n_teams), dtype=int)

    for sim_idx in range(n_simulations):
        pts = sim_points[sim_idx]
        gd = sim_gd[sim_idx]
        gf = sim_gf[sim_idx]

        order = np.lexsort((gf, gd, pts))[::-1]

        for pos, team_idx in enumerate(order):
            position_counts[team_idx, pos] += 1

        points_per_sim[sim_idx] = pts

    return {
        "team_list": team_list,
        "position_counts": position_counts,
        "points_per_sim": points_per_sim,
        "wins_per_sim": sim_wins,
        "draws_per_sim": sim_draws,
        "losses_per_sim": sim_losses,
        "gf_per_sim": sim_gf,
        "ga_per_sim": sim_ga,
        "n_simulations": n_simulations,
        "n_teams": n_teams,
    }


def aggregate_results(sim_output: dict) -> pd.DataFrame:
    team_list = sim_output["team_list"]
    n_sims = sim_output["n_simulations"]
    n_teams = sim_output["n_teams"]
    position_counts = sim_output["position_counts"]
    points_per_sim = sim_output["points_per_sim"]
    wins_per_sim = sim_output["wins_per_sim"]
    draws_per_sim = sim_output["draws_per_sim"]
    losses_per_sim = sim_output["losses_per_sim"]
    gf_per_sim = sim_output["gf_per_sim"]
    ga_per_sim = sim_output["ga_per_sim"]

    rows = []
    for i, team in enumerate(team_list):
        counts = position_counts[i]
        pts = points_per_sim[:, i]
        wins = wins_per_sim[:, i]
        draws = draws_per_sim[:, i]
        losses = losses_per_sim[:, i]
        goals_for = gf_per_sim[:, i]
        goals_against = ga_per_sim[:, i]

        position_probs = {
            pos + 1: int(counts[pos]) / n_sims for pos in range(n_teams)
        }

        relegation_positions = range(max(1, n_teams - 2), n_teams + 1)

        rows.append(
            {
                "team": team,
                "p_title": position_probs.get(1, 0.0),
                "p_top_4": sum(position_probs.get(p, 0.0) for p in range(1, min(4, n_teams) + 1)),
                "p_top_6": sum(position_probs.get(p, 0.0) for p in range(1, min(6, n_teams) + 1)),
                "p_relegation": sum(position_probs.get(p, 0.0) for p in relegation_positions),
                "projected_points_mean": float(pts.mean()),
                "projected_points_median": float(np.median(pts)),
                "projected_points_5th": float(np.percentile(pts, CI_LOWER_PERCENTILE)),
                "projected_points_95th": float(np.percentile(pts, CI_UPPER_PERCENTILE)),
                "modal_position": int(np.argmax(counts)) + 1,
                "position_probs": position_probs,
                "simulated_wins": float(wins.mean()),
                "simulated_draws": float(draws.mean()),
                "simulated_losses": float(losses.mean()),
                "simulated_goals_for": float(goals_for.mean()),
                "simulated_goals_against": float(goals_against.mean()),
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["projected_points_mean", "p_title", "team"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def simulate_with_locked_results(
    actual_results: list[dict],
    remaining_fixtures: list[dict],
    lambda_home: np.ndarray,
    lambda_away: np.ndarray,
    locked_results: list[dict],
    n_simulations: int = N_SIMULATIONS,
    seed: int = RANDOM_SEED,
) -> dict:
    locked_set = {
        (r["home_team"], r["away_team"]) for r in locked_results
    }

    new_actual = list(actual_results) + list(locked_results)
    new_remaining = []
    new_lambda_h = []
    new_lambda_a = []

    for i, fix in enumerate(remaining_fixtures):
        key = (fix["home_team"], fix["away_team"])
        if key not in locked_set:
            new_remaining.append(fix)
            new_lambda_h.append(lambda_home[i])
            new_lambda_a.append(lambda_away[i])

    return simulate_season(
        new_actual,
        new_remaining,
        np.array(new_lambda_h) if new_lambda_h else np.array([]),
        np.array(new_lambda_a) if new_lambda_a else np.array([]),
        n_simulations=n_simulations,
        seed=seed,
    )