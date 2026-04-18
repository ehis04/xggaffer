from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.test import TestCase


def build_overview_payload() -> dict:
    return {
        "generated_at": "2026-03-30T10:00:00Z",
        "league_order": ["PL", "LL", "BL1", "SA", "FL1", "RPL"],
        "league_snapshot": [
            {
                "competition": {
                    "id": 1,
                    "code": "PL",
                    "name": "Premier League",
                    "country": "England",
                    "emblem_url": "",
                },
                "synced_at": "2026-03-30T09:59:00Z",
                "top_rows": [
                    {
                        "position": 1,
                        "team": {
                            "id": 101,
                            "name": "Arsenal",
                            "short_name": "Arsenal",
                            "crest_url": "",
                        },
                        "played": 30,
                        "won": 22,
                        "drawn": 5,
                        "lost": 3,
                        "goals_for": 65,
                        "goals_against": 29,
                        "goal_difference": 36,
                        "points": 71,
                        "form_label": "W-W-D-W-W",
                    }
                ],
                "bottom_rows": [
                    {
                        "position": 20,
                        "team": {
                            "id": 102,
                            "name": "Sheffield United",
                            "short_name": "Sheff Utd",
                            "crest_url": "",
                        },
                        "played": 30,
                        "won": 3,
                        "drawn": 4,
                        "lost": 23,
                        "goals_for": 25,
                        "goals_against": 72,
                        "goal_difference": -47,
                        "points": 13,
                        "form_label": "L-L-L-D-L",
                    }
                ],
                "cta": {
                    "label": "View league",
                    "path": "/livefootball/leagues",
                    "query": {"competition": "PL"},
                },
            }
        ],
        "top_performing_teams": {
            "updated_at": None,
            "items": [],
        },
        "top_performing_scorers": {
            "updated_at": "2026-03-30T09:58:00Z",
            "items": [
                {
                    "rank": 1,
                    "player": {
                        "id": 201,
                        "name": "Harry Kane",
                        "short_name": "H. Kane",
                        "position": "ST",
                        "shirt_number": None,
                        "photo_url": None,
                    },
                    "team": {
                        "id": 202,
                        "name": "Bayern Munich",
                        "short_name": "Bayern",
                        "crest_url": "",
                    },
                    "competition": {
                        "id": 3,
                        "code": "BL1",
                        "name": "Bundesliga",
                        "country": "Germany",
                        "emblem_url": "",
                    },
                    "summary": "25 league goals for Bayern Munich",
                    "metric_label": "Goals",
                    "metric_value": "25",
                    "cta": {
                        "label": "View player",
                        "path": "/livefootball/players",
                        "query": {
                            "trend": "top-performing-scorers",
                            "playerId": "201",
                        },
                    },
                }
            ],
        },
        "latest_hat_tricks": {
            "updated_at": None,
            "items": [],
        },
        "strikers_with_a_lull": {
            "updated_at": None,
            "items": [],
        },
        "recent_matches_by_league": [
            {
                "competition": {
                    "id": 1,
                    "code": "PL",
                    "name": "Premier League",
                    "country": "England",
                    "emblem_url": "",
                },
                "synced_at": "2026-03-30T09:57:00Z",
                "items": [
                    {
                        "id": 301,
                        "utc_date": "2026-03-28T15:00:00Z",
                        "status": "FINISHED",
                        "home_team": {
                            "id": 101,
                            "name": "Arsenal",
                            "short_name": "Arsenal",
                            "crest_url": "",
                        },
                        "away_team": {
                            "id": 103,
                            "name": "Chelsea",
                            "short_name": "Chelsea",
                            "crest_url": "",
                        },
                        "home_score": 2,
                        "away_score": 1,
                        "score_line": "2-1",
                        "venue_label": "Arsenal vs Chelsea",
                    }
                ],
                "cta": {
                    "label": "View matches",
                    "path": "/livefootball/matches",
                    "query": {"competition": "PL", "tab": "recent"},
                },
            }
        ],
        "upcoming_matches_by_league": [
            {
                "competition": {
                    "id": 1,
                    "code": "PL",
                    "name": "Premier League",
                    "country": "England",
                    "emblem_url": "",
                },
                "synced_at": "2026-03-30T09:57:00Z",
                "items": [
                    {
                        "id": 302,
                        "utc_date": "2026-04-01T19:45:00Z",
                        "status": "SCHEDULED",
                        "home_team": {
                            "id": 101,
                            "name": "Arsenal",
                            "short_name": "Arsenal",
                            "crest_url": "",
                        },
                        "away_team": {
                            "id": 104,
                            "name": "Liverpool",
                            "short_name": "Liverpool",
                            "crest_url": "",
                        },
                        "home_score": None,
                        "away_score": None,
                        "score_line": None,
                        "venue_label": "Arsenal vs Liverpool",
                    }
                ],
                "cta": {
                    "label": "View matches",
                    "path": "/livefootball/matches",
                    "query": {"competition": "PL", "tab": "upcoming"},
                },
            }
        ],
        "first_vs_last_by_league": [
            {
                "competition": {
                    "id": 1,
                    "code": "PL",
                    "name": "Premier League",
                    "country": "England",
                    "emblem_url": "",
                },
                "synced_at": "2026-03-30T09:56:00Z",
                "leader": {
                    "position": 1,
                    "team": {
                        "id": 101,
                        "name": "Arsenal",
                        "short_name": "Arsenal",
                        "crest_url": "",
                    },
                    "played": 30,
                    "won": 22,
                    "drawn": 5,
                    "lost": 3,
                    "goals_for": 65,
                    "goals_against": 29,
                    "goal_difference": 36,
                    "points": 71,
                    "form_label": "W-W-D-W-W",
                },
                "bottom": {
                    "position": 20,
                    "team": {
                        "id": 102,
                        "name": "Sheffield United",
                        "short_name": "Sheff Utd",
                        "crest_url": "",
                    },
                    "played": 30,
                    "won": 3,
                    "drawn": 4,
                    "lost": 23,
                    "goals_for": 25,
                    "goals_against": 72,
                    "goal_difference": -47,
                    "points": 13,
                    "form_label": "L-L-L-D-L",
                },
                "spotlight_players": [
                    {
                        "team_id": 101,
                        "team_name": "Arsenal",
                        "player": {
                            "id": 401,
                            "name": "Kai Havertz",
                            "short_name": "K. Havertz",
                            "position": "ST",
                            "shirt_number": 29,
                            "photo_url": None,
                        },
                        "minutes_played": 2200,
                        "reason_label": "Highest-minutes attacker",
                    }
                ],
                "cta": {
                    "label": "View clubs",
                    "path": "/livefootball/clubs",
                    "query": {"competition": "PL", "mode": "first-v-last"},
                },
            }
        ],
        "all_time_streaks": {
            "updated_at": "2026-03-30T09:55:00Z",
            "all_time": [
                {
                    "competition_code": "",
                    "competition_name": "",
                    "team_name": "Arsenal",
                    "team_id": None,
                    "crest_url": None,
                    "streak_value": 49,
                    "label": "Longest all-time unbeaten run",
                    "summary": "49 matches without defeat",
                }
            ],
            "current": [],
            "cta": {
                "label": "View streaks",
                "path": "/livefootball/streaks",
                "query": {},
            },
        },
    }


class LiveFootballOverviewViewTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.url = reverse("livefootball-overview")
        self.user = get_user_model().objects.create_user(
            username="overviewtester",
            email="overviewtester@example.com",
            password="pass1234",
        )

    @patch("apps.livefootball.views.get_livefootball_homepage_payload")
    def test_authenticated_request_returns_200_and_expected_keys(self, mock_payload) -> None:
        mock_payload.return_value = build_overview_payload()
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            sorted(response.data.keys()),
            sorted(build_overview_payload().keys()),
        )
        self.assertEqual(
            response.data["league_order"],
            ["PL", "LL", "BL1", "SA", "FL1", "RPL"],
        )
        mock_payload.assert_called_once()

    @patch("apps.livefootball.views.get_livefootball_homepage_payload")
    def test_overview_survives_empty_enrichment_sections(self, mock_payload) -> None:
        payload = build_overview_payload()
        payload["top_performing_teams"] = {"updated_at": None, "items": []}
        payload["latest_hat_tricks"] = {"updated_at": None, "items": []}
        payload["strikers_with_a_lull"] = {"updated_at": None, "items": []}
        payload["all_time_streaks"] = {
            "updated_at": None,
            "all_time": [],
            "current": [],
            "cta": {
                "label": "View streaks",
                "path": "/livefootball/streaks",
                "query": {},
            },
        }
        mock_payload.return_value = payload
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["top_performing_teams"]["items"], [])
        self.assertEqual(response.data["latest_hat_tricks"]["items"], [])
        self.assertEqual(response.data["strikers_with_a_lull"]["items"], [])
        self.assertEqual(response.data["all_time_streaks"]["all_time"], [])

    def test_unauthenticated_request_is_rejected(self) -> None:
        response = self.client.get(self.url)
        self.assertIn(
            response.status_code,
            {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN},
        )