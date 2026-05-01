from django.test import SimpleTestCase

from apps.playerdata.serializers import (
    MergedProviderCoverageSerializer,
    PlayerOverviewComparisonSerializer,
    PlayerOverviewSerializer,
)


class PlayerDataMergedSerializersTests(SimpleTestCase):
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
                "notes": ["League-only sample"],
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
                            "unit": None,
                            "rank": None,
                            "percentile": None,
                            "sample_size": None,
                            "is_available": True,
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
                },
                {
                    "key": "role_focus",
                    "label": "Attacking output",
                    "metrics": [
                        {
                            "key": "goals",
                            "label": "Goals",
                            "value": 14,
                            "formatted_value": "14",
                            "unit": None,
                            "rank": None,
                            "percentile": None,
                            "sample_size": None,
                            "is_available": True,
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
                },
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
                        "provider": "understat",
                        "has_data": True,
                        "coverage_status": "available",
                        "freshness_label": "stored",
                        "source_updated_at": None,
                        "last_synced_at": None,
                        "matches_sampled": 24,
                        "minutes_sampled": 2011,
                        "coverage_notes": ["Stored enrichment coverage exists for this player."],
                        "record_count": 1,
                        "seasons": ["2024/2025"],
                        "competitions": ["Premier League"],
                        "items": [],
                    },
                    "livefootball": {
                        "source": "livefootball",
                        "provider": "football-data",
                        "has_data": True,
                        "coverage_status": "available",
                        "freshness_label": "stored",
                        "source_updated_at": None,
                        "last_synced_at": None,
                        "matches_sampled": None,
                        "minutes_sampled": None,
                        "coverage_notes": ["Livefootball directory context is available for this player."],
                        "team": {"id": 10, "name": "Arsenal"},
                        "competition": {"id": 20, "code": "EPL", "name": "Premier League"},
                        "season_label": "2024/2025",
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
                            "unit": None,
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

    def test_merged_provider_coverage_serializer_preserves_counts_and_sources(self):
        payload = self._overview_payload()["provider_coverage"]

        serializer = MergedProviderCoverageSerializer(payload)

        self.assertEqual(serializer.data["coverage_status"], "available")
        self.assertEqual(serializer.data["available_sources"], ["playerdata", "livefootball"])
        self.assertEqual(serializer.data["source_count"], 2)
        self.assertIn("playerdata", serializer.data["source_details"])
        self.assertIn("livefootball", serializer.data["source_details"])

    def test_player_overview_serializer_renders_grouped_metric_sections(self):
        payload = self._overview_payload()

        serializer = PlayerOverviewSerializer(payload)

        self.assertEqual(serializer.data["player"]["id"], 7)
        self.assertEqual(serializer.data["general_overview"]["headline"], "Merged player overview")
        self.assertEqual(serializer.data["metric_groups"][0]["key"], "general")
        self.assertEqual(serializer.data["metric_groups"][1]["key"], "role_focus")
        self.assertEqual(
            serializer.data["metric_groups"][1]["metrics"][0]["source"],
            "playerdata",
        )

    def test_player_overview_comparison_serializer_renders_comparison_shape(self):
        payload = self._comparison_payload()

        serializer = PlayerOverviewComparisonSerializer(payload)

        self.assertEqual(serializer.data["player_a"]["player"]["id"], 7)
        self.assertEqual(serializer.data["player_b"]["player"]["id"], 8)
        self.assertEqual(serializer.data["overall_winner"]["winner"], "player_a")
        self.assertEqual(serializer.data["metric_groups"][0]["label"], "Attacking output")
        self.assertTrue(serializer.data["has_comparison_data"])