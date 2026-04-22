import pytest
from django.utils import timezone

from apps.sync_pipeline.models import PublishedSnapshot, SourceHealth, SyncRun
from apps.sync_pipeline.selectors import compute_surface_freshness, get_active_snapshot
from apps.sync_pipeline.services import (
    close_sync_run_failure,
    close_sync_run_success,
    mark_provider_session_invalid,
    open_sync_run,
    publish_snapshot,
    record_provider_request,
)
from common.constants import ProviderName, SyncStatus


@pytest.mark.django_db
class TestSyncRunLifecycle:
    def test_open_creates_running_run(self):
        run = open_sync_run('understat', 'player_stats', 'PL/2024')
        assert run.status == SyncStatus.RUNNING
        assert run.finished_at is None

    def test_close_success_sets_fields(self):
        run = open_sync_run('understat', 'player_stats', 'PL/2024')
        close_sync_run_success(run, rows_seen=100, rows_changed=10)
        run.refresh_from_db()
        assert run.status == SyncStatus.SUCCESS
        assert run.finished_at is not None
        assert run.rows_seen == 100
        assert run.rows_changed == 10

    def test_close_failure_sets_fields(self):
        run = open_sync_run('understat', 'player_stats', 'PL/2024')
        close_sync_run_failure(run, error_summary='timeout')
        run.refresh_from_db()
        assert run.status == SyncStatus.FAILED
        assert run.error_summary == 'timeout'

    def test_failure_increments_consecutive_failures(self):
        run = open_sync_run('understat', 'player_stats', 'PL/2024')
        close_sync_run_failure(run)
        health = SourceHealth.objects.get(provider='understat')
        assert health.consecutive_failures == 1

    def test_success_resets_consecutive_failures(self):
        run1 = open_sync_run('understat', 'player_stats', 'PL/2024')
        close_sync_run_failure(run1)
        run2 = open_sync_run('understat', 'player_stats', 'PL/2024')
        close_sync_run_success(run2)
        health = SourceHealth.objects.get(provider='understat')
        assert health.consecutive_failures == 0


@pytest.mark.django_db
class TestPublishSnapshot:
    def test_creates_active_snapshot(self):
        snap = publish_snapshot('livefootball', ['football_data'])
        assert snap.is_active is True
        assert snap.published_at is not None

    def test_replaces_previous_active(self):
        snap1 = publish_snapshot('livefootball', ['football_data'])
        snap2 = publish_snapshot('livefootball', ['football_data'])
        snap1.refresh_from_db()
        assert snap1.is_active is False
        assert snap2.is_active is True

    def test_only_one_active_per_surface(self):
        publish_snapshot('livefootball', ['football_data'])
        publish_snapshot('livefootball', ['football_data'])
        assert PublishedSnapshot.objects.filter(surface='livefootball', is_active=True).count() == 1

    def test_different_surfaces_independent(self):
        publish_snapshot('livefootball', ['football_data'])
        publish_snapshot('predictions', ['understat'])
        assert PublishedSnapshot.objects.filter(surface='livefootball', is_active=True).count() == 1
        assert PublishedSnapshot.objects.filter(surface='predictions', is_active=True).count() == 1


@pytest.mark.django_db
class TestGetActiveSnapshot:
    def test_returns_none_when_no_snapshot(self):
        assert get_active_snapshot('livefootball') is None

    def test_returns_active_snapshot(self):
        publish_snapshot('livefootball', ['football_data'])
        snap = get_active_snapshot('livefootball')
        assert snap is not None
        assert snap.is_active is True


@pytest.mark.django_db
class TestComputeSurfaceFreshness:
    def test_no_snapshot_returns_stale(self):
        fp = compute_surface_freshness('livefootball', sla_seconds=900)
        assert fp.is_stale is True
        assert fp.stale_reason == 'no_snapshot_published'

    def test_fresh_snapshot_within_sla(self):
        publish_snapshot('livefootball', ['football_data'])
        fp = compute_surface_freshness('livefootball', sla_seconds=900)
        assert fp.is_stale is False

    def test_degraded_when_consecutive_failures_at_threshold(self):
        publish_snapshot('livefootball', ['understat'])
        SourceHealth.objects.update_or_create(
            provider='understat',
            defaults={'window_started_at': timezone.now(), 'consecutive_failures': 3},
        )
        fp = compute_surface_freshness('livefootball', sla_seconds=900)
        assert fp.is_degraded is True


@pytest.mark.django_db
class TestSourceHealthHelpers:
    def test_record_provider_request_increments(self):
        record_provider_request('football_data', count=1)
        record_provider_request('football_data', count=1)
        health = SourceHealth.objects.get(provider='football_data')
        assert health.requests_used == 2

    def test_mark_session_invalid(self):
        mark_provider_session_invalid('sofascore')
        health = SourceHealth.objects.get(provider='sofascore')
        assert health.session_valid is False