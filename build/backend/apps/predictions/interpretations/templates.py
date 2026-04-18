from __future__ import annotations


def pct(value: float) -> str:
    return f"{round(float(value) * 100)}%"


def ordinal(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def expected_title_headline(team: str, league: str, probability: float) -> str:
    return f"The model predicts {team} to win the {league} title with a {pct(probability)} probability."


def expected_settled_title_headline(team: str, league: str) -> str:
    return (
        f"No fixtures remain to simulate, so {team} finish top of the {league} "
        "in the model’s settled table."
    )


def expected_confident_team(team: str, position: int, confidence: float) -> str:
    return f"{team} look relatively settled in {ordinal(position)} place, with a {pct(confidence)} chance of finishing there."


def expected_uncertain_team(team: str, position: int, confidence: float) -> str:
    return f"{team} are harder to pin down: the model has them most likely in {ordinal(position)}, but only with {pct(confidence)} confidence."


def expected_title_race(team_a: str, prob_a: float, team_b: str, prob_b: float) -> str:
    return (
        f"The title race still looks open between {team_a} ({pct(prob_a)}) "
        f"and {team_b} ({pct(prob_b)})."
    )


def expected_relegation_warning(team: str, probability: float) -> str:
    return f"{team} carry the heaviest relegation risk in the model at {pct(probability)}."


def expected_mode_caveat(
    mode: str,
    matchweek: int | None = None,
    remaining_fixtures: int | None = None,
) -> str:
    if remaining_fixtures == 0 and mode == "current_expected":
        return (
            "No remaining fixtures were left to simulate, so this table reflects a settled "
            "season state rather than an open projection."
        )
    if mode == "pre_season":
        return (
            "This is a pre-season projection built without using any matches from the target season."
        )
    if mode == "as_of_matchweek":
        if matchweek is None:
            return (
                "This projection is frozen to a historical matchweek, using only data available at that point in the season."
            )
        return (
            f"This projection is frozen to matchweek {matchweek}, using only data available at that point in the season."
        )
    return (
        "This is a current-expected projection using the season state available up to the current cut-off."
    )


def expected_accuracy_caveat(simulation_count: int | None) -> str:
    if simulation_count is None:
        return (
            "These outputs are probabilistic model estimates rather than guarantees, and should be read as ranges of likelihood."
        )
    return (
        f"These outputs come from a deterministic Monte Carlo workflow with {simulation_count} simulations and should be treated as probabilities, not certainties."
    )


def comparison_headline(team: str, actual_position: int, expected_position: int) -> str:
    delta = expected_position - actual_position
    return (
        f"{team} are outperforming the model by {abs(delta)} places, currently sitting {ordinal(actual_position)} instead of the projected {ordinal(expected_position)}."
    )


def comparison_underperformer(team: str, actual_position: int, expected_position: int) -> str:
    delta = actual_position - expected_position
    return (
        f"{team} are underperforming relative to the model by {abs(delta)} places, currently {ordinal(actual_position)} versus an expected {ordinal(expected_position)}."
    )


def comparison_points_gap(team: str, actual_points: float, expected_points: float) -> str:
    diff = actual_points - expected_points
    direction = "ahead of" if diff > 0 else "behind"
    return (
        f"{team} are {abs(round(diff, 1))} points {direction} their projected total."
    )


def comparison_alignment(team: str) -> str:
    return f"The model and the live table are broadly aligned at the top with {team} leading both views."


def comparison_full_alignment() -> str:
    return "The model and the final table are fully aligned across the league."


def comparison_mode_caveat(mode: str, remaining_fixtures: int | None = None) -> str:
    if remaining_fixtures == 0 and mode == "current_expected":
        return (
            "This comparison uses the final season state, so the remaining differences show "
            "how closely the model tracked the finished table."
        )
    if mode == "pre_season":
        return "The comparison uses a pre-season projection as the expectation baseline."
    if mode == "as_of_matchweek":
        return "The comparison uses a historical as-of-matchweek projection as the expectation baseline."
    return "The comparison uses the current-expected projection as the expectation baseline."


def comparison_generic_caveat() -> str:
    return (
        "Position deltas highlight where reality has diverged from expectation, but they do not by themselves explain why that divergence happened."
    )