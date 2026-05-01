from __future__ import annotations

from apps.predictions.ml.models.match_outcome.config import DEFAULT_TOP_FACTORS
from apps.predictions.ml.models.match_outcome.interpret import explain_match


def build_match_prediction_payload(
    home_team: str,
    away_team: str,
    league: str,
    season: str,
    top_n: int = DEFAULT_TOP_FACTORS,
) -> dict:
    result = explain_match(
        home_team=home_team,
        away_team=away_team,
        league=league,
        season=season,
        top_n=top_n,
    )

    return {
        "home_team": home_team,
        "away_team": away_team,
        "league": league,
        "season": season,
        "prediction": result["prediction"],
        "probabilities": result["probabilities"],
        "top_factors": result["top_factors"],
        "metrics": result["metrics"],
        "model_type": result["model_type"],
        "version": result["version"],
        "contract_version": result.get("contract_version"),
    }