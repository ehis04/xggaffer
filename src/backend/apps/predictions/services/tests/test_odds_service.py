from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock

import requests
from django.test import TestCase

from apps.predictions.ml.data.odds.devig import devig_single as ml_devig_single
from apps.predictions.models import Bookmaker, BookmakerQuote, FixtureOddsSnapshot
from apps.predictions.services.odds.client import TheOddsApiClient
from apps.predictions.services.odds.devig import (
    compute_implied_probabilities,
    compute_overround,
    devig_probabilities,
    devig_quote_dict,
    validate_quote_odds,
)
from apps.predictions.services.odds.exceptions import (
    OddsDataUnavailableError,
    OddsMatchingError,
    OddsSourceError,
)
from apps.predictions.services.odds.matcher import (
    match_fixture_names,
    to_canonical_team_name,
)
from apps.predictions.services.odds.service import OddsComparisonService


class OddsDevigWrapperTests(TestCase):
    def test_devig_wrapper_reuses_ml_utility(self):
        home, draw, away = devig_probabilities(2.1, 3.4, 3.6)
        expected_home, expected_draw, expected_away = ml_devig_single(2.1, 3.4, 3.6)

        self.assertAlmostEqual(home, expected_home)
        self.assertAlmostEqual(draw, expected_draw)
        self.assertAlmostEqual(away, expected_away)

    def test_valid_quote_dict_produces_implied_devig_and_overround(self):
        result = devig_quote_dict(
            {
                "home_odds": 2.0,
                "draw_odds": 3.5,
                "away_odds": 4.0,
            }
        )

        implied_home, implied_draw, implied_away = compute_implied_probabilities(2.0, 3.5, 4.0)

        self.assertAlmostEqual(result["implied_home"], implied_home)
        self.assertAlmostEqual(result["implied_draw"], implied_draw)
        self.assertAlmostEqual(result["implied_away"], implied_away)
        self.assertAlmostEqual(
            result["overround"],
            compute_overround(2.0, 3.5, 4.0),
        )
        self.assertIn("devig_home", result)
        self.assertIn("devig_draw", result)
        self.assertIn("devig_away", result)

    def test_invalid_odds_are_rejected(self):
        self.assertFalse(validate_quote_odds(1.0, 3.2, 4.1))

        with self.assertRaises(OddsDataUnavailableError):
            devig_quote_dict(
                {
                    "home_odds": 1.0,
                    "draw_odds": 3.2,
                    "away_odds": 4.1,
                }
            )


class OddsMatcherTests(TestCase):
    def test_deterministic_team_matching_succeeds_for_the_odds_api_names(self):
        self.assertEqual(
            to_canonical_team_name("Arsenal", "the_odds_api"),
            "Arsenal",
        )
        self.assertEqual(
            to_canonical_team_name("Man City", "the_odds_api"),
            "Manchester City",
        )

        fixture = match_fixture_names(
            home_team="Man City",
            away_team="Liverpool",
            source_name="the_odds_api",
        )

        self.assertEqual(fixture["home_team"], "Manchester City")
        self.assertEqual(fixture["away_team"], "Liverpool")

    def test_unmapped_team_names_raise_matching_error(self):
        with self.assertRaises(OddsMatchingError):
            to_canonical_team_name("Made Up FC", "the_odds_api")


class TheOddsApiClientTests(TestCase):
    def test_client_failures_raise_odds_source_error_on_request_exception(self):
        session = Mock()
        session.get.side_effect = requests.RequestException("boom")

        client = TheOddsApiClient(api_key="test-key", session=session)

        with self.assertRaises(OddsSourceError):
            client.fetch_match_odds(
                sport_key="soccer_epl",
                regions="uk",
            )

    def test_client_failures_raise_odds_source_error_on_error_response(self):
        response = Mock()
        response.status_code = 401
        response.headers = {}
        response.json.return_value = {"message": "Invalid API key"}
        response.text = "Invalid API key"

        session = Mock()
        session.get.return_value = response

        client = TheOddsApiClient(api_key="bad-key", session=session)

        with self.assertRaises(OddsSourceError):
            client.fetch_match_odds(
                sport_key="soccer_epl",
                regions="uk",
            )

    def test_client_formats_datetime_params_as_strict_utc_z(self):
        response = Mock()
        response.status_code = 200
        response.headers = {}
        response.json.return_value = []

        session = Mock()
        session.get.return_value = response

        client = TheOddsApiClient(api_key="test-key", session=session)

        commence_from = datetime(2026, 4, 18, 10, 35, 23, 761116, tzinfo=timezone.utc)
        commence_to = datetime(2026, 4, 18, 16, 35, 23, 123456, tzinfo=timezone.utc)

        client.fetch_match_odds(
            sport_key="soccer_epl",
            regions="uk",
            commence_time_from=commence_from,
            commence_time_to=commence_to,
        )

        call_kwargs = session.get.call_args.kwargs
        params = call_kwargs["params"]
        self.assertEqual(params["commenceTimeFrom"], "2026-04-18T10:35:23Z")
        self.assertEqual(params["commenceTimeTo"], "2026-04-18T16:35:23Z")


class OddsComparisonServiceTests(TestCase):
    def setUp(self):
        self.client = Mock()
        self.service = OddsComparisonService(client=self.client)

    def test_no_valid_quotes_raises_data_unavailable(self):
        self.client.fetch_match_odds.return_value = {
            "data": [
                {
                    "id": "fixture-1",
                    "home_team": "Arsenal",
                    "away_team": "Liverpool",
                    "commence_time": "2026-04-20T15:00:00Z",
                    "bookmakers": [
                        {
                            "key": "bet365",
                            "title": "Bet365",
                            "last_update": "2026-04-18T10:00:00Z",
                            "markets": [
                                {
                                    "key": "h2h",
                                    "outcomes": [
                                        {"name": "Arsenal", "price": 1.0},
                                        {"name": "Draw", "price": 3.5},
                                        {"name": "Liverpool", "price": 4.2},
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
            "request_meta": {},
            "source": "the_odds_api",
        }

        with self.assertRaises(OddsDataUnavailableError):
            self.service.get_fixture_odds_comparison(
                sport_key="soccer_epl",
                league="Premier League",
                season="2025",
            )

    def test_consensus_market_calculation_is_stable_for_mocked_fixture(self):
        response_payload = self._build_mock_odds_response()

        self.client.fetch_match_odds.return_value = response_payload

        payload = self.service.get_fixture_odds_comparison(
            sport_key="soccer_epl",
            league="Premier League",
            season="2025",
        )

        self.assertEqual(payload["fixture_count"], 1)
        self.assertEqual(len(payload["fixtures"]), 1)

        fixture = payload["fixtures"][0]
        self.assertEqual(fixture["home_team"], "Arsenal")
        self.assertEqual(fixture["away_team"], "Liverpool")
        self.assertEqual(len(fixture["bookmaker_quotes"]), 2)

        quote_one = ml_devig_single(2.1, 3.4, 3.6)
        quote_two = ml_devig_single(2.2, 3.3, 3.5)

        expected_home = (quote_one[0] + quote_two[0]) / 2
        expected_draw = (quote_one[1] + quote_two[1]) / 2
        expected_away = (quote_one[2] + quote_two[2]) / 2

        consensus = fixture["consensus"]

        self.assertAlmostEqual(consensus["consensus_home_probability"], expected_home)
        self.assertAlmostEqual(consensus["consensus_draw_probability"], expected_draw)
        self.assertAlmostEqual(consensus["consensus_away_probability"], expected_away)
        self.assertEqual(consensus["market_favourite"], "home")

    def test_optional_persistence_creates_snapshot_and_quote_rows(self):
        self.client.fetch_match_odds.return_value = self._build_mock_odds_response()

        payload = self.service.fetch_and_store_fixture_odds(
            sport_key="soccer_epl",
            league="Premier League",
            season="2025",
        )

        self.assertEqual(payload["fixture_count"], 1)
        self.assertEqual(FixtureOddsSnapshot.objects.count(), 1)
        self.assertEqual(BookmakerQuote.objects.count(), 2)
        self.assertEqual(Bookmaker.objects.count(), 2)

        snapshot = FixtureOddsSnapshot.objects.get()
        self.assertEqual(snapshot.home_team, "Arsenal")
        self.assertEqual(snapshot.away_team, "Liverpool")
        self.assertEqual(snapshot.league, "Premier League")
        self.assertEqual(snapshot.season, "2025")

        bookmaker_names = set(Bookmaker.objects.values_list("name", flat=True))
        self.assertEqual(bookmaker_names, {"Bet365", "Paddy Power"})

    def test_refresh_fixture_snapshot_raises_data_unavailable_when_match_missing(self):
        self.client.fetch_match_odds.return_value = self._build_mock_odds_response()

        with self.assertRaises(OddsDataUnavailableError) as context:
            self.service.refresh_fixture_odds_snapshot(
                sport_key="soccer_epl",
                league="EPL",
                season="2025",
                home_team="Arsenal",
                away_team="Chelsea",
            )

        self.assertIn("No odds snapshot match found", str(context.exception))

    def _build_mock_odds_response(self) -> dict:
        return {
            "data": [
                {
                    "id": "fixture-1",
                    "home_team": "Arsenal",
                    "away_team": "Liverpool",
                    "commence_time": "2026-04-20T15:00:00Z",
                    "bookmakers": [
                        {
                            "key": "bet365",
                            "title": "Bet365",
                            "last_update": "2026-04-18T10:00:00Z",
                            "markets": [
                                {
                                    "key": "h2h",
                                    "outcomes": [
                                        {"name": "Arsenal", "price": 2.1},
                                        {"name": "Draw", "price": 3.4},
                                        {"name": "Liverpool", "price": 3.6},
                                    ],
                                }
                            ],
                        },
                        {
                            "key": "paddypower",
                            "title": "Paddy Power",
                            "last_update": "2026-04-18T10:05:00Z",
                            "markets": [
                                {
                                    "key": "h2h",
                                    "outcomes": [
                                        {"name": "Arsenal", "price": 2.2},
                                        {"name": "Draw", "price": 3.3},
                                        {"name": "Liverpool", "price": 3.5},
                                    ],
                                }
                            ],
                        },
                    ],
                }
            ],
            "request_meta": {
                "requests_remaining": 100,
                "requests_used": 1,
                "requests_last": 1,
                "status_code": 200,
            },
            "source": "the_odds_api",
        }

    def test_refresh_upcoming_fixture_odds_uses_bounded_window_and_filters(self):
        response_payload = self._build_mock_odds_response()
        self.client.fetch_match_odds.return_value = response_payload

        payload = self.service.refresh_upcoming_fixture_odds(
            sport_keys=["soccer_epl"],
            max_fixtures=1,
            lookahead_hours=48,
            bookmakers=["bet365", "paddypower"],
            persist=True,
        )

        self.client.fetch_match_odds.assert_called_once()
        _, kwargs = self.client.fetch_match_odds.call_args

        self.assertEqual(kwargs["sport_key"], "soccer_epl")
        self.assertEqual(kwargs["bookmakers"], ["bet365", "paddypower"])
        self.assertEqual(kwargs["markets"], "h2h")
        self.assertEqual(kwargs["odds_format"], "decimal")
        self.assertEqual(kwargs["date_format"], "iso")
        self.assertEqual(payload["fixtures_seen"], 1)
        self.assertEqual(payload["snapshots_created"], 1)
        self.assertEqual(payload["requests_used"], 1)
        self.assertEqual(payload["leagues_processed"], ["EPL"])


    def test_refresh_fixture_odds_snapshot_returns_single_fixture_summary(self):
        response_payload = self._build_mock_odds_response()
        self.client.fetch_match_odds.return_value = response_payload

        result = self.service.refresh_fixture_odds_snapshot(
            sport_key="soccer_epl",
            league="Premier League",
            season="2025",
            home_team="Arsenal",
            away_team="Liverpool",
            external_fixture_id="fixture-1",
            commence_time="2026-04-20T15:00:00Z",
            bookmakers=["bet365"],
            regions=["uk"],
        )

        self.assertEqual(result["external_fixture_id"], "fixture-1")
        self.assertEqual(result["home_team"], "Arsenal")
        self.assertEqual(result["away_team"], "Liverpool")
        self.assertEqual(result["bookmaker_quote_count"], 2)
        self.assertIsNotNone(result["snapshot_id"])