from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from common.utils import latest_datetime

from apps.predictions.models import Bookmaker, BookmakerQuote, FixtureOddsSnapshot
from apps.predictions.services.odds.client import DEFAULT_REGIONS, TheOddsApiClient
from apps.predictions.services.odds.devig import devig_quote_dict, validate_quote_odds
from apps.predictions.services.odds.exceptions import (
    OddsDataUnavailableError,
    OddsMatchingError,
    OddsPersistenceError,
)
from apps.predictions.services.odds.matcher import match_fixture_names
from apps.predictions.services.odds.normalisers import normalise_the_odds_api_response

_logger = logging.getLogger(__name__)

UPCOMING_ODDS_SPORT_KEY_TO_LEAGUE = {
    "soccer_epl": "EPL",
    "soccer_spain_la_liga": "La_Liga",
    "soccer_germany_bundesliga": "Bundesliga",
    "soccer_italy_serie_a": "Serie_A",
    "soccer_france_ligue_one": "Ligue_1",
}

class OddsComparisonService:
    def __init__(self, *, client: TheOddsApiClient | None = None) -> None:
        self.client = client or TheOddsApiClient()

    def get_fixture_odds_comparison(
        self,
        *,
        sport_key: str,
        league: str,
        season: str,
        regions: str | list[str] | tuple[str, ...] | None = DEFAULT_REGIONS,
        bookmakers: str | list[str] | tuple[str, ...] | None = None,
        markets: str = "h2h",
        odds_format: str = "decimal",
        date_format: str = "iso",
        commence_time_from: datetime | str | None = None,
        commence_time_to: datetime | str | None = None,
        persist: bool = False,
    ) -> dict[str, Any]:
        raw_response = self.client.fetch_match_odds(
            sport_key=sport_key,
            regions=regions,
            bookmakers=bookmakers,
            markets=markets,
            odds_format=odds_format,
            date_format=date_format,
            commence_time_from=commence_time_from,
            commence_time_to=commence_time_to,
        )

        return self._build_fixture_payload(
            raw_response=raw_response,
            sport_key=sport_key,
            league=league,
            season=season,
            persist=persist,
        )

    def fetch_and_store_fixture_odds(
        self,
        *,
        sport_key: str,
        league: str,
        season: str,
        regions: str | list[str] | tuple[str, ...] | None = DEFAULT_REGIONS,
        bookmakers: str | list[str] | tuple[str, ...] | None = None,
        markets: str = "h2h",
        odds_format: str = "decimal",
        date_format: str = "iso",
        commence_time_from: datetime | str | None = None,
        commence_time_to: datetime | str | None = None,
    ) -> dict[str, Any]:
        return self.get_fixture_odds_comparison(
            sport_key=sport_key,
            league=league,
            season=season,
            regions=regions,
            bookmakers=bookmakers,
            markets=markets,
            odds_format=odds_format,
            date_format=date_format,
            commence_time_from=commence_time_from,
            commence_time_to=commence_time_to,
            persist=True,
        )

    def refresh_upcoming_fixture_odds(
        self,
        *,
        sport_keys: list[str] | tuple[str, ...] | None = None,
        max_fixtures: int | None = None,
        lookahead_hours: int = 72,
        bookmakers: str | list[str] | tuple[str, ...] | None = None,
        persist: bool = True,
    ) -> dict[str, Any]:
        selected_sport_keys = tuple(sport_keys or UPCOMING_ODDS_SPORT_KEY_TO_LEAGUE.keys())

        if max_fixtures is not None and max_fixtures <= 0:
            return {
                "sport_keys_processed": [],
                "leagues_processed": [],
                "fixtures_seen": 0,
                "snapshots_created": 0,
                "requests_used": 0,
                "errors": [],
                "max_fixtures": max_fixtures,
                "lookahead_hours": lookahead_hours,
                "bookmakers_requested": list(bookmakers) if isinstance(bookmakers, (list, tuple)) else bookmakers,
            }

        now = timezone.now()
        commence_time_to = now + timedelta(hours=lookahead_hours)

        remaining_fixture_budget = max_fixtures
        fixtures_seen = 0
        snapshots_created = 0
        requests_used = 0
        processed_sport_keys: list[str] = []
        errors: list[dict[str, str]] = []

        for sport_key in selected_sport_keys:
            if remaining_fixture_budget is not None and remaining_fixture_budget <= 0:
                break

            try:
                raw_response = self.client.fetch_match_odds(
                    sport_key=sport_key,
                    regions=DEFAULT_REGIONS,
                    bookmakers=bookmakers,
                    markets="h2h",
                    odds_format="decimal",
                    date_format="iso",
                    commence_time_from=now,
                    commence_time_to=commence_time_to,
                )
                requests_used += 1

                raw_events = list(raw_response.get("data", []))
                if remaining_fixture_budget is not None:
                    raw_events = raw_events[:remaining_fixture_budget]

                if not raw_events:
                    continue

                bounded_response = {
                    **raw_response,
                    "data": raw_events,
                }

                fixtures_seen += len(raw_events)

                payload = self._build_fixture_payload(
                    raw_response=bounded_response,
                    sport_key=sport_key,
                    league=self._league_for_sport_key(sport_key),
                    season=self._season_for_upcoming_events(raw_events),
                    persist=persist,
                )

                processed_sport_keys.append(sport_key)

                if persist:
                    snapshots_created += payload["fixture_count"]

                if remaining_fixture_budget is not None:
                    remaining_fixture_budget -= payload["fixture_count"]

            except (OddsDataUnavailableError, OddsMatchingError) as exc:
                _logger.warning(
                    "Upcoming odds refresh skipped for %s: %s",
                    sport_key,
                    exc,
                )
                errors.append(
                    {
                        "sport_key": sport_key,
                        "error": str(exc),
                    }
                )
            except Exception as exc:
                _logger.warning(
                    "Upcoming odds refresh failed for %s: %s",
                    sport_key,
                    exc,
                )
                errors.append(
                    {
                        "sport_key": sport_key,
                        "error": str(exc),
                    }
                )

        return {
            "sport_keys_processed": processed_sport_keys,
            "leagues_processed": [self._league_for_sport_key(key) for key in processed_sport_keys],
            "fixtures_seen": fixtures_seen,
            "snapshots_created": snapshots_created,
            "requests_used": requests_used,
            "errors": errors,
            "max_fixtures": max_fixtures,
            "lookahead_hours": lookahead_hours,
            "bookmakers_requested": list(bookmakers) if isinstance(bookmakers, (list, tuple)) else bookmakers,
        }

    def refresh_fixture_odds_snapshot(
        self,
        *,
        sport_key: str,
        league: str,
        season: str,
        home_team: str,
        away_team: str,
        external_fixture_id: str | None = None,
        commence_time: datetime | str | None = None,
        bookmakers: str | list[str] | tuple[str, ...] | None = None,
        regions: str | list[str] | tuple[str, ...] | None = DEFAULT_REGIONS,
        markets: str = "h2h",
        odds_format: str = "decimal",
        date_format: str = "iso",
    ) -> dict[str, Any]:
        commence_dt = self._coerce_datetime(commence_time)

        commence_time_from = None
        commence_time_to = None
        if commence_dt is not None:
            commence_time_from = commence_dt - timedelta(hours=6)
            commence_time_to = commence_dt + timedelta(hours=6)

        payload = self.get_fixture_odds_comparison(
            sport_key=sport_key,
            league=league,
            season=season,
            regions=regions,
            bookmakers=bookmakers,
            markets=markets,
            odds_format=odds_format,
            date_format=date_format,
            commence_time_from=commence_time_from,
            commence_time_to=commence_time_to,
            persist=True,
        )

        fixture = self._select_fixture_from_payload(
            fixtures=payload["fixtures"],
            external_fixture_id=external_fixture_id,
            home_team=home_team,
            away_team=away_team,
            commence_time=commence_dt,
            league=league,
            season=season,
        )

        return {
            "external_fixture_id": fixture["external_fixture_id"],
            "snapshot_id": fixture["snapshot_id"],
            "home_team": fixture["home_team"],
            "away_team": fixture["away_team"],
            "league": fixture["league"],
            "season": fixture["season"],
            "commence_time": fixture["commence_time"],
            "bookmaker_source": fixture["bookmaker_source"],
            "bookmaker_quote_count": len(fixture["bookmaker_quotes"]),
        }


    def _select_fixture_from_payload(
        self,
        *,
        fixtures: list[dict[str, Any]],
        external_fixture_id: str | None,
        home_team: str,
        away_team: str,
        commence_time: datetime | None,
        league: str,
        season: str,
    ) -> dict[str, Any]:
        serialised_commence_time = self._serialise_datetime(commence_time)

        for fixture in fixtures:
            if external_fixture_id and fixture["external_fixture_id"] == external_fixture_id:
                return fixture

        for fixture in fixtures:
            if (
                fixture["home_team"].lower() == home_team.lower()
                and fixture["away_team"].lower() == away_team.lower()
            ):
                if serialised_commence_time is None or fixture["commence_time"] == serialised_commence_time:
                    return fixture

        raise OddsDataUnavailableError(
            f"No odds snapshot match found for {home_team} vs {away_team} in {league} {season}."
        )

    def _league_for_sport_key(self, sport_key: str) -> str:
        return UPCOMING_ODDS_SPORT_KEY_TO_LEAGUE.get(sport_key, sport_key)


    def _season_for_upcoming_events(self, raw_events: list[dict[str, Any]]) -> str:
        for event in raw_events:
            commence_time = self._coerce_datetime(event.get("commence_time"))
            if commence_time is not None:
                return self._season_for_commence_time(commence_time)

        return self._season_for_commence_time(None)


    def _season_for_commence_time(self, commence_time: datetime | None) -> str:
        if commence_time is None:
            now = timezone.now()
            start_year = now.year - 1 if now.month < 7 else now.year
            return str(start_year)

        if timezone.is_aware(commence_time):
            commence_time = timezone.localtime(commence_time)

        start_year = commence_time.year - 1 if commence_time.month < 7 else commence_time.year
        return str(start_year)


    def _coerce_datetime(self, value: datetime | str | None) -> datetime | None:
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
            
    def get_consensus_market_view(self, quote_rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not quote_rows:
            raise OddsDataUnavailableError("No valid bookmaker quotes are available for consensus.")

        quote_count = len(quote_rows)
        consensus_home_probability = sum(row["devig_home"] for row in quote_rows) / quote_count
        consensus_draw_probability = sum(row["devig_draw"] for row in quote_rows) / quote_count
        consensus_away_probability = sum(row["devig_away"] for row in quote_rows) / quote_count

        consensus_market_favourite = max(
            (
                ("home", consensus_home_probability),
                ("draw", consensus_draw_probability),
                ("away", consensus_away_probability),
            ),
            key=lambda item: item[1],
        )[0]

        latest_seen_at = latest_datetime(
            *(self._coerce_datetime(row.get("last_seen_at")) for row in quote_rows)
        )

        return {
            "quote_count": quote_count,
            "consensus_home_probability": consensus_home_probability,
            "consensus_draw_probability": consensus_draw_probability,
            "consensus_away_probability": consensus_away_probability,
            "market_favourite": consensus_market_favourite,
            "latest_last_seen_at": self._serialise_datetime(latest_seen_at),
        }

    def _build_fixture_payload(
        self,
        *,
        raw_response: dict[str, Any],
        sport_key: str,
        league: str,
        season: str,
        persist: bool,
    ) -> dict[str, Any]:
        normalised_rows = normalise_the_odds_api_response(raw_response)

        if not normalised_rows:
            raise OddsDataUnavailableError("No supported odds rows were returned by the source.")

        processed_rows = self._prepare_quote_rows(normalised_rows)

        if not processed_rows:
            raise OddsDataUnavailableError("No valid odds quotes were available after processing.")

        fixture_groups = self._group_rows_by_fixture(processed_rows)

        fetched_at = timezone.now()
        persisted_snapshots_by_fixture: dict[tuple, FixtureOddsSnapshot] = {}

        if persist:
            persisted_snapshots_by_fixture = self._persist_fixture_groups(
                fixture_groups=fixture_groups,
                league=league,
                season=season,
                fetched_at=fetched_at,
            )

        fixtures_payload: list[dict[str, Any]] = []

        for fixture_key, quote_rows in fixture_groups.items():
            first_row = quote_rows[0]
            snapshot = persisted_snapshots_by_fixture.get(fixture_key)

            fixtures_payload.append(
                {
                    "external_fixture_id": first_row["external_fixture_id"],
                    "bookmaker_source": first_row["bookmaker_source"],
                    "league": league,
                    "season": season,
                    "home_team": first_row["home_team"],
                    "away_team": first_row["away_team"],
                    "source_home_team": first_row["source_home_team"],
                    "source_away_team": first_row["source_away_team"],
                    "commence_time": self._serialise_datetime(first_row["commence_time"]),
                    "market_type": first_row["market_type"],
                    "snapshot_id": snapshot.id if snapshot else None,
                    "bookmaker_quotes": [self._serialise_quote_row(row) for row in quote_rows],
                    "consensus": self.get_consensus_market_view(quote_rows),
                }
            )

        fixtures_payload.sort(
            key=lambda fixture: (
                fixture["commence_time"] or "",
                fixture["home_team"],
                fixture["away_team"],
            )
        )

        return {
            "source": raw_response.get("source", "the_odds_api"),
            "sport_key": sport_key,
            "league": league,
            "season": season,
            "request_meta": raw_response.get("request_meta", {}),
            "fixture_count": len(fixtures_payload),
            "fixtures": fixtures_payload,
        }

    def _prepare_quote_rows(self, normalised_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        processed_rows: list[dict[str, Any]] = []
        matching_errors: list[OddsMatchingError] = []

        for row in normalised_rows:
            home_odds = row["home_odds"]
            draw_odds = row["draw_odds"]
            away_odds = row["away_odds"]

            if not validate_quote_odds(home_odds, draw_odds, away_odds):
                _logger.warning(
                    "Discarding invalid odds quote.",
                    extra={
                        "bookmaker_name": row.get("bookmaker_name"),
                        "external_fixture_id": row.get("external_fixture_id"),
                        "home_odds": home_odds,
                        "draw_odds": draw_odds,
                        "away_odds": away_odds,
                    },
                )
                continue

            try:
                matched_fixture = match_fixture_names(
                    home_team=row["home_team_source"],
                    away_team=row["away_team_source"],
                    source_name=row["bookmaker_source"],
                )
            except OddsMatchingError as exc:
                matching_errors.append(exc)
                continue

            enriched_row = devig_quote_dict(
                {
                    **row,
                    "home_team": matched_fixture["home_team"],
                    "away_team": matched_fixture["away_team"],
                    "source_home_team": matched_fixture["source_home_team"],
                    "source_away_team": matched_fixture["source_away_team"],
                }
            )
            processed_rows.append(enriched_row)

        if not processed_rows and matching_errors:
            raise matching_errors[0]

        return processed_rows

    def _group_rows_by_fixture(
        self,
        processed_rows: list[dict[str, Any]],
    ) -> dict[tuple, list[dict[str, Any]]]:
        grouped_rows: dict[tuple, list[dict[str, Any]]] = defaultdict(list)

        for row in processed_rows:
            fixture_key = (
                row["external_fixture_id"],
                row["home_team"],
                row["away_team"],
                row["commence_time"],
                row["market_type"],
            )
            grouped_rows[fixture_key].append(row)

        return dict(grouped_rows)

    def _persist_fixture_groups(
        self,
        *,
        fixture_groups: dict[tuple, list[dict[str, Any]]],
        league: str,
        season: str,
        fetched_at: datetime,
    ) -> dict[tuple, FixtureOddsSnapshot]:
        persisted_snapshots_by_fixture: dict[tuple, FixtureOddsSnapshot] = {}

        try:
            with transaction.atomic():
                for fixture_key, quote_rows in fixture_groups.items():
                    snapshot = self._create_snapshot_for_fixture(
                        quote_rows=quote_rows,
                        league=league,
                        season=season,
                        fetched_at=fetched_at,
                    )
                    self._create_quotes_for_snapshot(snapshot=snapshot, quote_rows=quote_rows)
                    persisted_snapshots_by_fixture[fixture_key] = snapshot
        except IntegrityError as exc:
            raise OddsPersistenceError(f"Failed to persist odds snapshot data: {exc}") from exc

        return persisted_snapshots_by_fixture

    def _create_snapshot_for_fixture(
        self,
        *,
        quote_rows: list[dict[str, Any]],
        league: str,
        season: str,
        fetched_at: datetime,
    ) -> FixtureOddsSnapshot:
        first_row = quote_rows[0]

        return FixtureOddsSnapshot.objects.create(
            bookmaker_source=first_row["bookmaker_source"],
            external_fixture_id=first_row["external_fixture_id"],
            league=league,
            season=season,
            home_team=first_row["home_team"],
            away_team=first_row["away_team"],
            commence_time=first_row["commence_time"],
            fetched_at=fetched_at,
            market_type=first_row["market_type"],
            is_consensus_snapshot=False,
        )

    def _create_quotes_for_snapshot(
        self,
        *,
        snapshot: FixtureOddsSnapshot,
        quote_rows: list[dict[str, Any]],
    ) -> None:
        for row in quote_rows:
            bookmaker = self._get_or_create_bookmaker(row)

            BookmakerQuote.objects.update_or_create(
                snapshot=snapshot,
                bookmaker=bookmaker,
                defaults={
                    "home_odds": row["home_odds"],
                    "draw_odds": row["draw_odds"],
                    "away_odds": row["away_odds"],
                    "implied_home": row["implied_home"],
                    "implied_draw": row["implied_draw"],
                    "implied_away": row["implied_away"],
                    "devig_home": row["devig_home"],
                    "devig_draw": row["devig_draw"],
                    "devig_away": row["devig_away"],
                    "last_seen_at": row.get("last_seen_at"),
                },
            )

    def _get_or_create_bookmaker(self, row: dict[str, Any]) -> Bookmaker:
        bookmaker, _ = Bookmaker.objects.get_or_create(
            slug=row["bookmaker_slug"],
            defaults={
                "name": row["bookmaker_name"],
                "source": Bookmaker.Source.THE_ODDS_API,
                "region": "",
                "is_active": True,
            },
        )

        fields_to_update: list[str] = []

        if bookmaker.name != row["bookmaker_name"]:
            bookmaker.name = row["bookmaker_name"]
            fields_to_update.append("name")

        if bookmaker.source != Bookmaker.Source.THE_ODDS_API:
            bookmaker.source = Bookmaker.Source.THE_ODDS_API
            fields_to_update.append("source")

        if not bookmaker.is_active:
            bookmaker.is_active = True
            fields_to_update.append("is_active")

        if fields_to_update:
            fields_to_update.append("updated_at")
            bookmaker.save(update_fields=fields_to_update)

        return bookmaker

    def fetch_and_store_historical_odds(
        self,
        *,
        sport_key: str,
        league: str,
        season: str,
        date: datetime,
        regions: str | list[str] | tuple[str, ...] | None = DEFAULT_REGIONS,
        bookmakers: str | list[str] | tuple[str, ...] | None = None,
        markets: str = "h2h",
        odds_format: str = "decimal",
        date_format: str = "iso",
    ) -> dict[str, Any]:
        raw_response = self.client.fetch_historical_match_odds(
            sport_key=sport_key,
            date=date,
            regions=regions,
            bookmakers=bookmakers,
            markets=markets,
            odds_format=odds_format,
            date_format=date_format,
        )

        return self._build_fixture_payload(
            raw_response=raw_response,
            sport_key=sport_key,
            league=league,
            season=season,
            persist=True,
        )

    def get_stored_fixture_odds(
        self,
        *,
        home_team: str,
        away_team: str,
        league: str,
        season: str,
    ) -> dict[str, Any]:
        snapshot = (
            FixtureOddsSnapshot.objects
            .filter(
                home_team__iexact=home_team,
                away_team__iexact=away_team,
                league=league,
                season=season,
            )
            .order_by("-fetched_at")
            .first()
        )

        if snapshot is None:
            raise OddsDataUnavailableError(
                f"No stored odds found for {home_team} vs {away_team} "
                f"in {league} {season}."
            )

        quotes = list(snapshot.quotes.select_related("bookmaker").all())

        if not quotes:
            raise OddsDataUnavailableError(
                f"Stored snapshot for {home_team} vs {away_team} has no quotes."
            )

        quote_rows = [self._serialise_stored_quote(q) for q in quotes]
        consensus = self.get_consensus_market_view(quote_rows)

        return {
            "external_fixture_id": snapshot.external_fixture_id,
            "bookmaker_source": snapshot.bookmaker_source,
            "league": snapshot.league,
            "season": snapshot.season,
            "home_team": snapshot.home_team,
            "away_team": snapshot.away_team,
            "source_home_team": snapshot.home_team,
            "source_away_team": snapshot.away_team,
            "commence_time": self._serialise_datetime(snapshot.commence_time),
            "market_type": snapshot.market_type,
            "snapshot_id": snapshot.id,
            "fetched_at": self._serialise_datetime(snapshot.fetched_at),
            "bookmaker_quotes": quote_rows,
            "consensus": consensus,
            "is_historical": True,
        }

    def _serialise_stored_quote(self, quote: BookmakerQuote) -> dict[str, Any]:
        return {
            "bookmaker_name": quote.bookmaker.name,
            "bookmaker_slug": quote.bookmaker.slug,
            "home_odds": quote.home_odds,
            "draw_odds": quote.draw_odds,
            "away_odds": quote.away_odds,
            "implied_home": quote.implied_home,
            "implied_draw": quote.implied_draw,
            "implied_away": quote.implied_away,
            "devig_home": quote.devig_home,
            "devig_draw": quote.devig_draw,
            "devig_away": quote.devig_away,
            "overround": quote.implied_home + quote.implied_draw + quote.implied_away,
            "last_seen_at": self._serialise_datetime(quote.last_seen_at),
        }

    def _serialise_quote_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "bookmaker_name": row["bookmaker_name"],
            "bookmaker_slug": row["bookmaker_slug"],
            "home_odds": row["home_odds"],
            "draw_odds": row["draw_odds"],
            "away_odds": row["away_odds"],
            "implied_home": row["implied_home"],
            "implied_draw": row["implied_draw"],
            "implied_away": row["implied_away"],
            "devig_home": row["devig_home"],
            "devig_draw": row["devig_draw"],
            "devig_away": row["devig_away"],
            "overround": row["overround"],
            "last_seen_at": self._serialise_datetime(row.get("last_seen_at")),
        }

    def _serialise_datetime(self, value: datetime | str | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            parsed_value = self._coerce_datetime(value)
            return parsed_value.isoformat() if parsed_value is not None else value
        return value.isoformat()