import pytest
from datetime import timedelta
from django.utils import timezone
from django.test import Client
from django.contrib.auth import get_user_model

from apps.sync_pipeline.models import SyncRun
from apps.sync_pipeline.tasks import aggregate_sync_health_task
from apps.sync_pipeline.services import open_sync_run
from common.constants import DatasetName, ProviderName, SyncStatus

User = get_user_model()


def make_staff_client():
    user, _ = User.objects.get_or_create(
        email='staff@xggaffer.test',
        defaults={'is_staff': True, 'is_active': True},
    )
    user.set_password('testpass')
    user.save()
    client = Client()
    client.force_login(user)
    return client


def make_non_staff_client():
    user, _ = User.objects.get_or_create(
        email='nostaff@xggaffer.test',
        defaults={'is_staff': False, 'is_active': True},
    )
    user.set_password('testpass')
    user.save()
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestStuckRunningCleanup:
    def test_marks_old_running_runs_as_failed(self):
        run = SyncRun.objects.create(
            provider=ProviderName.UNDERSTAT,
            dataset=DatasetName.PLAYER_STATS,
            scope_key='EPL/2024',
            status=SyncStatus.RUNNING,
            triggered_by='celery_beat',
        )
        run.started_at = timezone.now() - timedelta(hours=3)
        run.save(update_fields=['started_at'])

        aggregate_sync_health_task.apply()

        run.refresh_from_db()
        assert run.status == SyncStatus.FAILED
        assert 'stuck' in run.error_summary.lower() or 'auto-marked' in run.error_summary.lower()

    def test_does_not_touch_recent_running_runs(self):
        run = open_sync_run(ProviderName.UNDERSTAT, DatasetName.PLAYER_STATS, 'EPL/2024')
        aggregate_sync_health_task.apply()
        run.refresh_from_db()
        assert run.status == SyncStatus.RUNNING


@pytest.mark.django_db
class TestFailedPublicationPreservesActiveSnapshot:
    def test_active_snapshot_unchanged_after_failed_validation(self):
        from apps.sync_pipeline.services import publish_snapshot
        from apps.sync_pipeline.selectors import get_active_snapshot
        from apps.livefootball.publication import run_livefootball_publication

        first = publish_snapshot('livefootball', ['football_data'])
        assert first.is_active is True

        run_livefootball_publication()

        current = get_active_snapshot('livefootball')
        assert current.id == first.id


@pytest.mark.django_db
class TestSofaScoreSessionExpiryPath:
    def test_invalid_session_skips_without_run(self):
        from apps.sync_pipeline.models import SourceHealth
        from apps.sync_pipeline.tasks import refresh_sofascore_cycle_task

        SourceHealth.objects.update_or_create(
            provider=ProviderName.SOFASCORE,
            defaults={
                'window_started_at': timezone.now(),
                'session_valid': False,
            },
        )
        refresh_sofascore_cycle_task.apply()
        assert SyncRun.objects.filter(provider=ProviderName.SOFASCORE).count() == 0


@pytest.mark.django_db
class TestHealthEndpoints:
    def test_health_endpoint_requires_staff(self):
        client = make_non_staff_client()
        response = client.get('/internal/sync/health/')
        assert response.status_code == 403

    def test_health_endpoint_returns_all_surfaces(self):
        client = make_staff_client()
        response = client.get('/internal/sync/health/')
        assert response.status_code == 200
        data = response.json()
        assert 'surfaces' in data
        surface_names = [s['surface'] for s in data['surfaces']]
        for surface in ['livefootball', 'predictions', 'playerdata', 'clubs']:
            assert surface in surface_names

    def test_surface_health_endpoint(self):
        client = make_staff_client()
        response = client.get('/internal/sync/health/livefootball/')
        assert response.status_code == 200
        data = response.json()
        assert 'freshness' in data
        assert 'surface' in data

    def test_unknown_surface_returns_404(self):
        client = make_staff_client()
        response = client.get('/internal/sync/health/notasurface/')
        assert response.status_code == 404

    def test_snapshots_endpoint_returns_all_surfaces(self):
        client = make_staff_client()
        response = client.get('/internal/sync/snapshots/')
        assert response.status_code == 200
        data = response.json()
        assert 'snapshots' in data
        for surface in ['livefootball', 'predictions', 'playerdata', 'clubs']:
            assert surface in data['snapshots']