from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests
from django.conf import settings

from apps.predictions.services.odds.exceptions import (
    OddsConfigurationError,
    OddsSourceError,
)

DEFAULT_BASE_URL = "https://api.the-odds-api.com"
DEFAULT_MARKETS = "h2h"
DEFAULT_ODDS_FORMAT = "decimal"
DEFAULT_DATE_FORMAT = "iso"
DEFAULT_REGIONS = "uk,eu"
DEFAULT_TIMEOUT_SECONDS = 15


class TheOddsApiClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.api_key = api_key or self._get_api_key()
        self.base_url = (base_url or getattr(settings, "THE_ODDS_API_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        self.timeout_seconds = timeout_seconds or getattr(
            settings,
            "THE_ODDS_API_TIMEOUT_SECONDS",
            DEFAULT_TIMEOUT_SECONDS,
        )
        self.session = session or requests.Session()

    def fetch_match_odds(
        self,
        *,
        sport_key: str,
        regions: str | list[str] | tuple[str, ...] | None = DEFAULT_REGIONS,
        bookmakers: str | list[str] | tuple[str, ...] | None = None,
        markets: str = DEFAULT_MARKETS,
        odds_format: str = DEFAULT_ODDS_FORMAT,
        date_format: str = DEFAULT_DATE_FORMAT,
        commence_time_from: datetime | str | None = None,
        commence_time_to: datetime | str | None = None,
    ) -> dict[str, Any]:
        if not sport_key:
            raise OddsConfigurationError("sport_key is required for odds requests.")

        params = self._build_odds_params(
            regions=regions,
            bookmakers=bookmakers,
            markets=markets,
            odds_format=odds_format,
            date_format=date_format,
            commence_time_from=commence_time_from,
            commence_time_to=commence_time_to,
        )

        endpoint = f"{self.base_url}/v4/sports/{sport_key}/odds"
        return self._get(endpoint, params)

    def fetch_upcoming_odds(
        self,
        *,
        sport_key: str,
        regions: str | list[str] | tuple[str, ...] | None = DEFAULT_REGIONS,
        bookmakers: str | list[str] | tuple[str, ...] | None = None,
        markets: str = DEFAULT_MARKETS,
        odds_format: str = DEFAULT_ODDS_FORMAT,
        date_format: str = DEFAULT_DATE_FORMAT,
        commence_time_from: datetime | str | None = None,
        commence_time_to: datetime | str | None = None,
    ) -> dict[str, Any]:
        return self.fetch_match_odds(
            sport_key=sport_key,
            regions=regions,
            bookmakers=bookmakers,
            markets=markets,
            odds_format=odds_format,
            date_format=date_format,
            commence_time_from=commence_time_from,
            commence_time_to=commence_time_to,
        )

    def _get(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise OddsSourceError(f"Odds source request failed: {exc}") from exc

        response_payload = self._safe_json(response)
        request_meta = self._extract_request_meta(response)

        if response.status_code >= 400:
            raise OddsSourceError(self._build_error_message(response, response_payload))

        if not isinstance(response_payload, list):
            raise OddsSourceError("Odds source returned an unexpected response shape.")

        return {
            "data": response_payload,
            "request_meta": request_meta,
            "source": "the_odds_api",
        }

    def _build_odds_params(
        self,
        *,
        regions: str | list[str] | tuple[str, ...] | None,
        bookmakers: str | list[str] | tuple[str, ...] | None,
        markets: str,
        odds_format: str,
        date_format: str,
        commence_time_from: datetime | str | None,
        commence_time_to: datetime | str | None,
    ) -> dict[str, str]:
        normalised_regions = self._normalise_csv_param(regions)
        normalised_bookmakers = self._normalise_csv_param(bookmakers)

        if not normalised_regions and not normalised_bookmakers:
            raise OddsConfigurationError(
                "Either regions or bookmakers must be provided for odds requests."
            )

        params: dict[str, str] = {
            "apiKey": self.api_key,
            "markets": markets,
            "oddsFormat": odds_format,
            "dateFormat": date_format,
        }

        if normalised_bookmakers:
            params["bookmakers"] = normalised_bookmakers
        elif normalised_regions:
            params["regions"] = normalised_regions

        if commence_time_from is not None:
            params["commenceTimeFrom"] = self._normalise_datetime_param(commence_time_from)

        if commence_time_to is not None:
            params["commenceTimeTo"] = self._normalise_datetime_param(commence_time_to)

        return params

    def _get_api_key(self) -> str:
        api_key = getattr(settings, "THE_ODDS_API_KEY", None) or os.getenv("THE_ODDS_API_KEY")
        if not api_key:
            raise OddsConfigurationError(
                "THE_ODDS_API_KEY is not configured in Django settings or environment."
            )
        return api_key

    def _normalise_csv_param(
        self,
        value: str | list[str] | tuple[str, ...] | None,
    ) -> str | None:
        if value is None:
            return None

        if isinstance(value, str):
            stripped_value = value.strip()
            return stripped_value or None

        if isinstance(value, (list, tuple)):
            items = [item.strip() for item in value if isinstance(item, str) and item.strip()]
            return ",".join(items) if items else None

        raise OddsConfigurationError("CSV query parameters must be a string, list, tuple, or None.")

    def _normalise_datetime_param(self, value: datetime | str) -> str:
        if isinstance(value, datetime):
            dt_value = value
        elif isinstance(value, str):
            iso_value = value.strip()
            if not iso_value:
                raise OddsConfigurationError("Datetime parameters cannot be blank.")
            try:
                dt_value = datetime.fromisoformat(iso_value.replace("Z", "+00:00"))
            except ValueError:
                return iso_value
        else:
            raise OddsConfigurationError("Datetime parameters must be datetime or ISO string.")

        if dt_value.tzinfo is None:
            dt_value = dt_value.replace(tzinfo=timezone.utc)
        else:
            dt_value = dt_value.astimezone(timezone.utc)

        dt_value = dt_value.replace(microsecond=0)
        return dt_value.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _extract_request_meta(self, response: requests.Response) -> dict[str, Any]:
        return {
            "status_code": response.status_code,
            "requests_remaining": self._coerce_int_header(response.headers.get("x-requests-remaining")),
            "requests_used": self._coerce_int_header(response.headers.get("x-requests-used")),
            "requests_last": self._coerce_int_header(response.headers.get("x-requests-last")),
        }

    def _coerce_int_header(self, value: str | None) -> int | None:
        if value is None:
            return None

        try:
            return int(value)
        except ValueError:
            return None

    def _safe_json(self, response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return None

    def _build_error_message(
        self,
        response: requests.Response,
        response_payload: Any,
    ) -> str:
        error_detail = None

        if isinstance(response_payload, dict):
            error_detail = (
                response_payload.get("message")
                or response_payload.get("error")
                or response_payload.get("detail")
            )

        if not error_detail:
            response_text = response.text.strip()
            error_detail = response_text or "Unknown odds source error."

        return f"The Odds API request failed with status {response.status_code}: {error_detail}"