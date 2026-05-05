"""
Tests for player data publication workflow

Checks snapshot validation, active snapshot promotion, published snapshot creation, and freshness after publication
"""

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


# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------

# Create a basic player for enrichment tests
def _make_player():
    from apps.players.models import Player
    return Player.objects.create(
        first_name='Test',
        last_name='Player',
        display_name='Test Player',
        primary_position='CM',
    )


# Create a basic player season enrichment row
def _make_player_enrichment(player=None):
    if player is None:
        player = _make_player()
    return PlayerSeasonEnrichment.objects.create(
        player=player,
        provider='understat',
        season_label='2024',
        competition_code='EPL',
    )


# ---------------------------------------------------------------------------
# Snapshot validation tests
# ---------------------------------------------------------------------------

# Tests for player data snapshot validation
@pytest.mark.django_db
class TestValidatePlayerdataSnapshot:

    # Check validation fails when no enrichment rows exist
    def test_fails_when_no_enrichment_rows(self):
        valid, warnings = validate_playerdata_snapshot()
        assert valid is False
        assert any('ClubSeasonEnrichment' in w or 'PlayerSeasonEnrichment' in w for w in warnings)

    # Check validation passes with partial player-only coverage
    def test_passes_with_player_enrichment_only_and_emits_club_warning(self):
        _make_player_enrichment()
        valid, warnings = validate_playerdata_snapshot()
        assert valid is True
        assert any('ClubSeasonEnrichment' in w for w in warnings)


# ---------------------------------------------------------------------------
# Player data snapshot promotion tests
# ---------------------------------------------------------------------------

# Tests for active player enrichment snapshot promotion
@pytest.mark.django_db
class TestPublishPlayerdataSnapshot:

    # Check a new active snapshot is created
    def test_creates_active_snapshot(self):
        snap = publish_playerdata_snapshot('all')
        assert snap.is_active is True
        assert snap.published_at is not None

    # Check a new snapshot deactivates the previous active snapshot
    def test_replaces_previous_active(self):
        s1 = publish_playerdata_snapshot('all')
        s2 = publish_playerdata_snapshot('all')
        s1.refresh_from_db()
        assert s1.is_active is False
        assert s2.is_active is True

    # Check only one active snapshot exists per scope
    def test_only_one_active_per_scope(self):
        for _ in range(3):
            publish_playerdata_snapshot('all')
        assert PlayerEnrichmentSnapshot.objects.filter(
            scope_key='all', is_active=True
        ).count() == 1


# ---------------------------------------------------------------------------
# Player data publication tests
# ---------------------------------------------------------------------------

# Tests for end-to-end player data publication
@pytest.mark.django_db
class TestRunPlayerdataPublication:

    # Check publication is skipped when there is no enrichment data
    def test_no_publication_when_no_data(self):
        run_playerdata_publication()
        assert PublishedSnapshot.objects.filter(surface='playerdata').count() == 0

    # Check a published snapshot is created when enrichment data exists
    def test_publishes_when_data_exists(self):
        _make_player_enrichment()
        run_playerdata_publication()
        snap = PublishedSnapshot.objects.filter(surface='playerdata', is_active=True).first()
        assert snap is not None

    # Check freshness is not stale immediately after publication
    def test_freshness_not_stale_after_publication(self):
        _make_player_enrichment()
        run_playerdata_publication()
        fp = compute_surface_freshness('playerdata', sla_seconds=21600)
        assert fp.is_stale is False