from __future__ import annotations

import dataclasses
import enum


class IntentClass(str, enum.Enum):
    MATCH_PREDICTION = "MATCH_PREDICTION"
    SCORE_PREDICTION = "SCORE_PREDICTION"
    SEASON_SIMULATION = "SEASON_SIMULATION"
    ELO_QUERY = "ELO_QUERY"
    AVAILABILITY_QUERY = "AVAILABILITY_QUERY"
    LINEUP_PREDICTION = "LINEUP_PREDICTION"
    TACTICAL_QUERY = "TACTICAL_QUERY"
    COMPOSITE_MATCH = "COMPOSITE_MATCH"
    STAT_COMPARISON = "STAT_COMPARISON"
    GLOSSARY = "GLOSSARY"
    UNKNOWN = "UNKNOWN"


@dataclasses.dataclass
class ParsedQuery:
    intent: IntentClass
    home_team: str | None
    away_team: str | None
    team: str | None
    player_name: str | None
    league: str | None
    season: str | None
    confidence: float
    raw_query: str
    error_code: str | None = None