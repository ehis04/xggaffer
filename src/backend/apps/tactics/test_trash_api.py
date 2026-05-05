from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.clubs.models import Club, ClubMembership
from apps.tactics.models import TacticsBoardItem
from apps.tactics.services import create_board_with_initial_frame, create_frame_for_board, create_item_for_frame


def create_test_club(user, name='Tactics Trash API Club'):
    club_kwargs = {
        'name': name,
        'description': 'Tactics trash API test club.',
        'creator': user,
        'visibility': Club.Visibility.PRIVATE,
    }

    if hasattr(Club, 'ClubType'):
        club_kwargs.update({
            'club_type': Club.ClubType.USER_FICTIONAL,
            'fictional_basis': Club.FictionalBasis.ORIGINAL,
            'directory_visibility': Club.DirectoryVisibility.LISTED,
            'join_policy': Club.JoinPolicy.APPROVAL_REQUIRED,
            'verification_status': Club.VerificationStatus.NOT_REQUIRED,
        })

    return Club.objects.create(**club_kwargs)


class TacticsBoardTrashApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.creator = get_user_model().objects.create_user(
            email='tactics-trash-api-creator@example.com',
            password='testpass123',
        )
        self.coach = get_user_model().objects.create_user(
            email='tactics-trash-api-coach@example.com',
            password='testpass123',
        )
        self.other_creator = get_user_model().objects.create_user(
            email='tactics-trash-api-other-creator@example.com',
            password='testpass123',
        )
        self.viewer = get_user_model().objects.create_user(
            email='tactics-trash-api-viewer@example.com',
            password='testpass123',
        )
        self.outsider = get_user_model().objects.create_user(
            email='tactics-trash-api-outsider@example.com',
            password='testpass123',
        )

        self.club = create_test_club(self.creator)

        ClubMembership.objects.create(
            user=self.creator,
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
        ClubMembership.objects.create(
            user=self.other_creator,
            club=self.club,
            role=ClubMembership.Role.COACH,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.viewer,
            club=self.club,
            role=ClubMembership.Role.VIEWER,
            is_active=True,
        )

        self.active_board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.creator,
            title='Active Board',
        )
        self.trashed_board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.creator,
            title='Trashed Board',
        )
        self.trashed_board.move_to_trash(self.creator)

        self.other_users_trashed_board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.other_creator,
            title='Other Users Trashed Board',
        )
        self.other_users_trashed_board.move_to_trash(self.other_creator)

    def test_default_list_excludes_trashed_boards(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(f'/api/clubs/{self.club.id}/tactics-boards/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in response.data}
        self.assertIn(self.active_board.id, returned_ids)
        self.assertNotIn(self.trashed_board.id, returned_ids)

    def test_list_trash_only_returns_only_trashed_boards(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(
            f'/api/clubs/{self.club.id}/tactics-boards/',
            {'trash': 'only'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in response.data}
        self.assertNotIn(self.active_board.id, returned_ids)
        self.assertIn(self.trashed_board.id, returned_ids)

    def test_list_trash_include_returns_active_and_trashed_boards(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(
            f'/api/clubs/{self.club.id}/tactics-boards/',
            {'trash': 'include'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in response.data}
        self.assertIn(self.active_board.id, returned_ids)
        self.assertIn(self.trashed_board.id, returned_ids)

    def test_default_retrieve_returns_404_for_trashed_board(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(
            f'/api/clubs/{self.club.id}/tactics-boards/{self.trashed_board.id}/'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_with_trash_only_can_load_trashed_board(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(
            f'/api/clubs/{self.club.id}/tactics-boards/{self.trashed_board.id}/',
            {'trash': 'only'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.trashed_board.id)
        self.assertTrue(response.data['is_trashed'])

    def test_creator_can_trash_board_via_action(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/{self.active_board.id}/trash/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.active_board.refresh_from_db()
        self.assertTrue(self.active_board.is_trashed)

    def test_non_creator_coach_cannot_trash_board(self):
        self.client.force_authenticate(user=self.coach)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/{self.active_board.id}/trash/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.active_board.refresh_from_db()
        self.assertFalse(self.active_board.is_trashed)

    def test_delete_soft_deletes_for_creator(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.delete(
            f'/api/clubs/{self.club.id}/tactics-boards/{self.active_board.id}/'
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.active_board.refresh_from_db()
        self.assertTrue(self.active_board.is_trashed)

    def test_restore_works_for_creator(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/{self.trashed_board.id}/restore/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.trashed_board.refresh_from_db()
        self.assertFalse(self.trashed_board.is_trashed)

    def test_permanent_delete_requires_trashed_board(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.delete(
            f'/api/clubs/{self.club.id}/tactics-boards/{self.active_board.id}/permanent-delete/'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            self.active_board.__class__.objects.filter(id=self.active_board.id).exists()
        )

    def test_permanent_delete_removes_trashed_board(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.delete(
            f'/api/clubs/{self.club.id}/tactics-boards/{self.trashed_board.id}/permanent-delete/'
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            self.trashed_board.__class__.objects.filter(id=self.trashed_board.id).exists()
        )

    def test_trashed_board_blocks_frame_access(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.creator,
            title='Frame Locked Board',
        )
        frame = board.frames.get(frame_index=0)
        board.move_to_trash(self.creator)

        self.client.force_authenticate(user=self.creator)

        response = self.client.get(
            f'/api/clubs/{self.club.id}/tactics-boards/{board.id}/frames/{frame.id}/'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_trashed_board_blocks_item_access(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.creator,
            title='Item Locked Board',
        )
        frame = board.frames.get(frame_index=0)
        item = create_item_for_frame(
            frame=frame,
            item_type=TacticsBoardItem.ItemType.TEXT,
            team_side=TacticsBoardItem.TeamSide.NEUTRAL,
            x=25,
            y=35,
            label='Press trigger',
        )
        board.move_to_trash(self.creator)

        self.client.force_authenticate(user=self.creator)

        response = self.client.get(
            f'/api/clubs/{self.club.id}/tactics-boards/{board.id}/frames/{frame.id}/items/{item.id}/'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_trash_only_list_returns_only_current_users_trashed_boards(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(
            f'/api/clubs/{self.club.id}/tactics-boards/',
            {'trash': 'only'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in response.data}

        self.assertIn(self.trashed_board.id, returned_ids)
        self.assertNotIn(self.other_users_trashed_board.id, returned_ids)

    def test_retrieve_with_trash_only_cannot_load_someone_elses_trashed_board(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(
            f'/api/clubs/{self.club.id}/tactics-boards/{self.other_users_trashed_board.id}/',
            {'trash': 'only'},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
