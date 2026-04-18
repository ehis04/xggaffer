from django.core.management.base import BaseCommand, CommandError

from services.providers.football_data.sync import sync_competition_teams


class Command(BaseCommand):
    help = "Sync football-data competition teams for provider identity refresh."

    def add_arguments(self, parser):
        parser.add_argument(
            "--competition-id",
            required=True,
        )
        parser.add_argument(
            "--provider",
            default="football_data",
        )

    def handle(self, *args, **options):
        competition_id = str(options["competition_id"])
        provider = options["provider"]

        self.stdout.write(
            f"Syncing competition teams for {provider}:{competition_id}"
        )

        try:
            result = sync_competition_teams(
                competition_external_id=competition_id,
                provider=provider,
            )
        except Exception as exc:
            raise CommandError(f"Failed to sync competition teams: {exc}") from exc

        job = result["job"]
        summary = result["summary"]
        metadata = summary.get("metadata", {})

        self.stdout.write(self.style.SUCCESS("Competition sync complete"))
        self.stdout.write(f"Provider: {provider}")
        self.stdout.write(f"Competition id: {competition_id}")
        self.stdout.write(f"Sync job id: {job.id}")
        self.stdout.write(f"Status: {summary.get('status')}")
        self.stdout.write(f"Records processed: {summary.get('records_processed', 0)}")
        self.stdout.write(f"Records created: {summary.get('records_created', 0)}")
        self.stdout.write(f"Records updated: {summary.get('records_updated', 0)}")
        self.stdout.write(
            "Matched club mappings updated: "
            f"{metadata.get('matched_club_mappings_updated', 0)}"
        )
        self.stdout.write(f"Error count: {summary.get('error_count', 0)}")

        raw_error_summary = summary.get("raw_error_summary", "")
        if raw_error_summary:
            self.stdout.write("")
            self.stdout.write("Errors:")
            self.stdout.write(raw_error_summary)