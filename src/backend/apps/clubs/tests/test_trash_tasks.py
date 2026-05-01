from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.clubs.models import Club, ClubMembership
from apps.clubs.tasks import purge_expired_trash
from apps.tactics.services import create_board_with_initial_frame
from apps.teamsheets.models import Teamsheet


def create_test_club(
    *,
    creator,
    name,
    visibility=Club.Visibility.PRIVATE,
    directory_visibility=None,
):
    club = Club.objects.create(
        name=name,
        description=f'{name} description',
        creator=creator,
        visibility=visibility,
        club_type=Club.ClubType.USER_FICTIONAL,
        fictional_basis=Club.FictionalBasis.ORIGINAL,
        directory_visibility=directory_visibility or Club.DirectoryVisibility.LISTED,
        join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
        verification_status=Club.VerificationStatus.NOT_REQUIRED,
    )

    ClubMembership.objects.create(
        user=creator,
        club=club,
        role=ClubMembership.Role.OWNER,
        is_active=True,
    )
    return club


class PurgeExpiredTrashTaskTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='trash-task-owner@example.com',
            password='testpass123',
        )

        self.club = create_test_club(
            creator=self.user,
            name='Active Parent Club',
        )

    def _expire_model_instance(self, instance):
        instance.is_trashed = True
        instance.trashed_at = timezone.now() - timedelta(days=8)
        instance.trash_expires_at = timezone.now() - timedelta(days=1)
        instance.trashed_by = self.user
        instance.save(
            update_fields=[
                'is_trashed',
                'trashed_at',
                'trash_expires_at',
                'trashed_by',
                'updated_at',
            ]
        )

    def _future_model_instance(self, instance):
        instance.is_trashed = True
        instance.trashed_at = timezone.now()
        instance.trash_expires_at = timezone.now() + timedelta(days=3)
        instance.trashed_by = self.user
        instance.save(
            update_fields=[
                'is_trashed',
                'trashed_at',
                'trash_expires_at',
                'trashed_by',
                'updated_at',
            ]
        )

    def test_purge_expired_trash_deletes_only_expired_rows(self):
        expired_teamsheet = Teamsheet.objects.create(
            club=self.club,
            created_by=self.user,
            title='Expired Teamsheet',
            formation='442',
        )
        active_teamsheet = Teamsheet.objects.create(
            club=self.club,
            created_by=self.user,
            title='Unexpired Teamsheet',
            formation='433',
        )

        expired_board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.user,
            title='Expired Board',
        )
        active_board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.user,
            title='Unexpired Board',
        )

        expired_club = create_test_club(
            creator=self.user,
            name='Expired Club',
        )
        active_club = create_test_club(
            creator=self.user,
            name='Unexpired Club',
        )

        self._expire_model_instance(expired_teamsheet)
        self._future_model_instance(active_teamsheet)

        self._expire_model_instance(expired_board)
        self._future_model_instance(active_board)

        self._expire_model_instance(expired_club)
        self._future_model_instance(active_club)

        result = purge_expired_trash()

        self.assertEqual(result['purged_teamsheets'], 1)
        self.assertEqual(result['purged_tactics_boards'], 1)
        self.assertEqual(result['purged_clubs'], 1)
        self.assertEqual(result['purged_total'], 3)

        self.assertFalse(
            Teamsheet.objects.filter(id=expired_teamsheet.id).exists()
        )
        self.assertTrue(
            Teamsheet.objects.filter(id=active_teamsheet.id).exists()
        )

        self.assertFalse(
            expired_board.__class__.objects.filter(id=expired_board.id).exists()
        )
        self.assertTrue(
            active_board.__class__.objects.filter(id=active_board.id).exists()
        )

        self.assertFalse(
            Club.objects.filter(id=expired_club.id).exists()
        )
        self.assertTrue(
            Club.objects.filter(id=active_club.id).exists()
        )

    def test_purge_expired_trash_returns_zero_counts_when_nothing_has_expired(self):
        teamsheet = Teamsheet.objects.create(
            club=self.club,
            created_by=self.user,
            title='Future Teamsheet',
            formation='442',
        )
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.user,
            title='Future Board',
        )
        extra_club = create_test_club(
            creator=self.user,
            name='Future Club',
        )

        self._future_model_instance(teamsheet)
        self._future_model_instance(board)
        self._future_model_instance(extra_club)

        result = purge_expired_trash()

        self.assertEqual(result['purged_teamsheets'], 0)
        self.assertEqual(result['purged_tactics_boards'], 0)
        self.assertEqual(result['purged_clubs'], 0)
        self.assertEqual(result['purged_total'], 0)

        self.assertTrue(Teamsheet.objects.filter(id=teamsheet.id).exists())
        self.assertTrue(board.__class__.objects.filter(id=board.id).exists())
        self.assertTrue(Club.objects.filter(id=extra_club.id).exists())