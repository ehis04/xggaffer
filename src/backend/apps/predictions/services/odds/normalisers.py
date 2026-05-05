from __future__ import annotations

from datetime import datetime

from django.utils.dateparse import parse_datetime
from django.utils.text import slugify

THE_ODDS_API_SOURCE = "the_odds_api"
SUPPORTED_MARKET_KEY = "h2h"
SERVICE_MARKET_TYPE = "1x2"
DRAW_OUTCOME_NAMES = frozenset({"draw", "the draw", "tie"})


def normalise_the_odds_api_response(raw_response: list[dict] | dict) -> list[dict]:
    fixtures = _extract_fixture_rows(raw_response)
    normalised_rows: list[dict] = []

    for fixture in fixtures:
        normalised_rows.extend(normalise_the_odds_api_fixture(fixture))

    return normalised_rows


def normalise_the_odds_api_fixture(fixture: dict) -> list[dict]:
    external_fixture_id = _normalise_fixture_id(fixture.get("id"))
    home_team_source = _normalise_text(fixture.get("home_team"))
    away_team_source = _normalise_text(fixture.get("away_team"))
    commence_time = _parse_timestamp(fixture.get("commence_time"))

    if not external_fixture_id:
        return []

    if not home_team_source or not away_team_source or commence_time is None:
        return []

    bookmakers = fixture.get("bookmakers")
    if not isinstance(bookmakers, list):
        return []

    normalised_rows: list[dict] = []

    for bookmaker in bookmakers:
        row = _normalise_bookmaker_quote(
            bookmaker=bookmaker,
            external_fixture_id=external_fixture_id,
            home_team_source=home_team_source,
            away_team_source=away_team_source,
            commence_time=commence_time,
        )
        if row is not None:
            normalised_rows.append(row)

    return normalised_rows


def _extract_fixture_rows(raw_response: list[dict] | dict) -> list[dict]:
    if isinstance(raw_response, list):
        return [row for row in raw_response if isinstance(row, dict)]

    if isinstance(raw_response, dict):
        data = raw_response.get("data")
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]

    return []


def _normalise_bookmaker_quote(
    bookmaker: dict,
    external_fixture_id: str,
    home_team_source: str,
    away_team_source: str,
    commence_time: datetime,
) -> dict | None:
    bookmaker_name = _normalise_bookmaker_name(bookmaker)
    if not bookmaker_name:
        return None

    market = _extract_h2h_market(bookmaker)
    if market is None:
        return None

    prices = _extract_1x2_prices(
        market=market,
        home_team_source=home_team_source,
        away_team_source=away_team_source,
    )
    if prices is None:
        return None

    last_seen_at = _parse_timestamp(
        bookmaker.get("last_update") or market.get("last_update")
    )

    return {
        "bookmaker_name": bookmaker_name,
        "bookmaker_slug": slugify(bookmaker_name),
        "bookmaker_key": _normalise_text(bookmaker.get("key")),
        "bookmaker_source": THE_ODDS_API_SOURCE,
        "external_fixture_id": external_fixture_id,
        "home_team_source": home_team_source,
        "away_team_source": away_team_source,
        "commence_time": commence_time,
        "market_type": SERVICE_MARKET_TYPE,
        "home_odds": prices["home_odds"],
        "draw_odds": prices["draw_odds"],
        "away_odds": prices["away_odds"],
        "last_seen_at": last_seen_at,
    }


def _normalise_bookmaker_name(bookmaker: dict) -> str | None:
    title = _normalise_text(bookmaker.get("title"))
    if title:
        return title

    key = _normalise_text(bookmaker.get("key"))
    if key:
        return key.replace("_", " ").title()

    return None


def _extract_h2h_market(bookmaker: dict) -> dict | None:
    markets = bookmaker.get("markets")
    if not isinstance(markets, list):
        return None

    for market in markets:
        if not isinstance(market, dict):
            continue
        if market.get("key") == SUPPORTED_MARKET_KEY:
            return market

    return None


def _extract_1x2_prices(
    market: dict,
    home_team_source: str,
    away_team_source: str,
) -> dict | None:
    outcomes = market.get("outcomes")
    if not isinstance(outcomes, list):
        return None

    home_key = home_team_source.casefold()
    away_key = away_team_source.casefold()

    prices_by_name: dict[str, float] = {}

    for outcome in outcomes:
        if not isinstance(outcome, dict):
            continue

        outcome_name = _normalise_text(outcome.get("name"))
        outcome_price = _coerce_float(outcome.get("price"))

        if not outcome_name or outcome_price is None:
            continue

        prices_by_name[outcome_name.casefold()] = outcome_price

    home_odds = prices_by_name.get(home_key)
    away_odds = prices_by_name.get(away_key)
    draw_odds = _extract_draw_odds(prices_by_name)

    if home_odds is None or draw_odds is None or away_odds is None:
        return None

    return {
        "home_odds": home_odds,
        "draw_odds": draw_odds,
        "away_odds": away_odds,
    }


def _extract_draw_odds(prices_by_name: dict[str, float]) -> float | None:
    for draw_name in DRAW_OUTCOME_NAMES:
        draw_odds = prices_by_name.get(draw_name)
        if draw_odds is not None:
            return draw_odds
    return None


def _normalise_fixture_id(value: object) -> str | None:
    if value is None:
        return None

    text_value = str(value).strip()
    if not text_value:
        return None

    return text_value


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None

    parsed_value = parse_datetime(value)
    if parsed_value is not None:
        return parsed_value

    if value.endswith("Z"):
        return parse_datetime(value.replace("Z", "+00:00"))

    return None


def _normalise_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    text_value = value.strip()
    if not text_value:
        return None

    return text_value


def _coerce_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        stripped_value = value.strip()
        if not stripped_value:
            return None
        try:
            return float(stripped_value)
        except ValueError:
            return None

    return None