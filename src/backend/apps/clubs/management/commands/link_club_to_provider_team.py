from django.core.management.base import BaseCommand, CommandError

from apps.clubs.models import Club
from services.providers.football_data.sync import link_club_to_provider_team


class Command(BaseCommand):
    help = "Create or update a provider-team mapping for a club."

    def add_arguments(self, parser):
        parser.add_argument(
            "--club-id",
            type=int,
            required=True,
        )
        parser.add_argument(
            "--provider-team-id",
            required=True,
        )
        parser.add_argument(
            "--provider",
            default="football_data",
        )
        parser.add_argument(
            "--display-name",
            default="",
        )

    def handle(self, *args, **options):
        club_id = options["club_id"]
        provider_team_id = str(options["provider_team_id"])
        provider = options["provider"]
        display_name = options["display_name"].strip()

        try:
            club = Club.objects.get(pk=club_id)
        except Club.DoesNotExist as exc:
            raise CommandError(f"Club with id {club_id} does not exist.") from exc

        self.stdout.write(
            f"Linking club {club.id} ({club.name}) to provider team "
            f"{provider}:{provider_team_id}"
        )

        try:
            result = link_club_to_provider_team(
                club=club,
                external_team_id=provider_team_id,
                provider=provider,
                provider_display_name=display_name,
            )
        except Exception as exc:
            raise CommandError(f"Failed to link provider team: {exc}") from exc

        job = result["job"]
        club_external_identity = result["club_external_identity"]
        summary = result["summary"]

        self.stdout.write(self.style.SUCCESS("Provider team link complete"))
        self.stdout.write(f"Club: {club.id} ({club.name})")
        self.stdout.write(f"Provider: {provider}")
        self.stdout.write(f"Provider team id: {club_external_identity.external_id}")
        self.stdout.write(
            f"Provider display name: {club_external_identity.provider_display_name or '-'}"
        )
        self.stdout.write(f"ClubExternalIdentity id: {club_external_identity.id}")
        self.stdout.write(f"Sync job id: {job.id}")
        self.stdout.write(f"Status: {summary.get('status')}")
        self.stdout.write(f"Records processed: {summary.get('records_processed', 0)}")
        self.stdout.write(f"Records created: {summary.get('records_created', 0)}")
        self.stdout.write(f"Records updated: {summary.get('records_updated', 0)}")
        self.stdout.write(f"Error count: {summary.get('error_count', 0)}")

        raw_error_summary = summary.get("raw_error_summary", "")
        if raw_error_summary:
            self.stdout.write("")
            self.stdout.write("Errors:")
            self.stdout.write(raw_error_summary)