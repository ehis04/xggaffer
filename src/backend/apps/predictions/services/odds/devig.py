from __future__ import annotations

import math

from apps.predictions.services.odds.exceptions import OddsDataUnavailableError


def validate_quote_odds(home_odds: float, draw_odds: float, away_odds: float) -> bool:
    odds = (home_odds, draw_odds, away_odds)
    if any(not isinstance(value, (int, float)) for value in odds):
        return False
    if any(not math.isfinite(float(value)) for value in odds):
        return False
    # Decimal odds at or below 1 imply zero/negative payout and cannot be de-vigged.
    return all(float(value) > 1.0 for value in odds)


def compute_implied_probabilities(
    home_odds: float,
    draw_odds: float,
    away_odds: float,
) -> tuple[float, float, float]:
    return (
        1.0 / home_odds,
        1.0 / draw_odds,
        1.0 / away_odds,
    )


def compute_overround(home_odds: float, draw_odds: float, away_odds: float) -> float:
    implied_home, implied_draw, implied_away = compute_implied_probabilities(
        home_odds,
        draw_odds,
        away_odds,
    )
    return implied_home + implied_draw + implied_away


def devig_probabilities(
    home_odds: float,
    draw_odds: float,
    away_odds: float,
) -> tuple[float, float, float]:
    if not validate_quote_odds(home_odds, draw_odds, away_odds):
        raise OddsDataUnavailableError("Invalid 1X2 odds supplied for de-vigging.")

    implied_home, implied_draw, implied_away = compute_implied_probabilities(
        home_odds,
        draw_odds,
        away_odds,
    )
    overround = implied_home + implied_draw + implied_away
    return (
        implied_home / overround,
        implied_draw / overround,
        implied_away / overround,
    )


def devig_quote_dict(quote: dict) -> dict:
    required_keys = (
        "home_odds",
        "draw_odds",
        "away_odds",
    )

    missing_keys = [key for key in required_keys if key not in quote]
    if missing_keys:
        missing_keys_display = ", ".join(missing_keys)
        raise OddsDataUnavailableError(
            f"Quote is missing required odds fields: {missing_keys_display}."
        )

    home_odds = quote["home_odds"]
    draw_odds = quote["draw_odds"]
    away_odds = quote["away_odds"]

    if not validate_quote_odds(home_odds, draw_odds, away_odds):
        raise OddsDataUnavailableError("Quote contains invalid 1X2 odds.")

    implied_home, implied_draw, implied_away = compute_implied_probabilities(
        home_odds,
        draw_odds,
        away_odds,
    )
    devig_home, devig_draw, devig_away = devig_probabilities(
        home_odds,
        draw_odds,
        away_odds,
    )

    return {
        **quote,
        "implied_home": implied_home,
        "implied_draw": implied_draw,
        "implied_away": implied_away,
        "devig_home": devig_home,
        "devig_draw": devig_draw,
        "devig_away": devig_away,
        "overround": compute_overround(home_odds, draw_odds, away_odds),
    }