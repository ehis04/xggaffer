"""
Tests for tactics board permissions

Checks club membership access rules for reading and creating tactics boards
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.clubs.models import Club, ClubMembership
from apps.tactics.permissions import TacticsBoardPermission


# Create a test club with compatibility for newer club model fields
def create_test_club(user, name='Permission Club'):
    club_kwargs = {
        'name': name,
        'description': 'Permission test club.',
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


# Minimal view object used for permission checks
class DummyView:

    # Store route keyword arguments for permission tests
    def __init__(self, club_pk):
        self.kwargs = {'club_pk': club_pk}


# Tests for tactics board permission checks
class TacticsBoardPermissionTests(TestCase):

    # Create users, memberships, and the permission instance
    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = TacticsBoardPermission()

        self.owner = get_user_model().objects.create_user(
            email='tactics-owner@example.com',
            password='testpass123',
        )
        self.viewer = get_user_model().objects.create_user(
            email='tactics-viewer@example.com',
            password='testpass123',
        )
        self.coach = get_user_model().objects.create_user(
            email='tactics-coach@example.com',
            password='testpass123',
        )
        self.non_member = get_user_model().objects.create_user(
            email='tactics-outsider@example.com',
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
            user=self.viewer,
            club=self.club,
            role=ClubMembership.Role.VIEWER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.coach,
            club=self.club,
            role=ClubMembership.Role.COACH,
            is_active=True,
        )

        self.view = DummyView(self.club.id)

    # Check non-members cannot read tactics boards
    def test_non_member_is_denied_read(self):
        request = self.factory.get('/api/clubs/1/tactics-boards/')
        request.user = self.non_member

        self.assertFalse(self.permission.has_permission(request, self.view))

    # Check viewers cannot create tactics boards
    def test_viewer_is_denied_create(self):
        request = self.factory.post('/api/clubs/1/tactics-boards/', {}, format='json')
        request.user = self.viewer

        self.assertFalse(self.permission.has_permission(request, self.view))

    # Check coaches can create tactics boards
    def test_coach_is_allowed_create(self):
        request = self.factory.post('/api/clubs/1/tactics-boards/', {}, format='json')
        request.user = self.coach

        self.assertTrue(self.permission.has_permission(request, self.view))

    # Check owners can create tactics boards
    def test_owner_is_allowed_create(self):
        request = self.factory.post('/api/clubs/1/tactics-boards/', {}, format='json')
        request.user = self.owner

        self.assertTrue(self.permission.has_permission(request, self.view))