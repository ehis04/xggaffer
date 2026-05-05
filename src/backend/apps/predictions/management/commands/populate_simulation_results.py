from django.core.management.base import BaseCommand

from apps.livefootball.models import Competition
from apps.livefootball.services.league_data import (
    RELEASE_ONE_COMPETITION_CODES,
    get_league_expected_table_payload,
)
from apps.predictions.models import SimulationResult


class Command(BaseCommand):
    help = "Run simulations for all supported competitions and persist results to SimulationResult."

    def add_arguments(self, parser):
        parser.add_argument(
            "--competition-id",
            action="append",
            dest="competition_ids",
            type=int,
            help=(
                "DB pk of a specific competition to simulate. "
                "Use multiple times for multiple competitions. "
                "Defaults to all supported competitions."
            ),
        )
        parser.add_argument(
            "--season",
            dest="season_label",
            default=None,
            help="Season label to simulate (e.g. '2024'). Defaults to each competition's current season.",
        )
        parser.add_argument(
            "--mode",
            default="current_expected",
            help="Simulation mode to use (default: current_expected).",
        )

    def handle(self, *args, **options):
        season_label = options.get("season_label")
        mode = options["mode"]
        competition_ids = options.get("competition_ids") or []

        if competition_ids:
            competitions = Competition.objects.filter(pk__in=competition_ids)
        else:
            competitions = Competition.objects.filter(code__in=RELEASE_ONE_COMPETITION_CODES)

        if not competitions.exists():
            self.stdout.write(self.style.WARNING("No competitions found."))
            return

        self.stdout.write(
            f"Simulating {competitions.count()} competition(s) "
            f"[mode={mode}, season={season_label or 'current'}]"
        )

        saved = 0
        skipped = 0

        for comp in competitions:
            try:
                get_league_expected_table_payload(
                    comp.id,
                    season_label=season_label,
                    mode=mode,
                )
                saved += 1
                self.stdout.write(self.style.SUCCESS(f"  OK  {comp.name}"))
            except Exception as exc:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"  SKIP {comp.name}: {exc}"))

        total = SimulationResult.objects.count()
        self.stdout.write("")
        self.stdout.write(
            f"Done. saved={saved} skipped={skipped} "
            f"total_simulation_results={total}"
        )
