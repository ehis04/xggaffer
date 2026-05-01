from __future__ import annotations

from decimal import Decimal

from services.playerdata.comparisons import (
    build_club_comparison_summary,
    build_comparison_table_data,
    build_player_comparison_summary,
    compare_club_seasons,
    compare_player_seasons,
)
from services.playerdata.tests.test_queries import PlayerDataQueryServiceTests


from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from services.playerdata.queries import PlayerSeasonEnrichmentRecord
from services.playerdata.comparisons import build_player_comparison


class PlayerDataComparisonPhase5ShapeTests(SimpleTestCase):
    def _player_a(self) -> PlayerSeasonEnrichmentRecord:
        return PlayerSeasonEnrichmentRecord(
            enrichment_id=101,
            player_id=7,
            player_name="Bukayo Saka",
            primary_position="RW",
            secondary_positions=["LW"],
            club_id=3,
            club_name="Arsenal",
            provider="understat",
            season_label="2024-2025",
            competition_code="EPL",
            competition_name="Premier League",
            matches_played=24,
            minutes_played=1950,
            goals=10,
            assists=6,
            shots=58,
            xg=Decimal("8.4"),
            xa=Decimal("7.2"),
            npg=Decimal("9"),
            npxg=Decimal("7.9"),
            key_passes=41,
            last_synced_at=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 1, 12, 5, tzinfo=timezone.utc),
        )

    def _player_b(self) -> PlayerSeasonEnrichmentRecord:
        return PlayerSeasonEnrichmentRecord(
            enrichment_id=102,
            player_id=11,
            player_name="Phil Foden",
            primary_position="AM",
            secondary_positions=["RW"],
            club_id=4,
            club_name="Manchester City",
            provider="understat",
            season_label="2024-2025",
            competition_code="EPL",
            competition_name="Premier League",
            matches_played=23,
            minutes_played=1800,
            goals=8,
            assists=6,
            shots=49,
            xg=Decimal("6.9"),
            xa=Decimal("6.1"),
            npg=Decimal("8"),
            npxg=Decimal("6.4"),
            key_passes=35,
            last_synced_at=datetime(2026, 3, 1, 13, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 1, 13, 5, tzinfo=timezone.utc),
        )

    def test_build_player_comparison_exposes_phase5_api_contract_properties(self):
        with patch(
            "services.playerdata.comparisons.get_player_season_enrichment",
            side_effect=[self._player_a(), self._player_b()],
        ):
            comparison = build_player_comparison(
                player_a_id=7,
                player_b_id=11,
                season="2024-2025",
                provider="understat",
                competition_code="EPL",
            )

        self.assertIsNotNone(comparison)
        self.assertEqual(comparison.player_a.player["id"], 7)
        self.assertEqual(comparison.player_b.player["id"], 11)
        self.assertEqual(comparison.context.provider, "understat")
        self.assertEqual(comparison.context.season, "2024-2025")
        self.assertTrue(len(comparison.metrics) > 0)

        first_metric = comparison.metrics[0]
        self.assertIsNotNone(first_metric.key)
        self.assertIn("player_a_value", first_metric.to_dict())
        self.assertIn("player_b_value", first_metric.to_dict())
        self.assertIn("delta", first_metric.to_dict())

        self.assertIn("winner", comparison.overall_winner)
        self.assertIn("reason", comparison.overall_winner)
        self.assertEqual(
            comparison.explanation["headline"],
            "Deterministic player comparison",
        )
        self.assertEqual(comparison.provider_coverage["provider"], "understat")
        self.assertTrue(comparison.has_comparison_data)
        self.assertEqual(comparison.missing_reasons, [])

    def test_build_player_comparison_returns_none_when_one_side_missing(self):
        with patch(
            "services.playerdata.comparisons.get_player_season_enrichment",
            side_effect=[self._player_a(), None],
        ):
            comparison = build_player_comparison(player_a_id=7, player_b_id=11)

        self.assertIsNone(comparison)
        
class PlayerDataComparisonServiceTests(PlayerDataQueryServiceTests):
    def test_compare_player_seasons_returns_correct_values_and_winners(self):
        comparison = compare_player_seasons(
            self.player_a.id,
            self.player_b.id,
            season_label="2024",
            provider=self.understat_provider,
            competition_code="EPL",
            club_a_id=self.club_alpha.id,
            club_b_id=self.club_alpha.id,
        )

        self.assertIsNotNone(comparison)
        self.assertEqual(comparison.left.player_name, "Player A")
        self.assertEqual(comparison.right.player_name, "Player B")

        self.assertTrue(comparison.context.same_provider)
        self.assertTrue(comparison.context.same_season)
        self.assertTrue(comparison.context.same_competition)
        self.assertEqual(comparison.context.provider, self.understat_provider)
        self.assertEqual(comparison.context.season_label, "2024")
        self.assertEqual(comparison.context.competition_code, "EPL")
        self.assertEqual(comparison.context.competition_name, "Premier League")
        self.assertEqual(
            comparison.context.sentence,
            f"Both records come from {self.understat_provider} in the 2024 season for Premier League.",
        )

        metrics = {metric.metric_key: metric for metric in comparison.metrics}

        self.assertEqual(metrics["goals"].left_value, 14)
        self.assertEqual(metrics["goals"].right_value, 5)
        self.assertEqual(metrics["goals"].winner, "Player A")
        self.assertEqual(metrics["goals"].difference, 9)

        self.assertEqual(metrics["assists"].left_value, 7)
        self.assertEqual(metrics["assists"].right_value, 11)
        self.assertEqual(metrics["assists"].winner, "Player B")
        self.assertEqual(metrics["assists"].difference, -4)

        self.assertEqual(metrics["xg"].left_value, Decimal("13.75"))
        self.assertEqual(metrics["xg"].right_value, Decimal("4.30"))
        self.assertEqual(metrics["xg"].winner, "Player A")
        self.assertEqual(metrics["xg"].difference, Decimal("9.45"))

        self.assertEqual(metrics["xa"].left_value, Decimal("6.20"))
        self.assertEqual(metrics["xa"].right_value, Decimal("8.40"))
        self.assertEqual(metrics["xa"].winner, "Player B")
        self.assertEqual(metrics["xa"].difference, Decimal("-2.20"))

        self.assertEqual(metrics["minutes_played"].winner, "Player A")
        self.assertEqual(metrics["matches_played"].winner, "Player A")
        self.assertEqual(metrics["shots"].winner, "Player A")
        self.assertEqual(metrics["key_passes"].winner, "Player B")

    def test_player_comparison_summary_remains_deterministic(self):
        comparison = compare_player_seasons(
            self.player_a.id,
            self.player_b.id,
            season_label="2024",
            provider=self.understat_provider,
            competition_code="EPL",
            club_a_id=self.club_alpha.id,
            club_b_id=self.club_alpha.id,
        )

        self.assertIsNotNone(comparison)
        self.assertEqual(
            comparison.summary_lines,
            [
                f"Both records come from {self.understat_provider} in the 2024 season for Premier League.",
                "Player A played 2,200 minutes across 30 matches, while Player B played 2,050 minutes across 28 matches.",
                "Player A leads in: Goals, xG, Shots, Minutes, Matches.",
                "Player B leads in: Assists, xA, Key passes.",
            ],
        )

        rebuilt_summary = build_player_comparison_summary(comparison)
        self.assertEqual(rebuilt_summary, comparison.summary_lines)

    def test_player_comparison_handles_missing_values_honestly(self):
        comparison = compare_player_seasons(
            self.player_a.id,
            self.player_c.id,
            season_label="2024",
            provider=self.understat_provider,
            competition_code="EPL",
            club_a_id=self.club_alpha.id,
        )

        self.assertIsNotNone(comparison)

        metrics = {metric.metric_key: metric for metric in comparison.metrics}

        self.assertTrue(metrics["goals"].is_comparable)
        self.assertEqual(metrics["goals"].winner, "Player A")

        self.assertFalse(metrics["xg"].is_comparable)
        self.assertIsNone(metrics["xg"].winner)
        self.assertIsNone(metrics["xg"].difference)
        self.assertEqual(
            metrics["xg"].sentence,
            "xG could not be compared honestly because at least one record is missing a value.",
        )

        self.assertFalse(metrics["xa"].is_comparable)
        self.assertEqual(
            metrics["xa"].sentence,
            "xA could not be compared honestly because at least one record is missing a value.",
        )

        self.assertIn(
            "Metrics not compared because of missing values: xG, xA.",
            comparison.summary_lines,
        )

    def test_player_comparison_handles_ties_honestly(self):
        comparison = compare_player_seasons(
            self.player_a.id,
            self.player_a.id,
            season_label="2024",
            provider=self.understat_provider,
            competition_code="EPL",
            club_a_id=self.club_alpha.id,
            club_b_id=self.club_alpha.id,
        )

        self.assertIsNotNone(comparison)

        for metric in comparison.metrics:
            self.assertTrue(metric.is_comparable)
            self.assertTrue(metric.is_tie)
            self.assertIsNone(metric.winner)

        self.assertIn(
            "Tied metrics: Goals, Assists, xG, xA, Shots, Key passes, Minutes, Matches.",
            comparison.summary_lines,
        )

    def test_compare_club_seasons_handles_higher_and_lower_is_better_metrics(self):
        comparison = compare_club_seasons(
            self.club_alpha.id,
            self.club_beta.id,
            season_label="2024",
        )

        self.assertIsNotNone(comparison)
        self.assertEqual(comparison.left.club_name, "Alpha FC")
        self.assertEqual(comparison.right.club_name, "Beta FC")

        self.assertFalse(comparison.context.same_provider)
        self.assertTrue(comparison.context.same_season)
        self.assertFalse(comparison.context.same_competition)
        self.assertEqual(
            comparison.context.sentence,
            f"Left record: {self.understat_provider}, 2024, Premier League. "
            f"Right record: {self.other_provider}, 2024, Champions League."
        )

        metrics = {metric.metric_key: metric for metric in comparison.metrics}

        self.assertEqual(metrics["wins"].winner, "Alpha FC")
        self.assertEqual(metrics["goals_for"].winner, "Alpha FC")
        self.assertEqual(metrics["xg"].winner, "Alpha FC")

        self.assertEqual(metrics["losses"].winner, "Beta FC")
        self.assertEqual(metrics["goals_against"].winner, "Beta FC")
        self.assertEqual(metrics["xga"].winner, "Beta FC")

        self.assertEqual(metrics["ppda"].winner, "Alpha FC")
        self.assertEqual(metrics["ppda"].difference, Decimal("-2.80"))

        rebuilt_summary = build_club_comparison_summary(comparison)
        self.assertEqual(rebuilt_summary, comparison.summary_lines)

    def test_build_comparison_table_data_returns_metric_payloads(self):
        comparison = compare_player_seasons(
            self.player_a.id,
            self.player_b.id,
            season_label="2024",
            provider=self.understat_provider,
            competition_code="EPL",
            club_a_id=self.club_alpha.id,
            club_b_id=self.club_alpha.id,
        )

        self.assertIsNotNone(comparison)

        table_data = build_comparison_table_data(comparison)

        self.assertEqual(len(table_data), len(comparison.metrics))
        self.assertEqual(table_data[0]["metric_key"], comparison.metrics[0].metric_key)
        self.assertIn("label", table_data[0])
        self.assertIn("left_value", table_data[0])
        self.assertIn("right_value", table_data[0])
        self.assertIn("winner", table_data[0])
        self.assertIn("sentence", table_data[0])

    def test_compare_functions_return_none_when_a_record_is_missing(self):
        self.assertIsNone(
            compare_player_seasons(
                999999,
                self.player_b.id,
                season_label="2024",
                provider=self.understat_provider,
                competition_code="EPL",
            )
        )
        self.assertIsNone(
            compare_club_seasons(
                999999,
                self.club_beta.id,
                season_label="2024",
            )
        )