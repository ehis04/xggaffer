from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.livefootball.models import (
    Competition,
    CompetitionFixture,
    CompetitionTableRow,
    CompetitionTableSnapshot,
    CompetitionTopScorer,
    PlayerDirectoryEntry,
    TeamDirectoryEntry,
)


class LiveFootballViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="livefootballtester",
            email="livefootball@example.com",
            password="testpass123",
        )
        self.client = APIClient(HTTP_HOST='localhost')
        self.client.force_authenticate(user=self.user)

        self.provider = "football_data"
        self.competition = Competition.objects.create(
            provider=self.provider,
            external_id="2021",
            code="PL",
            name="Premier League",
            area_name="England",
            current_season_label="2025",
        )
        self.other_competition = Competition.objects.create(
            provider=self.provider,
            external_id="2014",
            code="PD",
            name="La Liga",
            area_name="Spain",
            current_season_label="2025",
        )

        self.team_one = TeamDirectoryEntry.objects.create(
            competition=self.competition,
            provider=self.provider,
            season_label="2025",
            external_id="64",
            name="Liverpool FC",
            short_name="Liverpool",
            tla="LIV",
            area_name="England",
        )
        self.team_two = TeamDirectoryEntry.objects.create(
            competition=self.competition,
            provider=self.provider,
            season_label="2025",
            external_id="65",
            name="Manchester City FC",
            short_name="Man City",
            tla="MCI",
            area_name="England",
        )
        self.team_old_season = TeamDirectoryEntry.objects.create(
            competition=self.competition,
            provider=self.provider,
            season_label="2024",
            external_id="66",
            name="Arsenal FC",
            short_name="Arsenal",
            tla="ARS",
            area_name="England",
        )

        self.snapshot = CompetitionTableSnapshot.objects.create(
            competition=self.competition,
            season_label="2025",
            snapshot_label="latest",
            matchday=28,
            synced_at=timezone.now(),
        )
        CompetitionTableRow.objects.create(
            snapshot=self.snapshot,
            team=None,
            position=1,
            external_team_id="64",
            team_name="Liverpool FC",
            played=28,
            won=20,
            drawn=5,
            lost=3,
            goals_for=60,
            goals_against=22,
            goal_difference=38,
            points=65,
            form="W,W,D,W,W",
        )

        now = timezone.now()
        CompetitionFixture.objects.create(
            competition=self.competition,
            season_label="2025",
            external_match_id="f1",
            status="FINISHED",
            kickoff_at=now - timedelta(days=3),
            matchday=27,
            home_team=None,
            away_team=self.team_two,
            home_external_team_id="64",
            home_team_name="Liverpool FC",
            away_external_team_id="65",
            away_team_name="Manchester City FC",
            home_score=2,
            away_score=1,
        )
        CompetitionFixture.objects.create(
            competition=self.competition,
            season_label="2025",
            external_match_id="f2",
            status="SCHEDULED",
            kickoff_at=now + timedelta(days=2),
            matchday=29,
            home_team=self.team_two,
            away_team=None,
            home_external_team_id="65",
            home_team_name="Manchester City FC",
            away_external_team_id="64",
            away_team_name="Liverpool FC",
            home_score=None,
            away_score=None,
        )

        CompetitionTopScorer.objects.create(
            competition=self.competition,
            season_label="2025",
            rank=1,
            external_player_id="9001",
            player_name="Mohamed Salah",
            team=None,
            team_name="Liverpool FC",
            external_team_id="64",
            goals=20,
            penalties=5,
        )

        PlayerDirectoryEntry.objects.create(
            team=self.team_one,
            provider=self.provider,
            external_player_id="9001",
            player_name="Mohamed Salah",
            first_name="Mohamed",
            last_name="Salah",
            nationality="Egypt",
            primary_position="RW",
            squad_number=11,
            is_active=True,
        )
        PlayerDirectoryEntry.objects.create(
            team=self.team_two,
            provider=self.provider,
            external_player_id="9002",
            player_name="Erling Haaland",
            first_name="Erling",
            last_name="Haaland",
            nationality="Norway",
            primary_position="ST",
            squad_number=9,
            is_active=True,
        )
        PlayerDirectoryEntry.objects.create(
            team=self.team_old_season,
            provider=self.provider,
            external_player_id="9003",
            player_name="Bukayo Saka",
            first_name="Bukayo",
            last_name="Saka",
            nationality="England",
            primary_position="RW",
            squad_number=7,
            is_active=False,
        )

    def test_competition_list_route_returns_expected_shape(self):
        response = self.client.get(reverse("livefootball-competition-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)
        item = response.json()[0]
        self.assertIn("id", item)
        self.assertIn("provider", item)
        self.assertIn("external_id", item)
        self.assertIn("name", item)
        self.assertIn("current_season_label", item)

    def test_competition_list_provider_filter(self):
        response = self.client.get(
            reverse("livefootball-competition-list"),
            {"provider": "football_data"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

    def test_competition_table_route_is_null_safe(self):
        response = self.client.get(
            reverse("livefootball-competition-table", args=[self.competition.id])
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["competition"]["id"], self.competition.id)
        self.assertEqual(len(payload["rows"]), 1)
        self.assertIsNone(payload["rows"][0]["team"]["id"])
        self.assertEqual(payload["rows"][0]["team"]["external_id"], "64")
        self.assertEqual(payload["rows"][0]["team"]["name"], "Liverpool FC")

    def test_competition_fixtures_route_filters_by_status(self):
        response = self.client.get(
            reverse("livefootball-competition-fixtures", args=[self.competition.id]),
            {"status": "FINISHED"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["items"][0]["external_match_id"], "f1")

    def test_competition_fixtures_route_rejects_bad_matchday(self):
        response = self.client.get(
            reverse("livefootball-competition-fixtures", args=[self.competition.id]),
            {"matchday": "bad"},
        )

        self.assertEqual(response.status_code, 400)

    def test_competition_previous_next_route_returns_split_shape(self):
        response = self.client.get(
            reverse("livefootball-competition-fixtures-split", args=[self.competition.id]),
            {"previous_limit": 2, "next_limit": 2},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("previous", payload)
        self.assertIn("next", payload)
        self.assertEqual(len(payload["previous"]), 1)
        self.assertEqual(len(payload["next"]), 1)

    def test_competition_scorers_route_is_null_safe(self):
        response = self.client.get(
            reverse("livefootball-competition-scorers", args=[self.competition.id])
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertIsNone(payload["items"][0]["team"]["id"])
        self.assertIsNone(payload["items"][0]["canonical_player"]["id"])
        self.assertEqual(payload["items"][0]["player_name"], "Mohamed Salah")

    def test_competition_teams_route_filters_by_season(self):
        response = self.client.get(
            reverse("livefootball-competition-teams", args=[self.competition.id]),
            {"season": "2025"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 2)
        self.assertEqual(
            {item["name"] for item in payload["items"]},
            {"Liverpool FC", "Manchester City FC"},
        )

    def test_team_players_route_returns_serializer_shape(self):
        response = self.client.get(
            reverse("livefootball-team-players", args=[self.team_one.id])
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["team"]["id"], self.team_one.id)
        self.assertEqual(payload["count"], 1)
        item = payload["items"][0]
        self.assertIn("player_name", item)
        self.assertIn("team", item)
        self.assertIn("canonical_player", item)

    def test_competition_players_route_filters_active_only(self):
        response = self.client.get(
            reverse("livefootball-competition-players", args=[self.competition.id]),
            {"active_only": "true"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 2)
        self.assertEqual(
            {item["player_name"] for item in payload["items"]},
            {"Mohamed Salah", "Erling Haaland"},
        )

    def test_player_search_route_supports_text_search(self):
        response = self.client.get(
            reverse("livefootball-player-search"),
            {"q": "Salah"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["items"][0]["player_name"], "Mohamed Salah")

    def test_player_search_route_supports_team_filter(self):
        response = self.client.get(
            reverse("livefootball-player-search"),
            {"q": "Haaland", "team_id": self.team_two.id},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["items"][0]["team"]["id"], self.team_two.id)

    def test_player_search_route_rejects_bad_limit(self):
        response = self.client.get(
            reverse("livefootball-player-search"),
            {"q": "Salah", "limit": "bad"},
        )

        self.assertEqual(response.status_code, 400)