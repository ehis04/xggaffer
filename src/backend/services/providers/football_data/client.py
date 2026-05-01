"""
HTTP client for the football-data provider service layer.

Handles authenticated requests, throttling, retries, and response validation.
"""

import logging
import re
from threading import Lock
from time import monotonic, sleep

import requests
from django.conf import settings

from .exceptions import (
    FootballDataAuthenticationError,
    FootballDataMalformedResponseError,
    FootballDataNotFoundError,
    FootballDataRateLimitError,
    FootballDataRequestError,
)

logger = logging.getLogger(__name__)


_throttle_lock = Lock()
_last_request_started_at: float | None = None
_COMPETITION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


# Client for making requests to the football-data API
class FootballDataClient:
    # Set up the client with settings, request limits, and an optional session
    def __init__(
        self,
        api_token=None,
        base_url=None,
        timeout=None,
        retry_count=None,
        session=None,
    ):
        self.api_token = api_token if api_token is not None else settings.FOOTBALL_DATA_API_TOKEN
        self.base_url = (
            base_url if base_url is not None else settings.FOOTBALL_DATA_API_BASE_URL
        ).rstrip("/")
        self.timeout = (
            timeout if timeout is not None else settings.FOOTBALL_DATA_TIMEOUT_SECONDS
        )
        self.retry_count = (
            retry_count
            if retry_count is not None
            else getattr(settings, "FOOTBALL_DATA_RETRY_COUNT", 0)
        )
        self.max_calls_per_minute = max(
            1,
            int(getattr(settings, "FOOTBALL_DATA_MAX_CALLS_PER_MINUTE", 10)),
        )
        self.min_request_interval_seconds = float(
            getattr(
                settings,
                "FOOTBALL_DATA_MIN_REQUEST_INTERVAL_SECONDS",
                60.0 / float(self.max_calls_per_minute),
            )
        )
        self.enabled = getattr(settings, "FOOTBALL_DATA_ENABLED", True)
        self.session = session or requests.Session()

    # Pause requests when needed to stay within the configured rate limit
    def _throttle(self):
        global _last_request_started_at

        if self.min_request_interval_seconds <= 0:
            return

        with _throttle_lock:
            now = monotonic()
            if _last_request_started_at is None:
                _last_request_started_at = now
                return

            elapsed = now - _last_request_started_at
            remaining = self.min_request_interval_seconds - elapsed
            if remaining > 0:
                sleep(remaining)

            _last_request_started_at = monotonic()

    # Build the request headers for the API call
    def _build_headers(self):
        if not self.api_token:
            raise FootballDataAuthenticationError(
                "Football-data API token is not configured."
            )

        return {
            "X-Auth-Token": self.api_token,
            "Accept": "application/json",
        }

    # Build the full request URL from a path
    def _build_url(self, path):
        normalized_path = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}{normalized_path}"

    # Parse the response body as JSON
    def _parse_json(self, response):
        try:
            return response.json()
        except ValueError as exc:
            raise FootballDataMalformedResponseError(
                "Football-data response did not contain valid JSON."
            ) from exc

    # Raise the correct custom error for an HTTP status code
    def _raise_for_status(self, response):
        status_code = response.status_code

        if status_code in (401, 403):
            raise FootballDataAuthenticationError(
                f"Football-data authentication failed with status {status_code}."
            )

        if status_code == 404:
            raise FootballDataNotFoundError("Football-data resource was not found.")

        if status_code == 429:
            raise FootballDataRateLimitError("Football-data rate limit exceeded.")

        if 400 <= status_code < 600:
            raise FootballDataRequestError(
                f"Football-data request failed with status {status_code}."
            )

    # Remove empty values and normalise request parameters
    def _clean_params(self, params=None):
        if not params:
            return None

        cleaned = {}
        for key, value in params.items():
            if value is None or value == "":
                continue
            if isinstance(value, (list, tuple, set)):
                if not value:
                    continue
                cleaned[key] = ",".join(str(item) for item in value)
            else:
                cleaned[key] = value

        return cleaned or None

    # Validate and clean a competition ID before using it in a request
    def _normalize_competition_id(self, competition_id):
        value = str(competition_id).strip()
        if not value or not _COMPETITION_ID_PATTERN.fullmatch(value):
            raise FootballDataRequestError(
                "Invalid competition_id. Use a real football-data competition ID/code "
                "(for example: PL, PD, BL1, SA, FL1, or 2021) and do not use placeholders."
            )
        return value

    # Send a request with retry handling and error conversion
    def _request(self, method, path, params=None):
        if not self.enabled:
            raise FootballDataRequestError("Football-data provider is disabled.")

        url = self._build_url(path)
        headers = self._build_headers()
        attempts = self.retry_count + 1

        for attempt in range(1, attempts + 1):
            try:
                self._throttle()
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=self._clean_params(params),
                    timeout=self.timeout,
                )
            except requests.Timeout as exc:
                if attempt < attempts:
                    logger.warning(
                        "Football-data request timed out, retrying %s/%s for %s %s",
                        attempt,
                        attempts,
                        method,
                        path,
                    )
                    continue
                raise FootballDataRequestError(
                    f"Football-data request timed out for {method} {path}."
                ) from exc
            except requests.RequestException as exc:
                if attempt < attempts:
                    logger.warning(
                        "Football-data request error, retrying %s/%s for %s %s",
                        attempt,
                        attempts,
                        method,
                        path,
                    )
                    continue
                raise FootballDataRequestError(
                    f"Football-data request error for {method} {path}."
                ) from exc

            if 200 <= response.status_code < 300:
                return self._parse_json(response)

            self._raise_for_status(response)

        raise FootballDataRequestError(
            f"Football-data request failed unexpectedly for {method} {path}."
        )

    # Get the list of competitions from the API
    def get_competitions(self, areas=None):
        return self._request(
            "GET",
            "/competitions",
            params={
                "areas": areas,
            },
        )

    # Get one team by its ID
    def get_team(self, team_id):
        return self._request("GET", f"/teams/{team_id}")

    # Get the squad list for a team
    def get_team_squad(self, team_id):
        payload = self.get_team(team_id)
        squad = payload.get("squad")

        if squad is None:
            raise FootballDataMalformedResponseError(
                "Football-data team payload did not include a squad field."
            )

        return squad

    # Get one competition by its ID or code
    def get_competition(self, competition_id):
        normalized_competition_id = self._normalize_competition_id(competition_id)
        return self._request("GET", f"/competitions/{normalized_competition_id}")

    # Get the teams in a competition for an optional season
    def get_competition_teams(self, competition_id, season=None):
        normalized_competition_id = self._normalize_competition_id(competition_id)
        return self._request(
            "GET",
            f"/competitions/{normalized_competition_id}/teams",
            params={
                "season": season,
            },
        )

    # Get the league table for a competition and optional season
    def get_competition_table(self, competition_id, season=None):
        normalized_competition_id = self._normalize_competition_id(competition_id)
        return self._request(
            "GET",
            f"/competitions/{normalized_competition_id}/standings",
            params={
                "season": season,
            },
        )

    # Get matches for a competition with optional filters
    def get_competition_matches(
        self,
        competition_id,
        season=None,
        matchday=None,
        status=None,
        date_from=None,
        date_to=None,
        stage=None,
        group=None,
    ):
        normalized_competition_id = self._normalize_competition_id(competition_id)
        return self._request(
            "GET",
            f"/competitions/{normalized_competition_id}/matches",
            params={
                "season": season,
                "matchday": matchday,
                "status": status,
                "dateFrom": date_from,
                "dateTo": date_to,
                "stage": stage,
                "group": group,
            },
        )

    # Get top scorers for a competition with optional filters
    def get_competition_scorers(
        self,
        competition_id,
        season=None,
        matchday=None,
    ):
        normalized_competition_id = self._normalize_competition_id(competition_id)
        return self._request(
            "GET",
            f"/competitions/{normalized_competition_id}/scorers",
            params={
                "season": season,
                "matchday": matchday,
            },
        )