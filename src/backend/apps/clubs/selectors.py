from __future__ import annotations

from django.conf import settings

from apps.sync_pipeline.selectors import compute_surface_freshness
from common.freshness import FreshnessPayload

CLUBS_SURFACE = 'clubs'


def get_club_freshness() -> FreshnessPayload:
    sla = settings.FRESHNESS_SLA_SECONDS.get(CLUBS_SURFACE, 21600)
    return compute_surface_freshness(CLUBS_SURFACE, sla_seconds=sla)