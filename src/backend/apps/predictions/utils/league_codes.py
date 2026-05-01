from __future__ import annotations

COMPETITION_TO_UNDERSTAT: dict[str, str] = {
    "PL":  "EPL",
    "PD":  "La_Liga",
    "BL1": "Bundesliga",
    "SA":  "Serie_A",
    "FL1": "Ligue_1",
}

UNDERSTAT_TO_COMPETITION: dict[str, str] = {
    v: k for k, v in COMPETITION_TO_UNDERSTAT.items()
}


def to_understat_code(competition_code: str) -> str | None:
    return COMPETITION_TO_UNDERSTAT.get(competition_code.upper())


def to_competition_code(understat_code: str) -> str | None:
    return UNDERSTAT_TO_COMPETITION.get(understat_code)