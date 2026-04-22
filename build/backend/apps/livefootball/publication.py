from __future__ import annotations

import logging

from apps.livefootball.models import Competition, CompetitionTableSnapshot
from apps.sync_pipeline.services import publish_snapshot
from common.constants import ProviderName

_logger = logging.getLogger(__name__)

LIVEFOOTBALL_SURFACE = 'livefootball'
LIVEFOOTBALL_PROVIDERS = [ProviderName.FOOTBALL_DATA, ProviderName.NATIVE_STATS]


def validate_livefootball_snapshot() -> tuple[bool, list[str]]:
    warnings = []

    if Competition.objects.count() == 0:
        warnings.append('No Competition rows found.')

    if CompetitionTableSnapshot.objects.count() == 0:
        warnings.append('No CompetitionTableSnapshot rows found.')

    if warnings:
        return False, warnings
    return True, []


def run_livefootball_publication(source_max_fetched_at=None) -> None:
    valid, warnings = validate_livefootball_snapshot()
    if not valid:
        _logger.warning('Livefootball publication validation failed: %s', warnings)
        return

    snapshot = publish_snapshot(
        surface=LIVEFOOTBALL_SURFACE,
        source_provider_set=LIVEFOOTBALL_PROVIDERS,
        source_max_fetched_at=source_max_fetched_at,
        metadata={'validation_warnings': warnings},
    )
    _logger.info('Livefootball publication promoted: version=%s', snapshot.version)