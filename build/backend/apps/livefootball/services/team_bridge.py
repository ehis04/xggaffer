from __future__ import annotations

import unicodedata
from typing import Iterable

from apps.livefootball.models import Competition, TeamDirectoryEntry
from data_collection.config.league_name_mappings import to_canonical as league_to_canonical
from data_collection.config.team_name_mappings import CANONICAL_TEAM_NAMES

from .exceptions import TeamMappingNotFoundError


TEAM_NAME_SOURCES = (
    "understat",
    "football_data_org",
    "football_data_co_uk",
    "sofascore",
)


def _normalise_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(value.casefold().strip().split())


def _build_alias_indexes() -> tuple[dict[str, str], dict[str, str]]:
    exact_index: dict[str, str] = {}
    normalised_index: dict[str, str] = {}

    for canonical_name, source_names in CANONICAL_TEAM_NAMES.items():
        aliases: list[str] = [canonical_name]

        for source in TEAM_NAME_SOURCES:
            alias = source_names.get(source)
            if alias:
                aliases.append(alias)

        for alias in aliases:
            cleaned = alias.strip()
            if not cleaned:
                continue

            exact_index.setdefault(cleaned, canonical_name)
            normalised_index.setdefault(_normalise_text(cleaned), canonical_name)

    return exact_index, normalised_index


_EXACT_ALIAS_INDEX, _NORMALISED_ALIAS_INDEX = _build_alias_indexes()


def _candidate_values(
    team_name: str,
    short_name: str | None = None,
    tla: str | None = None,
) -> list[str]:
    raw_candidates = [team_name, short_name or "", tla or ""]
    seen: set[str] = set()
    ordered: list[str] = []

    for value in raw_candidates:
        cleaned = value.strip()
        if not cleaned:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        ordered.append(cleaned)

    return ordered


def resolve_understat_team_name(
    team_name: str,
    *,
    short_name: str | None = None,
    tla: str | None = None,
) -> str:
    candidates = _candidate_values(team_name, short_name=short_name, tla=tla)

    for candidate in candidates:
        canonical = _EXACT_ALIAS_INDEX.get(candidate)
        if canonical:
            return canonical

    for candidate in candidates:
        canonical = _NORMALISED_ALIAS_INDEX.get(_normalise_text(candidate))
        if canonical:
            return canonical

    raise TeamMappingNotFoundError(
        team_name=team_name,
        short_name=short_name,
        tla=tla,
    )


def resolve_understat_team_name_for_entry(team: TeamDirectoryEntry) -> str:
    return resolve_understat_team_name(
        team.name,
        short_name=team.short_name,
        tla=team.tla,
    )


def _resolve_competition(competition: int | Competition) -> Competition:
    if isinstance(competition, Competition):
        return competition

    return Competition.objects.get(pk=competition)


def get_understat_league_code(competition: int | Competition) -> str:
    competition_obj = _resolve_competition(competition)

    if not competition_obj.code:
        raise ValueError(
            f"Competition {competition_obj.id} has no code, so it cannot be mapped to an Understat league."
        )

    try:
        return league_to_canonical(competition_obj.code, "football_data_org")
    except KeyError as exc:
        raise ValueError(
            f"Competition code '{competition_obj.code}' could not be mapped to an Understat league."
        ) from exc


def get_competition_team_bridge(
    competition: int | Competition,
    *,
    season_label: str | None = None,
) -> dict[int, str]:
    competition_obj = _resolve_competition(competition)
    resolved_season = (season_label or competition_obj.current_season_label or "").strip()

    if not resolved_season:
        raise ValueError(
            f"Competition {competition_obj.id} does not have a current_season_label and no season_label was supplied."
        )

    teams = TeamDirectoryEntry.objects.filter(
        competition=competition_obj,
        season_label=resolved_season,
    ).order_by("name", "id")

    if not teams.exists():
        raise ValueError(
            f"No TeamDirectoryEntry rows found for competition {competition_obj.id} in season '{resolved_season}'."
        )

    mapping: dict[int, str] = {}

    for team in teams:
        try:
            mapping[team.id] = resolve_understat_team_name_for_entry(team)
        except TeamMappingNotFoundError as exc:
            raise TeamMappingNotFoundError(
                team_name=team.name,
                short_name=team.short_name,
                tla=team.tla,
                competition_name=competition_obj.name,
                season_label=resolved_season,
            ) from exc

    return mapping