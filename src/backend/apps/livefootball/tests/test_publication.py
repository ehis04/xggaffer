import pytest
from django.utils import timezone

from apps.livefootball.models import NativeStatsSnapshot
from apps.livefootball.publication import run_livefootball_publication, validate_livefootball_snapshot
from apps.livefootball.services.native_stats import persist_native_stats_snapshot
from apps.sync_pipeline.models import PublishedSnapshot
from apps.sync_pipeline.selectors import compute_surface_freshness, get_active_snapshot


def _make_valid_livefootball_data():
    from apps.livefootball.models import Competition, CompetitionTableSnapshot
    comp = Competition.objects.create(
        provider='football_data',
        name='Test League',
        code='TL',
        external_id='999',
    )
    CompetitionTableSnapshot.objects.create(
        competition=comp,
        season_label='2024',
        matchday=1,
        synced_at=timezone.now(),
    )
    return comp


@pytest.mark.django_db
class TestValidateLivefootballSnapshot:
    def test_fails_with_no_competitions(self):
        valid, warnings = validate_livefootball_snapshot()
        assert valid is False
        assert any('Competition' in w for w in warnings)

    def test_passes_with_competitions_and_table(self):
        _make_valid_livefootball_data()
        valid, warnings = validate_livefootball_snapshot()
        assert valid is True
        assert warnings == []


@pytest.mark.django_db
class TestRunLivefootballPublication:
    def test_no_publication_when_validation_fails(self):
        run_livefootball_publication()
        assert PublishedSnapshot.objects.filter(surface='livefootball').count() == 0

    def test_publishes_when_valid(self):
        _make_valid_livefootball_data()
        run_livefootball_publication()
        snap = get_active_snapshot('livefootball')
        assert snap is not None
        assert snap.is_active is True

    def test_second_publication_replaces_first(self):
        _make_valid_livefootball_data()
        run_livefootball_publication()
        run_livefootball_publication()
        assert PublishedSnapshot.objects.filter(surface='livefootball', is_active=True).count() == 1


@pytest.mark.django_db
class TestPersistNativeStatsSnapshot:
    def test_creates_active_snapshot(self):
        persist_native_stats_snapshot('homepage', {'top_performing_teams': []})
        snap = NativeStatsSnapshot.objects.filter(surface_key='homepage', is_active=True).first()
        assert snap is not None
        assert snap.payload == {'top_performing_teams': []}

    def test_replaces_previous_active(self):
        persist_native_stats_snapshot('homepage', {'top_performing_teams': ['a']})
        persist_native_stats_snapshot('homepage', {'top_performing_teams': ['b']})
        active = NativeStatsSnapshot.objects.filter(surface_key='homepage', is_active=True)
        assert active.count() == 1
        assert active.first().payload == {'top_performing_teams': ['b']}


@pytest.mark.django_db
class TestFreshnessAfterPublication:
    def test_freshness_is_not_stale_after_publication(self):
        _make_valid_livefootball_data()
        run_livefootball_publication()
        fp = compute_surface_freshness('livefootball', sla_seconds=1800)
        assert fp.is_stale is False
        assert fp.snapshot_published_at is not None