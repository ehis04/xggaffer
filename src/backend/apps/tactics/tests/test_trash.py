"""
Tests for tactics board trash model behaviour and permissions

Checks creator-only trash actions, restore behaviour, trash limits, and object-level trash permissions
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory

from apps.clubs.models import Club, ClubMembership
from apps.tactics.permissions import TacticsBoardPermission
from apps.tactics.services import create_board_with_initial_frame


# Create a test club for tactics trash tests
def create_test_club(user, name='Tactics Trash Club'):
    return Club.objects.create(
        name=name,
        description='Tactics trash test club.',
        creator=user,
        visibility=Club.Visibility.PRIVATE,
        club_type=Club.ClubType.USER_FICTIONAL,
        fictional_basis=Club.FictionalBasis.ORIGINAL,
        directory_visibility=Club.DirectoryVisibility.LISTED,
        join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
        verification_status=Club.VerificationStatus.NOT_REQUIRED,
    )


# Minimal view object used for trash permission checks
class DummyView:

    # Store route keyword arguments and action for permission tests
    def __init__(self, club_pk, action='list'):
        self.kwargs = {'club_pk': club_pk}
        self.action = action


# Tests for tactics board trash model helpers
class TacticsBoardTrashModelTests(TestCase):

    # Create a board owner, another user, and a board for trash tests
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='tactics-trash-owner@example.com',
            password='testpass123',
        )
        self.other_user = get_user_model().objects.create_user(
            email='tactics-trash-other@example.com',
            password='testpass123',
        )
        self.club = create_test_club(self.user)
        self.board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.user,
            title='Trash Me',
        )

    # Check the creator can move a board to trash
    @override_settings(TRASH_RETENTION_DAYS=7)
    def test_creator_can_move_board_to_trash(self):
        self.board.move_to_trash(self.user)
        self.board.refresh_from_db()

        self.assertTrue(self.board.is_trashed)
        self.assertIsNotNone(self.board.trashed_at)
        self.assertIsNotNone(self.board.trash_expires_at)
        self.assertEqual(self.board.trashed_by_id, self.user.id)

    # Check non-creators cannot move a board to trash
    def test_non_creator_cannot_move_board_to_trash(self):
        with self.assertRaises(ValidationError):
            self.board.move_to_trash(self.other_user)

    # Check restoring a board clears trash fields
    def test_restore_from_trash_clears_fields(self):
        self.board.move_to_trash(self.user)
        self.board.restore_from_trash(self.user)
        self.board.refresh_from_db()

        self.assertFalse(self.board.is_trashed)
        self.assertIsNone(self.board.trashed_at)
        self.assertIsNone(self.board.trash_expires_at)
        self.assertIsNone(self.board.trashed_by)

    # Check per-user trash limits are enforced
    @override_settings(TACTICS_BOARD_TRASH_LIMIT_PER_USER=1)
    def test_trash_limit_is_enforced(self):
        first = create_board_with_initial_frame(
            club=self.club,
            created_by=self.user,
            title='First Board',
        )
        second = create_board_with_initial_frame(
            club=self.club,
            created_by=self.user,
            title='Second Board',
        )

        first.move_to_trash(self.user)

        with self.assertRaises(ValidationError):
            second.move_to_trash(self.user)


# Tests for creator-only trash permissions
class TacticsBoardCreatorOnlyTrashPermissionTests(TestCase):

    # Create users, club memberships, and a protected board
    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = TacticsBoardPermission()

        self.owner = get_user_model().objects.create_user(
            email='tactics-trash-permission-owner@example.com',
            password='testpass123',
        )
        self.coach = get_user_model().objects.create_user(
            email='tactics-trash-permission-coach@example.com',
            password='testpass123',
        )

        self.club = create_test_club(self.owner)

        ClubMembership.objects.create(
            user=self.owner,
            club=self.club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.coach,
            club=self.club,
            role=ClubMembership.Role.COACH,
            is_active=True,
        )

        self.board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.owner,
            title='Protected Board',
        )

    # Check creators pass route and object permission checks for trash actions
    def test_creator_can_trash_board(self):
        request = self.factory.post('/api/clubs/1/tactics-boards/1/trash/', {}, format='json')
        request.user = self.owner
        view = DummyView(self.club.id, action='trash')

        self.assertTrue(self.permission.has_permission(request, view))
        self.assertTrue(self.permission.has_object_permission(request, view, self.board))

    # Check non-creator coaches fail object permission checks for trash actions
    def test_non_creator_coach_cannot_trash_board(self):
        request = self.factory.post('/api/clubs/1/tactics-boards/1/trash/', {}, format='json')
        request.user = self.coach
        view = DummyView(self.club.id, action='trash')

        self.assertTrue(self.permission.has_permission(request, view))
        self.assertFalse(self.permission.has_object_permission(request, view, self.board))