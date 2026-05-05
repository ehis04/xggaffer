"""
Tests for player data API views

Checks response envelopes, serializer output shapes, query validation, null data handling, and authentication requirements
"""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.playerdata.views import (
    ClubSeasonSummaryView,
    EnrichedPlayerListView,
    PlayerComparisonView,
    PlayerSeasonSummaryView,
)
from common.freshness import FreshnessPayload


# Tests for player data API view contracts
class PlayerDataViewTests(SimpleTestCase):

    # Set up the request factory, fake authenticated user, and stable freshness payload
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = SimpleNamespace(is_authenticated=True)
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

    # Authenticate a test request
    def _authenticate(self, request):
        force_authenticate(request, user=self.user)
        return request

    # Extract the data block from a response envelope
    def _payload(self, response):
        return response.data["data"]

    # Build a complete player season summary payload
    def _player_summary_payload(self):
        return {
            "player": {
                "id": 7,
                "full_name": "Bukayo Saka",
                "display_name": "Bukayo Saka",
                "short_name": "Saka",
                "position": "RW",
                "nationality": None,
                "age": None,
                "photo_url": None,
            },
            "club": {
                "id": 3,
                "name": "Arsenal",
                "short_name": "Arsenal",
                "crest_url": None,
            },
            "context": {
                "provider": "understat",
                "season": "2024-2025",
                "competition_code": "EPL",
                "competition_name": "Premier League",
            },
            "metrics": [
                {
                    "key": "goals",
                    "label": "Goals",
                    "value": 10,
                    "formatted_value": "10",
                    "unit": None,
                    "rank": None,
                    "percentile": None,
                    "sample_size": None,
                    "is_available": True,
                },
                {
                    "key": "xg",
                    "label": "xG",
                    "value": 8.4,
                    "formatted_value": "8.4",
                    "unit": None,
                    "rank": None,
                    "percentile": None,
                    "sample_size": None,
                    "is_available": True,
                },
            ],
            "explanation": {
                "headline": "Deterministic season summary",
                "summary": "10 goals, 6 assists, 1,950 minutes.",
                "strengths": ["Recorded 10 goals."],
                "watchouts": [],
                "notes": ["xG value stored for this season: 8.4."],
            },
            "provider_coverage": {
                "provider": "understat",
                "has_data": True,
                "coverage_status": "available",
                "freshness_label": "synced",
                "source_updated_at": None,
                "last_synced_at": None,
                "matches_sampled": 24,
                "minutes_sampled": 1950,
                "coverage_notes": [],
            },
            "has_summary_data": True,
            "missing_reasons": [],
        }

    # Build a complete club season summary payload
    def _club_summary_payload(self):
        return {
            "club": {
                "id": 3,
                "name": "Arsenal",
                "short_name": "Arsenal",
                "crest_url": None,
            },
            "context": {
                "provider": "understat",
                "season": "2024-2025",
                "competition_code": "EPL",
                "competition_name": None,
            },
            "metrics": [
                {
                    "key": "wins",
                    "label": "Wins",
                    "value": 18,
                    "formatted_value": "18",
                    "unit": None,
                    "rank": None,
                    "percentile": None,
                    "sample_size": None,
                    "is_available": True,
                },
                {
                    "key": "xg",
                    "label": "xG",
                    "value": 42.7,
                    "formatted_value": "42.7",
                    "unit": None,
                    "rank": None,
                    "percentile": None,
                    "sample_size": None,
                    "is_available": True,
                },
            ],
            "explanation": {
                "headline": "Deterministic club season summary",
                "summary": "27 matches, 18 wins, 6 draws, 3 losses.",
                "strengths": ["Wins exceed losses in the stored season summary."],
                "watchouts": [],
                "notes": ["xG value stored for this season: 42.7."],
            },
            "provider_coverage": {
                "provider": "understat",
                "has_data": True,
                "coverage_status": "available",
                "freshness_label": "stored",
                "source_updated_at": None,
                "last_synced_at": None,
                "matches_sampled": 27,
                "minutes_sampled": None,
                "coverage_notes": [
                    "No explicit sync timestamp is stored; using updated_at instead."
                ],
            },
            "has_summary_data": True,
            "missing_reasons": [],
        }

    # Build a complete player comparison payload
    def _comparison_payload(self):
        return {
            "player_a": {
                "player": {
                    "id": 7,
                    "full_name": "Bukayo Saka",
                    "display_name": "Bukayo Saka",
                    "short_name": "Saka",
                    "position": "RW",
                    "nationality": None,
                    "age": None,
                    "photo_url": None,
                },
                "club": {
                    "id": 3,
                    "name": "Arsenal",
                    "short_name": "Arsenal",
                    "crest_url": None,
                },
            },
            "player_b": {
                "player": {
                    "id": 11,
                    "full_name": "Phil Foden",
                    "display_name": "Phil Foden",
                    "short_name": "Foden",
                    "position": "AM",
                    "nationality": None,
                    "age": None,
                    "photo_url": None,
                },
                "club": {
                    "id": 4,
                    "name": "Manchester City",
                    "short_name": "Man City",
                    "crest_url": None,
                },
            },
            "context": {
                "provider": "understat",
                "season": "2024-2025",
                "competition_code": "EPL",
                "competition_name": "Premier League",
            },
            "metrics": [
                {
                    "key": "goals",
                    "label": "Goals",
                    "player_a_value": 10,
                    "player_a_formatted": "10",
                    "player_b_value": 8,
                    "player_b_formatted": "8",
                    "delta": 2,
                    "formatted_delta": "2",
                    "unit": None,
                    "winner": "Bukayo Saka",
                    "is_tie": False,
                },
                {
                    "key": "assists",
                    "label": "Assists",
                    "player_a_value": 6,
                    "player_a_formatted": "6",
                    "player_b_value": 6,
                    "player_b_formatted": "6",
                    "delta": 0,
                    "formatted_delta": "0",
                    "unit": None,
                    "winner": None,
                    "is_tie": True,
                },
            ],
            "overall_winner": {
                "winner": "Bukayo Saka",
                "winner_player_id": 7,
                "reason": "Bukayo Saka leads 1 comparable metric to 0.",
            },
            "explanation": {
                "headline": "Deterministic player comparison",
                "summary": "Bukayo Saka played more minutes and led goals.",
                "strengths": ["Bukayo Saka leads 1 comparable metric to 0."],
                "watchouts": [],
                "notes": ["Both records come from understat in the same season."],
            },
            "provider_coverage": {
                "provider": "understat",
                "has_data": True,
                "coverage_status": "available",
                "freshness_label": "partial",
                "source_updated_at": None,
                "last_synced_at": None,
                "matches_sampled": None,
                "minutes_sampled": None,
                "coverage_notes": ["Both records come from understat in the same season."],
            },
            "has_comparison_data": True,
            "missing_reasons": [],
        }

    # Build a complete enriched player list payload
    def _enriched_list_payload(self):
        return {
            "count": 2,
            "results": [
                {
                    "player": {
                        "id": 7,
                        "full_name": "Bukayo Saka",
                        "display_name": "Bukayo Saka",
                        "short_name": "Saka",
                        "position": "RW",
                        "nationality": None,
                        "age": None,
                        "photo_url": None,
                    },
                    "club": {
                        "id": 3,
                        "name": "Arsenal",
                        "short_name": "Arsenal",
                        "crest_url": None,
                    },
                    "context": {
                        "provider": "understat",
                        "season": "2024-2025",
                        "competition_code": "EPL",
                        "competition_name": "Premier League",
                    },
                    "key_metrics": [
                        {
                            "key": "goals",
                            "label": "Goals",
                            "value": 10,
                            "formatted_value": "10",
                            "unit": None,
                            "rank": None,
                            "percentile": None,
                            "sample_size": None,
                            "is_available": True,
                        }
                    ],
                    "explanation_snippet": "24 matches, 1950 minutes, 10 goals, 6 assists.",
                    "provider_coverage": {
                        "provider": "understat",
                        "has_data": True,
                        "coverage_status": "available",
                        "freshness_label": "synced",
                        "source_updated_at": None,
                        "last_synced_at": None,
                        "matches_sampled": 24,
                        "minutes_sampled": 1950,
                        "coverage_notes": [],
                    },
                    "has_enrichment_data": True,
                },
                {
                    "player": {
                        "id": 11,
                        "full_name": "Phil Foden",
                        "display_name": "Phil Foden",
                        "short_name": "Foden",
                        "position": "AM",
                        "nationality": None,
                        "age": None,
                        "photo_url": None,
                    },
                    "club": None,
                    "context": {
                        "provider": "understat",
                        "season": "2024-2025",
                        "competition_code": "EPL",
                        "competition_name": "Premier League",
                    },
                    "key_metrics": [],
                    "explanation_snippet": None,
                    "provider_coverage": None,
                    "has_enrichment_data": True,
                },
            ],
        }

    # Check the player season summary endpoint returns the expected envelope shape
    def test_player_season_summary_endpoint_returns_stable_shape(self):
        request = self.factory.get(
            "/playerdata/players/7/season-summary/",
            {"provider": "understat", "season": "2024-2025"},
        )
        request = self._authenticate(request)

        with patch.object(
            PlayerSeasonSummaryView,
            "player_summary_function_names",
            ["get_player_season_summary"],
        ), patch.object(
            PlayerSeasonSummaryView,
            "player_query_function_names",
            ["get_player_season_enrichment"],
        ), patch(
            "apps.playerdata.views.summaries.get_player_season_summary",
            return_value=self._player_summary_payload(),
        ):
            response = PlayerSeasonSummaryView.as_view()(request, player_id=7)

        payload = self._payload(response)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["player"]["id"], 7)
        self.assertEqual(payload["context"]["provider"], "understat")
        self.assertIn("metrics", payload)
        self.assertIn("explanation", payload)
        self.assertIn("provider_coverage", payload)
        self.assertEqual(
            payload["explanation"]["headline"],
            "Deterministic season summary",
        )
        self.assertEqual(payload["missing_reasons"], [])

    # Check the club season summary endpoint handles nullable fields
    def test_club_season_summary_endpoint_is_null_safe(self):
        request = self.factory.get(
            "/playerdata/clubs/3/season-summary/",
            {"provider": "understat", "season": "2024-2025"},
        )
        request = self._authenticate(request)

        with patch.object(
            ClubSeasonSummaryView,
            "club_summary_function_names",
            ["get_club_season_summary"],
        ), patch.object(
            ClubSeasonSummaryView,
            "club_query_function_names",
            ["get_club_season_enrichment"],
        ), patch(
            "apps.playerdata.views.summaries.get_club_season_summary",
            return_value=self._club_summary_payload(),
        ):
            response = ClubSeasonSummaryView.as_view()(request, club_id=3)

        payload = self._payload(response)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["club"]["id"], 3)
        self.assertIsNone(payload["context"]["competition_name"])
        self.assertIsNone(payload["provider_coverage"]["last_synced_at"])
        self.assertIsNone(payload["provider_coverage"]["minutes_sampled"])
        self.assertIn("notes", payload["explanation"])

    # Check the player comparison endpoint returns the expected contract
    def test_player_comparison_endpoint_returns_expected_contract(self):
        request = self.factory.get(
            "/playerdata/players/compare/",
            {
                "player_a_id": 7,
                "player_b_id": 11,
                "provider": "understat",
                "season": "2024-2025",
            },
        )
        request = self._authenticate(request)

        with patch.object(
            PlayerComparisonView,
            "comparison_function_names",
            ["compare_players"],
        ), patch(
            "apps.playerdata.views.comparisons.compare_players",
            return_value=self._comparison_payload(),
        ):
            response = PlayerComparisonView.as_view()(request)

        payload = self._payload(response)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["player_a"]["player"]["id"], 7)
        self.assertEqual(payload["player_b"]["player"]["id"], 11)
        self.assertEqual(payload["overall_winner"]["winner_player_id"], 7)
        self.assertEqual(len(payload["metrics"]), 2)
        self.assertIn("explanation", payload)
        self.assertIn("provider_coverage", payload)

    # Check the enriched player list endpoint returns count and results
    def test_enriched_player_list_endpoint_returns_count_and_results(self):
        request = self.factory.get(
            "/playerdata/players/enriched/",
            {
                "provider": "understat",
                "season": "2024-2025",
                "club_id": 3,
                "ordering": "goals",
                "limit": 2,
            },
        )
        request = self._authenticate(request)

        with patch.object(
            EnrichedPlayerListView,
            "enriched_player_list_function_names",
            ["get_enriched_players"],
        ), patch(
            "apps.playerdata.views.queries.get_enriched_players",
            return_value=self._enriched_list_payload(),
        ):
            response = EnrichedPlayerListView.as_view()(request)

        payload = self._payload(response)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["count"], 2)
        self.assertEqual(len(payload["results"]), 2)
        self.assertEqual(payload["results"][0]["player"]["id"], 7)
        self.assertIsNone(payload["results"][1]["club"])
        self.assertIsNone(payload["results"][1]["provider_coverage"])

    # Check missing player summary data returns a null envelope
    def test_player_season_summary_endpoint_returns_null_envelope_when_no_data_exists(self):
        request = self.factory.get(
            "/playerdata/players/999/season-summary/",
            {"provider": "understat", "season": "2024-2025"},
        )
        request = self._authenticate(request)

        with patch.object(
            PlayerSeasonSummaryView,
            "player_summary_function_names",
            ["get_player_season_summary"],
        ), patch.object(
            PlayerSeasonSummaryView,
            "player_query_function_names",
            ["get_player_season_enrichment"],
        ), patch(
            "apps.playerdata.views.summaries.get_player_season_summary",
            return_value=None,
        ), patch(
            "apps.playerdata.views.queries.get_player_season_enrichment",
            return_value=None,
        ):
            response = PlayerSeasonSummaryView.as_view()(request, player_id=999)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["data"])
        self.assertIn("freshness", response.data)

    # Check player comparison requires both player IDs
    def test_player_comparison_endpoint_requires_both_player_ids(self):
        request = self.factory.get(
            "/playerdata/players/compare/",
            {"player_a_id": 7},
        )
        request = self._authenticate(request)

        response = PlayerComparisonView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("player_b_id", response.data)

    # Check player data views reject unauthenticated requests
    def test_views_require_authentication(self):
        request = self.factory.get("/playerdata/players/7/season-summary/")

        response = PlayerSeasonSummaryView.as_view()(request, player_id=7)

        self.assertIn(
            response.status_code,
            {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN},
        )