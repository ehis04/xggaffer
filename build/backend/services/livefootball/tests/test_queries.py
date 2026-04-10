from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.livefootball.models import (
    Competition,
    CompetitionFixture,
    CompetitionTableRow,
    CompetitionTableSnapshot,
    CompetitionTopScorer,
    PlayerDirectoryEntry,
    TeamDirectoryEntry,
)
from services.livefootball.queries import (
    get_competition_fixtures,
    get_competition_previous_next_fixtures,
    get_competition_scorers,
    get_competition_table,
    list_competition_players,
    list_competition_teams,
    list_competitions,
    list_team_players,
    search_players,
)


class LiveFootballQueryTests(TestCase):
    def setUp(self):
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
        self.other_team = TeamDirectoryEntry.objects.create(
            competition=self.other_competition,
            provider=self.provider,
            season_label="2025",
            external_id="81",
            name="Barcelona",
            short_name="Barca",
            tla="BAR",
            area_name="Spain",
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
            team=self.team_one,
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
        CompetitionTableRow.objects.create(
            snapshot=self.snapshot,
            team=self.team_two,
            position=2,
            external_team_id="65",
            team_name="Manchester City FC",
            played=28,
            won=19,
            drawn=6,
            lost=3,
            goals_for=59,
            goals_against=24,
            goal_difference=35,
            points=63,
            form="W,W,W,D,W",
        )

        now = timezone.now()
        self.previous_fixture_older = CompetitionFixture.objects.create(
            competition=self.competition,
            season_label="2025",
            external_match_id="f1",
            status="FINISHED",
            kickoff_at=now - timedelta(days=10),
            matchday=26,
            home_team=self.team_one,
            away_team=self.team_two,
            home_external_team_id="64",
            home_team_name="Liverpool FC",
            away_external_team_id="65",
            away_team_name="Manchester City FC",
            home_score=1,
            away_score=0,
        )
        self.previous_fixture_newer = CompetitionFixture.objects.create(
            competition=self.competition,
            season_label="2025",
            external_match_id="f2",
            status="FINISHED",
            kickoff_at=now - timedelta(days=3),
            matchday=27,
            home_team=self.team_two,
            away_team=self.team_one,
            home_external_team_id="65",
            home_team_name="Manchester City FC",
            away_external_team_id="64",
            away_team_name="Liverpool FC",
            home_score=2,
            away_score=2,
        )
        self.next_fixture_earlier = CompetitionFixture.objects.create(
            competition=self.competition,
            season_label="2025",
            external_match_id="f3",
            status="SCHEDULED",
            kickoff_at=now + timedelta(days=2),
            matchday=29,
            home_team=self.team_one,
            away_team=self.team_two,
            home_external_team_id="64",
            home_team_name="Liverpool FC",
            away_external_team_id="65",
            away_team_name="Manchester City FC",
        )
        self.next_fixture_later = CompetitionFixture.objects.create(
            competition=self.competition,
            season_label="2025",
            external_match_id="f4",
            status="TIMED",
            kickoff_at=now + timedelta(days=7),
            matchday=30,
            home_team=self.team_two,
            away_team=self.team_one,
            home_external_team_id="65",
            home_team_name="Manchester City FC",
            away_external_team_id="64",
            away_team_name="Liverpool FC",
        )

        CompetitionTopScorer.objects.create(
            competition=self.competition,
            season_label="2025",
            rank=1,
            external_player_id="9001",
            player_name="Mohamed Salah",
            team=self.team_one,
            team_name="Liverpool FC",
            external_team_id="64",
            goals=20,
            penalties=5,
        )
        CompetitionTopScorer.objects.create(
            competition=self.competition,
            season_label="2025",
            rank=2,
            external_player_id="9002",
            player_name="Erling Haaland",
            team=self.team_two,
            team_name="Manchester City FC",
            external_team_id="65",
            goals=19,
            penalties=2,
        )

        self.team_one_player = PlayerDirectoryEntry.objects.create(
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
        self.team_two_player = PlayerDirectoryEntry.objects.create(
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
            team=self.other_team,
            provider=self.provider,
            external_player_id="9010",
            player_name="Lamine Yamal",
            first_name="Lamine",
            last_name="Yamal",
            nationality="Spain",
            primary_position="RW",
            squad_number=19,
            is_active=True,
        )

    def test_list_competitions(self):
        items = list_competitions()

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["name"], "La Liga")
        self.assertEqual(items[1]["name"], "Premier League")

    def test_get_competition_table(self):
        payload = get_competition_table(self.competition.id)

        self.assertEqual(payload["competition"]["id"], self.competition.id)
        self.assertEqual(payload["season_label"], "2025")
        self.assertEqual(payload["matchday"], 28)
        self.assertEqual(len(payload["rows"]), 2)
        self.assertEqual(payload["rows"][0]["position"], 1)
        self.assertEqual(payload["rows"][0]["team"]["id"], self.team_one.id)

    def test_get_competition_fixtures(self):
        payload = get_competition_fixtures(self.competition.id, status="FINISHED")

        self.assertEqual(payload["competition"]["id"], self.competition.id)
        self.assertEqual(payload["count"], 2)
        self.assertEqual(payload["items"][0]["external_match_id"], "f1")
        self.assertEqual(payload["items"][1]["external_match_id"], "f2")

    def test_get_competition_previous_next_fixtures(self):
        payload = get_competition_previous_next_fixtures(
            self.competition.id,
            previous_limit=2,
            next_limit=2,
        )

        self.assertEqual(len(payload["previous"]), 2)
        self.assertEqual(len(payload["next"]), 2)
        self.assertEqual(payload["previous"][0]["external_match_id"], "f2")
        self.assertEqual(payload["previous"][1]["external_match_id"], "f1")
        self.assertEqual(payload["next"][0]["external_match_id"], "f3")
        self.assertEqual(payload["next"][1]["external_match_id"], "f4")

    def test_get_competition_scorers(self):
        payload = get_competition_scorers(self.competition.id)

        self.assertEqual(payload["count"], 2)
        self.assertEqual(payload["items"][0]["rank"], 1)
        self.assertEqual(payload["items"][0]["player_name"], "Mohamed Salah")
        self.assertEqual(payload["items"][1]["player_name"], "Erling Haaland")

    def test_list_competition_teams(self):
        payload = list_competition_teams(self.competition.id)

        self.assertEqual(payload["count"], 2)
        self.assertEqual(payload["items"][0]["name"], "Liverpool FC")
        self.assertEqual(payload["items"][1]["name"], "Manchester City FC")

    def test_list_team_players(self):
        payload = list_team_players(self.team_one.id)

        self.assertEqual(payload["team"]["id"], self.team_one.id)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["items"][0]["player_name"], "Mohamed Salah")
        self.assertEqual(payload["items"][0]["team"]["id"], self.team_one.id)

    def test_list_competition_players(self):
        payload = list_competition_players(self.competition.id)

        self.assertEqual(payload["competition"]["id"], self.competition.id)
        self.assertEqual(payload["count"], 2)
        self.assertEqual(
            {item["player_name"] for item in payload["items"]},
            {"Mohamed Salah", "Erling Haaland"},
        )

    def test_search_players(self):
        payload = search_players("Salah")

        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["items"][0]["player_name"], "Mohamed Salah")

    def test_search_players_with_competition_filter(self):
        payload = search_players("Yamal", competition_id=self.competition.id)

        self.assertEqual(payload["count"], 0)

    def test_search_players_with_team_filter(self):
        payload = search_players("Haaland", team_id=self.team_two.id)

        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["items"][0]["team"]["id"], self.team_two.id)