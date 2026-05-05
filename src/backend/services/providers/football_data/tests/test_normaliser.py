from django.test import SimpleTestCase

from services.providers.football_data.normalisers import (
    normalize_competition_matches_payload,
    normalize_competition_scorers_payload,
    normalize_competition_table,
    normalize_competitions_payload,
    normalize_competition_teams_payload,
    normalize_team_players_payload,
)


class FootballDataNormaliserTests(SimpleTestCase):
    def test_normalize_competitions_payload(self):
        payload = {
            "competitions": [
                {
                    "id": 2021,
                    "code": "PL",
                    "name": "Premier League",
                    "type": "LEAGUE",
                    "emblem": "https://img/pl.png",
                    "area": {"name": "England", "code": "ENG", "flag": "https://flag"},
                    "currentSeason": {
                        "startDate": "2025-08-10",
                        "endDate": "2026-05-20",
                        "currentMatchday": 28,
                    },
                }
            ]
        }

        items = normalize_competitions_payload(payload)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["provider"], "football_data")
        self.assertEqual(items[0]["external_id"], "2021")
        self.assertEqual(items[0]["code"], "PL")
        self.assertEqual(items[0]["name"], "Premier League")
        self.assertEqual(items[0]["area_name"], "England")
        self.assertEqual(items[0]["current_season_label"], "2025")
        self.assertEqual(items[0]["current_matchday"], 28)

    def test_normalize_competition_teams_payload(self):
        payload = {
            "competition": {"id": 2021},
            "season": {"startDate": "2025-08-10"},
            "teams": [
                {
                    "id": 64,
                    "name": "Liverpool FC",
                    "shortName": "Liverpool",
                    "tla": "LIV",
                    "crest": "https://img/liv.png",
                    "venue": "Anfield",
                    "website": "https://liverpoolfc.com",
                    "founded": 1892,
                    "area": {"name": "England", "code": "ENG", "flag": "https://flag"},
                }
            ],
        }

        items = normalize_competition_teams_payload(payload)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["competition_external_id"], "2021")
        self.assertEqual(items[0]["season_label"], "2025")
        self.assertEqual(items[0]["external_id"], "64")
        self.assertEqual(items[0]["name"], "Liverpool FC")
        self.assertEqual(items[0]["tla"], "LIV")

    def test_normalize_team_players_payload(self):
        payload = [
            {
                "id": 9001,
                "name": "Mohamed Salah",
                "position": "Right Winger",
                "shirtNumber": 11,
                "dateOfBirth": "1992-06-15",
                "nationality": "Egypt",
            }
        ]

        items = normalize_team_players_payload(payload, team_external_id=64)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["team_external_id"], "64")
        self.assertEqual(items[0]["external_player_id"], "9001")
        self.assertEqual(items[0]["player_name"], "Mohamed Salah")
        self.assertEqual(items[0]["primary_position"], "RW")
        self.assertEqual(items[0]["squad_number"], 11)

    def test_normalize_competition_table(self):
        payload = {
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
                            "team": {
                                "id": 64,
                                "name": "Liverpool FC",
                                "shortName": "Liverpool",
                                "tla": "LIV",
                                "crest": "https://img/liv.png",
                            },
                        }
                    ],
                }
            ],
        }

        item = normalize_competition_table(payload, snapshot_label="latest")

        self.assertEqual(item["competition_external_id"], "2021")
        self.assertEqual(item["season_label"], "2025")
        self.assertEqual(item["snapshot_label"], "latest")
        self.assertEqual(item["matchday"], 28)
        self.assertEqual(len(item["rows"]), 1)
        self.assertEqual(item["rows"][0]["position"], 1)
        self.assertEqual(item["rows"][0]["external_team_id"], "64")
        self.assertEqual(item["rows"][0]["points"], 65)

    def test_normalize_competition_matches_payload(self):
        payload = {
            "competition": {"id": 2021},
            "season": {"startDate": "2025-08-10"},
            "matches": [
                {
                    "id": 555,
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

        items = normalize_competition_matches_payload(payload)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["competition_external_id"], "2021")
        self.assertEqual(items[0]["season_label"], "2025")
        self.assertEqual(items[0]["external_match_id"], "555")
        self.assertEqual(items[0]["home_external_team_id"], "64")
        self.assertEqual(items[0]["away_external_team_id"], "65")
        self.assertEqual(items[0]["home_score"], 2)
        self.assertEqual(items[0]["away_score"], 1)

    def test_normalize_competition_scorers_payload(self):
        payload = {
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
                    "team": {
                        "id": 64,
                        "name": "Liverpool FC",
                    },
                    "goals": 20,
                    "penalties": 5,
                    "assists": 10,
                    "playedMatches": 27,
                }
            ],
        }

        items = normalize_competition_scorers_payload(payload)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["competition_external_id"], "2021")
        self.assertEqual(items[0]["season_label"], "2025")
        self.assertEqual(items[0]["rank"], 1)
        self.assertEqual(items[0]["external_player_id"], "9001")
        self.assertEqual(items[0]["external_team_id"], "64")
        self.assertEqual(items[0]["goals"], 20)
        self.assertEqual(items[0]["penalties"], 5)