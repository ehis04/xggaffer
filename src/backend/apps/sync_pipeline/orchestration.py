from __future__ import annotations

import logging

_logger = logging.getLogger(__name__)

SURFACE_FOOTBALL_DATA = 'livefootball'
SURFACE_PREDICTIONS   = 'predictions'
SURFACE_PLAYERDATA    = 'playerdata'
SURFACE_CLUBS         = 'clubs'


def trigger_publication_rebuild(surface: str) -> None:
    if surface == SURFACE_FOOTBALL_DATA:
        from apps.livefootball.tasks import rebuild_livefootball_publication
        rebuild_livefootball_publication.delay()
        return
    if surface == SURFACE_PREDICTIONS:
        from apps.predictions.tasks import rebuild_predictions_publication_task
        rebuild_predictions_publication_task.delay()
        return
    if surface == SURFACE_PLAYERDATA:
        from apps.playerdata.tasks import rebuild_playerdata_publication_task
        rebuild_playerdata_publication_task.delay()
        return
    if surface == SURFACE_CLUBS:
        from apps.clubs.tasks import rebuild_club_publication_task
        rebuild_club_publication_task.delay()
        return
    _logger.info('Publication rebuild stub for surface=%s — not yet wired', surface)

def get_football_data_task_chain(dataset: str, scope: str):
    _logger.debug('football_data task chain: dataset=%s scope=%s', dataset, scope)
    return None


def get_understat_task_chain(scope: str):
    _logger.debug('understat task chain: scope=%s', scope)
    return None


def get_native_stats_task_chain(scope: str):
    _logger.debug('native_stats task chain: scope=%s', scope)
    return None