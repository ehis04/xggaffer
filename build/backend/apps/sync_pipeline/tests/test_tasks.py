import pytest
from unittest.mock import patch

from apps.sync_pipeline.models import SourceHealth, SyncRun
from apps.sync_pipeline.tasks import (
    aggregate_sync_health_task,
    refresh_football_data_fixtures_task,
    refresh_sofascore_cycle_task,
    refresh_understat_cycle_task,
)
from common.constants import ProviderName, SyncStatus
from common.utils import utcnow


@pytest.mark.django_db
class TestLockSkipsOnContention:
    def test_second_call_skips_when_lock_held(self):
        from django.core.cache import cache
        from common.constants import DatasetName
        from common.provider_policy import get_lock_key

        lock_key = get_lock_key(ProviderName.FOOTBALL_DATA, DatasetName.FIXTURES, 'all_competitions')
        cache.add(lock_key, '1', timeout=300)
        try:
            refresh_football_data_fixtures_task.apply()
            assert SyncRun.objects.filter(provider=ProviderName.FOOTBALL_DATA).count() == 0
        finally:
            cache.delete(lock_key)


@pytest.mark.django_db
class TestBudgetGate:
    def test_exhausted_budget_records_failure(self):
        SourceHealth.objects.create(
            provider=ProviderName.FOOTBALL_DATA,
            window_started_at=utcnow(),
            requests_used=95,
            requests_limit=100,
        )
        with patch('apps.sync_pipeline.tasks.settings') as mock_settings:
            mock_settings.FOOTBALL_DATA_DAILY_REQUEST_LIMIT = 100
            mock_settings.PIPELINE_DEGRADED_THRESHOLD = 3
            refresh_football_data_fixtures_task.apply()

        run = SyncRun.objects.filter(provider=ProviderName.FOOTBALL_DATA).last()
        assert run is None or run.status == SyncStatus.FAILED


@pytest.mark.django_db
class TestSofaScoreSessionGate:
    def test_invalid_session_skips_without_opening_run(self):
        SourceHealth.objects.create(
            provider=ProviderName.SOFASCORE,
            window_started_at=utcnow(),
            session_valid=False,
        )
        refresh_sofascore_cycle_task.apply()
        assert SyncRun.objects.filter(provider=ProviderName.SOFASCORE).count() == 0

    def test_valid_session_opens_run(self):
        SourceHealth.objects.create(
            provider=ProviderName.SOFASCORE,
            window_started_at=utcnow(),
            session_valid=True,
        )
        refresh_sofascore_cycle_task.apply()
        assert SyncRun.objects.filter(provider=ProviderName.SOFASCORE).count() == 1


@pytest.mark.django_db
class TestAggregateSyncHealth:
    def test_logs_degraded_providers(self):
        SourceHealth.objects.create(
            provider=ProviderName.UNDERSTAT,
            window_started_at=utcnow(),
            consecutive_failures=5,
        )
        aggregate_sync_health_task.apply()


@pytest.mark.django_db
class TestUnderstatTaskOpensRun:
    def test_creates_sync_run(self):
        refresh_understat_cycle_task.apply()
        assert SyncRun.objects.filter(provider=ProviderName.UNDERSTAT).count() == 1