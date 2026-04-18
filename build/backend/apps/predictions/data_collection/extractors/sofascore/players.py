from __future__ import annotations

import re
from typing import Any, Optional

import pandas as pd
import tls_requests

SOFASCORE_API_BASE = "https://api.sofascore.com/api/v1"
DEFAULT_TIMEOUT = 30
DEFAULT_LIMIT = 100

DEFAULT_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "origin": "https://www.sofascore.com",
    "referer": "https://www.sofascore.com/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    ),
}

SOFASCORE_LEAGUE_ALIASES = {
    "EPL": "Premier League",
    "La_Liga": "La Liga",
    "Bundesliga": "Bundesliga",
    "Serie_A": "Serie A",
    "Ligue_1": "Ligue 1",
    "RFPL": "Premier Liga",
}


class SofascorePlayersExtractionError(RuntimeError):
    pass


def fetch_sofascore_players(
    league: str,
    season: str,
    accumulation: str = "total",
    group: str = "summary",
    order: str = "-rating",
    limit: int = DEFAULT_LIMIT,
    request_timeout: int = DEFAULT_TIMEOUT,
    session: Optional[tls_requests.Client] = None,
) -> pd.DataFrame:
    created_session = session is None
    http = session or _build_session()

    try:
        requested_league = str(league).strip()
        requested_season = str(season).strip()

        tournaments = _fetch_unique_tournaments(
            session=http,
            request_timeout=request_timeout,
        )
        tournament = _select_tournament(
            tournaments=tournaments,
            requested_league=requested_league,
        )

        seasons = _fetch_tournament_seasons(
            session=http,
            tournament_id=int(tournament["id"]),
            request_timeout=request_timeout,
        )
        selected_season = _select_season(
            seasons=seasons,
            requested_season=requested_season,
        )

        rows = _read_player_statistics(
            session=http,
            tournament_id=int(tournament["id"]),
            season_id=int(selected_season["id"]),
            accumulation=accumulation,
            group=group,
            order=order,
            limit=limit,
            request_timeout=request_timeout,
        )

        if not rows:
            return pd.DataFrame()

        df = pd.json_normalize(rows, sep="__")

        if df.empty:
            return df

        df["requested_league"] = requested_league
        df["requested_season"] = requested_season
        df["sofascore_tournament_id"] = int(tournament["id"])
        df["sofascore_tournament_name"] = tournament.get("name")
        df["sofascore_season_id"] = int(selected_season["id"])
        df["sofascore_season_name"] = selected_season.get("name")
        df["stat_group"] = group
        df["stat_accumulation"] = accumulation
        df["stat_order"] = order

        return df.reset_index(drop=True)
    finally:
        if created_session:
            http.close()


def _build_session() -> tls_requests.Client:
    session = tls_requests.Client()
    session.headers.update(DEFAULT_HEADERS)
    return session


def _fetch_unique_tournaments(
    session: tls_requests.Client,
    request_timeout: int,
) -> list[dict[str, Any]]:
    url = f"{SOFASCORE_API_BASE}/config/default-unique-tournaments/EN/football"
    payload = _get_json(session=session, url=url, request_timeout=request_timeout)
    tournaments = payload.get("uniqueTournaments") or []

    if not isinstance(tournaments, list) or not tournaments:
        raise SofascorePlayersExtractionError(
            "Sofascore unique tournament list was empty or malformed."
        )

    return tournaments


def _fetch_tournament_seasons(
    session: tls_requests.Client,
    tournament_id: int,
    request_timeout: int,
) -> list[dict[str, Any]]:
    url = f"{SOFASCORE_API_BASE}/unique-tournament/{tournament_id}/seasons"
    payload = _get_json(session=session, url=url, request_timeout=request_timeout)
    seasons = payload.get("seasons") or []

    if not isinstance(seasons, list) or not seasons:
        raise SofascorePlayersExtractionError(
            f"No Sofascore seasons were returned for tournament_id={tournament_id}."
        )

    return seasons


def _read_player_statistics(
    session: tls_requests.Client,
    tournament_id: int,
    season_id: int,
    accumulation: str,
    group: str,
    order: str,
    limit: int,
    request_timeout: int,
) -> list[dict[str, Any]]:
    url = f"{SOFASCORE_API_BASE}/unique-tournament/{tournament_id}/season/{season_id}/statistics"
    offset = 0
    rows: list[dict[str, Any]] = []
    seen_page_signatures: set[tuple[Any, Any, int]] = set()

    while True:
        params = {
            "accumulation": accumulation,
            "group": group,
            "limit": limit,
            "offset": offset,
            "order": order,
        }

        payload = _get_json(
            session=session,
            url=url,
            params=params,
            request_timeout=request_timeout,
        )

        page_rows = payload.get("results") or payload.get("items") or []

        if not isinstance(page_rows, list) or not page_rows:
            break

        signature = _build_page_signature(page_rows)
        if signature in seen_page_signatures:
            break
        seen_page_signatures.add(signature)

        for row in page_rows:
            if not isinstance(row, dict):
                continue

            enriched_row = dict(row)
            enriched_row["_page_offset"] = offset
            enriched_row["_page_limit"] = limit
            rows.append(enriched_row)

        if len(page_rows) < limit:
            break

        offset += limit

    return rows


def _get_json(
    session: tls_requests.Client,
    url: str,
    request_timeout: int,
    params: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    response = session.get(url, params=params, timeout=request_timeout)

    if response.status_code != 200:
        raise SofascorePlayersExtractionError(
            f"Sofascore request failed with status {response.status_code} for {response.url}."
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise SofascorePlayersExtractionError(
            f"Sofascore returned non-JSON content for {response.url}."
        ) from exc

    if not isinstance(payload, dict):
        raise SofascorePlayersExtractionError(
            f"Sofascore returned an unexpected payload shape for {response.url}."
        )

    return payload


def _select_tournament(
    tournaments: list[dict[str, Any]],
    requested_league: str,
) -> dict[str, Any]:
    aliases = {
        _normalise_token(requested_league),
        _normalise_token(SOFASCORE_LEAGUE_ALIASES.get(requested_league, requested_league)),
    }

    for tournament in tournaments:
        name = str(tournament.get("name", "")).strip()
        slug = str(tournament.get("slug", "")).strip()

        tournament_tokens = {
            _normalise_token(name),
            _normalise_token(slug),
        }

        if aliases & tournament_tokens:
            return tournament

    available_names = sorted(
        {
            str(tournament.get("name", "")).strip()
            for tournament in tournaments
            if tournament.get("name")
        }
    )

    raise SofascorePlayersExtractionError(
        f'Could not resolve Sofascore tournament for league="{requested_league}". '
        f"Available examples: {available_names[:15]}"
    )


def _select_season(
    seasons: list[dict[str, Any]],
    requested_season: str,
) -> dict[str, Any]:
    requested = str(requested_season).strip()

    for season in seasons:
        year = str(season.get("year", "")).strip()
        name = str(season.get("name", "")).strip()

        if year == requested:
            return season

        if name.startswith(requested):
            return season

        if f"{requested}/" in name or f"{requested}-" in name:
            return season

        if len(requested) == 4 and requested.isdigit():
            short_year = requested[2:]
            if year.startswith(f"{short_year}/"):
                return season

    available = [
        {
            "id": season.get("id"),
            "year": season.get("year"),
            "name": season.get("name"),
        }
        for season in seasons[:15]
    ]

    raise SofascorePlayersExtractionError(
        f'Could not resolve Sofascore season for season="{requested_season}". '
        f"Available examples: {available}"
    )


def _build_page_signature(page_rows: list[dict[str, Any]]) -> tuple[Any, Any, int]:
    first = page_rows[0] if page_rows else {}
    last = page_rows[-1] if page_rows else {}

    return (
        _nested_value(first, "player", "id"),
        _nested_value(last, "player", "id"),
        len(page_rows),
    )


def _nested_value(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload

    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)

    return current


def _normalise_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())