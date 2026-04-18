from unittest.mock import Mock

from django.test import TestCase

from apps.livefootball.models import (
    Competition,
    CompetitionFixture,
    PlayerDirectoryEntry,
    CompetitionTableRow,
    CompetitionTableSnapshot,
    CompetitionTopScorer,
    TeamDirectoryEntry,
)
from services.providers.football_data.exceptions import FootballDataAuthenticationError
from services.providers.football_data.sync import FootballDataSyncService


class FootballDataSyncServiceTests(TestCase):
    def setUp(self):
        self.provider = "football_data"
        self.client = Mock()
        self.service = FootballDataSyncService(client=self.client)
        self.competition = Competition.objects.create(
            provider=self.provider,
            external_id="2021",
            code="PL",
            name="Premier League",
            area_name="England",
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

    def test_sync_competitions_creates_competition_records(self):
        self.client.get_competitions.return_value = {
            "competitions": [
                {
                    "id": 2014,
                    "code": "PD",
                    "name": "La Liga",
                    "type": "LEAGUE",
                    "emblem": "https://img/pd.png",
                    "area": {"name": "Spain", "code": "ESP", "flag": "https://flag"},
                    "currentSeason": {
                        "startDate": "2025-08-15",
                        "endDate": "2026-05-25",
                        "currentMatchday": 27,
                    },
                }
            ]
        }

        result = self.service.sync_competitions(areas=[2072, 2224])

        self.assertEqual(result["summary"]["status"], "success")
        self.assertTrue(
            Competition.objects.filter(provider=self.provider, external_id="2014").exists()
        )
        competition = Competition.objects.get(provider=self.provider, external_id="2014")
        self.assertEqual(competition.name, "La Liga")
        self.assertEqual(result["summary"]["records_processed"], 1)

    def test_sync_competition_table_replaces_snapshot_rows(self):
        snapshot = CompetitionTableSnapshot.objects.create(
            competition=self.competition,
            season_label="2025",
            snapshot_label="latest",
        )
        CompetitionTableRow.objects.create(
            snapshot=snapshot,
            team=self.team_one,
            position=1,
            external_team_id="64",
            team_name="Liverpool FC",
            played=1,
            won=1,
            drawn=0,
            lost=0,
            goals_for=3,
            goals_against=0,
            goal_difference=3,
            points=3,
        )

        self.client.get_competition_table.return_value = {
            "competition": {"id": 2021},
            "season": {"startDate": "2025-08-10", "currentMatchday": 28},
            "standings": [
                {
                    "type": "TOTAL",
                    "stage": "REGULAR_SEASON",
                    "table": [
                        {
                            "position": 1,
                            "playedGames": 28,
                            "won": 20,
                            "draw": 5,
                            "lost": 3,
                            "goalsFor": 60,
                            "goalsAgainst": 22,
                            "goalDifference": 38,
                            "points": 65,
                            "form": "W,W,D,W,W",
                            "team": {"id": 64, "name": "Liverpool FC", "shortName": "Liverpool", "tla": "LIV"},
                        },
                        {
                            "position": 2,
                            "playedGames": 28,
                            "won": 19,
                            "draw": 6,
                            "lost": 3,
                            "goalsFor": 59,
                            "goalsAgainst": 24,
                            "goalDifference": 35,
                            "points": 63,
                            "form": "W,W,W,D,W",
                            "team": {"id": 65, "name": "Manchester City FC", "shortName": "Man City", "tla": "MCI"},
                        },
                    ],
                }
            ],
        }

        result = self.service.sync_competition_table("2021", season=2025, snapshot_label="latest")

        snapshot.refresh_from_db()
        self.assertEqual(result["summary"]["status"], "success")
        self.assertEqual(snapshot.matchday, 28)
        self.assertEqual(snapshot.rows.count(), 2)
        self.assertEqual(snapshot.rows.order_by("position").first().team_id, self.team_one.id)

    def test_sync_competition_fixtures_upserts_fixtures(self):
        self.client.get_competition_matches.return_value = {
            "competition": {"id": 2021},
            "season": {"startDate": "2025-08-10"},
            "matches": [
                {
                    "id": 777,
                    "status": "FINISHED",
                    "utcDate": "2026-03-14T15:00:00Z",
                    "matchday": 28,
                    "stage": "REGULAR_SEASON",
                    "group": None,
                    "homeTeam": {"id": 64, "name": "Liverpool FC", "shortName": "Liverpool", "tla": "LIV"},
                    "awayTeam": {"id": 65, "name": "Manchester City FC", "shortName": "Man City", "tla": "MCI"},
                    "score": {
                        "winner": "HOME_TEAM",
                        "duration": "REGULAR",
                        "fullTime": {"home": 2, "away": 1},
                    },
                }
            ],
        }

        result = self.service.sync_competition_fixtures("2021", season=2025)

        self.assertEqual(result["summary"]["status"], "success")
        fixture = CompetitionFixture.objects.get(
            competition=self.competition,
            season_label="2025",
            external_match_id="777",
        )
        self.assertEqual(fixture.home_team_id, self.team_one.id)
        self.assertEqual(fixture.away_team_id, self.team_two.id)
        self.assertEqual(fixture.home_score, 2)
        self.assertEqual(fixture.away_score, 1)

    def test_sync_competition_scorers_replaces_existing_rows(self):
        CompetitionTopScorer.objects.create(
            competition=self.competition,
            season_label="2025",
            rank=1,
            external_player_id="old-1",
            player_name="Old Player",
            team=self.team_one,
            team_name="Liverpool FC",
            external_team_id="64",
            goals=99,
        )

        self.client.get_competition_scorers.return_value = {
            "competition": {"id": 2021},
            "season": {"startDate": "2025-08-10"},
            "scorers": [
                {
                    "player": {
                        "id": 9001,
                        "name": "Mohamed Salah",
                        "firstName": "Mohamed",
                        "lastName": "Salah",
                        "dateOfBirth": "1992-06-15",
                        "nationality": "Egypt",
                    },
                    "team": {"id": 64, "name": "Liverpool FC"},
                    "goals": 20,
                    "penalties": 5,
                    "assists": 10,
                    "playedMatches": 27,
                },
                {
                    "player": {
                        "id": 9002,
                        "name": "Erling Haaland",
                        "firstName": "Erling",
                        "lastName": "Haaland",
                        "dateOfBirth": "2000-07-21",
                        "nationality": "Norway",
                    },
                    "team": {"id": 65, "name": "Manchester City FC"},
                    "goals": 19,
                    "penalties": 2,
                    "assists": 7,
                    "playedMatches": 26,
                },
            ],
        }

        result = self.service.sync_competition_scorers("2021", season=2025)

        self.assertEqual(result["summary"]["status"], "success")
        self.assertEqual(
            CompetitionTopScorer.objects.filter(
                competition=self.competition,
                season_label="2025",
            ).count(),
            2,
        )
        self.assertFalse(
            CompetitionTopScorer.objects.filter(
                competition=self.competition,
                season_label="2025",
                external_player_id="old-1",
            ).exists()
        )
        top = CompetitionTopScorer.objects.get(
            competition=self.competition,
            season_label="2025",
            rank=1,
        )
        self.assertEqual(top.player_name, "Mohamed Salah")
        self.assertEqual(top.team_id, self.team_one.id)

    def test_sync_team_squad_directory_falls_back_to_understat_on_auth_error(self):
        self.client.get_team.side_effect = FootballDataAuthenticationError(
            "Football-data authentication failed with status 403."
        )

        understat_client = Mock()
        understat_client.get_team_players.return_value = [
            {"id": 5001, "player_name": "Fallback One", "position": "FWD"},
            {"id": 5002, "player_name": "Fallback Two", "position": "MID"},
        ]
        self.service._understat_client = understat_client

        result = self.service.sync_team_squad_directory(
            competition_external_id="2021",
            team_external_id="64",
            season=2025,
        )

        self.assertEqual(result["summary"]["status"], "success")
        self.assertTrue(result["summary"]["metadata"]["fallback_used"])
        self.assertEqual(result["summary"]["metadata"]["fallback_provider"], "understat")
        self.assertEqual(result["summary"]["records_processed"], 2)

        entries = PlayerDirectoryEntry.objects.filter(
            team=self.team_one,
            provider=self.provider,
            is_active=True,
        ).order_by("external_player_id")

        self.assertEqual(entries.count(), 2)
        self.assertTrue(entries[0].external_player_id.startswith("understat:"))
        self.assertTrue(entries[1].external_player_id.startswith("understat:"))
        self.assertEqual(entries[0].metadata.get("source"), "understat_fallback")
        self.assertEqual(entries[1].metadata.get("source"), "understat_fallback")