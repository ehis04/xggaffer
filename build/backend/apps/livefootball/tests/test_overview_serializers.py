from __future__ import annotations

from django.test import SimpleTestCase

from apps.livefootball.serializers import LiveFootballOverviewSerializer


def build_payload() -> dict:
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
                            "id": 1,
                            "name": "Arsenal",
                            "short_name": "Arsenal",
                            "crest_url": "",
                        },
                        "played": 30,
                        "won": 22,
                        "drawn": 4,
                        "lost": 4,
                        "goals_for": 60,
                        "goals_against": 25,
                        "goal_difference": 35,
                        "points": 70,
                        "form_label": "W-W-W-D-W",
                    }
                ],
                "bottom_rows": [],
                "cta": {
                    "label": "View league",
                    "path": "/livefootball/leagues",
                    "query": {"competition": "PL"},
                },
            }
        ],
        "top_performing_teams": {
            "updated_at": None,
            "items": [
                {
                    "rank": 1,
                    "team": {
                        "id": 1,
                        "name": "Arsenal",
                        "short_name": "Arsenal",
                        "crest_url": "",
                    },
                    "competition": {
                        "id": 1,
                        "code": "PL",
                        "name": "Premier League",
                        "country": "England",
                        "emblem_url": "",
                    },
                    "summary": "2.33 points per game and 2.00 goals per game.",
                    "metric_label": "PPG",
                    "metric_value": "2.33",
                    "form_label": "W-W-W-D-W",
                    "cta": {
                        "label": "View club",
                        "path": "/livefootball/clubs",
                        "query": {"competition": "PL", "teamId": 1},
                    },
                }
            ],
        },
        "top_performing_scorers": {
            "updated_at": "2026-03-30T09:58:00Z",
            "items": [
                {
                    "rank": 1,
                    "player": {
                        "id": 9,
                        "name": "Harry Kane",
                        "short_name": "H. Kane",
                        "position": "ST",
                        "shirt_number": None,
                        "photo_url": None,
                    },
                    "team": {
                        "id": 10,
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
                        "query": {"trend": "top-performing-scorers", "playerId": "9"},
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
                        "id": 1001,
                        "utc_date": "2026-03-28T15:00:00Z",
                        "status": "FINISHED",
                        "home_team": {
                            "id": 1,
                            "name": "Arsenal",
                            "short_name": "Arsenal",
                            "crest_url": "",
                        },
                        "away_team": {
                            "id": 2,
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
                        "id": 1002,
                        "utc_date": "2026-04-01T19:45:00Z",
                        "status": "SCHEDULED",
                        "home_team": {
                            "id": 1,
                            "name": "Arsenal",
                            "short_name": "Arsenal",
                            "crest_url": "",
                        },
                        "away_team": {
                            "id": 3,
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
                        "id": 1,
                        "name": "Arsenal",
                        "short_name": "Arsenal",
                        "crest_url": "",
                    },
                    "played": 30,
                    "won": 22,
                    "drawn": 4,
                    "lost": 4,
                    "goals_for": 60,
                    "goals_against": 25,
                    "goal_difference": 35,
                    "points": 70,
                    "form_label": "W-W-W-D-W",
                },
                "bottom": {
                    "position": 20,
                    "team": {
                        "id": 20,
                        "name": "Bottom Club",
                        "short_name": "Bottom",
                        "crest_url": "",
                    },
                    "played": 30,
                    "won": 2,
                    "drawn": 5,
                    "lost": 23,
                    "goals_for": 20,
                    "goals_against": 70,
                    "goal_difference": -50,
                    "points": 11,
                    "form_label": "L-L-L-D-L",
                },
                "spotlight_players": [
                    {
                        "team_id": 1,
                        "team_name": "Arsenal",
                        "player": {
                            "id": 200,
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
            "updated_at": None,
            "all_time": [],
            "current": [],
            "cta": {
                "label": "View streaks",
                "path": "/livefootball/streaks",
                "query": {},
            },
        },
    }


class LiveFootballOverviewSerializerTests(SimpleTestCase):
    def test_full_payload_serialises(self) -> None:
        serializer = LiveFootballOverviewSerializer(data=build_payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_nullable_and_empty_fields_serialise(self) -> None:
        payload = build_payload()
        payload["top_performing_teams"] = {"updated_at": None, "items": []}
        payload["latest_hat_tricks"] = {"updated_at": None, "items": []}
        payload["strikers_with_a_lull"] = {"updated_at": None, "items": []}
        payload["league_snapshot"][0]["bottom_rows"] = []
        payload["recent_matches_by_league"][0]["items"][0]["score_line"] = None
        payload["first_vs_last_by_league"][0]["spotlight_players"][0]["minutes_played"] = None

        serializer = LiveFootballOverviewSerializer(data=payload)

        self.assertTrue(serializer.is_valid(), serializer.errors)