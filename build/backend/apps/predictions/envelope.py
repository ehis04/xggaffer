from __future__ import annotations

from django.conf import settings

from apps.sync_pipeline.selectors import compute_surface_freshness
from common.response_envelopes import build_degraded_envelope, build_envelope

SURFACE = 'predictions'


def build_predictions_envelope(data, warnings: list | None = None) -> dict:
    sla = settings.FRESHNESS_SLA_SECONDS.get(SURFACE, 21600)
    freshness = compute_surface_freshness(SURFACE, sla_seconds=sla)

    if freshness.is_degraded and data is None:
        return build_degraded_envelope(
            freshness, message='Prediction data temporarily unavailable.'
        )

    return build_envelope(data, freshness, warnings=warnings)