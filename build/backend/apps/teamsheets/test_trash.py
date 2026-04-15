from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from apps.clubs.models import Club
from apps.teamsheets.models import Teamsheet


def create_test_club(user, name='Teamsheet Trash Club'):
    return Club.objects.create(
        name=name,
        description='Teamsheet trash test club.',
        creator=user,
        visibility=Club.Visibility.PRIVATE,
        club_type=Club.ClubType.USER_FICTIONAL,
        fictional_basis=Club.FictionalBasis.ORIGINAL,
        directory_visibility=Club.DirectoryVisibility.LISTED,
        join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
        verification_status=Club.VerificationStatus.NOT_REQUIRED,
    )


class TeamsheetTrashModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='teamsheet-trash-owner@example.com',
            password='testpass123',
        )
        self.other_user = get_user_model().objects.create_user(
            email='teamsheet-trash-other@example.com',
            password='testpass123',
        )
        self.club = create_test_club(self.user)
        self.teamsheet = Teamsheet.objects.create(
            club=self.club,
            created_by=self.user,
            title='Trash Me',
            formation='442',
            opponent='Example FC',
        )

    @override_settings(TRASH_RETENTION_DAYS=7)
    def test_creator_can_move_teamsheet_to_trash(self):
        self.teamsheet.move_to_trash(self.user)
        self.teamsheet.refresh_from_db()

        self.assertTrue(self.teamsheet.is_trashed)
        self.assertIsNotNone(self.teamsheet.trashed_at)
        self.assertIsNotNone(self.teamsheet.trash_expires_at)
        self.assertEqual(self.teamsheet.trashed_by_id, self.user.id)

    def test_non_creator_cannot_move_teamsheet_to_trash(self):
        with self.assertRaises(ValidationError):
            self.teamsheet.move_to_trash(self.other_user)

    def test_restore_from_trash_clears_fields(self):
        self.teamsheet.move_to_trash(self.user)
        self.teamsheet.restore_from_trash(self.user)
        self.teamsheet.refresh_from_db()

        self.assertFalse(self.teamsheet.is_trashed)
        self.assertIsNone(self.teamsheet.trashed_at)
        self.assertIsNone(self.teamsheet.trash_expires_at)
        self.assertIsNone(self.teamsheet.trashed_by)

    @override_settings(TEAMSHEET_TRASH_LIMIT_PER_USER=1)
    def test_trash_limit_is_enforced(self):
        first = Teamsheet.objects.create(
            club=self.club,
            created_by=self.user,
            title='First',
            formation='442',
        )
        second = Teamsheet.objects.create(
            club=self.club,
            created_by=self.user,
            title='Second',
            formation='433',
        )

        first.move_to_trash(self.user)

        with self.assertRaises(ValidationError):
            second.move_to_trash(self.user)