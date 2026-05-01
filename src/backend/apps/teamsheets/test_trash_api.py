from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.clubs.models import Club, ClubMembership
from apps.teamsheets.models import Teamsheet


def create_test_club(user, name='Teamsheet Trash API Club'):
    return Club.objects.create(
        name=name,
        description='Teamsheet trash API test club.',
        creator=user,
        visibility=Club.Visibility.PRIVATE,
        club_type=Club.ClubType.USER_FICTIONAL,
        fictional_basis=Club.FictionalBasis.ORIGINAL,
        directory_visibility=Club.DirectoryVisibility.LISTED,
        join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
        verification_status=Club.VerificationStatus.NOT_REQUIRED,
    )


class TeamsheetTrashApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.creator = get_user_model().objects.create_user(
            email='teamsheet-trash-api-creator@example.com',
            password='testpass123',
        )
        self.coach = get_user_model().objects.create_user(
            email='teamsheet-trash-api-coach@example.com',
            password='testpass123',
        )
        self.other_creator = get_user_model().objects.create_user(
            email='teamsheet-trash-api-other-creator@example.com',
            password='testpass123',
        )
        self.outsider = get_user_model().objects.create_user(
            email='teamsheet-trash-api-outsider@example.com',
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

        self.active_teamsheet = Teamsheet.objects.create(
            club=self.club,
            created_by=self.creator,
            title='Active Teamsheet',
            formation='442',
            opponent='Example FC',
        )
        self.trashed_teamsheet = Teamsheet.objects.create(
            club=self.club,
            created_by=self.creator,
            title='Trashed Teamsheet',
            formation='433',
            opponent='Sample United',
        )
        self.trashed_teamsheet.move_to_trash(self.creator)

        self.other_users_trashed_teamsheet = Teamsheet.objects.create(
            club=self.club,
            created_by=self.other_creator,
            title='Other Users Trashed Teamsheet',
            formation='4231',
            opponent='Hidden Town',
        )
        self.other_users_trashed_teamsheet.move_to_trash(self.other_creator)

    def test_default_list_excludes_trashed_teamsheets(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(f'/api/clubs/{self.club.id}/teamsheets/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in response.data}
        self.assertIn(self.active_teamsheet.id, returned_ids)
        self.assertNotIn(self.trashed_teamsheet.id, returned_ids)

    def test_list_trash_only_returns_only_trashed_teamsheets(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(
            f'/api/clubs/{self.club.id}/teamsheets/',
            {'trash': 'only'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in response.data}
        self.assertNotIn(self.active_teamsheet.id, returned_ids)
        self.assertIn(self.trashed_teamsheet.id, returned_ids)

    def test_list_trash_include_returns_active_and_trashed_teamsheets(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(
            f'/api/clubs/{self.club.id}/teamsheets/',
            {'trash': 'include'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in response.data}
        self.assertIn(self.active_teamsheet.id, returned_ids)
        self.assertIn(self.trashed_teamsheet.id, returned_ids)

    def test_default_retrieve_returns_404_for_trashed_teamsheet(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(
            f'/api/clubs/{self.club.id}/teamsheets/{self.trashed_teamsheet.id}/'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_with_trash_only_can_load_trashed_teamsheet(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(
            f'/api/clubs/{self.club.id}/teamsheets/{self.trashed_teamsheet.id}/',
            {'trash': 'only'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.trashed_teamsheet.id)
        self.assertTrue(response.data['is_trashed'])

    def test_creator_can_trash_teamsheet_via_action(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/teamsheets/{self.active_teamsheet.id}/trash/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.active_teamsheet.refresh_from_db()
        self.assertTrue(self.active_teamsheet.is_trashed)

    def test_non_creator_member_cannot_trash_teamsheet(self):
        self.client.force_authenticate(user=self.coach)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/teamsheets/{self.active_teamsheet.id}/trash/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.active_teamsheet.refresh_from_db()
        self.assertFalse(self.active_teamsheet.is_trashed)

    def test_destroy_soft_deletes_for_creator(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.delete(
            f'/api/clubs/{self.club.id}/teamsheets/{self.active_teamsheet.id}/'
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.active_teamsheet.refresh_from_db()
        self.assertTrue(self.active_teamsheet.is_trashed)

    def test_restore_works_for_creator(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/teamsheets/{self.trashed_teamsheet.id}/restore/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.trashed_teamsheet.refresh_from_db()
        self.assertFalse(self.trashed_teamsheet.is_trashed)

    def test_permanent_delete_requires_trashed_item(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.delete(
            f'/api/clubs/{self.club.id}/teamsheets/{self.active_teamsheet.id}/permanent-delete/'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            Teamsheet.objects.filter(id=self.active_teamsheet.id).exists()
        )

    def test_permanent_delete_removes_trashed_item(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.delete(
            f'/api/clubs/{self.club.id}/teamsheets/{self.trashed_teamsheet.id}/permanent-delete/'
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Teamsheet.objects.filter(id=self.trashed_teamsheet.id).exists()
        )

    def test_outsider_cannot_list_teamsheets(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.client.get(f'/api/clubs/{self.club.id}/teamsheets/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_trash_only_list_returns_only_current_users_trashed_teamsheets(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(
            f'/api/clubs/{self.club.id}/teamsheets/',
            {'trash': 'only'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in response.data}

        self.assertIn(self.trashed_teamsheet.id, returned_ids)
        self.assertNotIn(self.other_users_trashed_teamsheet.id, returned_ids)


    def test_retrieve_with_trash_only_cannot_load_someone_elses_trashed_teamsheet(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.get(
            f'/api/clubs/{self.club.id}/teamsheets/{self.other_users_trashed_teamsheet.id}/',
            {'trash': 'only'},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)