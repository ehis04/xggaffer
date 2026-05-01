from __future__ import annotations

import numpy as np
import pandas as pd


MIN_VALID_ODDS = 1.01
MAX_VALID_ODDS = 501.0


def devig_single(home_odds: float, draw_odds: float, away_odds: float) -> tuple[float, float, float]:
    implied_home = 1.0 / home_odds
    implied_draw = 1.0 / draw_odds
    implied_away = 1.0 / away_odds
    total = implied_home + implied_draw + implied_away

    return (
        implied_home / total,
        implied_draw / total,
        implied_away / total,
    )


def devig_columns(
    df: pd.DataFrame,
    home_col: str,
    draw_col: str,
    away_col: str,
) -> pd.DataFrame:
    implied_home = 1.0 / df[home_col]
    implied_draw = 1.0 / df[draw_col]
    implied_away = 1.0 / df[away_col]
    total = implied_home + implied_draw + implied_away

    result = pd.DataFrame({
        "market_home_prob": implied_home / total,
        "market_draw_prob": implied_draw / total,
        "market_away_prob": implied_away / total,
        "overround": total,
    }, index=df.index)

    return result


def validate_odds(home_odds: float, draw_odds: float, away_odds: float) -> bool:
    for odds in (home_odds, draw_odds, away_odds):
        if not np.isfinite(odds):
            return False
        if odds < MIN_VALID_ODDS or odds > MAX_VALID_ODDS:
            return False
    return True