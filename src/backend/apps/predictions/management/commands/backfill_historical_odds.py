from __future__ import annotations

import time
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.livefootball.models import Competition, CompetitionFixture
from apps.predictions.models import FixtureOddsSnapshot
from apps.predictions.services.odds.exceptions import OddsConfigurationError, OddsSourceError
from apps.predictions.services.odds.service import OddsComparisonService

LEAGUES = {
    "epl": ("soccer_epl", "EPL", "PL"),
    "la_liga": ("soccer_spain_la_liga", "La_Liga", "PD"),
    "bundesliga": ("soccer_germany_bundesliga", "Bundesliga", "BL1"),
    "serie_a": ("soccer_italy_serie_a", "Serie_A", "SA"),
    "ligue_1": ("soccer_france_ligue_one", "Ligue_1", "FL1"),
}

_LF_TO_SNAPSHOT_NAME = {
    'Man City': 'Manchester City',
    'Man United': 'Manchester United',
    'Newcastle': 'Newcastle United',
    'Nottingham': 'Nottingham Forest',
    'Brighton Hove': 'Brighton',
    'Leeds United': 'Leeds',
    'Wolverhampton': 'Wolverhampton Wanderers',
    'Athletic': 'Athletic Club',
    'Bayern': 'Bayern Munich',
    'Angers SCO': 'Angers',
}


def _lf_to_snapshot(name: str) -> str:
    return _LF_TO_SNAPSHOT_NAME.get(name, name)


class Command(BaseCommand):
    help = (
        "Backfill pre-match consensus odds for past 2025/26 fixtures using "
        "The Odds API historical endpoint."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--league",
            choices=list(LEAGUES.keys()) + ["all"],
            default="all",
        )
        parser.add_argument(
            "--season",
            default="2025",
            help="Season label (e.g. '2025'). Defaults to 2025.",
        )
        parser.add_argument(
            "--hours-before",
            type=int,
            default=2,
            help="Fetch odds this many hours before kickoff. Defaults to 2.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be fetched without making API calls.",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=1.5,
            help="Seconds to wait between API calls. Defaults to 1.5.",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            default=True,
            help="Skip fixtures that already have a snapshot (default: True).",
        )

    def handle(self, *args, **options):
        league_arg = options["league"]
        season = options["season"]
        hours_before = options["hours_before"]
        dry_run = options["dry_run"]
        delay = options["delay"]
        skip_existing = options["skip_existing"]

        targets = list(LEAGUES.items()) if league_arg == "all" else [(league_arg, LEAGUES[league_arg])]
        service = OddsComparisonService()
        now = timezone.now()

        total_fetched = 0
        total_skipped = 0

        for league_key, (sport_key, prediction_league, comp_code) in targets:
            self.stdout.write(f"\n── {league_key} ({sport_key}) ──")

            try:
                comp = Competition.objects.get(code=comp_code)
            except Competition.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Competition {comp_code} not found, skipping."))
                continue

            fixtures = list(
                CompetitionFixture.objects.filter(
                    competition=comp,
                    season_label=season,
                    kickoff_at__lt=now,
                    home_score__isnull=False,
                    away_score__isnull=False,
                ).order_by("kickoff_at")
            )

            self.stdout.write(f"  Found {len(fixtures)} completed fixtures.")

            if not fixtures:
                continue

            # Group by fetch date (kickoff - hours_before, rounded to the hour)
            date_groups: dict[str, list[CompetitionFixture]] = {}
            for cf in fixtures:
                if cf.kickoff_at is None:
                    continue

                snap_home = _lf_to_snapshot(cf.home_team_name)
                snap_away = _lf_to_snapshot(cf.away_team_name)

                if skip_existing:
                    exists = FixtureOddsSnapshot.objects.filter(
                        home_team=snap_home,
                        away_team=snap_away,
                        league=prediction_league,
                        season=season,
                    ).exists()
                    if exists:
                        total_skipped += 1
                        continue

                fetch_dt = cf.kickoff_at - timedelta(hours=hours_before)
                date_key = fetch_dt.strftime("%Y-%m-%dT%H:00:00Z")
                date_groups.setdefault(date_key, []).append(cf)

            self.stdout.write(f"  {total_skipped} already have snapshots, {len(date_groups)} fetch dates needed.")

            for date_key, group_fixtures in sorted(date_groups.items()):
                teams = ", ".join(
                    f"{_lf_to_snapshot(f.home_team_name)} vs {_lf_to_snapshot(f.away_team_name)}"
                    for f in group_fixtures
                )
                self.stdout.write(f"  {date_key}: {teams}")

                if dry_run:
                    continue

                try:
                    result = service.fetch_and_store_historical_odds(
                        sport_key=sport_key,
                        league=prediction_league,
                        season=season,
                        date=date_key,
                    )
                    count = result.get("fixture_count", 0)
                    total_fetched += count
                    self.stdout.write(self.style.SUCCESS(f"    Stored {count} snapshot(s)."))
                except OddsConfigurationError as exc:
                    raise CommandError(f"Configuration error: {exc}") from exc
                except OddsSourceError as exc:
                    self.stderr.write(self.style.WARNING(f"    Source error for {date_key}: {exc}"))

                if delay > 0:
                    time.sleep(delay)

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] No API calls made."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nDone. {total_fetched} snapshot(s) stored in total."))
