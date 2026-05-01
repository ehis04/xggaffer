"""
Builds standard API response envelopes for live football data

Adds freshness metadata, warning support, data version details, and degraded responses when live football data is unavailable
"""

from __future__ import annotations

from django.conf import settings

from apps.sync_pipeline.selectors import compute_surface_freshness
from common.response_envelopes import build_degraded_envelope, build_envelope

SURFACE = 'livefootball'


# Build a live football response envelope with freshness and degradation handling
def build_livefootball_envelope(data, warnings: list | None = None, data_version: str | None = None) -> dict:
    sla = settings.FRESHNESS_SLA_SECONDS.get(SURFACE, 21600)
    freshness = compute_surface_freshness(SURFACE, sla_seconds=sla)

    if freshness.is_degraded and data is None:
        return build_degraded_envelope(
            freshness, message='Live football data temporarily unavailable.'
        )

    return build_envelope(data, freshness, warnings=warnings, data_version=data_version)