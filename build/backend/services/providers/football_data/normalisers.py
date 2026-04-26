"""
Normalisers for football-data payloads

Converts raw football-data API responses into the internal dictionary structure used by the application
"""

from datetime import date, datetime
from typing import Any


PROVIDER_NAME = "football_data"

_POSITION_MAP = {
    "goalkeeper": "GK",
    "keeper": "GK",
    "centre-back": "CB",
    "center-back": "CB",
    "left-back": "LB",
    "right-back": "RB",
    "left wing-back": "LWB",
    "right wing-back": "RWB",
    "defensive midfield": "CDM",
    "central midfield": "CM",
    "attacking midfield": "CAM",
    "left midfield": "LM",
    "right midfield": "RM",
    "left winger": "LW",
    "right winger": "RW",
    "centre-forward": "ST",
    "center-forward": "ST",
    "striker": "ST",
    "second striker": "CF",
}


# Clean any value into a trimmed string
def _clean_string(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return value.strip()


# Return a cleaned string or None if it is empty
def _string_or_none(value: Any) -> str | None:
    cleaned = _clean_string(value)
    return cleaned or None


# Convert a value into an external ID string
def _external_id(value: Any) -> str:
    return _clean_string(value)


# Parse a value into a date if possible
def _parse_date(value: Any) -> date | None:
    cleaned = _clean_string(value)
    if not cleaned:
        return None

    try:
        return date.fromisoformat(cleaned[:10])
    except ValueError:
        return None


# Parse a value into a datetime if possible
def _parse_datetime(value: Any) -> datetime | None:
    cleaned = _clean_string(value)
    if not cleaned:
        return None

    normalized = cleaned.replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


# Parse a value into an integer if possible
def _parse_int(value: Any) -> int | None:
    if value in (None, ""):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# Normalise a nationality value to a two-letter code
def _normalize_nationality(value: Any) -> str:
    cleaned = _clean_string(value).upper()
    if len(cleaned) == 2:
        return cleaned
    return ""


# Map a raw position value to the internal position code
def _normalize_position(value: Any) -> str:
    cleaned = _clean_string(value).lower()
    if not cleaned:
        return ""
    return _POSITION_MAP.get(cleaned, "")


# Split a name into first name, last name, and display name
def _split_name(first_name: Any, last_name: Any, full_name: Any) -> tuple[str, str, str]:
    first = _clean_string(first_name)
    last = _clean_string(last_name)
    display = _clean_string(full_name)

    if first or last:
        if not display:
            display = " ".join(part for part in [first, last] if part).strip()
        return first, last, display

    if not display:
        return "", "", ""

    parts = display.split()

    if len(parts) == 1:
        return parts[0], "", display

    if len(parts) == 2:
        return parts[0], parts[1], display

    return "", "", display


# Build a competition context string from running competitions
def _competition_context(payload: dict[str, Any]) -> str:
    running_competitions = payload.get("runningCompetitions") or []
    codes = []

    for competition in running_competitions:
        code = _clean_string(competition.get("code"))
        if code:
            codes.append(code)

    return ", ".join(codes)


# Work out the season label from the payload
def _season_label_from_payload(payload: dict[str, Any]) -> str:
    start_date = _parse_date(payload.get("startDate"))
    if start_date:
        return str(start_date.year)

    year = _parse_int(payload.get("year"))
    if year is not None:
        return str(year)

    current_matchday = _parse_int(payload.get("currentMatchday"))
    if current_matchday is not None:
        return ""

    return ""


# Pick the best team name from the payload
def _team_name_from_payload(payload: dict[str, Any]) -> str:
    return _clean_string(
        payload.get("shortName")
        or payload.get("tla")
        or payload.get("name")
    )


# Get the main standings block from the table payload
def _extract_table_block(payload: dict[str, Any]) -> dict[str, Any]:
    standings = payload.get("standings") or []

    for block in standings:
        if _clean_string(block.get("type")).upper() == "TOTAL":
            return block

    if standings:
        return standings[0]

    return {}


# Normalise a team payload into the internal team shape
def normalize_team(payload: dict[str, Any]) -> dict[str, Any]:
    area = payload.get("area") or {}

    return {
        "provider": PROVIDER_NAME,
        "external_id": _external_id(payload.get("id")),
        "provider_display_name": _clean_string(payload.get("shortName") or payload.get("name")),
        "name": _clean_string(payload.get("name")),
        "short_name": _clean_string(payload.get("shortName")),
        "tla": _clean_string(payload.get("tla")),
        "country": _clean_string(area.get("name")),
        "competition_context": _competition_context(payload),
        "venue": _clean_string(payload.get("venue")),
        "website": _clean_string(payload.get("website")),
        "founded": _parse_int(payload.get("founded")),
        "club_colors": _clean_string(payload.get("clubColors")),
        "crest_url": _clean_string(payload.get("crest")),
        "metadata": {
            "area_code": _clean_string(area.get("code")),
            "area_flag": _clean_string(area.get("flag")),
        },
    }


# Normalise a competition team payload with source context included
def normalize_competition_team(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_team(payload)
    normalized["metadata"] = {
        **normalized["metadata"],
        "source_context": "competition_teams",
    }
    return normalized


# Normalise a squad player payload into the internal player shape
def normalize_squad_player(
    payload: dict[str, Any],
    external_team_id: Any = None,
) -> dict[str, Any]:
    raw_name = payload.get("name") or payload.get("fullName") or payload.get("displayName")
    first_name = payload.get("firstName")
    last_name = payload.get("lastName")
    parsed_first_name, parsed_last_name, display_name = _split_name(
        first_name,
        last_name,
        raw_name,
    )

    raw_provider_position = _clean_string(payload.get("position"))
    raw_nationality = _clean_string(payload.get("nationality"))

    full_name = " ".join(
        part for part in [parsed_first_name, parsed_last_name] if part
    ).strip() or display_name

    return {
        "provider": PROVIDER_NAME,
        "external_id": _external_id(payload.get("id")),
        "external_team_id": _external_id(external_team_id),
        "first_name": parsed_first_name,
        "last_name": parsed_last_name,
        "display_name": display_name,
        "full_name": full_name,
        "date_of_birth": _parse_date(payload.get("dateOfBirth")),
        "nationality": _normalize_nationality(raw_nationality),
        "primary_position": _normalize_position(raw_provider_position),
        "squad_number": _parse_int(payload.get("shirtNumber")),
        "raw_provider_position": raw_provider_position,
        "profile_image": _clean_string(
            payload.get("image")
            or payload.get("photo")
            or payload.get("profileImage")
        ),
        "metadata": {
            "raw_nationality": raw_nationality,
        },
    }


# Normalise a competition payload into the internal competition shape
def normalize_competition(payload: dict[str, Any]) -> dict[str, Any]:
    area = payload.get("area") or {}
    current_season = payload.get("currentSeason") or {}

    return {
        "provider": PROVIDER_NAME,
        "external_id": _external_id(payload.get("id")),
        "code": _clean_string(payload.get("code")),
        "name": _clean_string(payload.get("name")),
        "area_name": _clean_string(area.get("name")),
        "emblem_url": _clean_string(payload.get("emblem")),
        "current_season_label": _season_label_from_payload(current_season),
        "current_season_start_date": _parse_date(current_season.get("startDate")),
        "current_season_end_date": _parse_date(current_season.get("endDate")),
        "current_matchday": _parse_int(current_season.get("currentMatchday")),
        "metadata": {
            "competition_type": _clean_string(payload.get("type")),
            "plan": _clean_string(payload.get("plan")),
            "area_code": _clean_string(area.get("code")),
            "area_flag": _clean_string(area.get("flag")),
        },
    }


# Normalise a competitions payload into a list of competitions
def normalize_competitions_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    competitions = payload.get("competitions") or []
    return [normalize_competition(item) for item in competitions]


# Normalise a team directory entry into the internal directory shape
def normalize_team_directory_entry(
    payload: dict[str, Any],
    competition_external_id: Any = None,
    season_label: str = "",
) -> dict[str, Any]:
    area = payload.get("area") or {}

    return {
        "competition_external_id": _external_id(competition_external_id),
        "provider": PROVIDER_NAME,
        "season_label": _clean_string(season_label),
        "external_id": _external_id(payload.get("id")),
        "name": _clean_string(payload.get("name")),
        "short_name": _clean_string(payload.get("shortName")),
        "tla": _clean_string(payload.get("tla")),
        "area_name": _clean_string(area.get("name")),
        "emblem_url": _clean_string(payload.get("crest")),
        "venue": _clean_string(payload.get("venue")),
        "website": _clean_string(payload.get("website")),
        "founded_year": _parse_int(payload.get("founded")),
        "metadata": {
            "area_code": _clean_string(area.get("code")),
            "area_flag": _clean_string(area.get("flag")),
        },
    }


# Normalise a competition teams payload into team directory entries
def normalize_competition_teams_payload(
    payload: dict[str, Any],
    competition_external_id: Any = None,
    season_label: str = "",
) -> list[dict[str, Any]]:
    teams = payload.get("teams") or []
    resolved_competition_external_id = _external_id(
        competition_external_id or (payload.get("competition") or {}).get("id")
    )
    resolved_season_label = _clean_string(season_label) or _season_label_from_payload(
        payload.get("season") or {}
    )

    return [
        normalize_team_directory_entry(
            item,
            competition_external_id=resolved_competition_external_id,
            season_label=resolved_season_label,
        )
        for item in teams
    ]


# Normalise a player directory entry into the internal player directory shape
def normalize_player_directory_entry(
    payload: dict[str, Any],
    team_external_id: Any = None,
) -> dict[str, Any]:
    raw_name = payload.get("name") or payload.get("fullName") or payload.get("displayName")
    first_name = payload.get("firstName")
    last_name = payload.get("lastName")
    parsed_first_name, parsed_last_name, display_name = _split_name(
        first_name,
        last_name,
        raw_name,
    )

    raw_provider_position = _clean_string(payload.get("position"))
    raw_nationality = _clean_string(payload.get("nationality"))

    return {
        "team_external_id": _external_id(team_external_id),
        "provider": PROVIDER_NAME,
        "external_player_id": _external_id(payload.get("id")),
        "player_name": display_name,
        "first_name": parsed_first_name,
        "last_name": parsed_last_name,
        "date_of_birth": _parse_date(payload.get("dateOfBirth")),
        "nationality": raw_nationality,
        "primary_position": _normalize_position(raw_provider_position),
        "raw_position": raw_provider_position,
        "squad_number": _parse_int(payload.get("shirtNumber")),
        "is_active": True,
        "metadata": {
            "nationality_code": _normalize_nationality(raw_nationality),
        },
    }


# Normalise a team players payload into player directory entries
def normalize_team_players_payload(
    players_payload: list[dict[str, Any]],
    team_external_id: Any = None,
) -> list[dict[str, Any]]:
    return [
        normalize_player_directory_entry(
            item,
            team_external_id=team_external_id,
        )
        for item in players_payload or []
    ]


# Normalise one competition table row into the internal table row shape
def normalize_competition_table_row(payload: dict[str, Any]) -> dict[str, Any]:
    team = payload.get("team") or {}

    return {
        "position": _parse_int(payload.get("position")) or 0,
        "external_team_id": _external_id(team.get("id")),
        "team_name": _team_name_from_payload(team),
        "played": _parse_int(payload.get("playedGames")) or 0,
        "won": _parse_int(payload.get("won")) or 0,
        "drawn": _parse_int(payload.get("draw")) or 0,
        "lost": _parse_int(payload.get("lost")) or 0,
        "goals_for": _parse_int(payload.get("goalsFor")) or 0,
        "goals_against": _parse_int(payload.get("goalsAgainst")) or 0,
        "goal_difference": _parse_int(payload.get("goalDifference")) or 0,
        "points": _parse_int(payload.get("points")) or 0,
        "form": _clean_string(payload.get("form")),
        "metadata": {
            "team_crest": _clean_string(team.get("crest")),
        },
    }


# Normalise a competition table payload into the internal table shape
def normalize_competition_table(
    payload: dict[str, Any],
    competition_external_id: Any = None,
    season_label: str = "",
    snapshot_label: str = "latest",
) -> dict[str, Any]:
    competition = payload.get("competition") or {}
    season = payload.get("season") or {}
    standings_block = _extract_table_block(payload)
    rows = standings_block.get("table") or []

    resolved_competition_external_id = _external_id(
        competition_external_id or competition.get("id")
    )
    resolved_season_label = _clean_string(season_label) or _season_label_from_payload(season)

    return {
        "competition_external_id": resolved_competition_external_id,
        "season_label": resolved_season_label,
        "snapshot_label": _clean_string(snapshot_label) or "latest",
        "matchday": _parse_int(season.get("currentMatchday")),
        "fetched_at": None,
        "metadata": {
            "standing_type": _clean_string(standings_block.get("type")),
            "stage": _clean_string(standings_block.get("stage")),
        },
        "rows": [normalize_competition_table_row(item) for item in rows],
    }


# Normalise one competition fixture into the internal fixture shape
def normalize_competition_fixture(
    payload: dict[str, Any],
    competition_external_id: Any = None,
    season_label: str = "",
) -> dict[str, Any]:
    competition = payload.get("competition") or {}
    season = payload.get("season") or {}
    home_team = payload.get("homeTeam") or {}
    away_team = payload.get("awayTeam") or {}
    score = payload.get("score") or {}
    full_time = score.get("fullTime") or {}

    resolved_competition_external_id = _external_id(
        competition_external_id or competition.get("id")
    )
    resolved_season_label = _clean_string(season_label) or _season_label_from_payload(season)

    return {
        "competition_external_id": resolved_competition_external_id,
        "season_label": resolved_season_label,
        "external_match_id": _external_id(payload.get("id")),
        "status": _clean_string(payload.get("status")),
        "kickoff_at": _parse_datetime(payload.get("utcDate")),
        "matchday": _parse_int(payload.get("matchday")),
        "home_external_team_id": _external_id(home_team.get("id")),
        "home_team_name": _team_name_from_payload(home_team),
        "away_external_team_id": _external_id(away_team.get("id")),
        "away_team_name": _team_name_from_payload(away_team),
        "home_score": _parse_int(full_time.get("home")),
        "away_score": _parse_int(full_time.get("away")),
        "metadata": {
            "stage": _clean_string(payload.get("stage")),
            "group": _clean_string(payload.get("group")),
            "winner": _clean_string(score.get("winner")),
            "duration": _clean_string(score.get("duration")),
        },
    }


# Normalise a competition matches payload into fixture entries
def normalize_competition_matches_payload(
    payload: dict[str, Any],
    competition_external_id: Any = None,
    season_label: str = "",
) -> list[dict[str, Any]]:
    matches = payload.get("matches") or []
    competition = payload.get("competition") or {}
    season = payload.get("season") or {}

    resolved_competition_external_id = _external_id(
        competition_external_id or competition.get("id")
    )
    resolved_season_label = _clean_string(season_label) or _season_label_from_payload(season)

    return [
        normalize_competition_fixture(
            item,
            competition_external_id=resolved_competition_external_id,
            season_label=resolved_season_label,
        )
        for item in matches
    ]


# Normalise one top scorer entry into the internal scorer shape
def normalize_competition_top_scorer(
    payload: dict[str, Any],
    competition_external_id: Any = None,
    season_label: str = "",
    rank: int | None = None,
) -> dict[str, Any]:
    player = payload.get("player") or {}
    team = payload.get("team") or {}

    return {
        "competition_external_id": _external_id(competition_external_id),
        "season_label": _clean_string(season_label),
        "rank": rank or 0,
        "external_player_id": _external_id(player.get("id")),
        "player_name": _clean_string(player.get("name")),
        "team_name": _clean_string(team.get("name")),
        "external_team_id": _external_id(team.get("id")),
        "goals": _parse_int(payload.get("goals")) or 0,
        "penalties": _parse_int(payload.get("penalties")),
        "metadata": {
            "assists": _parse_int(payload.get("assists")),
            "played_matches": _parse_int(payload.get("playedMatches")),
            "player_first_name": _clean_string(player.get("firstName")),
            "player_last_name": _clean_string(player.get("lastName")),
            "player_date_of_birth": _clean_string(player.get("dateOfBirth")),
            "player_nationality": _clean_string(player.get("nationality")),
        },
    }


# Normalise a scorers payload into top scorer entries
def normalize_competition_scorers_payload(
    payload: dict[str, Any],
    competition_external_id: Any = None,
    season_label: str = "",
) -> list[dict[str, Any]]:
    scorers = payload.get("scorers") or []
    competition = payload.get("competition") or {}
    season = payload.get("season") or {}

    resolved_competition_external_id = _external_id(
        competition_external_id or competition.get("id")
    )
    resolved_season_label = _clean_string(season_label) or _season_label_from_payload(season)

    return [
        normalize_competition_top_scorer(
            item,
            competition_external_id=resolved_competition_external_id,
            season_label=resolved_season_label,
            rank=index,
        )
        for index, item in enumerate(scorers, start=1)
    ]