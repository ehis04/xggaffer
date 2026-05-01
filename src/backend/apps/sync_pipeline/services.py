from __future__ import annotations

from django.db import transaction

from apps.sync_pipeline.models import PublishedSnapshot, SourceHealth, SyncRun
from common.constants import PublishStatus, SyncStatus
from common.utils import utcnow

TRIGGERED_BY_CELERY = 'celery_beat'
TRIGGERED_BY_COMMAND = 'management_command'
TRIGGERED_BY_MANUAL = 'manual'


def open_sync_run(
    provider: str,
    dataset: str,
    scope_key: str,
    triggered_by: str = TRIGGERED_BY_CELERY,
) -> SyncRun:
    return SyncRun.objects.create(
        provider=provider,
        dataset=dataset,
        scope_key=scope_key,
        status=SyncStatus.RUNNING,
        triggered_by=triggered_by,
    )


def close_sync_run_success(
    run: SyncRun,
    rows_seen: int | None = None,
    rows_changed: int | None = None,
) -> SyncRun:
    run.status = SyncStatus.SUCCESS
    run.finished_at = utcnow()
    run.rows_seen = rows_seen
    run.rows_changed = rows_changed
    run.save(update_fields=['status', 'finished_at', 'rows_seen', 'rows_changed'])
    _reset_consecutive_failures(run.provider)
    return run


def close_sync_run_failure(run: SyncRun, error_summary: str = '') -> SyncRun:
    run.status = SyncStatus.FAILED
    run.finished_at = utcnow()
    run.error_summary = error_summary
    run.save(update_fields=['status', 'finished_at', 'error_summary'])
    _increment_consecutive_failures(run.provider)
    return run


def publish_snapshot(
    surface: str,
    source_provider_set: list[str],
    source_max_fetched_at=None,
    metadata: dict | None = None,
) -> PublishedSnapshot:
    now = utcnow()
    version = now.strftime('%Y%m%dT%H%M%SZ')

    with transaction.atomic():
        candidate = PublishedSnapshot.objects.create(
            surface=surface,
            version=version,
            status=PublishStatus.CANDIDATE,
            source_provider_set=source_provider_set,
            source_max_fetched_at=source_max_fetched_at,
            built_at=now,
            is_active=False,
            metadata=metadata or {},
        )

        (
            PublishedSnapshot.objects
            .select_for_update()
            .filter(surface=surface, is_active=True)
            .update(
                is_active=False,
                status=PublishStatus.INVALIDATED,
                invalidated_at=now,
            )
        )

        candidate.is_active = True
        candidate.status = PublishStatus.ACTIVE
        candidate.published_at = now
        candidate.save(update_fields=['is_active', 'status', 'published_at'])

    return candidate


def record_provider_request(provider: str, count: int = 1) -> None:
    now = utcnow()
    health, _ = SourceHealth.objects.get_or_create(
        provider=provider,
        defaults={'window_started_at': now, 'requests_used': 0},
    )
    window_age_hours = (now - health.window_started_at).total_seconds() / 3600
    if window_age_hours >= 24:
        health.window_started_at = now
        health.requests_used = count
    else:
        health.requests_used += count
    health.save(update_fields=['window_started_at', 'requests_used'])


def mark_provider_session_invalid(provider: str) -> None:
    now = utcnow()
    SourceHealth.objects.update_or_create(
        provider=provider,
        defaults={
            'session_valid': False,
            'last_error_at': now,
            'window_started_at': now,
        },
    )


def _increment_consecutive_failures(provider: str) -> None:
    now = utcnow()
    health, _ = SourceHealth.objects.get_or_create(
        provider=provider,
        defaults={'window_started_at': now},
    )
    health.consecutive_failures += 1
    health.last_error_at = now
    health.save(update_fields=['consecutive_failures', 'last_error_at'])


def _reset_consecutive_failures(provider: str) -> None:
    SourceHealth.objects.filter(provider=provider).update(consecutive_failures=0)