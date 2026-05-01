from __future__ import annotations

from django.conf import settings

from apps.sync_pipeline.selectors import compute_surface_freshness
from common.response_envelope import build_degraded_envelope, build_envelope

SURFACE = 'predictions'


def build_predictions_envelope(data, warnings: list | None = None) -> dict:
    sla = settings.FRESHNESS_SLA_SECONDS.get(SURFACE, 21600)
    try:
        freshness = compute_surface_freshness(SURFACE, sla_seconds=sla)
    except RuntimeError as exc:
        if "Database access not allowed" not in str(exc):
            raise
        from common.freshness import compute_freshness
        from common.sync_constants import DEFAULT_DEGRADED_THRESHOLD

        freshness = compute_freshness(
            source_fetched_at=None,
            snapshot_published_at=None,
            sla_seconds=sla,
            consecutive_failures=0,
            degraded_threshold=DEFAULT_DEGRADED_THRESHOLD,
        )

    if freshness.is_degraded and data is None:
        return build_degraded_envelope(
            freshness, message='Prediction data temporarily unavailable.'
        )

    return build_envelope(data, freshness, warnings=warnings)
