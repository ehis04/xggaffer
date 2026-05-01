from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.predictions.services.odds.exceptions import OddsConfigurationError, OddsSourceError
from apps.predictions.services.odds.service import OddsComparisonService
from common.utils import current_football_season

LEAGUES = {
    "epl": ("soccer_epl", "EPL"),
    "la_liga": ("soccer_spain_la_liga", "La_Liga"),
    "bundesliga": ("soccer_germany_bundesliga", "Bundesliga"),
    "serie_a": ("soccer_italy_serie_a", "Serie_A"),
    "ligue_1": ("soccer_france_ligue_one", "Ligue_1"),
}

class Command(BaseCommand):
    help = "Fetch current odds from The Odds API and persist them as FixtureOddsSnapshots."

    def add_arguments(self, parser):
        parser.add_argument(
            "--league",
            choices=list(LEAGUES.keys()) + ["all"],
            default="all",
            help="League to fetch odds for. Defaults to all supported leagues.",
        )
        parser.add_argument(
            "--season",
            default=None,
            help="Season string to tag snapshots with (e.g. '2025'). Defaults to the current football season.",
        )

    def handle(self, *args, **options):
        league_arg = options["league"]
        season = options["season"] or current_football_season()

        targets = list(LEAGUES.items()) if league_arg == "all" else [(league_arg, LEAGUES[league_arg])]
        service = OddsComparisonService()
        total_fixtures = 0

        for league_key, (sport_key, prediction_league) in targets:
            self.stdout.write(f"Fetching odds for {league_key} ({sport_key}) season {season} ...")
            try:
                result = service.fetch_and_store_fixture_odds(
                    sport_key=sport_key,
                    league=prediction_league,
                    season=season,
                )
                count = result.get("fixture_count", 0)
                total_fixtures += count
                self.stdout.write(
                    self.style.SUCCESS(f"  Stored {count} fixture snapshot(s) for {league_key}.")
                )
            except OddsConfigurationError as exc:
                raise CommandError(f"Configuration error: {exc}") from exc
            except OddsSourceError as exc:
                self.stderr.write(
                    self.style.WARNING(f"  Skipping {league_key}: source error — {exc}")
                )

        self.stdout.write(self.style.SUCCESS(f"Done. {total_fixtures} fixture snapshot(s) stored in total."))
