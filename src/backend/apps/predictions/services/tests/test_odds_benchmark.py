from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
from django.test import SimpleTestCase

from apps.predictions.services.odds.benchmark_builder import build_benchmark_rows
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.predictions.models import HistoricalMarketBenchmark

class SeedOddsBenchmarkCommandTests(TestCase):
    def test_command_reads_csv_and_writes_benchmark_rows(self):
        dataframe = pd.DataFrame(
            [
                self._row("Premier League", 2024, 1, 1, 1),
                self._row("Premier League", 2024, 2, 3, 0),
                self._row("La Liga", 2024, 1, 1, 1),
            ]
        )

        csv_path = self._write_csv(dataframe)
        stdout = StringIO()

        call_command(
            "seed_odds_benchmark",
            csv_path=str(csv_path),
            stdout=stdout,
        )

        self.assertEqual(HistoricalMarketBenchmark.objects.count(), 2)

        premier_league_row = HistoricalMarketBenchmark.objects.get(
            league="Premier League",
            season="2024",
            source_label="engine4_backtest",
            evaluation_scope="engine4_season_simulation_backtest",
        )
        self.assertEqual(premier_league_row.sample_size, 2)
        self.assertAlmostEqual(premier_league_row.model_accuracy, 0.5)

        output = stdout.getvalue()
        self.assertIn("Odds benchmark seeding completed successfully", output)

    def test_repeated_command_run_does_not_create_duplicates(self):
        dataframe = pd.DataFrame(
            [
                self._row("Premier League", 2024, 1, 1, 1),
                self._row("Premier League", 2024, 2, 2, 1),
            ]
        )

        csv_path = self._write_csv(dataframe)

        call_command(
            "seed_odds_benchmark",
            csv_path=str(csv_path),
        )
        self.assertEqual(HistoricalMarketBenchmark.objects.count(), 1)

        updated_dataframe = pd.DataFrame(
            [
                self._row("Premier League", 2024, 1, 1, 1),
                self._row("Premier League", 2024, 2, 3, 0),
                self._row("Premier League", 2024, 3, 3, 1),
            ]
        )
        updated_dataframe.to_csv(csv_path, index=False)

        call_command(
            "seed_odds_benchmark",
            csv_path=str(csv_path),
        )

        self.assertEqual(HistoricalMarketBenchmark.objects.count(), 1)

        benchmark_row = HistoricalMarketBenchmark.objects.get(
            league="Premier League",
            season="2024",
            source_label="engine4_backtest",
            evaluation_scope="engine4_season_simulation_backtest",
        )
        self.assertEqual(benchmark_row.sample_size, 3)
        self.assertAlmostEqual(benchmark_row.model_accuracy, 2 / 3)

    def test_replace_existing_rewrites_matching_rows_cleanly(self):
        dataframe = pd.DataFrame(
            [
                self._row("Premier League", 2024, 1, 1, 1),
                self._row("Premier League", 2024, 2, 2, 1),
            ]
        )

        csv_path = self._write_csv(dataframe)

        call_command(
            "seed_odds_benchmark",
            csv_path=str(csv_path),
        )
        self.assertEqual(HistoricalMarketBenchmark.objects.count(), 1)

        replacement_dataframe = pd.DataFrame(
            [
                self._row("Premier League", 2024, 1, 2, 0),
                self._row("Premier League", 2024, 2, 2, 1),
                self._row("Premier League", 2024, 3, 4, 0),
                self._row("Premier League", 2024, 4, 4, 1),
            ]
        )
        replacement_dataframe.to_csv(csv_path, index=False)

        call_command(
            "seed_odds_benchmark",
            csv_path=str(csv_path),
            replace_existing=True,
        )

        self.assertEqual(HistoricalMarketBenchmark.objects.count(), 1)

        benchmark_row = HistoricalMarketBenchmark.objects.get(
            league="Premier League",
            season="2024",
            source_label="engine4_backtest",
            evaluation_scope="engine4_season_simulation_backtest",
        )
        self.assertEqual(benchmark_row.sample_size, 4)
        self.assertAlmostEqual(benchmark_row.model_accuracy, 0.5)

    def _write_csv(self, dataframe: pd.DataFrame) -> Path:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        csv_path = Path(temp_dir.name) / "engine4_backtest_results.csv"
        dataframe.to_csv(csv_path, index=False)
        return csv_path

    def _row(
        self,
        league: str,
        season: int,
        actual_position: int,
        modal_position: int,
        in_interval: int,
    ) -> dict:
        return {
            "league": league,
            "season": season,
            "actual_position": actual_position,
            "modal_position": modal_position,
            "p_top_4": 0.4,
            "p_relegation": 0.1,
            "position_5th": 2,
            "position_95th": 8,
            "in_interval": in_interval,
        }

class OddsBenchmarkBuilderTests(SimpleTestCase):
    def test_builder_groups_rows_by_league_and_season(self):
        dataframe = pd.DataFrame(
            [
                self._row("Premier League", 2024, 1, 1, 1),
                self._row("Premier League", 2024, 2, 3, 0),
                self._row("Premier League", 2025, 4, 4, 1),
                self._row("La Liga", 2024, 1, 1, 1),
            ]
        )

        csv_path = self._write_csv(dataframe)
        benchmark_rows = build_benchmark_rows(csv_path)

        self.assertEqual(len(benchmark_rows), 3)

        grouped_keys = {
            (row["league"], row["season"])
            for row in benchmark_rows
        }
        self.assertSetEqual(
            grouped_keys,
            {
                ("Premier League", "2024"),
                ("Premier League", "2025"),
                ("La Liga", "2024"),
            },
        )

    def test_builder_computes_sample_size_and_model_accuracy_correctly(self):
        dataframe = pd.DataFrame(
            [
                self._row("Premier League", 2024, 1, 1, 1),
                self._row("Premier League", 2024, 2, 2, 1),
                self._row("Premier League", 2024, 3, 4, 0),
            ]
        )

        csv_path = self._write_csv(dataframe)
        benchmark_rows = build_benchmark_rows(csv_path)

        self.assertEqual(len(benchmark_rows), 1)

        row = benchmark_rows[0]
        self.assertEqual(row["league"], "Premier League")
        self.assertEqual(row["season"], "2024")
        self.assertEqual(row["sample_size"], 3)
        self.assertAlmostEqual(row["model_accuracy"], 2 / 3)

    def test_builder_leaves_market_metrics_as_none_for_v1(self):
        dataframe = pd.DataFrame(
            [
                self._row("Premier League", 2024, 1, 1, 1),
                self._row("Premier League", 2024, 2, 3, 0),
            ]
        )

        csv_path = self._write_csv(dataframe)
        benchmark_rows = build_benchmark_rows(csv_path)

        row = benchmark_rows[0]
        self.assertIsNone(row["market_favourite_accuracy"])
        self.assertIsNone(row["model_brier_score"])
        self.assertIsNone(row["market_brier_score"])

    def test_builder_raises_clear_error_for_missing_required_columns(self):
        dataframe = pd.DataFrame(
            [
                {
                    "league": "Premier League",
                    "season": 2024,
                    "actual_position": 1,
                }
            ]
        )

        csv_path = self._write_csv(dataframe)

        with self.assertRaises(ValueError) as context:
            build_benchmark_rows(csv_path)

        error_message = str(context.exception)
        self.assertIn("Benchmark CSV is missing required columns", error_message)
        self.assertIn("modal_position", error_message)
        self.assertIn("in_interval", error_message)

    def test_builder_output_shape_matches_historical_market_benchmark_fields(self):
        dataframe = pd.DataFrame(
            [
                self._row("Premier League", 2024, 1, 1, 1),
                self._row("Premier League", 2024, 2, 2, 1),
            ]
        )

        csv_path = self._write_csv(dataframe)
        benchmark_rows = build_benchmark_rows(csv_path)

        row = benchmark_rows[0]
        self.assertEqual(
            set(row.keys()),
            {
                "league",
                "season",
                "sample_size",
                "model_accuracy",
                "market_favourite_accuracy",
                "model_brier_score",
                "market_brier_score",
                "evaluation_scope",
                "source_label",
            },
        )

    def _write_csv(self, dataframe: pd.DataFrame) -> Path:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        csv_path = Path(temp_dir.name) / "engine4_backtest_results.csv"
        dataframe.to_csv(csv_path, index=False)
        return csv_path

    def _row(
        self,
        league: str,
        season: int,
        actual_position: int,
        modal_position: int,
        in_interval: int,
    ) -> dict:
        return {
            "league": league,
            "season": season,
            "actual_position": actual_position,
            "modal_position": modal_position,
            "p_top_4": 0.4,
            "p_relegation": 0.1,
            "position_5th": 2,
            "position_95th": 8,
            "in_interval": in_interval,
        }