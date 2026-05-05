"""
Management command for syncing Understat league season data

Runs a manual league-wide enrichment backfill for a selected Understat league and season
"""

from django.core.management.base import BaseCommand, CommandError

from apps.players.models import ExternalProvider
from services.providers.understat.sync import sync_understat_league_season


# Command for manually syncing one Understat league season
class Command(BaseCommand):
    help = 'Manual backfill and admin repair tool. Automated scheduling is handled by sync_pipeline.'

    # Register command line arguments for the sync
    def add_arguments(self, parser):
        parser.add_argument(
            "--league-code",
            dest="league_code",
            type=str,
            required=True,
            help="Understat league code, for example EPL.",
        )
        parser.add_argument(
            "--season",
            dest="season",
            type=str,
            required=True,
            help="Season label to sync, for example 2024.",
        )
        parser.add_argument(
            "--competition-code",
            dest="competition_code",
            type=str,
            default="",
            help="Optional competition code to store on enrichment rows. Defaults to league code.",
        )
        parser.add_argument(
            "--provider",
            dest="provider",
            type=str,
            default=ExternalProvider.UNDERSTAT,
            help="Provider to use. Phase 3 expects understat.",
        )

    # Run the league season sync and print a breakdown summary
    def handle(self, *args, **options):
        provider = (options["provider"] or "").strip()
        if provider != ExternalProvider.UNDERSTAT:
            raise CommandError(
                f"This command only supports provider='{ExternalProvider.UNDERSTAT}'. "
                f"Received '{provider}'."
            )

        league_code = str(options["league_code"]).strip()
        season_label = str(options["season"]).strip()
        competition_code = (options["competition_code"] or "").strip()

        self.stdout.write(
            self.style.NOTICE(
                f"Starting Understat league-season sync for league={league_code}, "
                f"season={season_label}, competition_code={competition_code or league_code}"
            )
        )

        try:
            result = sync_understat_league_season(
                league_code=league_code,
                season_label=season_label,
                competition_code=competition_code or None,
            )
        except Exception as exc:
            raise CommandError(f"Understat league-season sync failed: {exc}") from exc

        summary = result.get("summary", {})
        job = result.get("job")

        self.stdout.write(self.style.SUCCESS("Understat league-season sync completed."))
        self.stdout.write(f"League code: {league_code}")
        self.stdout.write(f"Season: {season_label}")
        self.stdout.write(f"Competition code: {competition_code or league_code}")
        self.stdout.write(f"Provider: {provider}")
        self.stdout.write(f"Job ID: {job.id if job else '-'}")
        self.stdout.write(f"Status: {summary.get('status', '-')}")
        self.stdout.write(f"Records processed: {summary.get('records_processed', 0)}")
        self.stdout.write(f"Records created: {summary.get('records_created', 0)}")
        self.stdout.write(f"Records updated: {summary.get('records_updated', 0)}")
        self.stdout.write(f"Error count: {summary.get('error_count', 0)}")

        metadata = summary.get("metadata", {}) or {}
        if metadata:
            self.stdout.write("")
            self.stdout.write("Breakdown:")
            for key in (
                "teams_seen",
                "clubs_matched",
                "clubs_unmatched",
                "club_sync_jobs_started",
                "league_code",
                "season_label",
                "competition_code",
            ):
                if key in metadata:
                    self.stdout.write(f"- {key}: {metadata[key]}")

        raw_error_summary = summary.get("raw_error_summary", "")
        if raw_error_summary:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Error summary:"))
            self.stdout.write(raw_error_summary)