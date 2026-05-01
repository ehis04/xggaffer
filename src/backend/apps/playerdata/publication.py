"""
Publishes validated player data snapshots

Checks player data coverage, promotes an active enrichment snapshot, publishes sync metadata, and clears cached player data responses
"""

from __future__ import annotations

import logging

from django.db import transaction

from apps.playerdata.models import (
    ClubSeasonEnrichment,
    PlayerEnrichmentSnapshot,
    PlayerSeasonEnrichment,
)
from apps.sync_pipeline.services import publish_snapshot
from common.cache_keys import clear_surface_cache
from common.constants import ProviderName
from common.utils import utcnow

_logger = logging.getLogger(__name__)

PLAYERDATA_SURFACE = 'playerdata'
PLAYERDATA_PROVIDERS = [ProviderName.UNDERSTAT]
SCOPE_ALL = 'all'


# Validate whether enough player data exists to publish a snapshot
def validate_playerdata_snapshot(scope_key: str = SCOPE_ALL) -> tuple[bool, list[str]]:
    warnings = []

    club_count = ClubSeasonEnrichment.objects.count()
    player_count = PlayerSeasonEnrichment.objects.count()

    if club_count == 0 and player_count == 0:
        warnings.append('No ClubSeasonEnrichment or PlayerSeasonEnrichment rows found.')
        return False, warnings

    if club_count == 0:
        warnings.append('No ClubSeasonEnrichment rows — partial coverage.')

    if player_count == 0:
        warnings.append('No PlayerSeasonEnrichment rows — partial coverage.')

    return True, warnings


# Promote a new active player enrichment snapshot for a scope
def publish_playerdata_snapshot(scope_key: str = SCOPE_ALL) -> PlayerEnrichmentSnapshot:
    now = utcnow()
    with transaction.atomic():
        PlayerEnrichmentSnapshot.objects.select_for_update().filter(
            scope_key=scope_key, is_active=True
        ).update(is_active=False)

        snapshot = PlayerEnrichmentSnapshot.objects.create(
            scope_key=scope_key,
            is_active=True,
            published_at=now,
        )

    return snapshot


# Run validation, snapshot promotion, sync publication, and cache clearing
def run_playerdata_publication(scope_key: str = SCOPE_ALL) -> None:
    valid, warnings = validate_playerdata_snapshot(scope_key)

    if not valid:
        _logger.warning('Playerdata publication validation failed: %s', warnings)
        return

    if warnings:
        _logger.warning('Playerdata publication proceeding with warnings: %s', warnings)

    publish_playerdata_snapshot(scope_key)

    snapshot = publish_snapshot(
        surface=PLAYERDATA_SURFACE,
        source_provider_set=PLAYERDATA_PROVIDERS,
        source_max_fetched_at=utcnow(),
        metadata={'scope_key': scope_key, 'warnings': warnings},
    )
    cleared = clear_surface_cache(PLAYERDATA_SURFACE)
    _logger.info('Playerdata publication promoted: version=%s cleared=%s', snapshot.version, cleared)