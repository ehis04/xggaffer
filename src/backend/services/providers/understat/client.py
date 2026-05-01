"""
Understat client for raw football data payload retrieval

Handles Understat HTTP requests, retry behaviour, AJAX endpoints, and embedded page payload extraction without writing to the database
"""

from __future__ import annotations

import html
import json
import logging
import re
import time
from typing import Any

import requests
from django.conf import settings
from requests import Session
from requests.exceptions import RequestException, Timeout

from common.provider_policy import exponential_backoff_seconds

from .exceptions import (
    UnderstatAuthenticationError,
    UnderstatMalformedResponseError,
    UnderstatNotFoundError,
    UnderstatRateLimitError,
    UnderstatRequestError,
)

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------
# Understat client
# -------------------------------------------------------------------------

# Client for retrieving raw Understat page and AJAX payloads
class UnderstatClient:

    # Set up the client with request settings and default headers
    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: int | None = None,
        retry_count: int | None = None,
        request_delay_seconds: float | None = None,
        user_agent: str | None = None,
        session: Session | None = None,
    ) -> None:
        self.base_url = (base_url or settings.UNDERSTAT_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.UNDERSTAT_TIMEOUT_SECONDS
        self.retry_count = retry_count if retry_count is not None else settings.UNDERSTAT_RETRY_COUNT
        self.request_delay_seconds = float(
            request_delay_seconds
            if request_delay_seconds is not None
            else getattr(settings, "UNDERSTAT_REQUEST_DELAY_SECONDS", 2.0)
        )
        self.user_agent = user_agent or settings.UNDERSTAT_USER_AGENT

        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-GB,en;q=0.9",
                "Referer": self.base_url,
            }
        )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    # Fetch raw league-level team, date, and player payloads for a season
    def get_league_teams(self, league: str, season: str | int) -> dict[str, Any]:
        try:
            ajax_payload = self._fetch_league_data_api(league, season)
            teams = ajax_payload.get("teams")
            if not isinstance(teams, dict) or not teams:
                raise UnderstatMalformedResponseError(
                    f"Understat AJAX league payload missing 'teams' for '{league}/{season}'."
                )

            dates = ajax_payload.get("dates")
            players = ajax_payload.get("players")
        except (UnderstatRequestError, UnderstatMalformedResponseError):
            # Fallback for legacy pages that embed payloads inside the HTML
            page_html = self._fetch_page(f"/league/{league}/{season}")

            teams = self._extract_required_payload(
                page_html,
                candidates=("teamsData", "tableData", "teams"),
                context=f"league teams for {league}/{season}",
            )
            dates = self._extract_optional_payload(
                page_html,
                candidates=("datesData", "dates"),
            )
            players = self._extract_optional_payload(
                page_html,
                candidates=("playersData", "players"),
            )

        return {
            "league": str(league),
            "season": str(season),
            "teams": teams,
            "dates": dates,
            "players": players,
        }

    # Fetch raw league data from the Understat AJAX endpoint
    def _fetch_league_data_api(self, league: str, season: str | int) -> dict[str, Any]:
        # Prime cookies and context from the visible league page first
        self._request("GET", f"/league/{league}/{season}")

        response = self._request(
            "GET",
            f"/getLeagueData/{league}/{season}",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": f"{self.base_url}/league/{league}/{season}",
            },
        )

        return self._parse_json_dict(
            response.text,
            context=f"AJAX league data for '{league}/{season}'",
        )

    # Fetch the raw Understat player list for a team season
    def get_team_players(self, team_external_id: str, season: str | int) -> list[dict[str, Any]]:
        payload = self.get_team_season_payload(team_external_id, season)
        players = payload.get("players")

        if not isinstance(players, list):
            raise UnderstatMalformedResponseError(
                f"Expected a players list for team '{team_external_id}' season '{season}'."
            )

        return players

    # Fetch the raw Understat statistics payload for a team season
    def get_team_stats(self, team_external_id: str, season: str | int) -> dict[str, Any] | list[Any]:
        payload = self.get_team_season_payload(team_external_id, season)
        stats = payload.get("stats")

        if stats is None:
            raise UnderstatMalformedResponseError(
                f"Expected a stats payload for team '{team_external_id}' season '{season}'."
            )

        return stats

    # Fetch all useful raw team-season payloads from Understat
    def get_team_season_payload(self, team_external_id: str, season: str | int) -> dict[str, Any]:
        try:
            ajax_payload = self._fetch_team_data_api(team_external_id, season)
            return {
                "team_external_id": str(team_external_id),
                "season": str(season),
                "players": ajax_payload.get("players") or [],
                "stats": ajax_payload.get("history") or ajax_payload.get("statistics") or {},
                "dates": ajax_payload.get("dates"),
            }
        except (UnderstatRequestError, UnderstatMalformedResponseError):
            page_html = self._fetch_page(f"/team/{team_external_id}/{season}")

            players = self._extract_required_payload(
                page_html,
                candidates=("playersData", "players"),
                context=f"team players for {team_external_id}/{season}",
            )
            stats = self._extract_required_payload(
                page_html,
                candidates=("history", "statistics", "statsData", "stats"),
                context=f"team stats for {team_external_id}/{season}",
            )
            dates = self._extract_optional_payload(
                page_html,
                candidates=("datesData", "dates"),
            )

            return {
                "team_external_id": str(team_external_id),
                "season": str(season),
                "players": players,
                "stats": stats,
                "dates": dates,
            }

    # Fetch raw team data from the Understat AJAX endpoint
    def _fetch_team_data_api(self, team_external_id: str, season: str | int) -> dict[str, Any]:
        response = self._request(
            "GET",
            f"/getTeamData/{team_external_id}/{season}",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{self.base_url}/team/{team_external_id}/{season}",
            },
        )

        payload = self._parse_json_dict(
            response.text,
            context=f"AJAX team data for '{team_external_id}/{season}'",
        )

        if "players" not in payload:
            raise UnderstatMalformedResponseError(
                f"Understat AJAX team payload missing 'players' for '{team_external_id}/{season}'."
            )

        return payload

    # Fetch raw match data from the Understat AJAX endpoint
    def _fetch_match_data_api(self, match_id: str | int) -> dict[str, Any]:
        response = self._request(
            "GET",
            f"/getMatchData/{match_id}",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{self.base_url}/match/{match_id}",
            },
        )

        return self._parse_json_dict(
            response.text,
            context=f"AJAX match data for '{match_id}'",
        )

    # Fetch raw player-page payloads for a player
    def get_player_stats(
        self,
        player_external_id: str,
        season: str | int | None = None,
    ) -> dict[str, Any]:
        page_html = self._fetch_page(f"/player/{player_external_id}")

        groups = self._extract_optional_payload(
            page_html,
            candidates=("groupsData", "groups"),
        )
        matches = self._extract_optional_payload(
            page_html,
            candidates=("matchesData", "matches"),
        )
        shots = self._extract_optional_payload(
            page_html,
            candidates=("shotsData", "shots"),
        )

        if groups is None and matches is None and shots is None:
            raise UnderstatMalformedResponseError(
                f"No recognisable player payloads found for player '{player_external_id}'."
            )

        return {
            "player_external_id": str(player_external_id),
            "requested_season": str(season) if season is not None else None,
            "groups": groups,
            "matches": matches,
            "shots": shots,
        }

    # Fetch the raw roster payload for a match
    def get_match_roster(self, match_id: str | int) -> dict[str, Any]:
        try:
            ajax_payload = self._fetch_match_data_api(match_id)
            roster = ajax_payload.get("rosters")

            if isinstance(roster, dict):
                return roster

            raise UnderstatMalformedResponseError(
                f"Understat AJAX match payload missing 'rosters' for match '{match_id}'."
            )
        except (UnderstatRequestError, UnderstatMalformedResponseError):
            page_html = self._fetch_page(f"/match/{match_id}")

            roster = self._extract_optional_payload(
                page_html,
                candidates=("rostersData", "rosters"),
            )

            if not isinstance(roster, dict):
                raise UnderstatMalformedResponseError(
                    f"No roster data found for match '{match_id}'."
                )

            return roster

    # -------------------------------------------------------------------------
    # HTTP helpers
    # -------------------------------------------------------------------------

    # Fetch a raw HTML page from Understat
    def _fetch_page(self, path: str) -> str:
        response = self._request("GET", path)
        return response.text

    # Send an Understat request with retry and error conversion
    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None

        for attempt in range(self.retry_count + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.timeout_seconds,
                    **kwargs,
                )
                self._raise_for_status(response)
                if self.request_delay_seconds > 0:
                    time.sleep(self.request_delay_seconds)
                return response
            except (Timeout, RequestException, UnderstatRequestError) as exc:
                last_error = exc

                should_retry = attempt < self.retry_count and self._is_retryable_error(exc)
                if should_retry:
                    delay = exponential_backoff_seconds(attempt + 1, base=2.0, cap=30.0)
                    logger.warning(
                        "Understat request failed on attempt %s/%s for %s: %s (retry in %.2fs)",
                        attempt + 1,
                        self.retry_count + 1,
                        url,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                    continue

                if isinstance(exc, UnderstatRequestError):
                    raise

                raise UnderstatRequestError(f"Understat request failed for {url}: {exc}") from exc

        raise UnderstatRequestError(f"Understat request failed for {url}: {last_error}")

    # Parse raw response text into a JSON dictionary
    @staticmethod
    def _parse_json_dict(raw_text: str, *, context: str) -> dict[str, Any]:
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise UnderstatMalformedResponseError(
                f"Could not parse Understat {context}."
            ) from exc

        if not isinstance(payload, dict):
            raise UnderstatMalformedResponseError(
                f"Unexpected Understat payload shape for {context}."
            )

        return payload

    # Return True when a failed request should be retried
    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        if isinstance(exc, (Timeout,)):
            return True

        if isinstance(exc, UnderstatRateLimitError):
            return True

        if isinstance(exc, UnderstatRequestError) and not isinstance(
            exc,
            (UnderstatAuthenticationError, UnderstatNotFoundError),
        ):
            return True

        return False

    # Convert HTTP error responses into provider-specific exceptions
    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        status_code = response.status_code

        if 200 <= status_code < 300:
            return

        if status_code in {401, 403}:
            raise UnderstatAuthenticationError(
                f"Understat rejected the request with status {status_code}."
            )

        if status_code == 404:
            raise UnderstatNotFoundError("Requested Understat resource was not found.")

        if status_code == 429:
            raise UnderstatRateLimitError("Understat rate limit encountered.")

        raise UnderstatRequestError(
            f"Unexpected Understat response status {status_code}."
        )

    # -------------------------------------------------------------------------
    # Embedded payload extraction
    # -------------------------------------------------------------------------

    # Extract a required embedded payload from a page
    def _extract_required_payload(
        self,
        page_html: str,
        *,
        candidates: tuple[str, ...],
        context: str,
    ) -> Any:
        payload = self._extract_optional_payload(page_html, candidates=candidates)
        if payload is None:
            candidate_text = ", ".join(candidates)
            raise UnderstatMalformedResponseError(
                f"Could not locate any expected Understat payload ({candidate_text}) for {context}."
            )
        return payload

    # Extract the first available embedded payload from a list of variable names
    def _extract_optional_payload(
        self,
        page_html: str,
        *,
        candidates: tuple[str, ...],
    ) -> Any | None:
        for variable_name in candidates:
            payload = self._extract_named_payload(page_html, variable_name)
            if payload is not None:
                return payload
        return None

    # Extract one named embedded payload from an Understat HTML page
    def _extract_named_payload(self, page_html: str, variable_name: str) -> Any | None:
        json_parse_match = re.search(
            rf"{re.escape(variable_name)}\s*=\s*JSON\.parse\((?P<quote>['\"])(?P<data>.*?)(?<!\\)(?P=quote)\)",
            page_html,
            flags=re.DOTALL,
        )
        if json_parse_match:
            encoded = json_parse_match.group("data")
            decoded = self._decode_embedded_string(encoded)
            return self._loads_json(decoded, variable_name)

        direct_json_match = re.search(
            rf"{re.escape(variable_name)}\s*=\s*(?P<data>\{{.*?\}}|\[.*?\])\s*;",
            page_html,
            flags=re.DOTALL,
        )
        if direct_json_match:
            raw_json = html.unescape(direct_json_match.group("data"))
            return self._loads_json(raw_json, variable_name)

        return None

    # Decode an escaped JSON string from an Understat page
    @staticmethod
    def _decode_embedded_string(value: str) -> str:
        try:
            decoded = bytes(value, "utf-8").decode("unicode_escape")
        except UnicodeDecodeError:
            decoded = value

        return html.unescape(decoded)

    # Decode JSON and raise a provider-specific error on failure
    @staticmethod
    def _loads_json(value: str, variable_name: str) -> Any:
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise UnderstatMalformedResponseError(
                f"Failed to decode embedded Understat payload '{variable_name}'."
            ) from exc