import logging

from celery import shared_task
from django.utils import timezone

from apps.clubs.models import Club
from apps.tactics.models import TacticsBoard
from apps.teamsheets.models import Teamsheet


logger = logging.getLogger(__name__)

@shared_task
def purge_expired_trash():
    """
    Permanently delete expired trashed rows across creator-owned content types.

    Deletion order:
    1. Teamsheets
    2. Tactics boards
    3. Clubs

    Clubs are deleted last because they are parent resources and may cascade
    related rows. Returning explicit model-level counts keeps the task output
    useful for logs and tests.
    """
    now = timezone.now()

    expired_teamsheets = Teamsheet.objects.filter(
        is_trashed=True,
        trash_expires_at__isnull=False,
        trash_expires_at__lte=now,
    )
    expired_tactics_boards = TacticsBoard.objects.filter(
        is_trashed=True,
        trash_expires_at__isnull=False,
        trash_expires_at__lte=now,
    )
    expired_clubs = Club.objects.filter(
        is_trashed=True,
        trash_expires_at__isnull=False,
        trash_expires_at__lte=now,
    )

    teamsheet_count = expired_teamsheets.count()
    tactics_board_count = expired_tactics_boards.count()
    club_count = expired_clubs.count()

    if teamsheet_count:
        expired_teamsheets.delete()

    if tactics_board_count:
        expired_tactics_boards.delete()

    if club_count:
        expired_clubs.delete()

    result = {
        'purged_teamsheets': teamsheet_count,
        'purged_tactics_boards': tactics_board_count,
        'purged_clubs': club_count,
        'purged_total': teamsheet_count + tactics_board_count + club_count,
        'run_at': now.isoformat(),
    }

    logger.info('Expired trash purge completed: %s', result)
    return result




@shared_task(name='apps.clubs.tasks.refresh_pro_club_squads_task', bind=True, max_retries=3)
def refresh_pro_club_squads_task(self):
    from apps.clubs.models import Club
    from apps.clubs.provider_mapping import assert_provider_managed
    from apps.sync_pipeline.services import (
        TRIGGERED_BY_CELERY,
        close_sync_run_failure,
        close_sync_run_success,
        open_sync_run,
        record_provider_request,
    )
    from common.constants import DatasetName, ProviderName

    pro_clubs = Club.objects.filter(
        club_type=Club.ClubType.SYSTEM_PROFESSIONAL,
    ).select_related('provider_link')

    for club in pro_clubs:
        if not hasattr(club, 'provider_link'):
            logger.warning('No ProClubProviderLink for club %s — skipping', club.id)
            continue

        assert_provider_managed(club)
        link = club.provider_link

        run = open_sync_run(
            ProviderName.FOOTBALL_DATA,
            DatasetName.SQUADS,
            f'club/{club.id}',
            triggered_by=TRIGGERED_BY_CELERY,
        )
        try:
            from services.providers.football_data.sync import sync_club_team_squad
            result = sync_club_team_squad(
                club=club,
                external_team_id=link.provider_team_id,
                provider=link.provider,
            )
            record_provider_request(ProviderName.FOOTBALL_DATA, count=1)
            summary = result.get('summary', {})
            seen = summary.get('records_processed', 0)
            changed = summary.get('records_created', 0) + summary.get('records_updated', 0)

            link.last_provider_sync_at = timezone.now()
            link.save(update_fields=['last_provider_sync_at'])

            close_sync_run_success(run, rows_seen=seen, rows_changed=changed)
        except Exception as exc:
            logger.warning('Squad sync failed for club %s: %s', club.id, exc)
            close_sync_run_failure(run, str(exc))

    rebuild_club_publication_task.delay()


@shared_task(name='apps.clubs.tasks.rebuild_club_publication_task', bind=True)
def rebuild_club_publication_task(self):
    from apps.clubs.publication import run_clubs_publication
    try:
        run_clubs_publication()
    except Exception as exc:
        logger.error('rebuild_club_publication_task failed: %s', exc)


@shared_task(name='apps.clubs.tasks.sync_pro_club_injuries_task', bind=True, max_retries=2)
def sync_pro_club_injuries_task(self):
    """
    Sync current injury/availability status for all pro clubs by scraping
    Transfermarkt injury pages for players that have a TM external identity.
    Runs twice daily to keep squad health data fresh.
    """
    from apps.clubs.models import Club
    from services.providers.transfermarkt.sync import TransfermarktSyncService
    from common.constants import ProviderName, DatasetName
    from apps.sync_pipeline.services import (
        TRIGGERED_BY_CELERY,
        close_sync_run_failure,
        close_sync_run_success,
        open_sync_run,
        record_provider_request,
    )

    pro_clubs = Club.objects.filter(club_type=Club.ClubType.SYSTEM_PROFESSIONAL)
    service = TransfermarktSyncService()

    for club in pro_clubs:
        run = open_sync_run(
            ProviderName.TRANSFERMARKT,
            DatasetName.INJURIES,
            f'club/{club.id}',
            triggered_by=TRIGGERED_BY_CELERY,
        )
        try:
            result = service.sync_club_player_injuries(
                club=club,
                triggered_by=TRIGGERED_BY_CELERY,
            )
            summary = result.get('summary', {})
            record_provider_request(ProviderName.TRANSFERMARKT, count=summary.get('records_processed', 0))
            close_sync_run_success(
                run,
                rows_seen=summary.get('records_processed', 0),
                rows_changed=summary.get('records_created', 0) + summary.get('records_updated', 0),
            )
        except Exception as exc:
            logger.warning('Injury sync failed for club %s: %s', club.id, exc)
            close_sync_run_failure(run, str(exc))