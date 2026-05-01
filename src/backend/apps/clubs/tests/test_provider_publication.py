import pytest
from django.contrib.auth import get_user_model

from apps.clubs.models import Club, ProClubProviderLink
from apps.clubs.provider_mapping import assert_provider_managed, get_clubs_for_provider_sync
from apps.clubs.publication import run_clubs_publication, validate_club_snapshot
from apps.sync_pipeline.models import PublishedSnapshot
from apps.sync_pipeline.selectors import compute_surface_freshness

User = get_user_model()


def _make_system_user():
    user, _ = User.objects.get_or_create(
        email='system@xggaffer.test',
        defaults={'is_staff': True},
    )
    return user


def _make_pro_club(name='Arsenal FC'):
    user = _make_system_user()
    club = Club.objects.create(
        name=name,
        description=f'{name} professional club.',
        creator=user,
        club_type=Club.ClubType.SYSTEM_PROFESSIONAL,
        visibility=Club.Visibility.PUBLIC,
        directory_visibility=Club.DirectoryVisibility.LISTED,
        join_policy=Club.JoinPolicy.SYSTEM_MANAGED,
    )
    ProClubProviderLink.objects.create(
        club=club,
        provider='football_data',
        provider_team_id='57',
    )
    return club


def _make_user_club(name='My Sunday FC'):
    user, _ = User.objects.get_or_create(
        email='user@xggaffer.test',
        defaults={},
    )
    return Club.objects.create(
        name=name,
        description='User-managed club.',
        creator=user,
        club_type=Club.ClubType.USER_FICTIONAL,
        fictional_basis=Club.FictionalBasis.ORIGINAL,
        visibility=Club.Visibility.PRIVATE,
        directory_visibility=Club.DirectoryVisibility.LISTED,
        join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
        verification_status=Club.VerificationStatus.NOT_REQUIRED,
    )


@pytest.mark.django_db
class TestProviderWriteGuard:
    def test_assert_passes_for_pro_club(self):
        club = _make_pro_club()
        assert_provider_managed(club)

    def test_assert_fails_for_user_club(self):
        club = _make_user_club()
        with pytest.raises(AssertionError):
            assert_provider_managed(club)


@pytest.mark.django_db
class TestGetClubsForProviderSync:
    def test_returns_only_pro_clubs(self):
        pro = _make_pro_club('Pro Club')
        qs = get_clubs_for_provider_sync('football_data')
        ids = list(qs.values_list('id', flat=True))
        assert pro.id in ids

    def test_does_not_return_user_clubs(self):
        user_club = _make_user_club()
        qs = get_clubs_for_provider_sync('football_data')
        ids = list(qs.values_list('id', flat=True))
        assert user_club.id not in ids


@pytest.mark.django_db
class TestValidateClubSnapshot:
    def test_fails_with_no_pro_clubs(self):
        valid, warnings = validate_club_snapshot()
        assert valid is False

    def test_passes_with_pro_club(self):
        _make_pro_club()
        valid, warnings = validate_club_snapshot()
        assert valid is True


@pytest.mark.django_db
class TestRunClubsPublication:
    def test_no_publication_without_pro_clubs(self):
        run_clubs_publication()
        assert PublishedSnapshot.objects.filter(surface='clubs').count() == 0

    def test_publishes_with_pro_club(self):
        _make_pro_club()
        run_clubs_publication()
        snap = PublishedSnapshot.objects.filter(surface='clubs', is_active=True).first()
        assert snap is not None

    def test_freshness_not_stale_after_publication(self):
        _make_pro_club()
        run_clubs_publication()
        fp = compute_surface_freshness('clubs', sla_seconds=21600)
        assert fp.is_stale is False