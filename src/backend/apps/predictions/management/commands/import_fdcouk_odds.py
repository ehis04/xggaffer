from __future__ import annotations

from datetime import datetime, timezone

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.predictions.ml.data.odds.download import (
    ALL_LEAGUES,
    download_one,
    build_output_path,
    LEAGUE_TO_FDCOUK_CODE,
    UNDERSTAT_TO_FDCOUK_SEASON,
)
from apps.predictions.ml.data.odds.parse import parse_single_csv
from apps.predictions.models import Bookmaker, BookmakerQuote, FixtureOddsSnapshot

try:
    from data_collection.config.team_name_mappings import to_canonical
    _HAS_CANONICAL = True
except ImportError:
    _HAS_CANONICAL = False

FDCOUK_BOOKMAKER_SLUG = "fdcouk-market"
FDCOUK_BOOKMAKER_NAME = "Football-Data Market Avg"


def _to_canonical(fdcouk_name: str) -> str | None:
    if not _HAS_CANONICAL:
        return fdcouk_name
    try:
        return to_canonical(fdcouk_name, "football_data_co_uk")
    except KeyError:
        return None


def _get_or_create_fdcouk_bookmaker() -> Bookmaker:
    bookmaker, _ = Bookmaker.objects.get_or_create(
        slug=FDCOUK_BOOKMAKER_SLUG,
        defaults={
            "name": FDCOUK_BOOKMAKER_NAME,
            "source": Bookmaker.Source.FDCOUK,
            "region": "",
            "is_active": True,
        },
    )
    return bookmaker


class Command(BaseCommand):
    help = (
        "Import Football-Data.co.uk market consensus odds as FixtureOddsSnapshot entries. "
        "Covers all seasons from 2014 to 2025 (including 2025/26 in progress)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--league",
            choices=list(LEAGUE_TO_FDCOUK_CODE.keys()) + ["all"],
            default="all",
        )
        parser.add_argument(
            "--season",
            default="2025",
            help="Season to import (e.g. '2025'). Defaults to 2025.",
        )
        parser.add_argument(
            "--overwrite-csv",
            action="store_true",
            help="Re-download the CSV even if it already exists.",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            default=True,
            help="Skip fixtures that already have an FDCOUK snapshot.",
        )

    def handle(self, *args, **options):
        league_arg = options["league"]
        season = options["season"]
        overwrite_csv = options["overwrite_csv"]
        skip_existing = options["skip_existing"]

        if season not in UNDERSTAT_TO_FDCOUK_SEASON:
            self.stderr.write(self.style.ERROR(
                f"Season '{season}' not in UNDERSTAT_TO_FDCOUK_SEASON. "
                f"Available: {sorted(UNDERSTAT_TO_FDCOUK_SEASON.keys())}"
            ))
            return

        leagues = ALL_LEAGUES if league_arg == "all" else [league_arg]
        bookmaker = _get_or_create_fdcouk_bookmaker()
        total_created = 0
        total_skipped = 0
        now = datetime.now(tz=timezone.utc)

        for league in leagues:
            self.stdout.write(f"\n── {league} {season} ──")

            # Download CSV
            path = build_output_path(league, season)
            if not path.exists() or overwrite_csv:
                self.stdout.write(f"  Downloading from football-data.co.uk…")
                try:
                    path = download_one(league, season, overwrite=overwrite_csv)
                    self.stdout.write(f"  Downloaded: {path.name} ({path.stat().st_size // 1024} KB)")
                except Exception as exc:
                    self.stderr.write(self.style.WARNING(f"  Download failed: {exc}"))
                    continue
            else:
                self.stdout.write(f"  Using cached: {path.name}")

            # Parse
            df = parse_single_csv(path, league, season)
            if df is None or len(df) == 0:
                self.stdout.write(self.style.WARNING("  No valid rows parsed, skipping."))
                continue

            self.stdout.write(f"  Parsed {len(df)} rows.")
            league_created = 0
            league_skipped = 0

            with transaction.atomic():
                for _, row in df.iterrows():
                    home_canonical = _to_canonical(row["fdcouk_home_team"])
                    away_canonical = _to_canonical(row["fdcouk_away_team"])

                    if home_canonical is None or away_canonical is None:
                        league_skipped += 1
                        continue

                    match_date = row["date"]
                    if hasattr(match_date, "to_pydatetime"):
                        match_date = match_date.to_pydatetime()

                    commence_time = match_date.replace(
                        hour=15, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
                    ) if match_date.tzinfo is None else match_date.replace(
                        hour=15, minute=0, second=0, microsecond=0
                    ).astimezone(timezone.utc)

                    date_str = commence_time.strftime("%Y-%m-%d")
                    external_id = f"fdcouk_{league}_{date_str}_{home_canonical}_{away_canonical}"

                    if skip_existing and FixtureOddsSnapshot.objects.filter(
                        external_fixture_id=external_id,
                        bookmaker_source="fdcouk",
                    ).exists():
                        league_skipped += 1
                        continue

                    home_prob = float(row["market_home_prob"])
                    draw_prob = float(row["market_draw_prob"])
                    away_prob = float(row["market_away_prob"])

                    if home_prob <= 0 or draw_prob <= 0 or away_prob <= 0:
                        league_skipped += 1
                        continue

                    home_odds = round(1.0 / home_prob, 3)
                    draw_odds = round(1.0 / draw_prob, 3)
                    away_odds = round(1.0 / away_prob, 3)

                    snapshot = FixtureOddsSnapshot.objects.create(
                        bookmaker_source="fdcouk",
                        external_fixture_id=external_id,
                        league=league,
                        season=season,
                        home_team=home_canonical,
                        away_team=away_canonical,
                        commence_time=commence_time,
                        fetched_at=now,
                        market_type=FixtureOddsSnapshot.MarketType.MATCH_RESULT,
                        is_consensus_snapshot=True,
                    )

                    BookmakerQuote.objects.create(
                        snapshot=snapshot,
                        bookmaker=bookmaker,
                        home_odds=home_odds,
                        draw_odds=draw_odds,
                        away_odds=away_odds,
                        implied_home=home_prob,
                        implied_draw=draw_prob,
                        implied_away=away_prob,
                        devig_home=home_prob,
                        devig_draw=draw_prob,
                        devig_away=away_prob,
                        last_seen_at=None,
                    )

                    league_created += 1

            total_created += league_created
            total_skipped += league_skipped
            self.stdout.write(
                self.style.SUCCESS(f"  Created {league_created} snapshot(s), skipped {league_skipped}.")
            )

        self.stdout.write(
            self.style.SUCCESS(f"\nDone. {total_created} snapshot(s) created, {total_skipped} skipped in total.")
        )
