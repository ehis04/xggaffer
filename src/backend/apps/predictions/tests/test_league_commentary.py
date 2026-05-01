from __future__ import annotations

from django.test import SimpleTestCase

from apps.predictions.interpretations.league_commentary import (
    generate_comparison_commentary,
    generate_expected_table_commentary,
)


class LeagueCommentaryTests(SimpleTestCase):
    def setUp(self) -> None:
        self.expected_table = [
            {
                "team": "Arsenal",
                "predicted_points": 86.2,
                "predicted_position": 1,
                "position_probabilities": {1: 0.58, 2: 0.28, 3: 0.10, 4: 0.04},
                "title_probability": 0.58,
                "top_4_probability": 0.96,
                "relegation_probability": 0.0,
                "simulated_wins": 26.2,
                "simulated_draws": 7.6,
                "simulated_losses": 4.2,
                "simulated_goals_for": 79.2,
                "simulated_goals_against": 31.4,
            },
            {
                "team": "Manchester City",
                "predicted_points": 83.1,
                "predicted_position": 2,
                "position_probabilities": {1: 0.29, 2: 0.34, 3: 0.21, 4: 0.16},
                "title_probability": 0.29,
                "top_4_probability": 0.93,
                "relegation_probability": 0.0,
                "simulated_wins": 25.1,
                "simulated_draws": 8.0,
                "simulated_losses": 4.9,
                "simulated_goals_for": 76.5,
                "simulated_goals_against": 34.2,
            },
            {
                "team": "Wolverhampton Wanderers",
                "predicted_points": 32.4,
                "predicted_position": 18,
                "position_probabilities": {16: 0.15, 17: 0.19, 18: 0.22, 19: 0.24, 20: 0.20},
                "title_probability": 0.0,
                "top_4_probability": 0.0,
                "relegation_probability": 0.66,
                "simulated_wins": 8.1,
                "simulated_draws": 8.1,
                "simulated_losses": 21.8,
                "simulated_goals_for": 35.2,
                "simulated_goals_against": 63.0,
            },
        ]

        self.actual_table = [
            {"position": 1, "team": {"name": "Manchester City"}, "points": 88},
            {"position": 2, "team": {"name": "Arsenal"}, "points": 84},
            {"position": 12, "team": {"name": "Wolverhampton Wanderers"}, "points": 46},
        ]

    def test_expected_commentary_returns_structured_blocks(self) -> None:
        blocks = generate_expected_table_commentary(
            self.expected_table,
            league="Premier League",
            season="2024",
            mode="current_expected",
            simulation_count=5000,
        )

        self.assertGreaterEqual(len(blocks), 4)

        for block in blocks:
            self.assertIn("type", block)
            self.assertIn("text", block)
            self.assertIn("confidence", block)
            self.assertIn("related_teams", block)

            self.assertIn(block["type"], {"headline", "observation", "comparison", "caveat"})
            self.assertIn(block["confidence"], {"high", "medium", "low"})
            self.assertIsInstance(block["related_teams"], list)

    def test_expected_commentary_handles_empty_table(self) -> None:
        blocks = generate_expected_table_commentary(
            [],
            league="Premier League",
            season="2024",
            mode="pre_season",
            simulation_count=100,
        )

        self.assertGreaterEqual(len(blocks), 1)
        self.assertIn("No expected table is available", blocks[0]["text"])

    def test_comparison_commentary_returns_structured_blocks(self) -> None:
        blocks = generate_comparison_commentary(
            self.actual_table,
            self.expected_table,
            league="Premier League",
            season="2024",
            mode="current_expected",
        )

        self.assertGreaterEqual(len(blocks), 3)

        for block in blocks:
            self.assertIn("type", block)
            self.assertIn("text", block)
            self.assertIn("confidence", block)
            self.assertIn("related_teams", block)

    def test_comparison_commentary_detects_overperformance(self) -> None:
        blocks = generate_comparison_commentary(
            self.actual_table,
            self.expected_table,
            league="Premier League",
            season="2024",
            mode="current_expected",
        )

        combined_text = " ".join(block["text"] for block in blocks)
        self.assertIn("Wolverhampton Wanderers", combined_text)

    def test_comparison_commentary_handles_missing_data(self) -> None:
        blocks = generate_comparison_commentary(
            [],
            self.expected_table,
            league="Premier League",
            season="2024",
            mode="current_expected",
        )

        self.assertGreaterEqual(len(blocks), 1)
        self.assertIn("No comparison commentary is available", blocks[0]["text"])

    def test_expected_commentary_includes_as_of_matchweek_caveat(self) -> None:
        blocks = generate_expected_table_commentary(
            self.expected_table,
            league="Premier League",
            season="2024",
            mode="as_of_matchweek",
            simulation_count=5000,
            based_on_matchweek=10,
        )

        caveat_text = " ".join(
            block["text"] for block in blocks if block["type"] == "caveat"
        )
        self.assertIn("matchweek 10", caveat_text)

        def test_expected_commentary_handles_settled_current_expected_output(self) -> None:
            blocks = generate_expected_table_commentary(
                self.expected_table,
                league="Premier League",
                season="2024",
                mode="current_expected",
                simulation_count=5000,
                based_on_matchweek=38,
                remaining_fixtures=0,
            )

        combined_text = " ".join(block["text"] for block in blocks)
        self.assertIn("settled", combined_text)

    def test_comparison_commentary_handles_full_alignment_for_finished_state(self) -> None:
        aligned_actual_table = [
            {"position": 1, "team": {"name": "Arsenal"}, "points": 86.2},
            {"position": 2, "team": {"name": "Manchester City"}, "points": 83.1},
            {"position": 18, "team": {"name": "Wolverhampton Wanderers"}, "points": 32.4},
        ]

        blocks = generate_comparison_commentary(
            aligned_actual_table,
            self.expected_table,
            league="Premier League",
            season="2024",
            mode="current_expected",
            remaining_fixtures=0,
        )

        self.assertIn("fully aligned", blocks[0]["text"])