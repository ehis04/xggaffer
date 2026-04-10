from __future__ import annotations

import pandas as pd

INITIAL_RATING = 1500
DEFAULT_K_FACTOR = 32
DEFAULT_HOME_ADVANTAGE = 100
SEASON_MEAN_REVERSION_WEIGHT = 0.25
PROMOTED_TEAM_OFFSET = -100
ELO_DENOMINATOR = 400
DEFAULT_DRAW_WIDTH = 0.16



def expected_score(
    home_elo: float,
    away_elo: float,
    home_advantage: float = DEFAULT_HOME_ADVANTAGE,
) -> float:
    exponent = (away_elo - home_elo - home_advantage) / ELO_DENOMINATOR
    return 1.0 / (1.0 + 10.0 ** exponent)


def actual_score(home_goals: int, away_goals: int) -> tuple[float, float]:
    if home_goals > away_goals:
        return 1.0, 0.0
    if home_goals < away_goals:
        return 0.0, 1.0
    return 0.5, 0.5


def update_ratings(
    home_elo: float,
    away_elo: float,
    home_goals: int,
    away_goals: int,
    k_factor: float = DEFAULT_K_FACTOR,
    home_advantage: float = DEFAULT_HOME_ADVANTAGE,
) -> tuple[float, float]:
    exp_home = expected_score(home_elo, away_elo, home_advantage)
    exp_away = 1.0 - exp_home
    act_home, act_away = actual_score(home_goals, away_goals)

    new_home = home_elo + k_factor * (act_home - exp_home)
    new_away = away_elo + k_factor * (act_away - exp_away)

    return new_home, new_away



def apply_season_reset(
    ratings: dict[str, float],
    league_mean: float | None = None,
) -> dict[str, float]:
    if not ratings:
        return {}
    if league_mean is None:
        league_mean = sum(ratings.values()) / len(ratings)
    weight = SEASON_MEAN_REVERSION_WEIGHT
    return {
        team: elo * (1 - weight) + league_mean * weight
        for team, elo in ratings.items()
    }



def _get_league_mean(
    ratings: dict[str, float],
    league_teams: set[str],
) -> float:
    league_ratings = [ratings[t] for t in league_teams if t in ratings]
    if not league_ratings:
        return INITIAL_RATING
    return sum(league_ratings) / len(league_ratings)


def _resolve_team_rating(
    team: str,
    league: str,
    ratings: dict[str, float],
    league_teams: dict[str, set[str]],
) -> float:
    if team in ratings:
        return ratings[team]

    current_league_teams = league_teams.get(league, set())
    league_ratings = [ratings[t] for t in current_league_teams if t in ratings]

    if league_ratings:
        return sum(league_ratings) / len(league_ratings) + PROMOTED_TEAM_OFFSET

    return INITIAL_RATING


def compute_elo_history(
    matches_df: pd.DataFrame,
    k_factor: float = DEFAULT_K_FACTOR,
    home_advantage: float = DEFAULT_HOME_ADVANTAGE,
) -> tuple[list[dict], dict[str, float]]:
    matches = matches_df.sort_values("date").reset_index(drop=True)

    ratings: dict[str, float] = {}
    league_teams: dict[str, set[str]] = {}
    current_season: dict[str, str] = {}
    history: list[dict] = []

    for row in matches.itertuples(index=False):
        league = row.league
        season = str(row.season)
        home_team = row.home_team
        away_team = row.away_team

        if league in current_season and current_season[league] != season:
            teams_to_reset = league_teams.get(league, set())
            if teams_to_reset:
                league_mean = _get_league_mean(ratings, teams_to_reset)
                weight = SEASON_MEAN_REVERSION_WEIGHT
                for team in teams_to_reset:
                    if team in ratings:
                        ratings[team] = ratings[team] * (1 - weight) + league_mean * weight

        current_season[league] = season

        if league not in league_teams:
            league_teams[league] = set()

        home_elo_before = _resolve_team_rating(home_team, league, ratings, league_teams)
        away_elo_before = _resolve_team_rating(away_team, league, ratings, league_teams)

        ratings[home_team] = home_elo_before
        ratings[away_team] = away_elo_before
        league_teams[league].add(home_team)
        league_teams[league].add(away_team)

        exp_home = expected_score(home_elo_before, away_elo_before, home_advantage)
        exp_away = 1.0 - exp_home
        act_home, act_away = actual_score(row.home_goals, row.away_goals)

        home_elo_after, away_elo_after = update_ratings(
            home_elo_before, away_elo_before,
            row.home_goals, row.away_goals,
            k_factor, home_advantage,
        )

        ratings[home_team] = home_elo_after
        ratings[away_team] = away_elo_after

        home_elo_before_r = round(home_elo_before, 2)
        away_elo_before_r = round(away_elo_before, 2)

        history.append({
            "match_id": row.match_id,
            "date": row.date,
            "home_team": home_team,
            "away_team": away_team,
            "league": league,
            "season": season,
            "home_elo_before": home_elo_before_r,
            "away_elo_before": away_elo_before_r,
            "home_elo_after": round(home_elo_after, 2),
            "away_elo_after": round(away_elo_after, 2),
            "elo_difference": round(home_elo_before_r - away_elo_before_r, 2),
            "expected_home": round(exp_home, 4),
            "expected_away": round(exp_away, 4),
            "actual_home": act_home,
            "actual_away": act_away,
        })

    return history, ratings



def elo_to_probabilities(
    home_elo: float,
    away_elo: float,
    home_advantage: float = DEFAULT_HOME_ADVANTAGE,
    draw_width: float = DEFAULT_DRAW_WIDTH,
) -> dict[str, float]:
    exp_home = expected_score(home_elo, away_elo, home_advantage)
    exp_away = 1.0 - exp_home

    p_draw = draw_width * (1.0 - abs(exp_home - exp_away))
    p_home = exp_home * (1.0 - p_draw)
    p_away = exp_away * (1.0 - p_draw)

    return {"H": p_home, "D": p_draw, "A": p_away}



def get_elo_at_date(
    elo_history_df: pd.DataFrame,
    team: str,
    date: pd.Timestamp,
) -> float:
    team_rows = elo_history_df[
        (elo_history_df["home_team"] == team) | (elo_history_df["away_team"] == team)
    ]
    before_date = team_rows[team_rows["date"] < date]

    if before_date.empty:
        return float(INITIAL_RATING)

    last_row = before_date.iloc[-1]
    if last_row["home_team"] == team:
        return float(last_row["home_elo_after"])
    return float(last_row["away_elo_after"])



def save_elo_history(history_df: pd.DataFrame, path: str | pd.io.common.PathLike) -> None:
    history_df.to_csv(path, index=False)


def load_elo_history(path: str | pd.io.common.PathLike) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["date"])