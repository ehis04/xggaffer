"""
Management command for syncing Understat player season data

Runs a manual player enrichment backfill for a selected player, season, and optional club or external player ID
"""

from django.core.management.base import BaseCommand, CommandError

from apps.clubs.models import Club
from apps.playerdata.models import PlayerSeasonEnrichment
from apps.players.models import ExternalProvider, Player
from services.providers.understat.sync import sync_understat_player_season


# Command for manually syncing one player season enrichment row
class Command(BaseCommand):
    help = 'Manual backfill and admin repair tool. Automated scheduling is handled by sync_pipeline.'

    # Register command line arguments for the sync
    def add_arguments(self, parser):
        parser.add_argument(
            "--player-id",
            dest="player_id",
            type=int,
            required=True,
            help="Internal canonical Player ID to sync.",
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
            help="Optional competition code, for example EPL.",
        )
        parser.add_argument(
            "--provider",
            dest="provider",
            type=str,
            default=ExternalProvider.UNDERSTAT,
            help="Provider to use. Phase 3 expects understat.",
        )
        parser.add_argument(
            "--external-player-id",
            dest="external_player_id",
            type=str,
            default="",
            help="Optional explicit Understat player id override.",
        )
        parser.add_argument(
            "--club-id",
            dest="club_id",
            type=int,
            default=None,
            help="Optional internal Club ID if you want to pin the enrichment row to a club.",
        )

    # Run the player season sync and print a verification summary
    def handle(self, *args, **options):
        provider = (options["provider"] or "").strip()
        if provider != ExternalProvider.UNDERSTAT:
            raise CommandError(
                f"This command only supports provider='{ExternalProvider.UNDERSTAT}'. "
                f"Received '{provider}'."
            )

        player_id = options["player_id"]
        season_label = str(options["season"]).strip()
        competition_code = (options["competition_code"] or "").strip()
        external_player_id = (options["external_player_id"] or "").strip()
        club_id = options["club_id"]

        try:
            player = Player.objects.get(pk=player_id)
        except Player.DoesNotExist as exc:
            raise CommandError(f"Player with id={player_id} does not exist.") from exc

        club = None
        if club_id is not None:
            try:
                club = Club.objects.get(pk=club_id)
            except Club.DoesNotExist as exc:
                raise CommandError(f"Club with id={club_id} does not exist.") from exc

        self.stdout.write(
            self.style.NOTICE(
                f"Starting Understat player-season sync for player={player.id} "
                f"({player.display_name or player.full_name}), season={season_label}, "
                f"competition_code={competition_code or '-'}"
            )
        )

        try:
            result = sync_understat_player_season(
                player=player,
                season_label=season_label,
                competition_code=competition_code or None,
                external_player_id=external_player_id or None,
                club=club,
            )
        except Exception as exc:
            raise CommandError(f"Understat player-season sync failed: {exc}") from exc

        summary = result.get("summary", {})
        enrichment = result.get("player_season_enrichment")
        job = result.get("job")

        self.stdout.write(self.style.SUCCESS("Understat player-season sync completed."))
        self.stdout.write(f"Player: {player.id} - {player.display_name or player.full_name}")
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
                f"club_id={enrichment.club_id}, "
                f"matches={enrichment.matches_played}, "
                f"goals={enrichment.goals}, "
                f"assists={enrichment.assists}, "
                f"xg={enrichment.xg}, "
                f"xa={enrichment.xa}, "
                f"last_synced_at={enrichment.last_synced_at}"
            )

        raw_error_summary = summary.get("raw_error_summary", "")
        if raw_error_summary:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Error summary:"))
            self.stdout.write(raw_error_summary)

        metadata = summary.get("metadata", {}) or {}
        if metadata:
            self.stdout.write("")
            self.stdout.write("Metadata:")
            for key, value in metadata.items():
                self.stdout.write(f"- {key}: {value}")

        latest_row = (
            PlayerSeasonEnrichment.objects.filter(
                player=player,
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