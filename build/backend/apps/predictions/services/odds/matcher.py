from __future__ import annotations

import logging

from apps.predictions.data_collection.config.team_name_mappings import (
    CANONICAL_TEAM_NAMES,
    SUPPORTED_SOURCES,
    to_canonical,
)
from apps.predictions.services.odds.exceptions import OddsMatchingError

_logger = logging.getLogger(__name__)

THE_ODDS_API_SOURCE = "the_odds_api"


def _validate_source_name(source_name: str) -> str:
    if source_name == THE_ODDS_API_SOURCE:
        return source_name

    if source_name in SUPPORTED_SOURCES:
        return source_name

    raise OddsMatchingError(f"Unsupported odds source '{source_name}'.")


def _match_the_odds_api_team_name(source_team_name: str) -> str:
    if source_team_name in CANONICAL_TEAM_NAMES:
        return source_team_name

    exact_matches: list[str] = []

    for canonical_name, mapped_names in CANONICAL_TEAM_NAMES.items():
        if source_team_name in mapped_names.values():
            exact_matches.append(canonical_name)

    if len(exact_matches) == 1:
        return exact_matches[0]

    if len(exact_matches) > 1:
        _logger.warning(
            "Ambiguous The Odds API team name mapping.",
            extra={
                "source_name": THE_ODDS_API_SOURCE,
                "source_team_name": source_team_name,
                "candidate_matches": exact_matches,
            },
        )
        raise OddsMatchingError(
            f"Ambiguous team mapping for '{source_team_name}' from source "
            f"'{THE_ODDS_API_SOURCE}'."
        )

    _logger.warning(
        "Unmapped The Odds API team name: %r",
        source_team_name,
        extra={
            "source_name": THE_ODDS_API_SOURCE,
            "source_team_name": source_team_name,
        },
    )
    raise OddsMatchingError(
        f"Could not map team '{source_team_name}' from source "
        f"'{THE_ODDS_API_SOURCE}'."
    )


def to_canonical_team_name(source_team_name: str, source_name: str) -> str:
    validated_source_name = _validate_source_name(source_name)

    if validated_source_name == THE_ODDS_API_SOURCE:
        return _match_the_odds_api_team_name(source_team_name)

    try:
        return to_canonical(source_team_name, validated_source_name)
    except KeyError as exc:
        _logger.warning(
            "Unmapped team name for supported source.",
            extra={
                "source_name": validated_source_name,
                "source_team_name": source_team_name,
            },
        )
        raise OddsMatchingError(
            f"Could not map team '{source_team_name}' from source "
            f"'{validated_source_name}'."
        ) from exc


def match_fixture_names(
    home_team: str,
    away_team: str,
    source_name: str,
) -> dict[str, str]:
    canonical_home_team = to_canonical_team_name(home_team, source_name)
    canonical_away_team = to_canonical_team_name(away_team, source_name)

    return {
        "home_team": canonical_home_team,
        "away_team": canonical_away_team,
        "source_home_team": home_team,
        "source_away_team": away_team,
        "source_name": source_name,
    }