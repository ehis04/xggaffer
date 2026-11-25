from unittest.mock import patch

import pandas as pd
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.users.models import User


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "match-lookup-tests"}})
class MatchLookupFixtureTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client = APIClient()
        self.client.force_authenticate(User.objects.create_user(email="fixtures@example.com"))
        self.endpoint = "/api/predictions/fixtures/lookup/"

    @patch("apps.predictions.ml.features.rolling.load_match_history")
    def test_lists_snapshot_fixtures_without_market_data(self, history):
        history.return_value = pd.DataFrame([
            {"home_team": "Arsenal", "away_team": "Chelsea", "date": pd.Timestamp("2025-10-10")},
            {"home_team": "Everton", "away_team": "Liverpool", "date": pd.Timestamp("2026-02-10")},
            {"home_team": "Arsenal", "away_team": "Chelsea", "date": pd.Timestamp("2025-10-10")},
        ])
        response = self.client.get(self.endpoint, {"league": "EPL", "season": "2025"})

        self.assertEqual(response.status_code, 200)
        history.assert_called_once_with(leagues=["EPL"], seasons=["2025"])
        self.assertEqual(response.json()["fixtures"], [
            {"home_team": "Everton", "away_team": "Liverpool", "date": "2026-02-10", "league": "EPL", "season": "2025"},
            {"home_team": "Arsenal", "away_team": "Chelsea", "date": "2025-10-10", "league": "EPL", "season": "2025"},
        ])

    def test_invalid_league_is_rejected(self):
        self.assertEqual(self.client.get(self.endpoint, {"league": "invalid"}).status_code, 400)
