from __future__ import annotations

import logging

from apps.clubs.models import Club, ClubPlayer
from apps.sync_pipeline.services import publish_snapshot
from common.constants import ProviderName
from common.utils import utcnow

_logger = logging.getLogger(__name__)

CLUBS_SURFACE = 'clubs'
CLUBS_PROVIDERS = [ProviderName.FOOTBALL_DATA]


def validate_club_snapshot() -> tuple[bool, list[str]]:
    warnings = []

    pro_club_count = Club.objects.filter(
        club_type=Club.ClubType.SYSTEM_PROFESSIONAL
    ).count()

    if pro_club_count == 0:
        warnings.append('No SYSTEM_PROFESSIONAL clubs found.')
        return False, warnings

    player_count = ClubPlayer.objects.filter(
        club__club_type=Club.ClubType.SYSTEM_PROFESSIONAL
    ).count()

    if player_count == 0:
        warnings.append('No ClubPlayer rows for SYSTEM_PROFESSIONAL clubs.')

    return True, warnings


def run_clubs_publication() -> None:
    valid, warnings = validate_club_snapshot()

    if not valid:
        _logger.warning('Clubs publication validation failed: %s', warnings)
        return

    if warnings:
        _logger.warning('Clubs publication proceeding with warnings: %s', warnings)

    snapshot = publish_snapshot(
        surface=CLUBS_SURFACE,
        source_provider_set=CLUBS_PROVIDERS,
        source_max_fetched_at=utcnow(),
        metadata={'warnings': warnings},
    )
    _logger.info('Clubs publication promoted: version=%s', snapshot.version)