from __future__ import annotations

from django.conf import settings

from apps.sync_pipeline.selectors import compute_surface_freshness
from common.freshness import compute_freshness
from common.response_envelope import build_degraded_envelope, build_envelope

SURFACE = 'predictions'
ODDS_SLA_SECONDS = 21600


def build_odds_envelope(data, league: str | None = None, warnings: list | None = None) -> dict:
    from apps.predictions.models import FixtureOddsSnapshot
    qs = FixtureOddsSnapshot.objects
    if league:
        qs = qs.filter(league=league)
    latest_fetched_at = qs.order_by('-fetched_at').values_list('fetched_at', flat=True).first()
    freshness = compute_freshness(
        source_fetched_at=latest_fetched_at,
        snapshot_published_at=latest_fetched_at,
        sla_seconds=ODDS_SLA_SECONDS,
    )
    return build_envelope(data, freshness, warnings=warnings)


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
