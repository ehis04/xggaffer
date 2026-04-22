from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.predictions.models import HistoricalMarketBenchmark
from apps.predictions.services.odds.benchmark_builder import (
    DEFAULT_BENCHMARK_CSV_PATH,
    build_benchmark_rows,
)


class Command(BaseCommand):
    help = "Seed HistoricalMarketBenchmark from engine4_backtest_results.csv."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-path",
            dest="csv_path",
            default=None,
            help="Optional path to a benchmark CSV file. Defaults to engine4_backtest_results.csv.",
        )
        parser.add_argument(
            "--replace-existing",
            action="store_true",
            help="Delete matching existing benchmark rows before inserting replacements.",
        )

    def handle(self, *args, **options):
        csv_path_option = options.get("csv_path")
        replace_existing = options["replace_existing"]

        resolved_csv_path = (
            Path(csv_path_option)
            if csv_path_option is not None
            else DEFAULT_BENCHMARK_CSV_PATH
        )

        if not resolved_csv_path.exists():
            raise CommandError(f"Benchmark CSV not found: {resolved_csv_path}")

        try:
            benchmark_rows = build_benchmark_rows(resolved_csv_path)
        except Exception as exc:
            raise CommandError(f"Failed to build benchmark rows: {exc}") from exc

        if not benchmark_rows:
            self.stdout.write(self.style.WARNING("No benchmark rows were generated."))
            return

        created_count = 0
        updated_count = 0
        replaced_count = 0

        try:
            with transaction.atomic():
                for row in benchmark_rows:
                    lookup = {
                        "league": row["league"],
                        "season": row["season"],
                        "source_label": row["source_label"],
                        "evaluation_scope": row["evaluation_scope"],
                    }
                    defaults = {
                        "sample_size": row["sample_size"],
                        "model_accuracy": row["model_accuracy"],
                        "market_favourite_accuracy": row["market_favourite_accuracy"],
                        "model_brier_score": row["model_brier_score"],
                        "market_brier_score": row["market_brier_score"],
                    }

                    if replace_existing:
                        HistoricalMarketBenchmark.objects.filter(**lookup).delete()
                        HistoricalMarketBenchmark.objects.create(**lookup, **defaults)
                        replaced_count += 1
                    else:
                        _, created = HistoricalMarketBenchmark.objects.update_or_create(
                            **lookup,
                            defaults=defaults,
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
        except Exception as exc:
            raise CommandError(f"Failed to persist benchmark rows: {exc}") from exc

        total_written = replaced_count if replace_existing else created_count + updated_count

        if replace_existing:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Odds benchmark seeding completed successfully. "
                    f"replaced={replaced_count} total_written={total_written} "
                    f"csv_path={resolved_csv_path}"
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Odds benchmark seeding completed successfully. "
                f"created={created_count} updated={updated_count} total_written={total_written} "
                f"csv_path={resolved_csv_path}"
            )
        )