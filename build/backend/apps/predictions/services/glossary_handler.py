from __future__ import annotations

from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery

GLOSSARY: dict[str, str] = {
    "xg": (
        "Expected Goals (xG) measures the quality of a shot based on several variables "
        "such as assist type, shot angle, distance from goal, and whether it was a headed "
        "shot. A value of 0.5 means that shot would be expected to result in a goal 50% "
        "of the time."
    ),
    "xga": (
        "Expected Goals Against (xGA) is the xG total conceded by a team. "
        "Lower is better for defences."
    ),
    "xa": (
        "Expected Assists (xA) measures the likelihood that a given pass will result in a "
        "goal. It credits the passer for the quality of the chance created."
    ),
    "npxg": (
        "Non-Penalty Expected Goals (npxG) excludes penalty kicks from the xG calculation, "
        "giving a cleaner picture of open-play attacking threat."
    ),
    "npxga": (
        "Non-Penalty Expected Goals Against (npxGA) excludes penalties from the defensive "
        "xG conceded metric."
    ),
    "ppda": (
        "Passes Per Defensive Action (PPDA) measures pressing intensity. Lower values "
        "indicate a team presses higher up the pitch more aggressively."
    ),
    "oppda": (
        "Opponent Passes Per Defensive Action (OPPDA) measures how much the opposition "
        "is allowed to pass before being pressed."
    ),
    "deep": (
        "Deep Completions are passes completed within 20 metres of the opponent's goal. "
        "A proxy for how often a team creates dangerous positions."
    ),
    "xpts": (
        "Expected Points (xPts) is the number of points a team would be expected to earn "
        "based on the xG of the chances created and conceded across their matches."
    ),
    "key passes": (
        "Key Passes are passes that directly lead to a shot on goal."
    ),
    "xg chain": (
        "xG Chain is the total xG of all moves a player was involved in, including "
        "dribbles and passes, not just shots."
    ),
    "xg buildup": (
        "xG Buildup is the xG of all moves a player was involved in excluding the "
        "key pass and shot itself."
    ),
    "shots on target": (
        "Shots on Target are shots that would have gone in if not saved by the goalkeeper "
        "or blocked on the line."
    ),
}

TERM_ALIASES: dict[str, str] = {
    "expected goals": "xg",
    "expected assists": "xa",
    "non-penalty": "npxg",
    "pressing": "ppda",
    "deep completions": "deep",
    "expected points": "xpts",
}


class GlossaryHandler(EngineHandler):
    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        query_lower = parsed_query.raw_query.lower()
        matched_term = None
        matched_definition = None

        for alias, canonical in TERM_ALIASES.items():
            if alias in query_lower:
                matched_term = canonical
                matched_definition = GLOSSARY.get(canonical)
                break

        if matched_term is None:
            for term, definition in GLOSSARY.items():
                if term in query_lower:
                    matched_term = term
                    matched_definition = definition
                    break

        if matched_term is None:
            return QueryPayload(
                intent=IntentClass.GLOSSARY,
                engine_data={"all_terms": list(GLOSSARY.keys())},
                partial=True,
                error="Term not recognised. Available terms listed.",
            )

        return QueryPayload(
            intent=IntentClass.GLOSSARY,
            engine_data={"term": matched_term, "definition": matched_definition},
            partial=False,
            error=None,
        )