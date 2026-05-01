from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.clubs.models import Club, ClubMembership
from apps.clubs.views import ClubViewSet


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


class ClubTrashApiTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.creator = get_user_model().objects.create_user(
            email='club-trash-creator@example.com',
            password='testpass123',
        )
        self.admin_member = get_user_model().objects.create_user(
            email='club-trash-admin@example.com',
            password='testpass123',
        )
        self.viewer_member = get_user_model().objects.create_user(
            email='club-trash-viewer@example.com',
            password='testpass123',
        )
        self.outsider = get_user_model().objects.create_user(
            email='club-trash-outsider@example.com',
            password='testpass123',
        )

        self.active_club = create_test_club(
            creator=self.creator,
            name='Active Club',
        )
        self.trashed_club = create_test_club(
            creator=self.creator,
            name='Trashed Club',
        )
        self.public_listed_club = create_test_club(
            creator=self.creator,
            name='Public Listed Club',
            visibility=Club.Visibility.PUBLIC,
            directory_visibility=Club.DirectoryVisibility.LISTED,
        )

        ClubMembership.objects.create(
            user=self.admin_member,
            club=self.active_club,
            role=ClubMembership.Role.ADMIN,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.viewer_member,
            club=self.active_club,
            role=ClubMembership.Role.VIEWER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.admin_member,
            club=self.trashed_club,
            role=ClubMembership.Role.ADMIN,
            is_active=True,
        )

        self.trashed_club.move_to_trash(self.creator)

    def perform(self, view, user, method='get', path='/clubs/', data=None, **kwargs):
        request_method = getattr(self.factory, method)
        request = request_method(path, data or {}, format='json')
        force_authenticate(request, user=user)
        return view(request, **kwargs)

    def response_items(self, response):
        return response.data.get('results', response.data) if isinstance(response.data, dict) else response.data

    def test_default_list_excludes_trashed_clubs(self):
        view = ClubViewSet.as_view({'get': 'list'})
        response = self.perform(view, self.creator, path='/clubs/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {entry['id'] for entry in self.response_items(response)}
        self.assertIn(self.active_club.id, returned_ids)
        self.assertIn(self.public_listed_club.id, returned_ids)
        self.assertNotIn(self.trashed_club.id, returned_ids)

    def test_list_trash_only_returns_only_creator_trashed_clubs(self):
        view = ClubViewSet.as_view({'get': 'list'})
        response = self.perform(
            view,
            self.creator,
            path='/clubs/',
            data={'trash': 'only'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {entry['id'] for entry in self.response_items(response)}
        self.assertIn(self.trashed_club.id, returned_ids)
        self.assertNotIn(self.active_club.id, returned_ids)

    def test_my_clubs_default_excludes_trashed_clubs(self):
        view = ClubViewSet.as_view({'get': 'my_clubs'})
        response = self.perform(view, self.creator, path='/clubs/my-clubs/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {entry['id'] for entry in response.data}
        self.assertIn(self.active_club.id, returned_ids)
        self.assertNotIn(self.trashed_club.id, returned_ids)

    def test_my_clubs_trash_only_returns_creator_trashed_clubs(self):
        view = ClubViewSet.as_view({'get': 'my_clubs'})
        response = self.perform(
            view,
            self.creator,
            path='/clubs/my-clubs/',
            data={'trash': 'only'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {entry['id'] for entry in response.data}
        self.assertEqual(returned_ids, {self.trashed_club.id})

    def test_default_retrieve_returns_404_for_trashed_club(self):
        view = ClubViewSet.as_view({'get': 'retrieve'})
        response = self.perform(
            view,
            self.creator,
            path=f'/clubs/{self.trashed_club.id}/',
            pk=self.trashed_club.id,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_with_trash_only_returns_trashed_club_for_creator(self):
        view = ClubViewSet.as_view({'get': 'retrieve'})
        response = self.perform(
            view,
            self.creator,
            path=f'/clubs/{self.trashed_club.id}/',
            data={'trash': 'only'},
            pk=self.trashed_club.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.trashed_club.id)
        self.assertTrue(response.data['is_trashed'])

    def test_non_creator_member_cannot_retrieve_trashed_club_in_trash_context(self):
        view = ClubViewSet.as_view({'get': 'retrieve'})
        response = self.perform(
            view,
            self.admin_member,
            path=f'/clubs/{self.trashed_club.id}/',
            data={'trash': 'only'},
            pk=self.trashed_club.id,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_creator_can_trash_club_via_action(self):
        view = ClubViewSet.as_view({'post': 'trash'})
        response = self.perform(
            view,
            self.creator,
            method='post',
            path=f'/clubs/{self.active_club.id}/trash/',
            pk=self.active_club.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.active_club.refresh_from_db()
        self.assertTrue(self.active_club.is_trashed)

    def test_non_creator_admin_member_cannot_trash_club(self):
        view = ClubViewSet.as_view({'post': 'trash'})
        response = self.perform(
            view,
            self.admin_member,
            method='post',
            path=f'/clubs/{self.active_club.id}/trash/',
            pk=self.active_club.id,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.active_club.refresh_from_db()
        self.assertFalse(self.active_club.is_trashed)

    def test_destroy_soft_deletes_for_creator(self):
        view = ClubViewSet.as_view({'delete': 'destroy'})
        response = self.perform(
            view,
            self.creator,
            method='delete',
            path=f'/clubs/{self.active_club.id}/',
            pk=self.active_club.id,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.active_club.refresh_from_db()
        self.assertTrue(self.active_club.is_trashed)

    def test_restore_works_for_creator(self):
        view = ClubViewSet.as_view({'post': 'restore'})
        response = self.perform(
            view,
            self.creator,
            method='post',
            path=f'/clubs/{self.trashed_club.id}/restore/',
            pk=self.trashed_club.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.trashed_club.refresh_from_db()
        self.assertFalse(self.trashed_club.is_trashed)

    def test_permanent_delete_requires_trashed_club(self):
        view = ClubViewSet.as_view({'delete': 'permanent_delete'})
        response = self.perform(
            view,
            self.creator,
            method='delete',
            path=f'/clubs/{self.active_club.id}/permanent-delete/',
            pk=self.active_club.id,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Club.objects.filter(id=self.active_club.id).exists())

    def test_permanent_delete_removes_trashed_club(self):
        view = ClubViewSet.as_view({'delete': 'permanent_delete'})
        response = self.perform(
            view,
            self.creator,
            method='delete',
            path=f'/clubs/{self.trashed_club.id}/permanent-delete/',
            pk=self.trashed_club.id,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Club.objects.filter(id=self.trashed_club.id).exists())

    def test_lookup_by_code_excludes_trashed_hidden_clubs(self):
        hidden_club = create_test_club(
            creator=self.creator,
            name='Hidden Trashed Club',
            directory_visibility=Club.DirectoryVisibility.HIDDEN_CODE_ONLY,
        )
        hidden_club.move_to_trash(self.creator)

        view = ClubViewSet.as_view({'get': 'lookup_by_code'})
        response = self.perform(
            view,
            self.creator,
            path='/clubs/lookup-by-code/',
            data={'code': hidden_club.join_code},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
