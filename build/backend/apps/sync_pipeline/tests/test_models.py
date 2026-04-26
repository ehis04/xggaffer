import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.sync_pipeline.models import PublishedSnapshot, SourceHealth, SyncRun
from common.constants import DatasetName, ProviderName, PublishStatus, SyncStatus


@pytest.mark.django_db
class TestSyncRun:
    def test_create_with_required_fields(self):
        run = SyncRun.objects.create(
            provider=ProviderName.UNDERSTAT,
            dataset=DatasetName.PLAYER_STATS,
            scope_key='PL/2024',
            status=SyncStatus.RUNNING,
            triggered_by='celery_beat',
        )
        assert run.pk is not None
        assert run.started_at is not None
        assert run.finished_at is None

    def test_str_representation(self):
        run = SyncRun(
            provider='understat',
            dataset='player_stats',
            scope_key='PL/2024',
            status='running',
        )
        assert 'understat' in str(run)
        assert 'PL/2024' in str(run)


@pytest.mark.django_db
class TestPublishedSnapshot:
    def test_only_one_active_per_surface(self):
        now = timezone.now()
        PublishedSnapshot.objects.create(
            surface='livefootball', version='v1', status=PublishStatus.ACTIVE,
            built_at=now, is_active=True,
        )
        with pytest.raises(IntegrityError):
            PublishedSnapshot.objects.create(
                surface='livefootball', version='v2', status=PublishStatus.ACTIVE,
                built_at=now, is_active=True,
            )

    def test_str_representation(self):
        snap = PublishedSnapshot(surface='predictions', version='20240101T000000Z', is_active=True, status='active')
        assert 'predictions' in str(snap)


@pytest.mark.django_db
class TestSourceHealth:
    def test_unique_per_provider(self):
        from django.db import IntegrityError
        SourceHealth.objects.create(provider=ProviderName.UNDERSTAT, window_started_at=timezone.now())
        with pytest.raises(IntegrityError):
            SourceHealth.objects.create(provider=ProviderName.UNDERSTAT, window_started_at=timezone.now())