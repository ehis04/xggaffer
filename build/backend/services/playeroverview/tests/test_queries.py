from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from services.playeroverview import queries as playeroverview_queries


class FakeCoverageSummary:
    def __init__(self, items, sentences=None):
        self._items = items
        self._sentences = sentences or []

    def to_dict(self):
        return {
            "items": self._items,
            "sentences": self._sentences,
        }


class PlayerOverviewQueriesTests(SimpleTestCase):
    def _make_player(self, player_id: int = 7, **overrides):
        defaults = {
            "id": player_id,
            "display_name": "Bukayo Saka",
            "full_name": "Bukayo Saka",
            "first_name": "Bukayo",
            "last_name": "Saka",
            "primary_position": "RW",
            "secondary_positions": ["LW"],
            "nationality": "England",
            "photo_url": "https://example.com/saka.png",
            "date_of_birth": None,
        }
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    def _make_summary(self, **overrides):
        defaults = {
            "provider": "understat",
            "season_label": "2024/2025",
            "competition_code": "EPL",
            "competition_name": "Premier League",
            "primary_position": "RW",
            "secondary_positions": ["LW"],
            "club": {
                "id": 2,
                "name": "Arsenal",
                "short_name": "ARS",
                "crest_url": "https://example.com/arsenal.png",
            },
            "matches_played": 24,
            "minutes_played": 2011,
            "metrics": [
                {"key": "shots", "label": "Shots", "value": 60, "formatted_value": "60"},
                {"key": "assists", "label": "Assists", "value": 10, "formatted_value": "10"},
                {"key": "goals", "label": "Goals", "value": 14, "formatted_value": "14"},
                {"key": "xg", "label": "xG", "value": 11.6, "formatted_value": "11.6"},
                {"key": "minutes_played", "label": "Minutes played", "value": 2011, "formatted_value": "2,011"},
                {"key": "matches_played", "label": "Matches played", "value": 24, "formatted_value": "24"},
                {"key": "xa", "label": "xA", "value": 8.2, "formatted_value": "8.2"},
            ],
            "explanation": {
                "headline": "Merged player overview",
                "summary": "Strong attacking contribution across volume and creation.",
                "strengths": ["Goal threat", "Chance creation"],
                "watchouts": ["No defensive metrics included"],
                "notes": ["Sample is league-only."],
            },
            "sentences": [
                "Strong attacking contribution across volume and creation.",
                "Sample is league-only.",
            ],
            "context": {
                "provider": "understat",
                "season": "2024/2025",
                "competition_code": "EPL",
                "competition_name": "Premier League",
            },
        }
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    @patch("services.playeroverview.queries.get_best_available_player_context")
    @patch("services.playeroverview.queries.build_player_provider_coverage_summary")
    @patch("services.playeroverview.queries.build_player_season_summary")
    @patch("services.playeroverview.queries.Player")
    def test_get_player_overview_returns_merged_shape_with_position_ordering(
        self,
        player_model_mock,
        build_summary_mock,
        coverage_summary_mock,
        context_mock,
    ):
        player = self._make_player()
        summary = self._make_summary()
        player_model_mock.objects.filter.return_value.first.return_value = player
        build_summary_mock.return_value = summary
        coverage_summary_mock.return_value = FakeCoverageSummary(
            items=[
                {
                    "provider": "understat",
                    "season_label": "2024/2025",
                    "competition_code": "EPL",
                    "competition_name": "Premier League",
                    "club_id": 2,
                    "last_synced_at": None,
                    "updated_at": None,
                }
            ],
            sentences=["Stored enrichment coverage exists for this player."],
        )
        context_mock.return_value = {
            "source": "directory_entry",
            "provider": "football-data",
            "player_name": "Bukayo Saka",
            "primary_position": "RW",
            "nationality": "England",
            "date_of_birth": None,
            "season_label": "2024/2025",
            "last_synced_at": None,
            "team": {"id": 10, "name": "Arsenal", "short_name": "ARS"},
            "competition": {"id": 20, "code": "EPL", "name": "Premier League"},
        }

        result = playeroverview_queries.get_player_overview(
            7,
            season_label="2024/2025",
            competition_code="EPL",
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["player"]["id"], 7)
        self.assertEqual(result["club"]["name"], "Arsenal")
        self.assertTrue(result["has_overview_data"])
        self.assertEqual(result["context"]["competition_code"], "EPL")
        self.assertEqual(result["provider_coverage"]["coverage_status"], "available")
        self.assertEqual(
            sorted(result["provider_coverage"]["available_sources"]),
            ["livefootball", "playerdata"],
        )

        general_group = result["metric_groups"][0]
        role_group = result["metric_groups"][1]

        self.assertEqual(general_group["key"], "general")
        self.assertEqual(
            [metric["key"] for metric in general_group["metrics"]],
            ["matches_played", "minutes_played"],
        )
        self.assertEqual(role_group["label"], "Attacking output")
        self.assertEqual(
            [metric["key"] for metric in role_group["metrics"]],
            ["goals", "xg", "shots", "assists", "xa"],
        )

        xg_metric = next(metric for metric in role_group["metrics"] if metric["key"] == "xg")
        self.assertEqual(xg_metric["source"], "playerdata")
        self.assertEqual(xg_metric["preferred_provider"], "understat")
        self.assertEqual(
            xg_metric["source_preference"]["preferred_provider"],
            "understat",
        )

    @patch("services.playeroverview.queries.build_player_provider_coverage_summary")
    def test_get_player_provider_coverage_builds_honest_merged_block(self, coverage_summary_mock):
        coverage_summary_mock.return_value = FakeCoverageSummary(
            items=[
                {
                    "provider": "understat",
                    "season_label": "2024/2025",
                    "competition_code": "EPL",
                    "competition_name": "Premier League",
                    "club_id": 2,
                    "last_synced_at": None,
                    "updated_at": None,
                }
            ],
            sentences=["Stored enrichment coverage exists for this player."],
        )

        summary = SimpleNamespace(matches_played=24, minutes_played=2011)
        livefootball_context = {
            "source": "directory_entry",
            "provider": "football-data",
            "season_label": "2024/2025",
            "last_synced_at": None,
            "team": {"id": 10, "name": "Arsenal"},
            "competition": {"id": 20, "code": "EPL", "name": "Premier League"},
        }

        result = playeroverview_queries.get_player_provider_coverage(
            7,
            season_label="2024/2025",
            competition_code="EPL",
            club_id=2,
            livefootball_context=livefootball_context,
            summary=summary,
        )

        self.assertTrue(result["has_data"])
        self.assertEqual(result["coverage_status"], "available")
        self.assertEqual(
            sorted(result["available_sources"]),
            ["livefootball", "playerdata"],
        )
        self.assertEqual(result["missing_sources"], [])
        self.assertEqual(result["matches_sampled"], 24)
        self.assertEqual(result["minutes_sampled"], 2011)
        self.assertIn("playerdata", result["source_details"])
        self.assertIn("livefootball", result["source_details"])

    @patch("services.playeroverview.queries.get_best_available_player_context")
    @patch("services.playeroverview.queries.build_player_provider_coverage_summary")
    @patch("services.playeroverview.queries.build_player_season_summary")
    @patch("services.playeroverview.queries.Player")
    def test_get_player_overview_is_null_safe_when_summary_and_context_are_missing(
        self,
        player_model_mock,
        build_summary_mock,
        coverage_summary_mock,
        context_mock,
    ):
        player_model_mock.objects.filter.return_value.first.return_value = self._make_player(
            player_id=11,
            display_name="Unknown Player",
            full_name="Unknown Player",
            primary_position="",
            secondary_positions=[],
            nationality="",
            photo_url="",
        )
        build_summary_mock.return_value = None
        coverage_summary_mock.return_value = None
        context_mock.return_value = None

        result = playeroverview_queries.get_player_overview(11)

        self.assertIsNotNone(result)
        self.assertFalse(result["has_overview_data"])
        self.assertEqual(result["metric_groups"], [])
        self.assertEqual(result["provider_coverage"]["coverage_status"], "missing")
        self.assertIn(
            "No stored playerdata season summary matched the requested filters.",
            result["missing_reasons"],
        )
        self.assertIn(
            "No livefootball context matched the requested filters.",
            result["missing_reasons"],
        )

    @patch("services.playeroverview.queries.build_player_comparison")
    @patch("services.playeroverview.queries.get_player_overview")
    def test_compare_players_overview_returns_grouped_comparison_shape(
        self,
        get_player_overview_mock,
        build_player_comparison_mock,
    ):
        player_a_overview = {
            "player": {
                "id": 7,
                "display_name": "Bukayo Saka",
                "position": "RW",
                "primary_position": "RW",
            },
            "club": {"id": 2, "name": "Arsenal"},
            "context": {
                "provider": "understat",
                "season": "2024/2025",
                "competition_code": "EPL",
                "competition_name": "Premier League",
            },
            "provider_coverage": {
                "available_sources": ["playerdata", "livefootball"],
                "missing_sources": [],
                "last_synced_at": None,
                "source_updated_at": None,
            },
            "has_overview_data": True,
        }
        player_b_overview = {
            "player": {
                "id": 8,
                "display_name": "Phil Foden",
                "position": "RW",
                "primary_position": "RW",
            },
            "club": {"id": 3, "name": "Manchester City"},
            "context": {
                "provider": "understat",
                "season": "2024/2025",
                "competition_code": "EPL",
                "competition_name": "Premier League",
            },
            "provider_coverage": {
                "available_sources": ["playerdata"],
                "missing_sources": ["livefootball"],
                "last_synced_at": None,
                "source_updated_at": None,
            },
            "has_overview_data": True,
        }
        get_player_overview_mock.side_effect = [player_a_overview, player_b_overview]

        comparison_context = SimpleNamespace(
            provider="understat",
            to_dict=lambda: {
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
        )
        comparison_metrics = [
            SimpleNamespace(
                key="shots",
                label="Shots",
                player_a_value=60,
                player_a_formatted="60",
                player_b_value=55,
                player_b_formatted="55",
                delta=5,
                formatted_delta="5",
                unit=None,
                winner="player_a",
                is_tie=False,
                is_comparable=True,
                sentence="Player A has taken more shots.",
            ),
            SimpleNamespace(
                key="goals",
                label="Goals",
                player_a_value=14,
                player_a_formatted="14",
                player_b_value=13,
                player_b_formatted="13",
                delta=1,
                formatted_delta="1",
                unit=None,
                winner="player_a",
                is_tie=False,
                is_comparable=True,
                sentence="Player A has scored more goals.",
            ),
            SimpleNamespace(
                key="minutes_played",
                label="Minutes played",
                player_a_value=2011,
                player_a_formatted="2,011",
                player_b_value=1988,
                player_b_formatted="1,988",
                delta=23,
                formatted_delta="23",
                unit=None,
                winner="player_a",
                is_tie=False,
                is_comparable=True,
                sentence="Player A has played slightly more minutes.",
            ),
        ]
        build_player_comparison_mock.return_value = SimpleNamespace(
            context=comparison_context,
            metrics=comparison_metrics,
            explanation={
                "headline": "Merged player comparison",
                "summary": "Player A narrowly leads the attacking comparison.",
                "strengths": ["Player A leads goals and shots"],
                "watchouts": [],
                "notes": [],
            },
            summary_lines=["Player A narrowly leads the attacking comparison."],
            overall_winner={
                "winner": "player_a",
                "winner_player_id": 7,
                "reason": "Player A leads more comparable metrics.",
            },
            provider_coverage={
                "provider": "merged",
                "has_data": True,
                "coverage_status": "available",
                "freshness_label": "stored",
                "source_updated_at": None,
                "last_synced_at": None,
                "matches_sampled": None,
                "minutes_sampled": None,
                "coverage_notes": [],
            },
        )

        result = playeroverview_queries.compare_players_overview(7, 8, season_label="2024/2025")

        self.assertIsNotNone(result)
        self.assertTrue(result["has_comparison_data"])
        self.assertEqual(result["overall_winner"]["winner"], "player_a")
        self.assertEqual(result["context"]["competition_code"], "EPL")
        self.assertEqual(result["player_a"]["player"]["id"], 7)
        self.assertEqual(result["player_b"]["player"]["id"], 8)
        self.assertEqual(result["metric_groups"][0]["key"], "general")
        self.assertEqual(
            [metric["key"] for metric in result["metric_groups"][0]["metrics"]],
            ["minutes_played"],
        )
        self.assertEqual(
            [metric["key"] for metric in result["metric_groups"][1]["metrics"]],
            ["goals", "shots"],
        )