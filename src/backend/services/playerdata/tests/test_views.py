from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.playerdata.views import (
    PlayerOverviewComparisonView,
    PlayerOverviewView,
)
from common.freshness import FreshnessPayload


class DummyUser:
    is_authenticated = True
    id = 1


class PlayerDataMergedViewsTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = DummyUser()
        self._freshness_patcher = patch(
            "apps.playerdata.envelope.compute_surface_freshness",
            return_value=FreshnessPayload(
                source_fetched_at=None,
                snapshot_published_at=None,
                is_stale=True,
                is_degraded=False,
                stale_reason="no_snapshot_published",
                sla_seconds=21600,
            ),
        )
        self._freshness_patcher.start()
        self.addCleanup(self._freshness_patcher.stop)

    def _payload(self, response):
        return response.data["data"]

    def _overview_payload(self):
        return {
            "player": {
                "id": 7,
                "full_name": "Bukayo Saka",
                "display_name": "Bukayo Saka",
                "short_name": "Bukayo Saka",
                "position": "RW",
                "primary_position": "RW",
                "secondary_positions": ["LW"],
                "nationality": "England",
                "age": 23,
                "photo_url": None,
                "first_name": "Bukayo",
                "last_name": "Saka",
            },
            "club": {
                "id": 2,
                "name": "Arsenal",
                "short_name": "ARS",
                "crest_url": None,
                "source": "playerdata",
            },
            "context": {
                "provider": "understat",
                "season": "2024/2025",
                "competition_code": "EPL",
                "competition_name": "Premier League",
                "competition_id": 20,
                "team_id": 10,
                "team_name": "Arsenal",
                "livefootball_source": "directory_entry",
            },
            "general_overview": {
                "headline": "Merged player overview",
                "summary": "Strong attacking contribution across volume and creation.",
                "strengths": ["Goal threat"],
                "watchouts": [],
                "notes": [],
                "sentences": ["Strong attacking contribution across volume and creation."],
            },
            "metric_groups": [
                {
                    "key": "general",
                    "label": "General overview",
                    "metrics": [
                        {
                            "key": "matches_played",
                            "label": "Matches played",
                            "value": 24,
                            "formatted_value": "24",
                            "source": "playerdata",
                            "preferred_provider": "understat",
                            "source_preference": {
                                "concept": "usage",
                                "primary_source": "playerdata",
                                "preferred_provider": None,
                                "reason": "Use one main displayed value for basic usage metrics in the merged overview.",
                            },
                        }
                    ],
                }
            ],
            "provider_coverage": {
                "provider": "merged",
                "has_data": True,
                "coverage_status": "available",
                "freshness_label": "stored",
                "source_updated_at": None,
                "last_synced_at": None,
                "matches_sampled": 24,
                "minutes_sampled": 2011,
                "coverage_notes": ["Stored enrichment coverage exists for this player."],
                "available_sources": ["playerdata", "livefootball"],
                "missing_sources": [],
                "source_count": 2,
                "available_source_count": 2,
                "missing_source_count": 0,
                "source_details": {
                    "playerdata": {
                        "source": "playerdata",
                        "has_data": True,
                        "coverage_status": "available",
                        "freshness_label": "stored",
                        "coverage_notes": ["Stored enrichment coverage exists for this player."],
                    },
                    "livefootball": {
                        "source": "livefootball",
                        "has_data": True,
                        "coverage_status": "available",
                        "freshness_label": "stored",
                        "coverage_notes": ["Livefootball directory context is available for this player."],
                    },
                },
            },
            "source_preferences": {
                "available_sources": ["playerdata", "livefootball"],
                "rules": [
                    {
                        "key": "context",
                        "primary_source": "livefootball",
                        "preferred_provider": "football-data",
                        "reason": "Use livefootball for competition, team, and player discovery context.",
                    }
                ],
                "metric_rules": [
                    {
                        "key": "advanced_attacking_metrics",
                        "primary_source": "playerdata",
                        "preferred_provider": "understat",
                        "reason": "Prefer Understat-backed advanced attacking metrics where clearly appropriate.",
                    }
                ],
            },
            "livefootball_context": {"source": "directory_entry"},
            "playerdata_context": {"provider": "understat"},
            "has_overview_data": True,
            "missing_reasons": [],
        }

    def _comparison_payload(self):
        overview_a = self._overview_payload()
        overview_b = self._overview_payload()
        overview_b["player"] = {
            **overview_b["player"],
            "id": 8,
            "full_name": "Phil Foden",
            "display_name": "Phil Foden",
            "short_name": "Phil Foden",
        }
        overview_b["club"] = {
            **overview_b["club"],
            "id": 3,
            "name": "Manchester City",
            "short_name": "MCI",
        }

        return {
            "player_a": overview_a,
            "player_b": overview_b,
            "context": {
                "provider": "understat",
                "season": "2024/2025",
                "competition_code": "EPL",
                "competition_name": "Premier League",
                "same_provider": True,
                "same_season": True,
                "same_competition": True,
                "left_last_synced_at": None,
                "right_last_synced_at": None,
                "sentence": "Both players are being compared within the same stored season context.",
            },
            "general_overview": {
                "headline": "Merged player comparison",
                "summary": "Player A narrowly leads the attacking comparison.",
                "strengths": ["Player A leads goals and shots"],
                "watchouts": [],
                "notes": [],
                "sentences": ["Player A narrowly leads the attacking comparison."],
            },
            "metric_groups": [
                {
                    "key": "role_focus",
                    "label": "Attacking output",
                    "metrics": [
                        {
                            "key": "goals",
                            "label": "Goals",
                            "player_a_value": 14,
                            "player_a_formatted": "14",
                            "player_b_value": 13,
                            "player_b_formatted": "13",
                            "delta": 1,
                            "formatted_delta": "1",
                            "winner": "player_a",
                            "is_tie": False,
                            "is_comparable": True,
                            "sentence": "Player A has scored more goals.",
                            "source": "playerdata",
                            "preferred_provider": "understat",
                            "source_preference": {
                                "concept": "end_product",
                                "primary_source": "playerdata",
                                "preferred_provider": None,
                                "reason": "Keep one primary end-product value rather than duplicating provider blocks.",
                            },
                        }
                    ],
                }
            ],
            "summary_lines": ["Player A narrowly leads the attacking comparison."],
            "overall_winner": {
                "winner": "player_a",
                "winner_player_id": 7,
                "reason": "Player A leads more comparable metrics.",
            },
            "provider_coverage": {
                "provider": "merged",
                "has_data": True,
                "coverage_status": "available",
                "freshness_label": "stored",
                "source_updated_at": None,
                "last_synced_at": None,
                "matches_sampled": None,
                "minutes_sampled": None,
                "coverage_notes": [],
                "available_sources": ["playerdata", "livefootball"],
                "missing_sources": [],
                "source_count": 2,
                "available_source_count": 2,
                "missing_source_count": 0,
                "source_details": {},
                "player_a": {"available_sources": ["playerdata", "livefootball"]},
                "player_b": {"available_sources": ["playerdata", "livefootball"]},
            },
            "source_preferences": {
                "available_sources": ["playerdata", "livefootball"],
                "rules": [],
                "metric_rules": [],
            },
            "has_comparison_data": True,
            "missing_reasons": [],
        }

    @patch("apps.playerdata.views.overview_queries.get_player_overview")
    def test_player_overview_view_returns_merged_overview_payload(self, get_player_overview_mock):
        get_player_overview_mock.return_value = self._overview_payload()

        request = self.factory.get(
            "/playerdata/players/7/overview/",
            {"season": "2024/2025", "competition_code": "EPL"},
        )
        force_authenticate(request, user=self.user)

        response = PlayerOverviewView.as_view()(request, player_id=7)
        payload = self._payload(response)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["player"]["id"], 7)
        self.assertEqual(payload["context"]["competition_code"], "EPL")
        self.assertEqual(payload["metric_groups"][0]["key"], "general")
        self.assertEqual(payload["provider_coverage"]["coverage_status"], "available")

    @patch("apps.playerdata.views.overview_queries.get_player_overview")
    def test_player_overview_view_preserves_honest_missing_data_payload(self, get_player_overview_mock):
        payload = self._overview_payload()
        payload["has_overview_data"] = False
        payload["metric_groups"] = []
        payload["provider_coverage"]["coverage_status"] = "missing"
        payload["provider_coverage"]["has_data"] = False
        payload["provider_coverage"]["available_sources"] = []
        payload["provider_coverage"]["missing_sources"] = ["playerdata", "livefootball"]
        payload["missing_reasons"] = [
            "No stored playerdata season summary matched the requested filters.",
            "No livefootball context matched the requested filters.",
        ]
        get_player_overview_mock.return_value = payload

        request = self.factory.get("/playerdata/players/7/overview/")
        force_authenticate(request, user=self.user)

        response = PlayerOverviewView.as_view()(request, player_id=7)
        payload = self._payload(response)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(payload["has_overview_data"])
        self.assertEqual(payload["metric_groups"], [])
        self.assertEqual(payload["provider_coverage"]["coverage_status"], "missing")
        self.assertEqual(
            payload["missing_reasons"],
            payload["missing_reasons"],
        )

    @patch("apps.playerdata.views.overview_queries.compare_players_overview")
    def test_player_overview_comparison_view_returns_merged_comparison_payload(
        self,
        compare_players_overview_mock,
    ):
        compare_players_overview_mock.return_value = self._comparison_payload()

        request = self.factory.get(
            "/playerdata/players/overview-compare/",
            {
                "player_a_id": 7,
                "player_b_id": 8,
                "season": "2024/2025",
                "competition_code": "EPL",
            },
        )
        force_authenticate(request, user=self.user)

        response = PlayerOverviewComparisonView.as_view()(request)
        payload = self._payload(response)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["player_a"]["player"]["id"], 7)
        self.assertEqual(payload["player_b"]["player"]["id"], 8)
        self.assertEqual(payload["overall_winner"]["winner"], "player_a")
        self.assertEqual(payload["metric_groups"][0]["key"], "role_focus")

    def test_player_overview_comparison_view_requires_two_distinct_players(self):
        request = self.factory.get(
            "/playerdata/players/overview-compare/",
            {"player_a_id": 7, "player_b_id": 7},
        )
        force_authenticate(request, user=self.user)

        response = PlayerOverviewComparisonView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("player_b_id", response.data)