from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.livefootball.services.overview import (
    get_homepage_top_performing_scorers,
    get_livefootball_homepage_payload,
)


def competition_list() -> list[dict]:
    return [
        {"id": 1, "code": "PL", "name": "Premier League"},
        {"id": 2, "code": "PD", "name": "La Liga"},
        {"id": 3, "code": "BL1", "name": "Bundesliga"},
        {"id": 4, "code": "SA", "name": "Serie A"},
        {"id": 5, "code": "FL1", "name": "Ligue 1"},
        {"id": 6, "code": "RPL", "name": "Russian Premier League"},
    ]


def table_payload(competition_id: int, code: str, name: str) -> dict:
    return {
        "competition": {
            "id": competition_id,
            "code": code,
            "name": name,
            "country": "",
            "emblem_url": "",
        },
        "synced_at": "2026-03-30T09:59:00Z",
        "rows": [
            {
                "position": 1,
                "team": {"id": competition_id * 100 + 1, "name": f"{name} Leaders", "short_name": "Leaders", "crest_url": ""},
                "played": 30,
                "won": 22,
                "drawn": 4,
                "lost": 4,
                "goals_for": 60,
                "goals_against": 25,
                "goal_difference": 35,
                "points": 70,
                "form": "W-W-W-W-D",
            },
            {
                "position": 2,
                "team": {"id": competition_id * 100 + 2, "name": f"{name} Second", "short_name": "Second", "crest_url": ""},
                "played": 30,
                "won": 20,
                "drawn": 6,
                "lost": 4,
                "goals_for": 55,
                "goals_against": 27,
                "goal_difference": 28,
                "points": 66,
                "form": "W-W-D-W-W",
            },
            {
                "position": 3,
                "team": {"id": competition_id * 100 + 3, "name": f"{name} Third", "short_name": "Third", "crest_url": ""},
                "played": 30,
                "won": 18,
                "drawn": 8,
                "lost": 4,
                "goals_for": 50,
                "goals_against": 30,
                "goal_difference": 20,
                "points": 62,
                "form": "W-D-W-W-D",
            },
            {
                "position": 20,
                "team": {"id": competition_id * 100 + 20, "name": f"{name} Bottom", "short_name": "Bottom", "crest_url": ""},
                "played": 30,
                "won": 3,
                "drawn": 5,
                "lost": 22,
                "goals_for": 20,
                "goals_against": 68,
                "goal_difference": -48,
                "points": 14,
                "form": "L-L-D-L-L",
            },
        ],
    }


def fixtures_payload(competition_id: int, code: str, name: str) -> dict:
    competition = {
        "id": competition_id,
        "code": code,
        "name": name,
        "country": "",
        "emblem_url": "",
        "last_synced_at": "2026-03-30T09:58:00Z",
    }
    return {
        "competition": competition,
        "previous": [
            {
                "id": competition_id * 1000 + 1,
                "kickoff_at": "2026-03-29T15:00:00Z",
                "status": "FINISHED",
                "home_team": {"id": 1, "name": "Home A", "short_name": "Home A", "crest_url": ""},
                "away_team": {"id": 2, "name": "Away B", "short_name": "Away B", "crest_url": ""},
                "home_score": 2,
                "away_score": 1,
            }
        ],
        "next": [
            {
                "id": competition_id * 1000 + 2,
                "kickoff_at": "2026-04-01T19:45:00Z",
                "status": "SCHEDULED",
                "home_team": {"id": 3, "name": "Home C", "short_name": "Home C", "crest_url": ""},
                "away_team": {"id": 4, "name": "Away D", "short_name": "Away D", "crest_url": ""},
                "home_score": None,
                "away_score": None,
            }
        ],
    }


def scorers_payload(competition_id: int, code: str, name: str) -> dict:
    return {
        "competition": {
            "id": competition_id,
            "code": code,
            "name": name,
            "country": "",
            "emblem_url": "",
            "last_synced_at": "2026-03-30T09:57:00Z",
        },
        "items": [
            {
                "rank": 1,
                "goals": 20 + competition_id,
                "penalties": 2,
                "player_name": f"{name} Striker",
                "external_player_id": str(competition_id * 500),
                "team": {"id": competition_id * 20, "name": f"{name} FC", "short_name": "FC", "crest_url": ""},
                "canonical_player": {
                    "id": competition_id * 500,
                    "display_name": f"{name} Striker",
                    "first_name": name,
                    "last_name": "Striker",
                },
            }
        ],
    }


def team_players_payload(team_id: int) -> dict:
    return {
        "items": [
            {
                "id": team_id * 10 + 1,
                "player_name": "Lead Attacker",
                "first_name": "Lead",
                "last_name": "Attacker",
                "primary_position": "ST",
                "raw_position": "ST",
                "squad_number": 9,
            },
            {
                "id": team_id * 10 + 2,
                "player_name": "Starting Keeper",
                "first_name": "Starting",
                "last_name": "Keeper",
                "primary_position": "GK",
                "raw_position": "GK",
                "squad_number": 1,
            },
        ]
    }


class LiveFootballOverviewHelpersTests(SimpleTestCase):
    @patch("apps.livefootball.services.overview.get_homepage_strikers_with_a_lull")
    @patch("apps.livefootball.services.overview.get_homepage_latest_hat_tricks")
    @patch("apps.livefootball.services.overview.get_homepage_all_time_streaks")
    @patch("apps.livefootball.services.overview.get_competition_scorers")
    @patch("apps.livefootball.services.overview.list_team_players")
    @patch("apps.livefootball.services.overview.get_competition_previous_next_fixtures")
    @patch("apps.livefootball.services.overview.get_competition_table")
    @patch("apps.livefootball.services.overview.list_competitions")
    def test_get_livefootball_homepage_payload_returns_expected_sections(
        self,
        mock_list_competitions,
        mock_get_table,
        mock_get_previous_next,
        mock_list_team_players,
        mock_get_scorers,
        mock_get_streaks,
        mock_hat_tricks,
        mock_lull,
    ) -> None:
        mock_hat_tricks.return_value = {"updated_at": None, "items": []}
        mock_lull.return_value = {"updated_at": None, "items": []}
        competitions = competition_list()
        mock_list_competitions.return_value = competitions
        mock_get_table.side_effect = lambda competition_id: table_payload(
            competition_id,
            next(item["code"] for item in competitions if item["id"] == competition_id),
            next(item["name"] for item in competitions if item["id"] == competition_id),
        )
        mock_get_previous_next.side_effect = lambda competition_id, previous_limit=5, next_limit=5: fixtures_payload(
            competition_id,
            next(item["code"] for item in competitions if item["id"] == competition_id),
            next(item["name"] for item in competitions if item["id"] == competition_id),
        )
        mock_get_scorers.side_effect = lambda competition_id, limit=3: scorers_payload(
            competition_id,
            next(item["code"] for item in competitions if item["id"] == competition_id),
            next(item["name"] for item in competitions if item["id"] == competition_id),
        )
        mock_list_team_players.side_effect = lambda team_id, active_only=True: team_players_payload(team_id)
        mock_get_streaks.return_value = {
            "updated_at": None,
            "all_time": [],
            "current": [],
            "cta": {"label": "View streaks", "path": "/livefootball/streaks", "query": {}},
        }

        payload = get_livefootball_homepage_payload()

        self.assertEqual(
            sorted(payload.keys()),
            sorted(
                [
                    "generated_at",
                    "league_order",
                    "league_snapshot",
                    "top_performing_teams",
                    "top_performing_scorers",
                    "latest_hat_tricks",
                    "strikers_with_a_lull",
                    "recent_matches_by_league",
                    "upcoming_matches_by_league",
                    "first_vs_last_by_league",
                    "all_time_streaks",
                ]
            ),
        )
        self.assertEqual(payload["league_order"], ["PL", "LL", "BL1", "SA", "FL1", "RPL"])
        self.assertEqual(len(payload["league_snapshot"]), 6)
        self.assertEqual(len(payload["recent_matches_by_league"]), 6)
        self.assertEqual(len(payload["upcoming_matches_by_league"]), 6)
        self.assertEqual(len(payload["first_vs_last_by_league"]), 6)

    @patch("apps.livefootball.services.overview.get_homepage_strikers_with_a_lull")
    @patch("apps.livefootball.services.overview.get_homepage_latest_hat_tricks")
    @patch("apps.livefootball.services.overview.get_homepage_all_time_streaks")
    @patch("apps.livefootball.services.overview.get_competition_scorers")
    @patch("apps.livefootball.services.overview.list_team_players")
    @patch("apps.livefootball.services.overview.get_competition_previous_next_fixtures")
    @patch("apps.livefootball.services.overview.get_competition_table")
    @patch("apps.livefootball.services.overview.list_competitions")
    def test_helper_payload_survives_empty_fixtures_and_missing_spotlights(
        self,
        mock_list_competitions,
        mock_get_table,
        mock_get_previous_next,
        mock_list_team_players,
        mock_get_scorers,
        mock_get_streaks,
        mock_hat_tricks,
        mock_lull,
    ) -> None:
        mock_hat_tricks.return_value = {"updated_at": None, "items": []}
        mock_lull.return_value = {"updated_at": None, "items": []}
        competitions = competition_list()
        mock_list_competitions.return_value = competitions
        mock_get_table.side_effect = lambda competition_id: table_payload(
            competition_id,
            next(item["code"] for item in competitions if item["id"] == competition_id),
            next(item["name"] for item in competitions if item["id"] == competition_id),
        )
        mock_get_previous_next.return_value = {
            "competition": {
                "id": 1,
                "code": "PL",
                "name": "Premier League",
                "country": "",
                "emblem_url": "",
                "last_synced_at": "2026-03-30T09:58:00Z",
            },
            "previous": [],
            "next": [],
        }
        mock_get_scorers.return_value = {
            "competition": {
                "id": 1,
                "code": "PL",
                "name": "Premier League",
                "country": "",
                "emblem_url": "",
                "last_synced_at": "2026-03-30T09:57:00Z",
            },
            "items": [],
        }
        mock_list_team_players.return_value = {"items": []}
        mock_get_streaks.return_value = {
            "updated_at": None,
            "all_time": [],
            "current": [],
            "cta": {"label": "View streaks", "path": "/livefootball/streaks", "query": {}},
        }

        payload = get_livefootball_homepage_payload()

        self.assertTrue(all(group["items"] == [] for group in payload["recent_matches_by_league"]))
        self.assertTrue(all(group["items"] == [] for group in payload["upcoming_matches_by_league"]))
        self.assertTrue(all(card["spotlight_players"] == [] for card in payload["first_vs_last_by_league"]))

    @patch("apps.livefootball.services.overview.get_competition_scorers")
    @patch("apps.livefootball.services.overview.list_competitions")
    def test_top_performing_scorers_deduplicates_name_variants_for_same_player(
        self,
        mock_list_competitions,
        mock_get_scorers,
    ) -> None:
        mock_list_competitions.return_value = [
            {"id": 1, "code": "PD", "name": "Primera Division"},
        ]

        mock_get_scorers.return_value = {
            "competition": {
                "id": 1,
                "code": "PD",
                "name": "Primera Division",
                "country": "Spain",
                "emblem_url": "",
                "last_synced_at": "2026-03-30T09:57:00Z",
            },
            "items": [
                {
                    "rank": 1,
                    "goals": 31,
                    "penalties": 5,
                    "player_name": "Kylian Mbappe",
                    "external_player_id": "mbappe-full",
                    "team": {"id": None, "name": "Real Madrid CF", "short_name": "Real Madrid", "crest_url": ""},
                    "canonical_player": {"id": None, "display_name": "", "first_name": "", "last_name": ""},
                },
                {
                    "rank": 2,
                    "goals": 23,
                    "penalties": 3,
                    "player_name": "K. Mbappe",
                    "external_player_id": "mbappe-short",
                    "team": {"id": None, "name": "Real Madrid", "short_name": "Real Madrid", "crest_url": ""},
                    "canonical_player": {"id": None, "display_name": "", "first_name": "", "last_name": ""},
                },
            ],
        }

        payload = get_homepage_top_performing_scorers()
        items = payload["items"]

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["metric_value"], "31")
        self.assertEqual(items[0]["team"]["name"], "Real Madrid CF")