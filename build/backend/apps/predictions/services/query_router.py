from __future__ import annotations

from apps.predictions.services.intent_types import IntentClass, ParsedQuery
from apps.predictions.services.intent_classifier import get_classifier
from apps.predictions.services.entity_extractor import EntityExtractor

TWO_TEAM_INTENTS: frozenset[IntentClass] = frozenset({
    IntentClass.MATCH_PREDICTION,
    IntentClass.SCORE_PREDICTION,
    IntentClass.COMPOSITE_MATCH,
    IntentClass.STAT_COMPARISON,
    IntentClass.HEAD_TO_HEAD,
    IntentClass.ODDS_COMPARISON,
})

SINGLE_TEAM_INTENTS: frozenset[IntentClass] = frozenset({
    IntentClass.FORM_ANALYSIS,
    IntentClass.REST_DAYS,
})

DEFAULT_LEAGUE = "EPL"


class QueryRouter:
    def __init__(self) -> None:
        self._classifier = get_classifier()
        self._extractor = EntityExtractor()

    def route(self, raw_query: str) -> ParsedQuery:
        intent, confidence = self._classifier.classify(raw_query)
        entities = self._extractor.extract(raw_query, intent)

        error_code: str | None = None

        home_team = entities.get("home_team")
        away_team = entities.get("away_team")
        team = entities.get("team")
        player_name = entities.get("player_name")
        league = entities.get("league")
        season = entities.get("season")

        if intent in TWO_TEAM_INTENTS:
            if not home_team or not away_team:
                intent = IntentClass.UNKNOWN
                error_code = "insufficient_teams"

        elif intent == IntentClass.SEASON_SIMULATION:
            if not league:
                league = DEFAULT_LEAGUE

        elif intent == IntentClass.AVAILABILITY_QUERY:
            if not player_name and not team:
                intent = IntentClass.UNKNOWN
                error_code = "insufficient_entities"

        elif intent == IntentClass.ELO_QUERY:
            if not team:
                intent = IntentClass.UNKNOWN
                error_code = "insufficient_entities"

        elif intent == IntentClass.LINEUP_PREDICTION:
            if not team:
                intent = IntentClass.UNKNOWN
                error_code = "insufficient_entities"

        elif intent == IntentClass.TEAM_RANKINGS:
            if not league:
                league = DEFAULT_LEAGUE

        elif intent in SINGLE_TEAM_INTENTS:
            if not team and not home_team:
                intent = IntentClass.UNKNOWN
                error_code = "insufficient_entities"

        elif intent == IntentClass.PLAYER_STATS:
            if not player_name:
                intent = IntentClass.UNKNOWN
                error_code = "insufficient_entities"

        return ParsedQuery(
            intent=intent,
            home_team=home_team,
            away_team=away_team,
            team=team,
            player_name=player_name,
            league=league,
            season=season,
            confidence=confidence,
            raw_query=raw_query,
            error_code=error_code,
        )