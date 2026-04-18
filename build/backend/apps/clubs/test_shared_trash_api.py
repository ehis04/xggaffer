from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.clubs.models import Club, ClubMembership
from apps.teamsheets.models import Teamsheet
from apps.tactics.services import create_board_with_initial_frame


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


class SharedTrashApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.creator = get_user_model().objects.create_user(
            email='shared-trash-creator@example.com',
            password='testpass123',
        )
        self.other_creator = get_user_model().objects.create_user(
            email='shared-trash-other@example.com',
            password='testpass123',
        )
        self.member_only_user = get_user_model().objects.create_user(
            email='shared-trash-member@example.com',
            password='testpass123',
        )

        self.creator_club = create_test_club(
            creator=self.creator,
            name='Creator Club',
        )
        self.trashed_creator_club = create_test_club(
            creator=self.creator,
            name='Creator Trashed Club',
        )
        self.trashed_creator_club.move_to_trash(self.creator)

        self.other_club = create_test_club(
            creator=self.other_creator,
            name='Other Creator Club',
        )
        self.other_trashed_club = create_test_club(
            creator=self.other_creator,
            name='Other Trashed Club',
        )
        self.other_trashed_club.move_to_trash(self.other_creator)

        ClubMembership.objects.create(
            user=self.member_only_user,
            club=self.other_trashed_club,
            role=ClubMembership.Role.ADMIN,
            is_active=True,
        )

        self.trashed_teamsheet = Teamsheet.objects.create(
            club=self.creator_club,
            created_by=self.creator,
            title='Creator Trashed Teamsheet',
            formation='442',
            opponent='Example FC',
        )
        self.trashed_teamsheet.move_to_trash(self.creator)

        self.other_trashed_teamsheet = Teamsheet.objects.create(
            club=self.other_club,
            created_by=self.other_creator,
            title='Other Trashed Teamsheet',
            formation='433',
            opponent='Other FC',
        )
        self.other_trashed_teamsheet.move_to_trash(self.other_creator)

        self.trashed_board = create_board_with_initial_frame(
            club=self.creator_club,
            created_by=self.creator,
            title='Creator Trashed Board',
        )
        self.trashed_board.move_to_trash(self.creator)

        self.other_trashed_board = create_board_with_initial_frame(
            club=self.other_club,
            created_by=self.other_creator,
            title='Other Trashed Board',
        )
        self.other_trashed_board.move_to_trash(self.other_creator)

    def test_shared_trash_returns_only_current_users_trashed_items(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get('/api/clubs/trash/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        sections = {item['section'] for item in response.data}
        titles = {item['title'] for item in response.data}

        self.assertIn('clubs', sections)
        self.assertIn('teamsheets', sections)
        self.assertIn('tactics', sections)

        self.assertIn('Creator Trashed Club', titles)
        self.assertIn('Creator Trashed Teamsheet', titles)
        self.assertIn('Creator Trashed Board', titles)

        self.assertNotIn('Other Trashed Club', titles)
        self.assertNotIn('Other Trashed Teamsheet', titles)
        self.assertNotIn('Other Trashed Board', titles)

    def test_shared_trash_section_filter_clubs_only(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get('/api/clubs/trash/?section=clubs')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all(item['section'] == 'clubs' for item in response.data))
        self.assertEqual({item['title'] for item in response.data}, {'Creator Trashed Club'})

    def test_shared_trash_section_filter_teamsheets_only(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get('/api/clubs/trash/?section=teamsheets')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all(item['section'] == 'teamsheets' for item in response.data))
        self.assertEqual(
            {item['title'] for item in response.data},
            {'Creator Trashed Teamsheet'}
        )

    def test_shared_trash_section_filter_tactics_only(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get('/api/clubs/trash/?section=tactics')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all(item['section'] == 'tactics' for item in response.data))
        self.assertEqual(
            {item['title'] for item in response.data},
            {'Creator Trashed Board'}
        )

    def test_invalid_section_returns_400(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get('/api/clubs/trash/?section=invalid')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('section', response.data)

    def test_member_cannot_see_other_creators_trash(self):
        self.client.force_authenticate(user=self.member_only_user)

        response = self.client.get('/api/clubs/trash/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_unauthenticated_user_cannot_access_shared_trash(self):
        response = self.client.get('/api/clubs/trash/')

        self.assertIn(response.status_code, {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN})