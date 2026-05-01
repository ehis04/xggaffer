from __future__ import annotations

import pytest

from apps.predictions.services.intent_types import IntentClass
from apps.predictions.services.query_router import QueryRouter


@pytest.fixture(scope="module")
def router() -> QueryRouter:
    return QueryRouter()


def test_match_prediction_two_teams(router: QueryRouter) -> None:
    result = router.route("who wins Arsenal vs Chelsea")
    assert result.intent == IntentClass.MATCH_PREDICTION
    assert result.home_team == "Arsenal"
    assert result.away_team == "Chelsea"


def test_match_prediction_requires_two_teams(router: QueryRouter) -> None:
    result = router.route("who wins Arsenal")
    assert result.intent == IntentClass.UNKNOWN
    assert result.error_code == "insufficient_teams"


def test_glossary_xg(router: QueryRouter) -> None:
    result = router.route("what is xG")
    assert result.intent == IntentClass.GLOSSARY


def test_season_simulation_defaults_epl(router: QueryRouter) -> None:
    result = router.route("who wins the league this season")
    assert result.intent == IntentClass.SEASON_SIMULATION
    assert result.league == "EPL"


def test_season_simulation_explicit_league(router: QueryRouter) -> None:
    result = router.route("who wins la liga")
    assert result.intent == IntentClass.SEASON_SIMULATION
    assert result.league == "La_Liga"


def test_season_extraction(router: QueryRouter) -> None:
    result = router.route("EPL 2022 title race")
    assert result.season == "2022"


def test_current_season_uses_latest_data_season(router: QueryRouter) -> None:
    result = router.route("who wins the league this season")
    assert result.season == "2025"


def test_slash_season_extraction(router: QueryRouter) -> None:
    result = router.route("EPL table 2025/26")
    assert result.intent == IntentClass.TEAM_RANKINGS
    assert result.season == "2025"


def test_short_slash_season_extraction(router: QueryRouter) -> None:
    result = router.route("Salah stats 25/26")
    assert result.intent == IntentClass.PLAYER_STATS
    assert result.season == "2025"


def test_common_team_aliases(router: QueryRouter) -> None:
    result = router.route("who wins Man U vs Liv this season")
    assert result.intent == IntentClass.MATCH_PREDICTION
    assert result.home_team == "Manchester United"
    assert result.away_team == "Liverpool"


def test_spurs_alias(router: QueryRouter) -> None:
    result = router.route("who wins Spurs v Arsenal")
    assert result.intent == IntentClass.MATCH_PREDICTION
    assert result.home_team in {"Tottenham Hotspur", "Tottenham"}
    assert result.away_team == "Arsenal"


def test_team_performance_routes_to_form(router: QueryRouter) -> None:
    result = router.route("how has Liverpool performed this season")
    assert result.intent == IntentClass.FORM_ANALYSIS
    assert result.team == "Liverpool"


def test_elo_query_single_team(router: QueryRouter) -> None:
    result = router.route("what is Arsenal elo rating")
    assert result.intent == IntentClass.ELO_QUERY
    assert result.team == "Arsenal"


def test_elo_query_no_team_returns_unknown(router: QueryRouter) -> None:
    result = router.route("what is the elo rating")
    assert result.intent == IntentClass.UNKNOWN


def test_availability_with_team(router: QueryRouter) -> None:
    result = router.route("injury risk Arsenal squad")
    assert result.intent == IntentClass.AVAILABILITY_QUERY
    assert result.team == "Arsenal"


def test_lineup_prediction(router: QueryRouter) -> None:
    result = router.route("what lineup will Arsenal use")
    assert result.intent == IntentClass.LINEUP_PREDICTION
    assert result.team == "Arsenal"


def test_tactical_single_team(router: QueryRouter) -> None:
    result = router.route("what is Arsenal style of play")
    assert result.intent == IntentClass.TACTICAL_QUERY
    assert result.team == "Arsenal"


def test_tactical_two_teams(router: QueryRouter) -> None:
    result = router.route("compare Arsenal and Chelsea tactics")
    assert result.intent == IntentClass.TACTICAL_QUERY
    assert result.home_team == "Arsenal"
    assert result.away_team == "Chelsea"


def test_composite_match(router: QueryRouter) -> None:
    result = router.route("full analysis Arsenal vs Chelsea")
    assert result.intent == IntentClass.COMPOSITE_MATCH
    assert result.home_team == "Arsenal"
    assert result.away_team == "Chelsea"


def test_unknown_gibberish(router: QueryRouter) -> None:
    result = router.route("asdfgh qwerty xyz")
    assert result.intent == IntentClass.UNKNOWN


def test_raw_query_preserved(router: QueryRouter) -> None:
    q = "who wins Arsenal vs Chelsea"
    result = router.route(q)
    assert result.raw_query == q


def test_confidence_is_float(router: QueryRouter) -> None:
    result = router.route("who wins Arsenal vs Chelsea")
    assert isinstance(result.confidence, float)
    assert 0.0 <= result.confidence <= 1.0

def test_odds_comparison_routes_with_two_teams(router: QueryRouter) -> None:
    result = router.route("compare Arsenal vs Chelsea with bookmaker odds")
    assert result.intent == IntentClass.ODDS_COMPARISON
    assert result.home_team == "Arsenal"
    assert result.away_team == "Chelsea"


def test_odds_comparison_requires_two_teams(router: QueryRouter) -> None:
    result = router.route("show me bookmaker odds for Arsenal")
    assert result.intent == IntentClass.UNKNOWN
    assert result.error_code == "insufficient_teams"


def test_odds_comparison_preserves_league_and_season(router: QueryRouter) -> None:
    result = router.route("compare Arsenal vs Chelsea with bookmaker odds in EPL 2022")
    assert result.intent == IntentClass.ODDS_COMPARISON
    assert result.home_team == "Arsenal"
    assert result.away_team == "Chelsea"
    assert result.league == "EPL"
    assert result.season == "2022"
