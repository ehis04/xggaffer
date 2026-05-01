from __future__ import annotations

import re

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

    def _rule_based_intent(self, raw_query: str) -> tuple[IntentClass | None, float]:
        q = raw_query.lower()

        if re.search(r"\b(what is|define|meaning of|explain)\b", q) and re.search(
            r"\b(xg|xga|xa|npxg|npxga|ppda|oppda|xpts|expected goals|expected assists|expected points|key passes)\b",
            q,
        ):
            return IntentClass.GLOSSARY, 0.99

        if any(term in q for term in ("odds", "bookmaker", "market price", "market edge")):
            return IntentClass.ODDS_COMPARISON, 0.96

        if any(term in q for term in ("full analysis", "complete analysis", "breakdown", "everything")):
            return IntentClass.COMPOSITE_MATCH, 0.9

        if re.search(r"\b(scoreline|final score|exact score|how many goals|goal forecast|predicted score)\b", q):
            return IntentClass.SCORE_PREDICTION, 0.94

        if re.search(r"\b(head to head|h2h|meetings|history between)\b", q):
            return IntentClass.HEAD_TO_HEAD, 0.94

        if re.search(r"\b(table|standings|top 4|top four|relegation zone|league position)\b", q):
            return IntentClass.TEAM_RANKINGS, 0.93

        if re.search(r"\b(title race|who wins the league|season simulation|simulate|projected table|expected points|xpts projection|relegated|top 4 chances|top four chances)\b", q):
            return IntentClass.SEASON_SIMULATION, 0.92

        if re.search(r"\bwho wins\b", q) and re.search(
            r"\b(premier league|epl|la liga|laliga|bundesliga|serie a|ligue 1)\b",
            q,
        ):
            if len(self._extractor.extract_teams(raw_query)) < 2:
                return IntentClass.SEASON_SIMULATION, 0.9

        if re.search(r"\b(lineup|line-up|starting xi|predicted xi|who starts|starting eleven)\b", q):
            return IntentClass.LINEUP_PREDICTION, 0.94

        if re.search(r"\b(injury|injured|fit|fitness|available|availability|doubtful|out for)\b", q):
            return IntentClass.AVAILABILITY_QUERY, 0.94

        if re.search(r"\b(tactic|tactics|style of play|pressing style|play style|formation style)\b", q):
            return IntentClass.TACTICAL_QUERY, 0.92

        if re.search(r"\b(elo|strength rating|power rating|power index|team strength)\b", q):
            return IntentClass.ELO_QUERY, 0.95

        if re.search(r"\b(rest|congestion|fixture density|schedule load|match frequency)\b", q):
            return IntentClass.REST_DAYS, 0.92

        if re.search(r"\b(form|performed|performing|record|win rate|xg trend|home record|away record)\b", q):
            return IntentClass.FORM_ANALYSIS, 0.91

        if re.search(r"\b(stats|goals|assists|saves|save percentage|performance|xg)\b", q):
            teams = self._extractor.extract_teams(raw_query)
            if len(teams) < 2:
                return IntentClass.PLAYER_STATS, 0.85
            return IntentClass.STAT_COMPARISON, 0.88

        if re.search(r"\b(who wins|predict|prediction|expected result|favoured|favored|beat|takes the three points|outcome|result)\b", q):
            return IntentClass.MATCH_PREDICTION, 0.9

        return None, 0.0

    def route(self, raw_query: str) -> ParsedQuery:
        intent, confidence = self._rule_based_intent(raw_query)
        if intent is None:
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
