from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.livefootball.models import (
    Competition,
    CompetitionTableRow,
    CompetitionTableSnapshot,
    TeamDirectoryEntry,
    SavedLeagueScenario,
)


TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}


@override_settings(CACHES=TEST_CACHES)
class LeagueViewsTests(APITestCase):
    def setUp(self) -> None:
        cache.clear()
        self.user = get_user_model().objects.create_user(
            email="league-test@example.com",
            password="password123",
        )
        self.client.force_authenticate(self.user)

        self.competition = Competition.objects.create(
            provider="football_data",
            external_id="PL",
            code="PL",
            name="Premier League",
            area_name="England",
            emblem_url="https://example.com/pl.png",
            current_season_label="2024",
        )

        self.arsenal = TeamDirectoryEntry.objects.create(
            competition=self.competition,
            provider="football_data",
            season_label="2024",
            external_id="57",
            name="Arsenal FC",
            short_name="Arsenal",
            tla="ARS",
            emblem_url="https://example.com/ars.png",
        )
        self.city = TeamDirectoryEntry.objects.create(
            competition=self.competition,
            provider="football_data",
            season_label="2024",
            external_id="65",
            name="Manchester City FC",
            short_name="Man City",
            tla="MCI",
            emblem_url="https://example.com/mci.png",
        )

        self.snapshot_2024 = CompetitionTableSnapshot.objects.create(
            competition=self.competition,
            season_label="2024",
            snapshot_label="latest",
        )
        CompetitionTableRow.objects.create(
            snapshot=self.snapshot_2024,
            team=self.arsenal,
            external_team_id=self.arsenal.external_id,
            team_name=self.arsenal.name,
            position=1,
            played=38,
            won=28,
            drawn=5,
            lost=5,
            goals_for=88,
            goals_against=29,
            goal_difference=59,
            points=89,
            form="W,W,D,W,W",
        )
        CompetitionTableRow.objects.create(
            snapshot=self.snapshot_2024,
            team=self.city,
            external_team_id=self.city.external_id,
            team_name=self.city.name,
            position=2,
            played=38,
            won=27,
            drawn=6,
            lost=5,
            goals_for=91,
            goals_against=34,
            goal_difference=57,
            points=87,
            form="W,D,W,W,W",
        )

        self.snapshot_2023 = CompetitionTableSnapshot.objects.create(
            competition=self.competition,
            season_label="2023",
            snapshot_label="latest",
        )

    def test_meta_requires_authentication(self) -> None:
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("livefootball-leagues-meta"))
        self.assertEqual(response.status_code, 401)

    def test_meta_returns_supported_leagues_and_seasons(self) -> None:
        response = self.client.get(reverse("livefootball-leagues-meta"))
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertIn("data", payload)
        self.assertIn("leagues", payload["data"])
        self.assertGreaterEqual(len(payload["data"]["leagues"]), 1)

        premier_league = next(item for item in payload["data"]["leagues"] if item["id"] == self.competition.id)
        self.assertEqual(premier_league["code"], "PL")
        self.assertIn("2024", premier_league["available_seasons"])
        self.assertIn("2023", premier_league["available_seasons"])
        self.assertIn("current_expected", premier_league["supported_modes"])
        self.assertIn("pre_season", premier_league["supported_modes"])
        self.assertEqual(premier_league["current_season_label"], "2024")
        self.assertIn("as_of_matchweek", premier_league["supported_modes"])

    @patch("apps.livefootball.services.league_data.generate_expected_table_commentary")
    @patch("apps.livefootball.services.league_data.simulate_league_season")
    def test_expected_table_endpoint_returns_commentary(
        self,
        mock_simulate,
        mock_commentary,
    ) -> None:
        mock_simulate.return_value = {
            "league": "EPL",
            "season": "2024",
            "mode": "current_expected",
            "simulation_count": 5000,
            "based_on_matchweek": 30,
            "data_cutoff_date": "2025-04-01",
            "expected_table": [
                {
                    "team": "Arsenal",
                    "predicted_points": 88.4,
                    "predicted_position": 1,
                    "position_probabilities": {1: 0.61, 2: 0.29},
                    "title_probability": 0.61,
                    "top_4_probability": 0.97,
                    "relegation_probability": 0.0,
                    "simulated_wins": 27.1,
                    "simulated_draws": 7.1,
                    "simulated_losses": 3.8,
                    "simulated_goals_for": 84.2,
                    "simulated_goals_against": 30.6,
                },
                {
                    "team": "Manchester City",
                    "predicted_points": 85.7,
                    "predicted_position": 2,
                    "position_probabilities": {1: 0.29, 2: 0.48},
                    "title_probability": 0.29,
                    "top_4_probability": 0.95,
                    "relegation_probability": 0.0,
                    "simulated_wins": 26.1,
                    "simulated_draws": 7.4,
                    "simulated_losses": 4.5,
                    "simulated_goals_for": 86.1,
                    "simulated_goals_against": 33.0,
                },
            ],
            "metadata": {
                "engine_versions": {
                    "elo": "v1",
                    "outcome": "v2",
                    "score": "score-test",
                    "simulation": "v1",
                },
                "remaining_fixtures": 8,
                "total_fixtures_simulated": 40000,
            },
        }
        mock_commentary.return_value = [
            {
                "type": "headline",
                "text": "Arsenal are projected to finish top.",
                "confidence": "high",
                "related_teams": ["Arsenal"],
            }
        ]

        response = self.client.get(
            reverse(
                "livefootball-league-expected-table",
                kwargs={"competition_id": self.competition.id},
            ),
            {"season": "2024", "mode": "current_expected"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"]["season_label"], "2024")
        self.assertEqual(payload["data"]["mode"], "current_expected")
        self.assertEqual(len(payload["data"]["expected_table"]), 2)
        self.assertEqual(payload["data"]["commentary"][0]["type"], "headline")
        self.assertIn("supported_modes", payload["data"]["metadata"])

    def test_expected_table_endpoint_rejects_invalid_mode(self) -> None:
        response = self.client.get(
            reverse(
                "livefootball-league-expected-table",
                kwargs={"competition_id": self.competition.id},
            ),
            {"season": "2024", "mode": "not_a_real_mode"},
        )

        self.assertEqual(response.status_code, 400)

    @patch("apps.livefootball.services.league_data.generate_comparison_commentary")
    @patch("apps.livefootball.services.league_data.generate_expected_table_commentary")
    @patch("apps.livefootball.services.league_data.simulate_league_season")
    def test_compare_endpoint_returns_actual_expected_deltas_and_commentary(
        self,
        mock_simulate,
        mock_expected_commentary,
        mock_compare_commentary,
    ) -> None:
        mock_simulate.return_value = {
            "league": "EPL",
            "season": "2024",
            "mode": "current_expected",
            "simulation_count": 5000,
            "based_on_matchweek": 30,
            "data_cutoff_date": "2025-04-01",
            "expected_table": [
                {
                    "team": "Arsenal",
                    "predicted_points": 88.4,
                    "predicted_position": 1,
                    "position_probabilities": {1: 0.61, 2: 0.29},
                    "title_probability": 0.61,
                    "top_4_probability": 0.97,
                    "relegation_probability": 0.0,
                    "simulated_wins": 27.1,
                    "simulated_draws": 7.1,
                    "simulated_losses": 3.8,
                    "simulated_goals_for": 84.2,
                    "simulated_goals_against": 30.6,
                },
                {
                    "team": "Manchester City",
                    "predicted_points": 85.7,
                    "predicted_position": 2,
                    "position_probabilities": {1: 0.29, 2: 0.48},
                    "title_probability": 0.29,
                    "top_4_probability": 0.95,
                    "relegation_probability": 0.0,
                    "simulated_wins": 26.1,
                    "simulated_draws": 7.4,
                    "simulated_losses": 4.5,
                    "simulated_goals_for": 86.1,
                    "simulated_goals_against": 33.0,
                },
            ],
            "metadata": {
                "engine_versions": {
                    "elo": "v1",
                    "outcome": "v2",
                    "score": "score-test",
                    "simulation": "v1",
                },
                "remaining_fixtures": 8,
                "total_fixtures_simulated": 40000,
            },
        }
        mock_expected_commentary.return_value = []
        mock_compare_commentary.return_value = [
            {
                "type": "comparison",
                "text": "Arsenal and the model are aligned at the top.",
                "confidence": "medium",
                "related_teams": ["Arsenal"],
            }
        ]

        response = self.client.get(
            reverse(
                "livefootball-league-compare",
                kwargs={"competition_id": self.competition.id},
            ),
            {"season": "2024", "mode": "current_expected"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("data", payload)
        self.assertIn("freshness", payload)
        self.assertIn("version", payload)
        self.assertIn("generated_at", payload)
        self.assertIn("actual_table", payload["data"])
        self.assertIn("expected_table", payload["data"])
        self.assertIn("deltas", payload["data"])
        self.assertIn("comparison_metrics", payload["data"])
        self.assertIn("commentary", payload["data"])
        self.assertEqual(payload["data"]["commentary"][0]["type"], "comparison")

    @patch("apps.livefootball.views.get_active_snapshot_version", return_value="42")
    @patch("apps.livefootball.services.league_data.generate_comparison_commentary")
    @patch("apps.livefootball.services.league_data.generate_expected_table_commentary")
    @patch("apps.livefootball.services.league_data.simulate_league_season")
    def test_compare_endpoint_uses_cached_envelope_when_available(
        self,
        mock_simulate,
        mock_expected_commentary,
        mock_compare_commentary,
        _mock_snapshot_version,
    ) -> None:
        cache.clear()
        mock_simulate.return_value = {
            "league": "EPL",
            "season": "2024",
            "mode": "current_expected",
            "simulation_count": 5000,
            "based_on_matchweek": 30,
            "data_cutoff_date": "2025-04-01",
            "expected_table": [
                {
                    "team": "Arsenal",
                    "predicted_points": 88.4,
                    "predicted_position": 1,
                    "position_probabilities": {1: 0.61, 2: 0.29},
                    "title_probability": 0.61,
                    "top_4_probability": 0.97,
                    "relegation_probability": 0.0,
                    "simulated_wins": 27.1,
                    "simulated_draws": 7.1,
                    "simulated_losses": 3.8,
                    "simulated_goals_for": 84.2,
                    "simulated_goals_against": 30.6,
                },
                {
                    "team": "Manchester City",
                    "predicted_points": 85.7,
                    "predicted_position": 2,
                    "position_probabilities": {1: 0.29, 2: 0.48},
                    "title_probability": 0.29,
                    "top_4_probability": 0.95,
                    "relegation_probability": 0.0,
                    "simulated_wins": 26.1,
                    "simulated_draws": 7.4,
                    "simulated_losses": 4.5,
                    "simulated_goals_for": 86.1,
                    "simulated_goals_against": 33.0,
                },
            ],
            "metadata": {
                "engine_versions": {
                    "elo": "v1",
                    "outcome": "v2",
                    "score": "score-test",
                    "simulation": "v1",
                },
                "remaining_fixtures": 8,
                "total_fixtures_simulated": 40000,
            },
        }
        mock_expected_commentary.return_value = []
        mock_compare_commentary.return_value = []

        url = reverse(
            "livefootball-league-compare",
            kwargs={"competition_id": self.competition.id},
        )
        params = {"season": "2024", "mode": "current_expected"}

        first_response = self.client.get(url, params)
        self.assertEqual(first_response.status_code, 200)
        self.assertIn("data", first_response.json())
        self.assertIn("freshness", first_response.json())

        mock_simulate.reset_mock()
        second_response = self.client.get(url, params)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(second_response.json(), first_response.json())
        mock_simulate.assert_not_called()

    def test_compare_endpoint_returns_404_for_unknown_competition(self) -> None:
        response = self.client.get(
            reverse(
                "livefootball-league-compare",
                kwargs={"competition_id": 999999},
            ),
            {"season": "2024", "mode": "current_expected"},
        )
        self.assertEqual(response.status_code, 404)

    @patch("apps.livefootball.services.league_data.generate_comparison_commentary")
    @patch("apps.livefootball.services.league_data.generate_expected_table_commentary")
    @patch("apps.livefootball.services.league_data.simulate_league_season")
    def test_compare_endpoint_as_of_matchweek_uses_historical_actual_snapshot(
        self,
        mock_simulate,
        mock_expected_commentary,
        mock_compare_commentary,
    ) -> None:
        snapshot_mw10 = CompetitionTableSnapshot.objects.create(
            competition=self.competition,
            season_label="2024",
            snapshot_label="matchday-10",
            matchday=10,
        )
        CompetitionTableRow.objects.create(
            snapshot=snapshot_mw10,
            team=self.arsenal,
            external_team_id=self.arsenal.external_id,
            team_name=self.arsenal.name,
            position=1,
            played=10,
            won=8,
            drawn=1,
            lost=1,
            goals_for=22,
            goals_against=8,
            goal_difference=14,
            points=25,
            form="W,W,W,D,L",
        )
        CompetitionTableRow.objects.create(
            snapshot=snapshot_mw10,
            team=self.city,
            external_team_id=self.city.external_id,
            team_name=self.city.name,
            position=2,
            played=10,
            won=7,
            drawn=2,
            lost=1,
            goals_for=24,
            goals_against=10,
            goal_difference=14,
            points=23,
            form="W,D,W,W,L",
        )

        mock_simulate.return_value = {
            "league": "EPL",
            "season": "2024",
            "mode": "as_of_matchweek",
            "simulation_count": 5000,
            "based_on_matchweek": 10,
            "data_cutoff_date": "2025-01-01",
            "expected_table": [
                {
                    "team": "Arsenal",
                    "predicted_points": 82.0,
                    "predicted_position": 1,
                    "position_probabilities": {1: 0.5, 2: 0.3},
                    "title_probability": 0.5,
                    "top_4_probability": 0.9,
                    "relegation_probability": 0.0,
                    "simulated_wins": 24.0,
                    "simulated_draws": 10.0,
                    "simulated_losses": 4.0,
                    "simulated_goals_for": 78.0,
                    "simulated_goals_against": 34.0,
                },
                {
                    "team": "Manchester City",
                    "predicted_points": 80.0,
                    "predicted_position": 2,
                    "position_probabilities": {1: 0.35, 2: 0.4},
                    "title_probability": 0.35,
                    "top_4_probability": 0.88,
                    "relegation_probability": 0.0,
                    "simulated_wins": 23.0,
                    "simulated_draws": 11.0,
                    "simulated_losses": 4.0,
                    "simulated_goals_for": 80.0,
                    "simulated_goals_against": 36.0,
                },
            ],
            "metadata": {
                "engine_versions": {
                    "elo": "v1",
                    "outcome": "v2",
                    "score": "score-test",
                    "simulation": "v1",
                },
                "remaining_fixtures": 280,
                "total_fixtures_simulated": 1400000,
            },
        }
        mock_expected_commentary.return_value = []
        mock_compare_commentary.return_value = []

        response = self.client.get(
            reverse(
                "livefootball-league-compare",
                kwargs={"competition_id": self.competition.id},
            ),
            {"season": "2024", "mode": "as_of_matchweek", "matchweek": 10},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"]["metadata"]["actual_matchday"], 10)
        self.assertEqual(payload["data"]["actual_table"][0]["played"], 10)

    def test_expected_table_endpoint_accepts_as_of_matchweek_for_current_season(self) -> None:
        response = self.client.get(
            reverse(
                "livefootball-league-expected-table",
                kwargs={"competition_id": self.competition.id},
            ),
            {"season": "2024", "mode": "as_of_matchweek", "matchweek": 10},
        )

        self.assertEqual(response.status_code, 200)

    @patch("apps.livefootball.services.league_data.generate_expected_table_commentary")
    @patch("apps.livefootball.services.league_data.simulate_league_season")
    def test_expected_table_endpoint_accepts_as_of_matchweek_for_completed_season(
        self,
        mock_simulate,
        mock_commentary,
    ) -> None:
        self.competition.current_season_label = "2025"
        self.competition.save(update_fields=["current_season_label"])

        mock_simulate.return_value = {
            "league": "EPL",
            "season": "2024",
            "mode": "as_of_matchweek",
            "simulation_count": 5000,
            "based_on_matchweek": 10,
            "data_cutoff_date": "2025-01-01",
            "expected_table": [
                {
                    "team": "Arsenal",
                    "predicted_points": 88.4,
                    "predicted_position": 1,
                    "position_probabilities": {1: 0.61, 2: 0.29},
                    "title_probability": 0.61,
                    "top_4_probability": 0.97,
                    "relegation_probability": 0.0,
                    "simulated_wins": 27.1,
                    "simulated_draws": 7.1,
                    "simulated_losses": 3.8,
                    "simulated_goals_for": 84.2,
                    "simulated_goals_against": 30.6,
                },
                {
                    "team": "Manchester City",
                    "predicted_points": 85.7,
                    "predicted_position": 2,
                    "position_probabilities": {1: 0.29, 2: 0.48},
                    "title_probability": 0.29,
                    "top_4_probability": 0.95,
                    "relegation_probability": 0.0,
                    "simulated_wins": 26.1,
                    "simulated_draws": 7.4,
                    "simulated_losses": 4.5,
                    "simulated_goals_for": 86.1,
                    "simulated_goals_against": 33.0,
                },
            ],
            "metadata": {
                "engine_versions": {
                    "elo": "v1",
                    "outcome": "v2",
                    "score": "score-test",
                    "simulation": "v1",
                },
                "remaining_fixtures": 8,
                "total_fixtures_simulated": 40000,
                "total_matchweeks": 38,
            },
        }
        mock_commentary.return_value = [
            {
                "type": "headline",
                "text": "Arsenal are projected to finish top.",
                "confidence": "high",
                "related_teams": ["Arsenal"],
            }
        ]

        response = self.client.get(
            reverse(
                "livefootball-league-expected-table",
                kwargs={"competition_id": self.competition.id},
            ),
            {"season": "2024", "mode": "as_of_matchweek", "matchweek": 10},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["mode"], "as_of_matchweek")
        mock_simulate.assert_called_once_with(
            league="EPL",
            season="2024",
            mode="as_of_matchweek",
            matchweek=10,
        )

    @patch("apps.livefootball.views.get_league_scenario_payload")
    def test_scenario_endpoint_returns_expected_shape(self, mock_payload) -> None:
        mock_payload.return_value = {
            "competition": {
                "id": self.competition.id,
                "provider": "football_data",
                "external_id": "PL",
                "code": "PL",
                "name": "Premier League",
                "area_name": "England",
                "emblem_url": "https://example.com/pl.png",
                "current_season_label": "2024",
                "current_season_start_date": None,
                "current_season_end_date": None,
                "current_matchday": None,
                "last_synced_at": None,
            },
            "season_label": "2024",
            "mode": "current_expected",
            "remaining_fixtures": [
                {
                    "fixture_key": "Arsenal__Manchester City",
                    "home_team": {
                        "id": self.arsenal.id,
                        "external_id": self.arsenal.external_id,
                        "name": self.arsenal.name,
                        "short_name": self.arsenal.short_name,
                        "tla": self.arsenal.tla,
                        "emblem_url": self.arsenal.emblem_url,
                    },
                    "away_team": {
                        "id": self.city.id,
                        "external_id": self.city.external_id,
                        "name": self.city.name,
                        "short_name": self.city.short_name,
                        "tla": self.city.tla,
                        "emblem_url": self.city.emblem_url,
                    },
                }
            ],
            "locked_results": [],
            "expected_table": [
                {
                    "team": {
                        "id": self.arsenal.id,
                        "external_id": self.arsenal.external_id,
                        "name": self.arsenal.name,
                        "short_name": self.arsenal.short_name,
                        "tla": self.arsenal.tla,
                        "emblem_url": self.arsenal.emblem_url,
                    },
                    "canonical_team_name": "Arsenal",
                    "predicted_points": 88.4,
                    "predicted_position": 1,
                    "position_probabilities": {1: 0.61, 2: 0.29},
                    "title_probability": 0.61,
                    "top_4_probability": 0.97,
                    "relegation_probability": 0.0,
                    "simulated_wins": 27.1,
                    "simulated_draws": 7.1,
                    "simulated_losses": 3.8,
                    "simulated_goals_for": 84.2,
                    "simulated_goals_against": 30.6,
                }
            ],
            "commentary": [
                {
                    "type": "headline",
                    "text": "Arsenal are projected to finish top.",
                    "confidence": "high",
                    "related_teams": ["Arsenal"],
                }
            ],
            "metadata": {
                "supported_modes": ["current_expected", "pre_season", "as_of_matchweek"],
                "unavailable_modes": [],
                "based_on_matchweek": None,
                "data_cutoff_date": "2025-04-01",
                "simulation_count": 5000,
                "engine_versions": {
                    "elo": "v1",
                    "outcome": "v2",
                    "score": "score-test",
                    "simulation": "v1",
                },
                "remaining_fixtures": 1,
                "remaining_fixtures_before_lock": 1,
                "remaining_fixtures_after_lock": 1,
                "total_fixtures_simulated": 5000,
                "total_matchweeks": 38,
                "actual_table_source": "football-data table snapshots",
                "expected_table_source": "understat-backed simulation service with locked results",
            },
        }

        response = self.client.post(
            reverse(
                "livefootball-league-scenario",
                kwargs={"competition_id": self.competition.id},
            ),
            {"locked_results": []},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("remaining_fixtures", payload)
        self.assertIn("locked_results", payload)
        self.assertIn("expected_table", payload)
        self.assertIn("commentary", payload)
        self.assertEqual(payload["remaining_fixtures"][0]["fixture_key"], "Arsenal__Manchester City")

    @patch("apps.livefootball.views.create_saved_league_scenario")
    def test_saved_scenario_create_endpoint_returns_201(self, mock_create) -> None:
        mock_create.return_value = {
            "id": 1,
            "competition": {
                "id": self.competition.id,
                "provider": "football_data",
                "external_id": "PL",
                "code": "PL",
                "name": "Premier League",
                "area_name": "England",
                "emblem_url": "https://example.com/pl.png",
                "current_season_label": "2024",
                "current_season_start_date": None,
                "current_season_end_date": None,
                "current_matchday": None,
                "last_synced_at": None,
            },
            "title": "My scenario",
            "description": "",
            "season_label": "2024",
            "mode": "current_expected",
            "based_on_matchweek": None,
            "locked_results": [],
            "created_at": "2026-04-04T12:00:00Z",
            "updated_at": "2026-04-04T12:00:00Z",
        }

        response = self.client.post(
            reverse(
                "livefootball-league-saved-scenarios",
                kwargs={"competition_id": self.competition.id},
            ),
            {
                "title": "My scenario",
                "description": "",
                "locked_results": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["title"], "My scenario")

    @patch("apps.livefootball.views.list_saved_league_scenarios")
    def test_saved_scenario_list_endpoint_returns_items(self, mock_list) -> None:
        mock_list.return_value = {
            "count": 1,
            "items": [
                {
                    "id": 1,
                    "competition_id": self.competition.id,
                    "competition_name": self.competition.name,
                    "title": "Loaded scenario",
                    "description": "",
                    "season_label": "2024",
                    "mode": "current_expected",
                    "based_on_matchweek": None,
                    "locked_result_count": 2,
                    "updated_at": "2026-04-04T12:00:00Z",
                }
            ],
        }

        response = self.client.get(
            reverse(
                "livefootball-league-saved-scenarios",
                kwargs={"competition_id": self.competition.id},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_saved_scenario_detail_endpoint_is_user_scoped(self) -> None:
        scenario = SavedLeagueScenario.objects.create(
            user=self.user,
            competition=self.competition,
            title="Scoped scenario",
            season_label="2024",
            mode="current_expected",
        )

        response = self.client.get(
            reverse(
                "livefootball-league-saved-scenario-detail",
                kwargs={"scenario_id": scenario.id},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Scoped scenario")
