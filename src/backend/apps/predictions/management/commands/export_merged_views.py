from django.core.management.base import BaseCommand, CommandError

from apps.predictions.data_collection.scripts.export_merged_views import (
    DEFAULT_DATASETS,
    DEFAULT_SOURCES,
    LAYER_PROCESSED,
    LAYER_RAW,
    run_export_jobs,
)


class Command(BaseCommand):
    help = "Create all-leagues merged raw and processed CSV exports for the predictions data pipeline."

    def add_arguments(self, parser):
        parser.add_argument(
            "--layer",
            action="append",
            dest="layers",
            choices=[LAYER_RAW, LAYER_PROCESSED],
            help="Limit the export to one or more layers. Defaults to both raw and processed.",
        )
        parser.add_argument(
            "--source",
            action="append",
            dest="sources",
            help="Source to include. Use multiple times for multiple sources.",
        )
        parser.add_argument(
            "--dataset",
            action="append",
            dest="datasets",
            help="Dataset to include. Use multiple times for multiple datasets.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print resolved input files and tracebacks on failures.",
        )
        parser.add_argument(
            "--stop-on-error",
            action="store_true",
            help="Stop immediately on the first failed export.",
        )

    def handle(self, *args, **options):
        layers = options.get("layers") or [LAYER_RAW, LAYER_PROCESSED]
        sources = options.get("sources") or list(DEFAULT_SOURCES)
        datasets = options.get("datasets") or list(DEFAULT_DATASETS)

        exit_code = run_export_jobs(
            layers=layers,
            sources=sources,
            datasets=datasets,
            verbose=options["verbose"],
            stop_on_error=options["stop_on_error"],
        )

        if exit_code != 0:
            raise CommandError("Merged export run did not complete successfully.")

        self.stdout.write(self.style.SUCCESS("Merged exports completed successfully."))