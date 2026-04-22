import pytest
from django.utils import timezone

from apps.playerdata.models import ClubSeasonEnrichment, PlayerEnrichmentSnapshot, PlayerSeasonEnrichment
from apps.playerdata.publication import (
    publish_playerdata_snapshot,
    run_playerdata_publication,
    validate_playerdata_snapshot,
)
from apps.sync_pipeline.models import PublishedSnapshot
from apps.sync_pipeline.selectors import compute_surface_freshness


def _make_player():
    from apps.players.models import Player
    return Player.objects.create(
        first_name='Test',
        last_name='Player',
        display_name='Test Player',
        primary_position='CM',
    )


def _make_player_enrichment(player=None):
    if player is None:
        player = _make_player()
    return PlayerSeasonEnrichment.objects.create(
        player=player,
        provider='understat',
        season_label='2024',
        competition_code='EPL',
    )


@pytest.mark.django_db
class TestValidatePlayerdataSnapshot:
    def test_fails_when_no_enrichment_rows(self):
        valid, warnings = validate_playerdata_snapshot()
        assert valid is False
        assert any('ClubSeasonEnrichment' in w or 'PlayerSeasonEnrichment' in w for w in warnings)

    def test_passes_with_player_enrichment_only_and_emits_club_warning(self):
        _make_player_enrichment()
        valid, warnings = validate_playerdata_snapshot()
        assert valid is True
        assert any('ClubSeasonEnrichment' in w for w in warnings)


@pytest.mark.django_db
class TestPublishPlayerdataSnapshot:
    def test_creates_active_snapshot(self):
        snap = publish_playerdata_snapshot('all')
        assert snap.is_active is True
        assert snap.published_at is not None

    def test_replaces_previous_active(self):
        s1 = publish_playerdata_snapshot('all')
        s2 = publish_playerdata_snapshot('all')
        s1.refresh_from_db()
        assert s1.is_active is False
        assert s2.is_active is True

    def test_only_one_active_per_scope(self):
        for _ in range(3):
            publish_playerdata_snapshot('all')
        assert PlayerEnrichmentSnapshot.objects.filter(
            scope_key='all', is_active=True
        ).count() == 1


@pytest.mark.django_db
class TestRunPlayerdataPublication:
    def test_no_publication_when_no_data(self):
        run_playerdata_publication()
        assert PublishedSnapshot.objects.filter(surface='playerdata').count() == 0

    def test_publishes_when_data_exists(self):
        _make_player_enrichment()
        run_playerdata_publication()
        snap = PublishedSnapshot.objects.filter(surface='playerdata', is_active=True).first()
        assert snap is not None

    def test_freshness_not_stale_after_publication(self):
        _make_player_enrichment()
        run_playerdata_publication()
        fp = compute_surface_freshness('playerdata', sla_seconds=21600)
        assert fp.is_stale is False