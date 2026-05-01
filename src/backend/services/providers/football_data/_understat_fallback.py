"""
Understat fallback helpers for the football-data sync service

Builds fallback squad data from Understat when football-data authentication fails during squad directory syncing
"""

import re
import unicodedata

from django.conf import settings

from apps.livefootball.services.exceptions import TeamMappingNotFoundError
from apps.livefootball.services.team_bridge import (
    resolve_understat_team_name,
    resolve_understat_team_name_for_entry,
)

from .exceptions import FootballDataAuthenticationError


# Build fallback squad data from Understat in the same shape as football-data output
def build_understat_fallback_players_data(team_entry, season_label, provider, get_client_fn):
    if not getattr(settings, "UNDERSTAT_ENABLED", True):
        raise FootballDataAuthenticationError(
            "Football-data authentication failed and Understat fallback is disabled."
        )

    understat_players = []
    understat_team_name = ""
    attempted_names = []

    for candidate in _understat_team_name_candidates(team_entry):
        attempted_names.append(candidate)
        try:
            candidate_players = get_client_fn().get_team_players(candidate, season_label)
        except Exception:
            continue

        if candidate_players:
            understat_team_name = candidate
            understat_players = candidate_players
            break

    if not understat_players:
        # TODO: Coverage still missing for Rotherham United FC (2023) and
        # Plymouth Argyle FC (2023, 2024) — add a dedicated fix later
        raise FootballDataAuthenticationError(
            "Football-data authentication failed and Understat fallback could not fetch squad data "
            f"for '{team_entry.name}' ({season_label}). Tried: {', '.join(attempted_names)}"
        )

    normalized = []
    for index, raw_player in enumerate(understat_players):
        external_player_id = _resolve_understat_player_external_id(raw_player, index)
        player_name = str(
            raw_player.get("player_name")
            or raw_player.get("player")
            or raw_player.get("name")
            or ""
        ).strip() or f"Unknown Understat Player {index + 1}"

        normalized.append(
            {
                "team_external_id": str(team_entry.external_id),
                "provider": provider,
                "external_player_id": external_player_id,
                "player_name": player_name,
                "first_name": "",
                "last_name": "",
                "date_of_birth": None,
                "nationality": "",
                "primary_position": "",
                "raw_position": str(raw_player.get("position") or "").strip(),
                "squad_number": None,
                "is_active": True,
                "metadata": {
                    "source": "understat_fallback",
                    "understat_team": understat_team_name,
                    "season_label": str(season_label),
                },
            }
        )

    return normalized


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Build a stable external player ID for an Understat player
def _resolve_understat_player_external_id(raw_player, index):
    base_id = str(
        raw_player.get("id")
        or raw_player.get("player_id")
        or raw_player.get("playerId")
        or ""
    ).strip() or f"missing-{index + 1}"
    return f"understat:{base_id}"


# Build candidate Understat team names from a team entry
def _understat_team_name_candidates(team_entry):
    candidates = []

    try:
        candidates.append(resolve_understat_team_name_for_entry(team_entry))
    except TeamMappingNotFoundError:
        pass

    for value in [team_entry.name, team_entry.short_name, team_entry.tla]:
        if not value:
            continue
        for candidate in _expanded_team_name_variants(value):
            try:
                candidates.append(resolve_understat_team_name(candidate))
            except TeamMappingNotFoundError:
                candidates.append(candidate)

    deduped = []
    seen = set()
    for candidate in candidates:
        cleaned = str(candidate or "").strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return deduped


# Build fallback team name variants for Understat matching
def _expanded_team_name_variants(raw_name):
    base = str(raw_name or "").strip()
    if not base:
        return []

    variants = [base]
    normalized = unicodedata.normalize("NFKD", base)
    ascii_name = "".join(ch for ch in normalized if not unicodedata.combining(ch)).strip()
    variants.append(ascii_name)

    no_prefix = re.sub(
        r"^(UD|CD|US|AC|AS|SV|VfL|1\.\s*FC)\s+", "", ascii_name, flags=re.IGNORECASE
    ).strip()
    variants.append(no_prefix)

    no_suffix = re.sub(r"\b(FC|CF|AFC|HSC|Calcio)\b", "", no_prefix, flags=re.IGNORECASE)
    no_suffix = re.sub(r"\s+", " ", no_suffix).strip()
    variants.append(no_suffix)

    no_trailing_year = re.sub(r"\s+\d{2,4}$", "", no_suffix).strip()
    variants.append(no_trailing_year)

    for token in [" Town", " United", " Foot"]:
        if no_trailing_year.endswith(token):
            variants.append(no_trailing_year[: -len(token)].strip())

    return [item for item in variants if item]