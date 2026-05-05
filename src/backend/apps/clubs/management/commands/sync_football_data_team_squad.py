from django.core.management.base import BaseCommand, CommandError

from apps.clubs.models import Club
from services.providers.football_data.sync import sync_club_team_squad


class Command(BaseCommand):
    help = "Sync a club squad from football-data using a mapped or explicit provider team id."

    def add_arguments(self, parser):
        parser.add_argument(
            "--club-id",
            type=int,
            required=True,
        )
        parser.add_argument(
            "--provider-team-id",
            required=False,
        )
        parser.add_argument(
            "--provider",
            default="football_data",
        )

    def handle(self, *args, **options):
        club_id = options["club_id"]
        provider_team_id = options.get("provider_team_id")
        provider = options["provider"]

        try:
            club = Club.objects.get(pk=club_id)
        except Club.DoesNotExist as exc:
            raise CommandError(f"Club with id {club_id} does not exist.") from exc

        if provider_team_id:
            self.stdout.write(
                f"Syncing squad for club {club.id} ({club.name}) using explicit "
                f"provider team id {provider}:{provider_team_id}"
            )
        else:
            self.stdout.write(
                f"Syncing squad for club {club.id} ({club.name}) using existing "
                f"{provider} club mapping"
            )

        try:
            result = sync_club_team_squad(
                club=club,
                external_team_id=provider_team_id,
                provider=provider,
            )
        except Exception as exc:
            raise CommandError(f"Failed to sync squad: {exc}") from exc

        job = result["job"]
        summary = result["summary"]
        metadata = summary.get("metadata", {})

        self.stdout.write(self.style.SUCCESS("Squad sync complete"))
        self.stdout.write(f"Club: {club.id} ({club.name})")
        self.stdout.write(f"Provider: {provider}")
        self.stdout.write(
            f"Provider team id: {metadata.get('provider_team_id') or provider_team_id or '-'}"
        )
        self.stdout.write(f"Sync job id: {job.id}")
        self.stdout.write(f"Status: {summary.get('status')}")
        self.stdout.write(f"Records processed: {summary.get('records_processed', 0)}")
        self.stdout.write(f"Records created: {summary.get('records_created', 0)}")
        self.stdout.write(f"Records updated: {summary.get('records_updated', 0)}")
        self.stdout.write(f"Players created: {metadata.get('players_created', 0)}")
        self.stdout.write(f"Players updated: {metadata.get('players_updated', 0)}")
        self.stdout.write(
            "Player external identities created: "
            f"{metadata.get('player_external_identities_created', 0)}"
        )
        self.stdout.write(
            "Player external identities updated: "
            f"{metadata.get('player_external_identities_updated', 0)}"
        )
        self.stdout.write(
            f"Club players created: {metadata.get('club_players_created', 0)}"
        )
        self.stdout.write(
            f"Club players updated: {metadata.get('club_players_updated', 0)}"
        )
        self.stdout.write(f"Error count: {summary.get('error_count', 0)}")

        raw_error_summary = summary.get("raw_error_summary", "")
        if raw_error_summary:
            self.stdout.write("")
            self.stdout.write("Errors:")
            self.stdout.write(raw_error_summary)