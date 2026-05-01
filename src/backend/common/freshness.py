from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from common.utils import age_seconds, utcnow


@dataclass(frozen=True)
class FreshnessPayload:
    __slots__ = (
        'source_fetched_at',
        'snapshot_published_at',
        'is_stale',
        'is_degraded',
        'stale_reason',
        'sla_seconds',
    )

    source_fetched_at: Optional[object]      # datetime | None
    snapshot_published_at: Optional[object]  # datetime | None
    is_stale: bool
    is_degraded: bool
    stale_reason: Optional[str]
    sla_seconds: int

    def to_dict(self) -> dict:
        from common.utils import iso_or_none
        return {
            'source_fetched_at': iso_or_none(self.source_fetched_at),
            'snapshot_published_at': iso_or_none(self.snapshot_published_at),
            'is_stale': self.is_stale,
            'is_degraded': self.is_degraded,
            'stale_reason': self.stale_reason,
            'sla_seconds': self.sla_seconds,
        }


def is_within_sla(published_at, sla_seconds: int) -> bool:
    if published_at is None:
        return False
    return age_seconds(published_at) <= sla_seconds


def compute_freshness(
    source_fetched_at,
    snapshot_published_at,
    sla_seconds: int,
    consecutive_failures: int = 0,
    degraded_threshold: int = 3,
) -> FreshnessPayload:
    is_degraded = consecutive_failures >= degraded_threshold

    if snapshot_published_at is None:
        return FreshnessPayload(
            source_fetched_at=source_fetched_at,
            snapshot_published_at=None,
            is_stale=True,
            is_degraded=is_degraded,
            stale_reason='no_snapshot_published',
            sla_seconds=sla_seconds,
        )

    stale = not is_within_sla(snapshot_published_at, sla_seconds)
    stale_reason = 'sla_exceeded' if stale else None

    return FreshnessPayload(
        source_fetched_at=source_fetched_at,
        snapshot_published_at=snapshot_published_at,
        is_stale=stale,
        is_degraded=is_degraded,
        stale_reason=stale_reason,
        sla_seconds=sla_seconds,
    )