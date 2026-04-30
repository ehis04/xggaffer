from django.core.management.base import BaseCommand, CommandError

from apps.clubs.models import Club
from services.providers.transfermarkt.sync import TransfermarktSyncService


class Command(BaseCommand):
    help = (
        "Sync current injury/availability status for pro club players from Transfermarkt."
        " Pass --club-id to sync a single club or omit it to sync all pro clubs."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--club-id",
            type=int,
            required=False,
            help="Sync only this club (by primary key). Omit to sync all pro clubs.",
        )

    def handle(self, *args, **options):
        club_id = options.get("club_id")

        if club_id:
            try:
                clubs = [Club.objects.get(pk=club_id)]
            except Club.DoesNotExist as exc:
                raise CommandError(f"Club with id {club_id} does not exist.") from exc
        else:
            clubs = list(
                Club.objects.filter(club_type=Club.ClubType.SYSTEM_PROFESSIONAL)
            )

        if not clubs:
            self.stdout.write(self.style.WARNING("No pro clubs found; nothing to do."))
            return

        service = TransfermarktSyncService()
        total_created = 0
        total_updated = 0
        total_errors = 0

        for club in clubs:
            self.stdout.write(f"Syncing injuries for club {club.id} ({club.name}) …")
            try:
                result = service.sync_club_player_injuries(club, triggered_by="management_command")
            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(f"  Failed for club {club.id}: {exc}")
                )
                total_errors += 1
                continue

            summary = result["summary"]
            created = summary.get("records_created", 0)
            updated = summary.get("records_updated", 0)
            processed = summary.get("records_processed", 0)
            err = summary.get("error_count", 0)
            total_created += created
            total_updated += updated
            total_errors += err

            self.stdout.write(
                f"  processed={processed}  created={created}  updated={updated}  errors={err}"
            )
            if summary.get("raw_error_summary"):
                self.stderr.write(
                    self.style.WARNING(f"  Errors: {summary['raw_error_summary']}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. created={total_created}  updated={total_updated}  errors={total_errors}"
            )
        )
