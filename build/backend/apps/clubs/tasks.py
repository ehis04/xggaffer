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