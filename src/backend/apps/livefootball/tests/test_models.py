from django.db import IntegrityError
from django.test import TestCase

from apps.livefootball.models import (
    Competition,
    CompetitionFixture,
    CompetitionTableSnapshot,
    CompetitionTopScorer,
    PlayerDirectoryEntry,
    SavedLeagueScenario,
    SavedLeagueScenarioLockedFixture,
    TeamDirectoryEntry,
)


class LiveFootballModelTests(TestCase):
    def setUp(self):
        self.provider = "football_data"
        self.competition = Competition.objects.create(
            provider=self.provider,
            external_id="PL",
            code="PL",
            name="Premier League",
            area_name="England",
            current_season_label="2025",
        )
        self.team = TeamDirectoryEntry.objects.create(
            competition=self.competition,
            provider=self.provider,
            season_label="2025",
            external_id="64",
            name="Liverpool",
            short_name="Liverpool",
            tla="LIV",
            area_name="England",
        )

    def test_competition_unique_provider_external_id(self):
        with self.assertRaises(IntegrityError):
            Competition.objects.create(
                provider=self.provider,
                external_id="PL",
                code="PL2",
                name="Duplicate Premier League",
                area_name="England",
            )

    def test_competition_unique_provider_code_when_code_present(self):
        with self.assertRaises(IntegrityError):
            Competition.objects.create(
                provider=self.provider,
                external_id="EPL-SECOND",
                code="PL",
                name="Another League",
                area_name="England",
            )

    def test_competition_rejects_duplicate_blank_codes(self):
        Competition.objects.create(
            provider=self.provider,
            external_id="SA",
            code="",
            name="Serie A",
            area_name="Italy",
        )

        with self.assertRaises(IntegrityError):
            Competition.objects.create(
                provider=self.provider,
                external_id="LL",
                code="",
                name="La Liga",
                area_name="Spain",
            )

    def test_team_directory_entry_unique_per_competition_season_provider_external_id(self):
        with self.assertRaises(IntegrityError):
            TeamDirectoryEntry.objects.create(
                competition=self.competition,
                provider=self.provider,
                season_label="2025",
                external_id="64",
                name="Liverpool Duplicate",
                short_name="Liverpool",
                tla="LIV",
                area_name="England",
            )

    def test_player_directory_entry_defaults_active_true(self):
        player = PlayerDirectoryEntry.objects.create(
            team=self.team,
            provider=self.provider,
            external_player_id="9001",
            player_name="Mohamed Salah",
            first_name="Mohamed",
            last_name="Salah",
            nationality="Egypt",
            primary_position="RW",
        )
        self.assertTrue(player.is_active)

    def test_player_directory_entry_unique_per_team_provider_external_player_id(self):
        PlayerDirectoryEntry.objects.create(
            team=self.team,
            provider=self.provider,
            external_player_id="9001",
            player_name="Mohamed Salah",
            first_name="Mohamed",
            last_name="Salah",
        )

        with self.assertRaises(IntegrityError):
            PlayerDirectoryEntry.objects.create(
                team=self.team,
                provider=self.provider,
                external_player_id="9001",
                player_name="Mohamed Salah Duplicate",
                first_name="Mohamed",
                last_name="Salah",
            )

    def test_competition_table_snapshot_unique_per_competition_season_snapshot_label(self):
        CompetitionTableSnapshot.objects.create(
            competition=self.competition,
            season_label="2025",
            snapshot_label="latest",
        )

        with self.assertRaises(IntegrityError):
            CompetitionTableSnapshot.objects.create(
                competition=self.competition,
                season_label="2025",
                snapshot_label="latest",
            )

    def test_competition_fixture_unique_per_competition_season_external_match_id(self):
        CompetitionFixture.objects.create(
            competition=self.competition,
            season_label="2025",
            external_match_id="match-1",
            status="SCHEDULED",
            home_team=self.team,
            away_team=self.team,
            home_external_team_id="64",
            home_team_name="Liverpool",
            away_external_team_id="64",
            away_team_name="Liverpool",
        )

        with self.assertRaises(IntegrityError):
            CompetitionFixture.objects.create(
                competition=self.competition,
                season_label="2025",
                external_match_id="match-1",
                status="TIMED",
                home_team=self.team,
                away_team=self.team,
                home_external_team_id="64",
                home_team_name="Liverpool",
                away_external_team_id="64",
                away_team_name="Liverpool",
            )

    def test_top_scorer_unique_per_competition_season_rank(self):
        CompetitionTopScorer.objects.create(
            competition=self.competition,
            season_label="2025",
            rank=1,
            external_player_id="9001",
            player_name="Mohamed Salah",
            team=self.team,
            team_name="Liverpool",
            external_team_id="64",
            goals=20,
        )

        with self.assertRaises(IntegrityError):
            CompetitionTopScorer.objects.create(
                competition=self.competition,
                season_label="2025",
                rank=1,
                external_player_id="9002",
                player_name="Erling Haaland",
                team=self.team,
                team_name="Liverpool",
                external_team_id="64",
                goals=19,
            )

    def test_top_scorer_unique_external_player_id_when_present(self):
        CompetitionTopScorer.objects.create(
            competition=self.competition,
            season_label="2025",
            rank=1,
            external_player_id="9001",
            player_name="Mohamed Salah",
            team=self.team,
            team_name="Liverpool",
            external_team_id="64",
            goals=20,
        )

        with self.assertRaises(IntegrityError):
            CompetitionTopScorer.objects.create(
                competition=self.competition,
                season_label="2025",
                rank=2,
                external_player_id="9001",
                player_name="Mohamed Salah",
                team=self.team,
                team_name="Liverpool",
                external_team_id="64",
                goals=20,
            )

    def test_saved_league_scenario_can_be_created(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(
            username="savedscenario",
            email="savedscenario@example.com",
            password="password123",
        )

        scenario = SavedLeagueScenario.objects.create(
            user=user,
            competition=self.competition,
            title="Title race swing",
            season_label="2025",
            mode="current_expected",
        )

        self.assertEqual(scenario.title, "Title race swing")
        self.assertEqual(scenario.season_label, "2025")

    def test_saved_locked_fixture_unique_per_scenario_fixture_key(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(
            username="savedfixture",
            email="savedfixture@example.com",
            password="password123",
        )

        scenario = SavedLeagueScenario.objects.create(
            user=user,
            competition=self.competition,
            title="Relegation escape",
            season_label="2025",
            mode="current_expected",
        )

        SavedLeagueScenarioLockedFixture.objects.create(
            scenario=scenario,
            fixture_key="Liverpool__Arsenal",
            home_team_name="Liverpool",
            away_team_name="Arsenal",
            home_goals=2,
            away_goals=1,
        )

        with self.assertRaises(IntegrityError):
            SavedLeagueScenarioLockedFixture.objects.create(
                scenario=scenario,
                fixture_key="Liverpool__Arsenal",
                home_team_name="Liverpool",
                away_team_name="Arsenal",
                home_goals=1,
                away_goals=1,
            )
