from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.predictions.tasks import (
    refresh_fixture_odds_snapshot_task,
    refresh_upcoming_fixture_odds_task,
)
from apps.predictions.services.odds.fetch_task import fetch_and_persist_odds


class RefreshUpcomingFixtureOddsTaskTests(SimpleTestCase):
    @patch("apps.predictions.services.odds.service.OddsComparisonService")
    def test_refresh_upcoming_fixture_odds_task_calls_service_helper(self, service_cls):
        service = service_cls.return_value
        service.refresh_upcoming_fixture_odds.return_value = {
            "sport_keys_processed": ["soccer_epl"],
            "leagues_processed": ["EPL"],
            "fixtures_seen": 4,
            "snapshots_created": 4,
            "requests_used": 1,
            "errors": [],
            "max_fixtures": 4,
            "lookahead_hours": 72,
            "bookmakers_requested": ["bet365", "paddypower"],
        }

        result = refresh_upcoming_fixture_odds_task.run(
            sport_keys=["soccer_epl"],
            max_fixtures=4,
        )

        service.refresh_upcoming_fixture_odds.assert_called_once_with(
            sport_keys=("soccer_epl",),
            max_fixtures=4,
            persist=True,
        )
        self.assertEqual(result["fixtures_seen"], 4)
        self.assertEqual(result["snapshots_created"], 4)

    @patch("apps.predictions.services.odds.service.OddsComparisonService")
    def test_refresh_upcoming_fixture_odds_task_propagates_failures(self, service_cls):
        service = service_cls.return_value
        service.refresh_upcoming_fixture_odds.side_effect = RuntimeError("odds source down")

        with self.assertRaises(RuntimeError) as context:
            refresh_upcoming_fixture_odds_task.run()

        self.assertIn("odds source down", str(context.exception))


class RefreshFixtureOddsSnapshotTaskTests(SimpleTestCase):
    @patch("apps.predictions.services.odds.service.OddsComparisonService")
    def test_refresh_fixture_odds_snapshot_task_calls_single_fixture_helper(self, service_cls):
        service = service_cls.return_value
        service.refresh_fixture_odds_snapshot.return_value = {
            "external_fixture_id": "fixture-1",
            "snapshot_id": 12,
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "league": "EPL",
            "season": "2025",
            "commence_time": "2026-04-20T15:00:00Z",
            "bookmaker_source": "the_odds_api",
            "bookmaker_quote_count": 2,
        }

        fixture_identity = {
            "sport_key": "soccer_epl",
            "league": "EPL",
            "season": "2025",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "external_fixture_id": "fixture-1",
            "commence_time": "2026-04-20T15:00:00Z",
            "bookmakers": ["bet365"],
            "regions": ["uk"],
        }

        result = refresh_fixture_odds_snapshot_task.run(fixture_identity)

        service.refresh_fixture_odds_snapshot.assert_called_once_with(
            sport_key="soccer_epl",
            league="EPL",
            season="2025",
            home_team="Arsenal",
            away_team="Chelsea",
            external_fixture_id="fixture-1",
            commence_time="2026-04-20T15:00:00Z",
            bookmakers=["bet365"],
            regions=["uk"],
        )
        self.assertEqual(result["snapshot_id"], 12)
        self.assertEqual(result["bookmaker_quote_count"], 2)

    def test_refresh_fixture_odds_snapshot_task_rejects_missing_required_fields(self):
        with self.assertRaises(ValueError) as context:
            refresh_fixture_odds_snapshot_task.run(
                {
                    "sport_key": "soccer_epl",
                    "league": "EPL",
                    "season": "2025",
                    "home_team": "Arsenal",
                }
            )

        self.assertIn("Missing: away_team", str(context.exception))

    @patch("apps.predictions.services.odds.service.OddsComparisonService")
    def test_refresh_fixture_odds_snapshot_task_defaults_regions_when_omitted(self, service_cls):
        service = service_cls.return_value
        service.refresh_fixture_odds_snapshot.return_value = {
            "external_fixture_id": "fixture-1",
            "snapshot_id": 12,
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "league": "EPL",
            "season": "2025",
            "commence_time": "2026-04-20T15:00:00Z",
            "bookmaker_source": "the_odds_api",
            "bookmaker_quote_count": 2,
        }

        refresh_fixture_odds_snapshot_task.run(
            {
                "sport_key": "soccer_epl",
                "league": "EPL",
                "season": "2025",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
            }
        )

        service.refresh_fixture_odds_snapshot.assert_called_once_with(
            sport_key="soccer_epl",
            league="EPL",
            season="2025",
            home_team="Arsenal",
            away_team="Chelsea",
            external_fixture_id=None,
            commence_time=None,
            bookmakers=None,
            regions="uk,eu",
        )

    @patch("apps.predictions.services.odds.service.OddsComparisonService")
    def test_refresh_fixture_odds_snapshot_task_propagates_service_failures(self, service_cls):
        service = service_cls.return_value
        service.refresh_fixture_odds_snapshot.side_effect = RuntimeError("fixture refresh failed")

        with self.assertRaises(RuntimeError) as context:
            refresh_fixture_odds_snapshot_task.run(
                {
                    "sport_key": "soccer_epl",
                    "league": "EPL",
                    "season": "2025",
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                }
            )

        self.assertIn("fixture refresh failed", str(context.exception))


class FetchAndPersistOddsWrapperTests(SimpleTestCase):
    @override_settings(
        ODDS_SNAPSHOT_MAX_FIXTURES_PER_RUN=8,
        ODDS_SNAPSHOT_LOOKAHEAD_HOURS=72,
        ODDS_SNAPSHOT_BOOKMAKERS="bet365,paddypower",
        ODDS_SNAPSHOT_SPORT_KEYS="soccer_epl,soccer_spain_la_liga",
    )
    @patch("apps.predictions.services.odds.fetch_task.OddsComparisonService")
    def test_fetch_and_persist_odds_uses_bounded_settings(self, service_cls):
        service = service_cls.return_value
        service.refresh_upcoming_fixture_odds.return_value = {
            "sport_keys_processed": ["soccer_epl"],
            "leagues_processed": ["EPL"],
            "fixtures_seen": 6,
            "snapshots_created": 6,
            "requests_used": 1,
            "errors": [],
            "max_fixtures": 8,
            "lookahead_hours": 72,
            "bookmakers_requested": ["bet365", "paddypower"],
        }

        result = fetch_and_persist_odds()

        service.refresh_upcoming_fixture_odds.assert_called_once_with(
            sport_keys=("soccer_epl", "soccer_spain_la_liga"),
            max_fixtures=8,
            lookahead_hours=72,
            bookmakers=("bet365", "paddypower"),
            persist=True,
        )
        self.assertEqual(result["fixtures_seen"], 6)
        self.assertEqual(result["requests_used"], 1)

    @override_settings(
        ODDS_SNAPSHOT_MAX_FIXTURES_PER_RUN=10,
        ODDS_SNAPSHOT_LOOKAHEAD_HOURS=72,
        ODDS_SNAPSHOT_BOOKMAKERS="",
        ODDS_SNAPSHOT_SPORT_KEYS="",
    )
    @patch("apps.predictions.services.odds.fetch_task.OddsComparisonService")
    def test_fetch_and_persist_odds_raises_when_everything_fails(self, service_cls):
        service = service_cls.return_value
        service.refresh_upcoming_fixture_odds.return_value = {
            "sport_keys_processed": [],
            "leagues_processed": [],
            "fixtures_seen": 0,
            "snapshots_created": 0,
            "requests_used": 1,
            "errors": [
                {
                    "sport_key": "soccer_epl",
                    "error": "source unavailable",
                }
            ],
            "max_fixtures": 10,
            "lookahead_hours": 72,
            "bookmakers_requested": None,
        }

        with self.assertRaises(RuntimeError) as context:
            fetch_and_persist_odds()

        self.assertIn("source unavailable", str(context.exception))