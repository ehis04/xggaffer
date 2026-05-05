"""
Tests for player data serializers

Checks summary, comparison, and enriched list serializer contracts using deterministic payload fixtures
"""

from django.test import SimpleTestCase

from apps.playerdata.serializers import (
    ClubSeasonEnrichmentSummarySerializer,
    EnrichedPlayerListItemSerializer,
    PlayerComparisonSerializer,
    PlayerSeasonEnrichmentSummarySerializer,
)


# Tests for player data serializer contracts
class PlayerDataSerializerTests(SimpleTestCase):

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
                }
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
                "coverage_notes": [],
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

    # Build one enriched player list item payload
    def _enriched_list_item_payload(self):
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
        }

    # Check the player season summary serializer accepts a full payload
    def test_player_season_summary_serializer_validates_complete_payload(self):
        serializer = PlayerSeasonEnrichmentSummarySerializer(
            data=self._player_summary_payload()
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["player"]["id"], 7)
        self.assertEqual(serializer.validated_data["context"]["provider"], "understat")
        self.assertEqual(len(serializer.validated_data["metrics"]), 2)

    # Check the player season summary serializer represents instance data
    def test_player_season_summary_serializer_represents_instance_payload(self):
        serializer = PlayerSeasonEnrichmentSummarySerializer(
            instance=self._player_summary_payload()
        )
        self.assertEqual(serializer.data["player"]["id"], 7)
        self.assertEqual(serializer.data["club"]["name"], "Arsenal")
        self.assertEqual(serializer.data["metrics"][0]["key"], "goals")
        self.assertEqual(
            serializer.data["explanation"]["headline"],
            "Deterministic season summary",
        )

    # Check the club season summary serializer accepts nullable fields
    def test_club_season_summary_serializer_is_null_safe(self):
        payload = self._club_summary_payload()
        serializer = ClubSeasonEnrichmentSummarySerializer(data=payload)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data["context"]["competition_name"])
        self.assertIsNone(serializer.validated_data["provider_coverage"]["last_synced_at"])
        self.assertIsNone(serializer.validated_data["provider_coverage"]["minutes_sampled"])

    # Check the player comparison serializer accepts the expected response shape
    def test_player_comparison_serializer_validates_expected_contract(self):
        serializer = PlayerComparisonSerializer(data=self._comparison_payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["player_a"]["player"]["id"], 7)
        self.assertEqual(serializer.validated_data["player_b"]["player"]["id"], 11)
        self.assertEqual(serializer.validated_data["metrics"][0]["key"], "goals")
        self.assertTrue(serializer.validated_data["metrics"][1]["is_tie"])
        self.assertIsNone(serializer.validated_data["metrics"][1]["winner"])

    # Check the player comparison serializer requires both comparison sides
    def test_player_comparison_serializer_requires_both_sides(self):
        payload = self._comparison_payload()
        del payload["player_b"]

        serializer = PlayerComparisonSerializer(data=payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn("player_b", serializer.errors)

    # Check the enriched list item serializer accepts a full payload
    def test_enriched_player_list_item_serializer_validates_complete_payload(self):
        serializer = EnrichedPlayerListItemSerializer(
            data=self._enriched_list_item_payload()
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["player"]["id"], 7)
        self.assertEqual(serializer.validated_data["key_metrics"][0]["label"], "Goals")

    # Check the enriched list item serializer accepts optional null blocks
    def test_enriched_player_list_item_serializer_allows_optional_null_blocks(self):
        payload = {
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
        }

        serializer = EnrichedPlayerListItemSerializer(data=payload)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data["club"])
        self.assertIsNone(serializer.validated_data["explanation_snippet"])
        self.assertIsNone(serializer.validated_data["provider_coverage"])

    # Check metric labels are required in summary payloads
    def test_summary_serializer_rejects_metric_without_required_label(self):
        payload = self._player_summary_payload()
        del payload["metrics"][0]["label"]

        serializer = PlayerSeasonEnrichmentSummarySerializer(data=payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn("metrics", serializer.errors)

    # Check enriched list items require a player block
    def test_enriched_player_list_item_serializer_requires_player(self):
        payload = self._enriched_list_item_payload()
        del payload["player"]

        serializer = EnrichedPlayerListItemSerializer(data=payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn("player", serializer.errors)