"""
Management command for syncing Understat club season data

Runs a manual club season enrichment backfill for a selected club, season, and optional competition code
"""

from django.core.management.base import BaseCommand, CommandError

from apps.clubs.models import Club
from apps.playerdata.models import ClubSeasonEnrichment
from apps.players.models import ExternalProvider
from services.providers.understat.sync import sync_understat_club_season


# Command for manually syncing one club season enrichment row
class Command(BaseCommand):
    help = 'Manual backfill and admin repair tool. Automated scheduling is handled by sync_pipeline.'

    # Register command line arguments for the sync
    def add_arguments(self, parser):
        parser.add_argument(
            "--club-id",
            type=int,
            required=True,
            help="Internal Club ID to sync.",
        )
        parser.add_argument(
            "--season",
            type=str,
            required=True,
            help="Season label to sync, e.g. 2024 or 2024/2025 depending on your local convention.",
        )
        parser.add_argument(
            "--competition-code",
            type=str,
            default="",
            help="Optional competition code, e.g. EPL.",
        )
        parser.add_argument(
            "--provider",
            type=str,
            default=ExternalProvider.UNDERSTAT,
            help="Provider to use. Phase 3 expects understat.",
        )
        parser.add_argument(
            "--external-team-id",
            type=str,
            default="",
            help="Optional explicit Understat team slug override, e.g. Real_Madrid. Common aliases like real-madrid are accepted.",
        )

    # Run the club season sync and print a verification summary
    def handle(self, *args, **options):
        provider = (options["provider"] or "").strip()
        if provider != ExternalProvider.UNDERSTAT:
            raise CommandError(
                f"This command only supports provider='{ExternalProvider.UNDERSTAT}'. "
                f"Received '{provider}'."
            )

        club_id = options["club_id"]
        season_label = str(options["season"]).strip()
        competition_code = (options["competition_code"] or "").strip()
        external_team_id = (options["external_team_id"] or "").strip()

        try:
            club = Club.objects.get(pk=club_id)
        except Club.DoesNotExist as exc:
            raise CommandError(f"Club with id={club_id} does not exist.") from exc

        self.stdout.write(
            self.style.NOTICE(
                f"Starting Understat club-season sync for club={club.id} "
                f"({club.name}), season={season_label}, "
                f"competition_code={competition_code or '-'}"
            )
        )

        try:
            result = sync_understat_club_season(
                club=club,
                season_label=season_label,
                competition_code=competition_code or None,
                external_team_id=external_team_id or None,
            )
        except Exception as exc:
            raise CommandError(f"Understat club-season sync failed: {exc}") from exc

        summary = result.get("summary", {})
        enrichment = result.get("club_season_enrichment")
        job = result.get("job")

        self.stdout.write(self.style.SUCCESS("Understat club-season sync completed."))

        self.stdout.write(f"Club: {club.id} - {club.name}")
        self.stdout.write(f"Season: {season_label}")
        self.stdout.write(f"Competition code: {competition_code or '-'}")
        self.stdout.write(f"Provider: {provider}")
        self.stdout.write(f"Job ID: {job.id if job else '-'}")
        self.stdout.write(f"Status: {summary.get('status', '-')}")
        self.stdout.write(f"Records processed: {summary.get('records_processed', 0)}")
        self.stdout.write(f"Records created: {summary.get('records_created', 0)}")
        self.stdout.write(f"Records updated: {summary.get('records_updated', 0)}")
        self.stdout.write(f"Error count: {summary.get('error_count', 0)}")

        if enrichment:
            self.stdout.write(
                "Enrichment row: "
                f"id={enrichment.id}, "
                f"matches={enrichment.matches_played}, "
                f"xg={enrichment.xg}, "
                f"xga={enrichment.xga}, "
                f"npxg={enrichment.npxg}, "
                f"last_synced_at={enrichment.last_synced_at}"
            )

        raw_error_summary = summary.get("raw_error_summary", "")
        if raw_error_summary:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Error summary:"))
            self.stdout.write(raw_error_summary)

        metadata = summary.get("metadata", {})
        if metadata:
            self.stdout.write("")
            self.stdout.write("Metadata:")
            for key, value in metadata.items():
                self.stdout.write(f"- {key}: {value}")

        latest_row = (
            ClubSeasonEnrichment.objects.filter(
                club=club,
                provider=ExternalProvider.UNDERSTAT,
                season_label=season_label,
                competition_code=competition_code or "",
            )
            .order_by("-updated_at")
            .first()
        )

        if latest_row:
            self.stdout.write("")
            self.stdout.write(
                "Verified stored enrichment: "
                f"id={latest_row.id}, "
                f"provider={latest_row.provider}, "
                f"season={latest_row.season_label}, "
                f"competition={latest_row.competition_code or '-'}"
            )