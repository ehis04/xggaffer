from __future__ import annotations

from apps.sync_pipeline.models import PublishedSnapshot, SourceHealth
from common.freshness import FreshnessPayload, compute_freshness
from common.sync_constants import DEFAULT_DEGRADED_THRESHOLD


def get_active_snapshot(surface: str) -> PublishedSnapshot | None:
    return PublishedSnapshot.objects.filter(surface=surface, is_active=True).first()


def get_source_health(provider: str) -> SourceHealth | None:
    return SourceHealth.objects.filter(provider=provider).first()


def compute_surface_freshness(surface: str, sla_seconds: int) -> FreshnessPayload:
    snapshot = get_active_snapshot(surface)

    if snapshot is None:
        return compute_freshness(
            source_fetched_at=None,
            snapshot_published_at=None,
            sla_seconds=sla_seconds,
            consecutive_failures=0,
            degraded_threshold=DEFAULT_DEGRADED_THRESHOLD,
        )

    consecutive_failures = 0
    for provider in (snapshot.source_provider_set or []):
        health = get_source_health(provider)
        if health:
            consecutive_failures = max(consecutive_failures, health.consecutive_failures)

    return compute_freshness(
        source_fetched_at=snapshot.source_max_fetched_at,
        snapshot_published_at=snapshot.published_at,
        sla_seconds=sla_seconds,
        consecutive_failures=consecutive_failures,
        degraded_threshold=DEFAULT_DEGRADED_THRESHOLD,
    )