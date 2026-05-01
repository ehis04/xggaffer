"""
Understat normalisers for team and player enrichment data

Converts raw Understat team, player, and team-player payloads into internal enrichment dictionary shapes
"""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


# ---------------------------------------------------------------------------
# Normalisation constants
# ---------------------------------------------------------------------------

_DECIMAL_PLACES = Decimal("0.01")
_COMPETITION_ALIASES = {
    "pl": "epl",
    "premierleague": "epl",
    "englandpremierleague": "epl",
    "epl": "epl",
    "pd": "laliga",
    "laliga": "laliga",
    "primeradivision": "laliga",
    "bl1": "bundesliga",
    "bundesliga": "bundesliga",
    "sa": "seriea",
    "seriea": "seriea",
    "fl1": "ligue1",
    "ligue1": "ligue1",
    "league1": "ligue1",
    "elc": "championship",
    "championship": "championship",
}


# ---------------------------------------------------------------------------
# Public normalisers
# ---------------------------------------------------------------------------

# Normalise an Understat team-season payload into the club season enrichment shape
def normalise_understat_team_season(
    payload: dict[str, Any],
    season_label: str,
    competition_code: str | None = None,
) -> dict[str, Any]:
    team_payload = _unwrap_team_payload(payload)
    team_rows = _extract_team_history_rows(team_payload)
    aggregated = _aggregate_team_history(team_rows)

    detected_competition_name = (
        _as_str(payload.get("competition_name"))
        or _as_str(payload.get("league"))
        or _as_str(team_payload.get("competition_name"))
        or _as_str(team_payload.get("league"))
    )

    detected_competition_code = (
        _clean_str(competition_code)
        or _as_str(payload.get("competition_code"))
        or _as_str(payload.get("league"))
        or _as_str(team_payload.get("competition_code"))
        or _as_str(team_payload.get("league"))
        or ""
    )

    external_team_id = (
        _as_str(payload.get("team_external_id"))
        or _as_str(team_payload.get("team_external_id"))
        or _as_str(team_payload.get("team_id"))
        or _as_str(team_payload.get("id"))
        or ""
    )

    return {
        "provider": "understat",
        "season_label": str(season_label),
        "competition_code": detected_competition_code,
        "competition_name": detected_competition_name or "",
        "external_team_id": external_team_id,
        "matches_played": aggregated["matches_played"],
        "wins": aggregated["wins"],
        "draws": aggregated["draws"],
        "losses": aggregated["losses"],
        "goals_for": aggregated["goals_for"],
        "goals_against": aggregated["goals_against"],
        "xg": aggregated["xg"],
        "xga": aggregated["xga"],
        "npxg": aggregated["npxg"],
        "ppda": aggregated["ppda"],
        "metadata": {
            "source": "understat",
            "normaliser": "normalise_understat_team_season",
            "history_row_count": len(team_rows),
            "competition_name_detected": detected_competition_name or "",
            "competition_code_input": competition_code or "",
        },
        "raw_snapshot": {
            "team_payload": deepcopy(team_payload),
            "history_rows": deepcopy(team_rows),
        },
    }


# Normalise an Understat player-season payload into the player season enrichment shape
def normalise_understat_player_season(
    payload: dict[str, Any],
    season_label: str,
    competition_code: str | None = None,
) -> dict[str, Any]:
    selected_rows = _select_player_season_rows(payload, season_label, competition_code)
    aggregated = _aggregate_player_rows(selected_rows)

    competition_name = (
        _first_non_blank(row.get("league") for row in selected_rows)
        or _first_non_blank(row.get("competition_name") for row in selected_rows)
        or _as_str(payload.get("competition_name"))
        or _as_str(payload.get("league"))
        or ""
    )

    resolved_competition_code = (
        _clean_str(competition_code)
        or _first_non_blank(row.get("league") for row in selected_rows)
        or _as_str(payload.get("competition_code"))
        or _as_str(payload.get("league"))
        or ""
    )

    external_player_id = (
        _first_non_blank(
            row.get("id")
            or row.get("player_id")
            or row.get("external_player_id")
            for row in selected_rows
        )
        or _as_str(payload.get("player_external_id"))
        or ""
    )

    external_team_id = _single_or_blank(
        _as_str(
            row.get("team_id")
            or row.get("team")
            or row.get("external_team_id")
        )
        for row in selected_rows
    )

    club_name = _single_or_blank(
        _as_str(
            row.get("team_title")
            or row.get("team_name")
            or row.get("club_name")
        )
        for row in selected_rows
    )

    raw_snapshot: dict[str, Any]
    if _looks_like_single_player_group_row(payload):
        raw_snapshot = {"selected_groups": [deepcopy(payload)]}
    else:
        raw_snapshot = {
            "selected_groups": deepcopy(selected_rows),
            "requested_season": str(season_label),
        }

    return {
        "provider": "understat",
        "season_label": str(season_label),
        "competition_code": resolved_competition_code,
        "competition_name": competition_name,
        "external_player_id": external_player_id,
        "external_team_id": external_team_id,
        "club_name": club_name,
        "matches_played": aggregated["matches_played"],
        "minutes_played": aggregated["minutes_played"],
        "goals": aggregated["goals"],
        "assists": aggregated["assists"],
        "shots": aggregated["shots"],
        "xg": aggregated["xg"],
        "xa": aggregated["xa"],
        "npg": aggregated["npg"],
        "npxg": aggregated["npxg"],
        "key_passes": aggregated["key_passes"],
        "metadata": {
            "source": "understat",
            "normaliser": "normalise_understat_player_season",
            "selected_group_count": len(selected_rows),
            "competition_code_input": competition_code or "",
        },
        "raw_snapshot": raw_snapshot,
    }


# Normalise a single Understat team-page player row into the player season enrichment shape
def normalise_understat_team_player(
    payload: dict[str, Any],
    season_label: str,
    competition_code: str | None = None,
    *,
    external_team_id: str | None = None,
    competition_name: str | None = None,
) -> dict[str, Any]:
    return {
        "provider": "understat",
        "season_label": str(season_label),
        "competition_code": _clean_str(competition_code) or "",
        "competition_name": _clean_str(competition_name)
        or _as_str(payload.get("league"))
        or "",
        "external_player_id": _as_str(
            payload.get("id")
            or payload.get("player_id")
            or payload.get("external_player_id")
        )
        or "",
        "external_team_id": _clean_str(external_team_id)
        or _as_str(payload.get("team_id"))
        or _as_str(payload.get("team"))
        or "",
        "club_name": _as_str(
            payload.get("team_title")
            or payload.get("team_name")
            or payload.get("club_name")
        )
        or "",
        "matches_played": _to_int(
            payload.get("games")
            or payload.get("matches")
            or payload.get("matches_played")
        ),
        "minutes_played": _to_int(
            payload.get("time")
            or payload.get("minutes")
            or payload.get("minutes_played")
        ),
        "goals": _to_int(payload.get("goals")),
        "assists": _to_int(payload.get("assists")),
        "shots": _to_int(payload.get("shots")),
        "xg": _to_decimal(payload.get("xG") or payload.get("xg")),
        "xa": _to_decimal(payload.get("xA") or payload.get("xa")),
        "npg": _to_decimal(payload.get("npg") or payload.get("nPG")),
        "npxg": _to_decimal(payload.get("npxG") or payload.get("npxg")),
        "xg_chain": _to_decimal(payload.get("xGChain") or payload.get("xg_chain")),
        "xg_buildup": _to_decimal(payload.get("xGBuildup") or payload.get("xg_buildup")),
        "yellow_cards": _to_int(payload.get("yellow_cards") or payload.get("yellowCards")),
        "red_cards": _to_int(payload.get("red_cards") or payload.get("redCards")),
        "key_passes": _to_int(
            payload.get("key_passes")
            or payload.get("keyPasses")
            or payload.get("keypasses")
        ),
        "metadata": {
            "source": "understat",
            "normaliser": "normalise_understat_team_player",
            "position": _as_str(payload.get("position")) or "",
            "player_name": _as_str(
                payload.get("player_name")
                or payload.get("player")
                or payload.get("name")
            )
            or "",
        },
        "raw_snapshot": deepcopy(payload),
    }


# ---------------------------------------------------------------------------
# Team helpers
# ---------------------------------------------------------------------------

# Unwrap a team-page envelope into the team stats payload used by the normaliser
def _unwrap_team_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    if "stats" in payload and isinstance(payload["stats"], (dict, list)):
        return {
            "stats": payload.get("stats"),
            "players": payload.get("players"),
            "dates": payload.get("dates"),
            "team_external_id": payload.get("team_external_id"),
            "competition_name": payload.get("competition_name"),
            "competition_code": payload.get("competition_code"),
            "league": payload.get("league"),
        }

    return payload


# Extract team history rows from an Understat team stats payload
def _extract_team_history_rows(team_payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(team_payload, dict):
        return []

    stats = team_payload.get("stats")

    if isinstance(stats, list):
        return [row for row in stats if isinstance(row, dict)]

    if isinstance(stats, dict):
        history = stats.get("history")
        if isinstance(history, list):
            return [row for row in history if isinstance(row, dict)]

        date_rows = _extract_team_date_rows(team_payload.get("dates"))
        if date_rows:
            return date_rows

        # Keep aggregate metric dictionaries as one pseudo-row for the aggregate helper
        return [stats]

    history = team_payload.get("history")
    if isinstance(history, list):
        return [row for row in history if isinstance(row, dict)]

    date_rows = _extract_team_date_rows(team_payload.get("dates"))
    if date_rows:
        return date_rows

    return []


def _extract_team_date_rows(dates: Any) -> list[dict[str, Any]]:
    if not isinstance(dates, list):
        return []

    rows: list[dict[str, Any]] = []
    for row in dates:
        if not isinstance(row, dict) or not row.get("isResult"):
            continue

        side = _as_str(row.get("side")).lower()
        if side not in {"h", "a"}:
            continue

        opponent_side = "a" if side == "h" else "h"
        goals = row.get("goals") if isinstance(row.get("goals"), dict) else {}
        xg = row.get("xG") if isinstance(row.get("xG"), dict) else {}

        rows.append(
            {
                "result": row.get("result"),
                "scored": goals.get(side),
                "missed": goals.get(opponent_side),
                "xG": xg.get(side),
                "xGA": xg.get(opponent_side),
                "datetime": row.get("datetime"),
                "match_id": row.get("id"),
            }
        )

    return rows


# Aggregate match-level team history rows into season totals
def _aggregate_team_history(rows: list[dict[str, Any]]) -> dict[str, Any]:
    matches_played = len(rows)
    wins = 0
    draws = 0
    losses = 0
    goals_for = 0
    goals_against = 0

    total_xg = Decimal("0")
    total_xga = Decimal("0")
    total_npxg = Decimal("0")

    has_xg = False
    has_xga = False
    has_npxg = False

    ppda_att_total = Decimal("0")
    ppda_def_total = Decimal("0")
    has_ppda = False

    for row in rows:
        result = _as_str(row.get("result")).lower()

        scored = _to_int(
            row.get("scored")
            or row.get("goals_for")
            or row.get("goals")
            or row.get("gf")
        )
        conceded = _to_int(
            row.get("missed")
            or row.get("goals_against")
            or row.get("ga")
            or row.get("conceded")
        )

        if result in {"w", "win", "won"}:
            wins += 1
        elif result in {"d", "draw", "drawn"}:
            draws += 1
        elif result in {"l", "loss", "lost"}:
            losses += 1
        elif scored or conceded:
            if scored > conceded:
                wins += 1
            elif scored < conceded:
                losses += 1
            else:
                draws += 1

        goals_for += scored
        goals_against += conceded

        xg = _to_decimal(
            row.get("xG")
            or row.get("xg")
            or row.get("team_xg")
        )
        if xg is not None:
            total_xg += xg
            has_xg = True

        xga = _to_decimal(
            row.get("xGA")
            or row.get("xga")
            or row.get("against_xg")
            or row.get("opponent_xg")
        )
        if xga is not None:
            total_xga += xga
            has_xga = True

        npxg = _to_decimal(row.get("npxG") or row.get("npxg"))
        if npxg is not None:
            total_npxg += npxg
            has_npxg = True

        ppda = row.get("ppda")
        if isinstance(ppda, dict):
            att = _to_decimal(ppda.get("att"))
            defending_actions = _to_decimal(ppda.get("def"))
            if att is not None and defending_actions not in {None, Decimal("0")}:
                ppda_att_total += att
                ppda_def_total += defending_actions
                has_ppda = True
        else:
            ppda_value = _to_decimal(ppda)
            if ppda_value is not None:
                # Average direct PPDA rows by treating each row equally
                ppda_att_total += ppda_value
                ppda_def_total += Decimal("1")
                has_ppda = True

    ppda_value = None
    if has_ppda and ppda_def_total != Decimal("0"):
        ppda_value = _quantize(ppda_att_total / ppda_def_total)

    return {
        "matches_played": matches_played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "xg": _quantize(total_xg) if has_xg else None,
        "xga": _quantize(total_xga) if has_xga else None,
        "npxg": _quantize(total_npxg) if has_npxg else None,
        "ppda": ppda_value,
    }


# ---------------------------------------------------------------------------
# Player helpers
# ---------------------------------------------------------------------------

# Select the rows matching the requested player season and optional competition
def _select_player_season_rows(
    payload: dict[str, Any],
    season_label: str,
    competition_code: str | None,
) -> list[dict[str, Any]]:
    if _looks_like_single_player_group_row(payload):
        return [payload]

    groups = payload.get("groups")
    if isinstance(groups, dict):
        candidate_rows = [row for row in groups.values() if isinstance(row, dict)]
    elif isinstance(groups, list):
        candidate_rows = [row for row in groups if isinstance(row, dict)]
    else:
        candidate_rows = []

    if not candidate_rows:
        return []

    season_matches = [
        row for row in candidate_rows if _season_matches(row.get("season"), season_label)
    ]

    if not season_matches:
        return []

    if competition_code:
        filtered = [
            row
            for row in season_matches
            if _competition_matches(
                row.get("league") or row.get("competition_code"),
                competition_code,
            )
        ]
        if filtered:
            return filtered

    return season_matches


# Return True when a payload already looks like one player-season group row
def _looks_like_single_player_group_row(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        return False

    has_row_signals = any(
        key in payload
        for key in (
            "season",
            "games",
            "time",
            "goals",
            "assists",
            "xG",
            "xA",
        )
    )
    return has_row_signals and "groups" not in payload


# Aggregate selected player rows into season totals
def _aggregate_player_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    matches_played = 0
    minutes_played = 0
    goals = 0
    assists = 0
    shots = 0
    key_passes = 0

    total_xg = Decimal("0")
    total_xa = Decimal("0")
    total_npg = Decimal("0")
    total_npxg = Decimal("0")

    has_xg = False
    has_xa = False
    has_npg = False
    has_npxg = False

    for row in rows:
        matches_played += _to_int(
            row.get("games")
            or row.get("matches")
            or row.get("matches_played")
        )
        minutes_played += _to_int(
            row.get("time")
            or row.get("minutes")
            or row.get("minutes_played")
        )
        goals += _to_int(row.get("goals"))
        assists += _to_int(row.get("assists"))
        shots += _to_int(row.get("shots"))
        key_passes += _to_int(
            row.get("key_passes")
            or row.get("keyPasses")
            or row.get("keypasses")
        )

        xg = _to_decimal(row.get("xG") or row.get("xg"))
        if xg is not None:
            total_xg += xg
            has_xg = True

        xa = _to_decimal(row.get("xA") or row.get("xa"))
        if xa is not None:
            total_xa += xa
            has_xa = True

        npg = _to_decimal(row.get("npg") or row.get("nPG"))
        if npg is not None:
            total_npg += npg
            has_npg = True

        npxg = _to_decimal(row.get("npxG") or row.get("npxg"))
        if npxg is not None:
            total_npxg += npxg
            has_npxg = True

    return {
        "matches_played": matches_played,
        "minutes_played": minutes_played,
        "goals": goals,
        "assists": assists,
        "shots": shots,
        "xg": _quantize(total_xg) if has_xg else None,
        "xa": _quantize(total_xa) if has_xa else None,
        "npg": _quantize(total_npg) if has_npg else None,
        "npxg": _quantize(total_npxg) if has_npxg else None,
        "key_passes": key_passes,
    }


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

# Return True when two season labels match after cleaning
def _season_matches(value: Any, season_label: str) -> bool:
    left = _clean_str(value)
    right = _clean_str(season_label)
    return bool(left and right and left == right)


# Return True when two competition values resolve to the same canonical code
def _competition_matches(value: Any, competition_code: str) -> bool:
    left = _canonical_competition_code(value)
    right = _canonical_competition_code(competition_code)
    return bool(left and right and left == right)


# Convert a competition value into its canonical internal code
def _canonical_competition_code(value: Any) -> str:
    raw = _clean_str(value).lower()
    if not raw:
        return ""

    compact = (
        raw.replace("_", "")
        .replace("-", "")
        .replace(" ", "")
        .replace(".", "")
    )

    return _COMPETITION_ALIASES.get(compact, compact)


# Convert a raw value to an integer, defaulting to zero
def _to_int(value: Any) -> int:
    if value in (None, "", False):
        return 0

    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return 0


# Convert a raw value to a two-decimal Decimal when possible
def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, "", False):
        return None

    try:
        return _quantize(Decimal(str(value).strip()))
    except (InvalidOperation, ValueError, TypeError):
        return None


# Round a Decimal to the configured number of places
def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_DECIMAL_PLACES, rounding=ROUND_HALF_UP)


# Convert a raw value to a stripped string
def _clean_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


# Convert a raw value to a stripped string or blank
def _as_str(value: Any) -> str:
    cleaned = _clean_str(value)
    return cleaned if cleaned else ""


# Return the first non-blank value from an iterable
def _first_non_blank(values: Any) -> str:
    for value in values:
        cleaned = _as_str(value)
        if cleaned:
            return cleaned
    return ""


# Return the only unique non-blank value or blank when ambiguous
def _single_or_blank(values: Any) -> str:
    cleaned_values = {value for value in (_as_str(v) for v in values) if value}
    if len(cleaned_values) == 1:
        return next(iter(cleaned_values))
    return ""
