from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from apps.clubs.models import Club
from apps.clubs.permissions import CanManageOwnClubTrash, user_can_manage_club_trash


class DummyView:
    kwargs = {}


class ClubTrashModelTests(TestCase):
    def setUp(self):
        self.creator = get_user_model().objects.create_user(
            email='club-trash-creator@example.com',
            password='testpass123',
        )
        self.other_user = get_user_model().objects.create_user(
            email='club-trash-other@example.com',
            password='testpass123',
        )
        self.club = Club.objects.create(
            name='Trashable Club',
            description='Club trash test.',
            creator=self.creator,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

    @override_settings(TRASH_RETENTION_DAYS=7)
    def test_creator_can_move_club_to_trash(self):
        self.club.move_to_trash(self.creator)
        self.club.refresh_from_db()

        self.assertTrue(self.club.is_trashed)
        self.assertIsNotNone(self.club.trashed_at)
        self.assertIsNotNone(self.club.trash_expires_at)
        self.assertEqual(self.club.trashed_by_id, self.creator.id)

    def test_non_creator_cannot_move_club_to_trash(self):
        with self.assertRaises(ValidationError):
            self.club.move_to_trash(self.other_user)

    def test_restore_from_trash_clears_fields(self):
        self.club.move_to_trash(self.creator)
        self.club.restore_from_trash(self.creator)
        self.club.refresh_from_db()

        self.assertFalse(self.club.is_trashed)
        self.assertIsNone(self.club.trashed_at)
        self.assertIsNone(self.club.trash_expires_at)
        self.assertIsNone(self.club.trashed_by)

    @override_settings(CLUB_TRASH_LIMIT_PER_USER=1)
    def test_trash_limit_is_enforced(self):
        first = Club.objects.create(
            name='First Club',
            description='First club',
            creator=self.creator,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )
        second = Club.objects.create(
            name='Second Club',
            description='Second club',
            creator=self.creator,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        first.move_to_trash(self.creator)

        with self.assertRaises(ValidationError):
            second.move_to_trash(self.creator)


class ClubTrashPermissionTests(TestCase):
    def setUp(self):
        self.creator = get_user_model().objects.create_user(
            email='club-trash-permission-creator@example.com',
            password='testpass123',
        )
        self.other_user = get_user_model().objects.create_user(
            email='club-trash-permission-other@example.com',
            password='testpass123',
        )
        self.club = Club.objects.create(
            name='Permission Club',
            description='Permission club',
            creator=self.creator,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

    def test_helper_allows_creator_only(self):
        self.assertTrue(user_can_manage_club_trash(self.creator, self.club))
        self.assertFalse(user_can_manage_club_trash(self.other_user, self.club))

    def test_permission_allows_creator_only(self):
        permission = CanManageOwnClubTrash()

        creator_request = type('Request', (), {'user': self.creator})()
        other_request = type('Request', (), {'user': self.other_user})()

        self.assertTrue(permission.has_object_permission(creator_request, DummyView(), self.club))
        self.assertFalse(permission.has_object_permission(other_request, DummyView(), self.club))