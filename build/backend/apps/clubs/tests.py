import io
from datetime import timedelta
from unittest.mock import patch

from apps.playerdata.models import ClubSeasonEnrichment, PlayerSeasonEnrichment
from apps.players.models import ExternalProvider, Player
from apps.users.models import Role, UserProfile, UserRole
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.utils import timezone
from openpyxl import Workbook
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from .models import (
    Club,
    ClubEvent,
    ClubImportJob,
    ClubInvitation,
    ClubJoinRequest,
    ClubMembership,
    ClubPlayer,
    ClubResource,
    ClubResourceView,
    Fixture,
)
from .permissions import (
    CanCommitClubImportJob,
    CanCreateClubInvitation,
    CanCreateJoinRequest,
    CanManageClubPlayerIdentity,
    CanRespondToClubInvitation,
    CanReviewClubJoinRequest,
    CanRevokeClubInvitation,
    CanWithdrawOwnClubJoinRequest,
)
from .serializers import (
    ClubCalendarFeedItemSerializer,
    ClubEventSerializer,
    ClubEventWriteSerializer,
    ClubImportJobCommitSerializer,
    ClubJoinRequestCreateSerializer,
    ClubJoinRequestApproveSerializer,
    ClubJoinRequestRejectSerializer,
    ClubJoinRequestWithdrawSerializer,
    ClubInvitationCreateSerializer,
    ClubInvitationAcceptSerializer,
    ClubInvitationDeclineSerializer,
    ClubInvitationRevokeSerializer,
    ClubPlayerCreateSerializer,
    ClubPlayerLinkSerializer,
    ClubPlayerRelinkSerializer,
    ClubPlayerSerializer,
    ClubPlayerUnlinkSerializer,
    ClubPlayerUpdateSerializer,
    ClubResourceArchiveSerializer,
    ClubResourceDetailSerializer,
    ClubResourceEngagementReadSerializer,
    ClubResourceHeartbeatSerializer,
    ClubResourceListSerializer,
    ClubResourceSignedAccessSerializer,
    ClubResourceUpdateSerializer,
    ClubResourceUploadSerializer,
    ClubResourceViewReadSerializer,
    ClubSerializer,
    ClubWriteSerializer,
    FixtureSerializer,
    FixtureWriteSerializer,
)
from .services import imports as import_services
from .services.imports import (
    ClubImportCommitError,
    ClubImportValidationError,
    commit_import_job,
    persist_import_preview,
    validate_import_job,
)
from .views import (
    ClubEventViewSet,
    ClubImportJobViewSet,
    ClubInvitationViewSet,
    ClubJoinRequestViewSet,
    ClubMembershipViewSet,
    ClubPlayerViewSet,
    ClubResourceViewSet,
    ClubViewSet,
    FixtureViewSet,
)

class ClubModelValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='coach@example.com',
            password='testpass123'
        )

    def build_club(self, **overrides):
        data = {
            'name': 'Test Club',
            'description': 'Test club description',
            'creator': self.user,
            'visibility': Club.Visibility.PRIVATE,
        }
        data.update(overrides)
        return Club(**data)

    def test_user_fictional_requires_fictional_basis(self):
        club = self.build_club(
            club_type=Club.ClubType.USER_FICTIONAL
        )

        with self.assertRaises(ValidationError) as context:
            club.full_clean()

        self.assertIn('fictional_basis', context.exception.message_dict)

    def test_real_club_copy_requires_source_real_club_name(self):
        club = self.build_club(
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.REAL_CLUB_COPY,
        )

        with self.assertRaises(ValidationError) as context:
            club.full_clean()

        self.assertIn('source_real_club_name', context.exception.message_dict)

    def test_fictional_basis_invalid_for_non_fictional_club(self):
        club = self.build_club(
            club_type=Club.ClubType.USER_REAL_NON_PRO,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            verification_contact_name='Alex Byrne',
            verification_contact_role='Manager',
            verification_contact_email='alex@example.com',
            verification_evidence_text='Club website and committee details provided.',
        )

        with self.assertRaises(ValidationError) as context:
            club.full_clean()

        self.assertIn('fictional_basis', context.exception.message_dict)

    def test_user_real_non_pro_requires_minimal_verification_evidence(self):
        club = self.build_club(
            club_type=Club.ClubType.USER_REAL_NON_PRO,
        )

        with self.assertRaises(ValidationError) as context:
            club.full_clean()

        errors = context.exception.message_dict
        self.assertIn('verification_contact_name', errors)
        self.assertIn('verification_contact_role', errors)
        self.assertIn('verification_contact_email', errors)
        self.assertIn('verification_evidence_text', errors)

    def test_hidden_code_only_generates_join_code_on_save(self):
        club = self.build_club(
            directory_visibility=Club.DirectoryVisibility.HIDDEN_CODE_ONLY
        )

        club.save()

        self.assertTrue(club.join_code)
        self.assertEqual(len(club.join_code), 8)

    def test_listed_club_can_have_null_join_code(self):
        club = self.build_club(
            directory_visibility=Club.DirectoryVisibility.LISTED
        )

        club.full_clean()
        club.save()

        self.assertIsNone(club.join_code)

    def test_user_real_non_pro_defaults_apply_on_save(self):
        club = self.build_club(
            club_type=Club.ClubType.USER_REAL_NON_PRO,
            verification_contact_name='Alex Byrne',
            verification_contact_role='Manager',
            verification_contact_email='alex@example.com',
            verification_evidence_text='Official club page and contact details supplied.',
        )

        club.full_clean()
        club.save()

        self.assertEqual(club.directory_visibility, Club.DirectoryVisibility.LISTED)
        self.assertEqual(club.join_policy, Club.JoinPolicy.APPROVAL_REQUIRED)
        self.assertEqual(club.verification_status, Club.VerificationStatus.PENDING)

    def test_user_fictional_defaults_apply_on_save(self):
        club = self.build_club(
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
        )

        club.full_clean()
        club.save()

        self.assertEqual(club.directory_visibility, Club.DirectoryVisibility.LISTED)
        self.assertEqual(club.join_policy, Club.JoinPolicy.APPROVAL_REQUIRED)
        self.assertEqual(club.verification_status, Club.VerificationStatus.NOT_REQUIRED)

    def test_system_professional_defaults_apply_on_save(self):
        club = self.build_club(
            club_type=Club.ClubType.SYSTEM_PROFESSIONAL,
        )

        club.full_clean()
        club.save()

        self.assertEqual(club.directory_visibility, Club.DirectoryVisibility.LISTED)
        self.assertEqual(club.join_policy, Club.JoinPolicy.SYSTEM_MANAGED)
        self.assertEqual(club.verification_status, Club.VerificationStatus.NOT_REQUIRED)

    def test_helper_methods_return_expected_values(self):
        club = self.build_club(
            club_type=Club.ClubType.USER_REAL_NON_PRO,
            directory_visibility=Club.DirectoryVisibility.HIDDEN_CODE_ONLY,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            join_code='ABCD2345',
            verification_contact_name='Alex Byrne',
            verification_contact_role='Manager',
            verification_contact_email='alex@example.com',
            verification_evidence_text='Committee contact details supplied.',
        )

        self.assertTrue(club.is_hidden_from_directory())
        self.assertTrue(club.requires_verification())
        self.assertFalse(club.is_system_club())
        self.assertTrue(club.can_accept_join_requests())

class ClubSerializerTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.user = get_user_model().objects.create_user(
            email='normal@example.com',
            password='testpass123'
        )

        self.staff_user = get_user_model().objects.create_user(
            email='staff@example.com',
            password='testpass123'
        )
        self.staff_user.is_staff = True
        self.staff_user.save(update_fields=['is_staff'])

    def build_request(self, user):
        request = self.factory.post('/clubs/', {}, format='json')
        request.user = user
        return request

    def test_legacy_create_defaults_to_user_fictional_original(self):
        serializer = ClubWriteSerializer(
            data={
                'name': 'Legacy Club',
                'description': 'Created through legacy flow.',
                'visibility': Club.Visibility.PRIVATE,
            },
            context={'request': self.build_request(self.user)}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        club = serializer.save(creator=self.user)

        self.assertEqual(club.club_type, Club.ClubType.USER_FICTIONAL)
        self.assertEqual(club.fictional_basis, Club.FictionalBasis.ORIGINAL)
        self.assertEqual(club.directory_visibility, Club.DirectoryVisibility.LISTED)
        self.assertEqual(club.join_policy, Club.JoinPolicy.APPROVAL_REQUIRED)
        self.assertEqual(club.verification_status, Club.VerificationStatus.NOT_REQUIRED)

    def test_user_real_non_pro_serializer_requires_evidence_and_defaults_to_pending(self):
        serializer = ClubWriteSerializer(
            data={
                'name': 'Real Club',
                'description': 'Real non-pro club.',
                'visibility': Club.Visibility.PRIVATE,
                'club_type': Club.ClubType.USER_REAL_NON_PRO,
                'verification_contact_name': 'Alex Byrne',
                'verification_contact_role': 'Manager',
                'verification_contact_email': 'alex@example.com',
                'verification_evidence_text': 'Official site and committee details supplied.',
            },
            context={'request': self.build_request(self.user)}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        club = serializer.save(creator=self.user)

        self.assertEqual(club.club_type, Club.ClubType.USER_REAL_NON_PRO)
        self.assertEqual(club.directory_visibility, Club.DirectoryVisibility.LISTED)
        self.assertEqual(club.join_policy, Club.JoinPolicy.APPROVAL_REQUIRED)
        self.assertEqual(club.verification_status, Club.VerificationStatus.PENDING)

    def test_ordinary_user_cannot_submit_system_professional(self):
        serializer = ClubWriteSerializer(
            data={
                'name': 'System Club Attempt',
                'description': 'Should fail.',
                'visibility': Club.Visibility.PUBLIC,
                'club_type': Club.ClubType.SYSTEM_PROFESSIONAL,
            },
            context={'request': self.build_request(self.user)}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('club_type', serializer.errors)

    def test_staff_user_can_submit_system_professional(self):
        serializer = ClubWriteSerializer(
            data={
                'name': 'System Club',
                'description': 'Staff-created system club.',
                'visibility': Club.Visibility.PUBLIC,
                'club_type': Club.ClubType.SYSTEM_PROFESSIONAL,
            },
            context={'request': self.build_request(self.staff_user)}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        club = serializer.save(creator=self.staff_user)

        self.assertEqual(club.club_type, Club.ClubType.SYSTEM_PROFESSIONAL)
        self.assertEqual(club.join_policy, Club.JoinPolicy.SYSTEM_MANAGED)
        self.assertEqual(club.verification_status, Club.VerificationStatus.NOT_REQUIRED)

    def test_hidden_code_only_create_gets_join_code(self):
        serializer = ClubWriteSerializer(
            data={
                'name': 'Hidden Club',
                'description': 'Invite by code only.',
                'visibility': Club.Visibility.PRIVATE,
                'directory_visibility': Club.DirectoryVisibility.HIDDEN_CODE_ONLY,
            },
            context={'request': self.build_request(self.user)}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        club = serializer.save(creator=self.user)

        self.assertTrue(club.join_code)
        self.assertEqual(len(club.join_code), 8)

    def test_hidden_update_preserves_existing_join_code(self):
        club = Club.objects.create(
            name='Existing Hidden Club',
            description='Already hidden.',
            creator=self.user,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.HIDDEN_CODE_ONLY,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )
        original_join_code = club.join_code

        serializer = ClubWriteSerializer(
            instance=club,
            data={
                'name': 'Existing Hidden Club Updated',
            },
            partial=True,
            context={'request': self.build_request(self.user)}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_club = serializer.save()

        self.assertEqual(updated_club.join_code, original_join_code)

    def test_transition_from_fictional_to_real_non_pro_stays_valid(self):
        club = Club.objects.create(
            name='Transition Club',
            description='Initially fictional.',
            creator=self.user,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        serializer = ClubWriteSerializer(
            instance=club,
            data={
                'club_type': Club.ClubType.USER_REAL_NON_PRO,
                'verification_contact_name': 'Alex Byrne',
                'verification_contact_role': 'Manager',
                'verification_contact_email': 'alex@example.com',
                'verification_evidence_text': 'Official club page supplied.',
            },
            partial=True,
            context={'request': self.build_request(self.user)}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_club = serializer.save()

        self.assertEqual(updated_club.club_type, Club.ClubType.USER_REAL_NON_PRO)
        self.assertIsNone(updated_club.fictional_basis)
        self.assertEqual(updated_club.verification_status, Club.VerificationStatus.PENDING)

    def test_read_serializer_exposes_phase_a_taxonomy_fields(self):
        club = Club.objects.create(
            name='Readable Club',
            description='Read serializer test.',
            creator=self.user,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        data = ClubSerializer(club).data

        self.assertIn('club_type', data)
        self.assertIn('fictional_basis', data)
        self.assertIn('source_real_club_name', data)
        self.assertIn('directory_visibility', data)
        self.assertIn('join_policy', data)
        self.assertIn('join_code', data)
        self.assertIn('verification_status', data)

class ClubCreationPermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def create_user_with_roles(self, email, roles=None, is_staff=False, is_superuser=False):
        user = get_user_model().objects.create_user(
            email=email,
            password='testpass123'
        )
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.save(update_fields=['is_staff', 'is_superuser'])

        # UserProfile is auto-created by UserManager.create_user().
        profile, _ = UserProfile.objects.get_or_create(user=user)

        for role in roles or []:
            UserRole.objects.create(
                user_profile=profile,
                role=role,
            )

        return user

    def perform_create(self, user, payload):
        view = ClubViewSet.as_view({'post': 'create'})
        request = self.factory.post('/clubs/', payload, format='json')
        force_authenticate(request, user=user)
        return view(request)

    def perform_retrieve(self, user, club):
        view = ClubViewSet.as_view({'get': 'retrieve'})
        request = self.factory.get(f'/clubs/{club.id}/')
        force_authenticate(request, user=user)
        return view(request, pk=club.id)

    def test_coach_user_can_create_user_managed_club(self):
        coach_user = self.create_user_with_roles(
            email='coach-create@example.com',
            roles=[Role.COACH],
        )

        response = self.perform_create(
            coach_user,
            {
                'name': 'Coach Created Club',
                'description': 'Created by a coach-capable user.',
                'visibility': Club.Visibility.PRIVATE,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_club = Club.objects.get(name='Coach Created Club')

        self.assertTrue(
            ClubMembership.objects.filter(
                user=coach_user,
                club=created_club,
                role=ClubMembership.Role.OWNER,
                is_active=True,
            ).exists()
        )

    def test_player_only_user_cannot_create_club(self):
        player_user = self.create_user_with_roles(
            email='player-only@example.com',
            roles=[Role.PLAYER],
        )

        response = self.perform_create(
            player_user,
            {
                'name': 'Blocked Player Club',
                'description': 'This should not be created.',
                'visibility': Club.Visibility.PRIVATE,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Club.objects.filter(name='Blocked Player Club').exists())

    def test_user_with_coach_and_player_roles_can_create_club(self):
        multi_role_user = self.create_user_with_roles(
            email='multi-role@example.com',
            roles=[Role.PLAYER, Role.COACH],
        )

        response = self.perform_create(
            multi_role_user,
            {
                'name': 'Multi Role Club',
                'description': 'Coach capability should allow creation.',
                'visibility': Club.Visibility.PRIVATE,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Club.objects.filter(name='Multi Role Club').exists())

    def test_non_staff_coach_cannot_create_system_professional_club(self):
        coach_user = self.create_user_with_roles(
            email='coach-system-attempt@example.com',
            roles=[Role.COACH],
        )

        response = self.perform_create(
            coach_user,
            {
                'name': 'Blocked System Club',
                'description': 'Should be blocked.',
                'visibility': Club.Visibility.PUBLIC,
                'club_type': Club.ClubType.SYSTEM_PROFESSIONAL,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Club.objects.filter(name='Blocked System Club').exists())

    def test_staff_user_can_create_system_professional_club(self):
        staff_user = self.create_user_with_roles(
            email='staff-system@example.com',
            roles=[],
            is_staff=True,
        )

        response = self.perform_create(
            staff_user,
            {
                'name': 'Staff System Club',
                'description': 'System-managed staff-created club.',
                'visibility': Club.Visibility.PUBLIC,
                'club_type': Club.ClubType.SYSTEM_PROFESSIONAL,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_club = Club.objects.get(name='Staff System Club')
        self.assertEqual(created_club.club_type, Club.ClubType.SYSTEM_PROFESSIONAL)

    def test_existing_public_detail_access_still_works_for_authenticated_non_member(self):
        creator = self.create_user_with_roles(
            email='creator@example.com',
            roles=[Role.COACH],
        )
        non_member = self.create_user_with_roles(
            email='non-member@example.com',
            roles=[Role.PLAYER],
        )

        club = Club.objects.create(
            name='Public Detail Club',
            description='Publicly readable club.',
            creator=creator,
            visibility=Club.Visibility.PUBLIC,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        response = self.perform_retrieve(non_member, club)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], club.id)

class ClubDiscoveryTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.coach_user = self.create_user_with_roles(
            email='coach-discovery@example.com',
            roles=[Role.COACH],
        )
        self.player_user = self.create_user_with_roles(
            email='player-discovery@example.com',
            roles=[Role.PLAYER],
        )

    def create_user_with_roles(self, email, roles=None):
        user = get_user_model().objects.create_user(
            email=email,
            password='testpass123'
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)

        for role in roles or []:
            UserRole.objects.create(
                user_profile=profile,
                role=role,
            )

        return user

    def extract_results(self, response):
        if isinstance(response.data, dict) and 'results' in response.data:
            return response.data['results']
        return response.data

    def perform_browse(self, user, params=None):
        view = ClubViewSet.as_view({'get': 'list'})
        request = self.factory.get('/clubs/', params or {'scope': 'browse'})
        force_authenticate(request, user=user)
        return view(request)

    def perform_lookup(self, user, code):
        view = ClubViewSet.as_view({'get': 'lookup_by_code'})
        request = self.factory.get('/clubs/lookup-by-code/', {'code': code})
        force_authenticate(request, user=user)
        return view(request)

    def perform_retrieve(self, user, club):
        view = ClubViewSet.as_view({'get': 'retrieve'})
        request = self.factory.get(f'/clubs/{club.id}/')
        force_authenticate(request, user=user)
        return view(request, pk=club.id)

    def test_listed_club_appears_in_browse(self):
        listed_club = Club.objects.create(
            name='Listed Browse Club',
            description='Should appear in browse.',
            creator=self.coach_user,
            visibility=Club.Visibility.PUBLIC,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        response = self.perform_browse(self.player_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = self.extract_results(response)
        returned_ids = {club['id'] for club in results}
        self.assertIn(listed_club.id, returned_ids)

    def test_hidden_club_does_not_appear_in_browse(self):
        hidden_club = Club.objects.create(
            name='Hidden Browse Club',
            description='Should not appear in browse.',
            creator=self.coach_user,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.HIDDEN_CODE_ONLY,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        response = self.perform_browse(self.player_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = self.extract_results(response)
        returned_ids = {club['id'] for club in results}
        self.assertNotIn(hidden_club.id, returned_ids)

    def test_hidden_club_does_not_appear_in_browse_search(self):
        hidden_club = Club.objects.create(
            name='Secret Tactical Club',
            description='Should remain hidden from search.',
            creator=self.coach_user,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.HIDDEN_CODE_ONLY,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        response = self.perform_browse(
            self.player_user,
            {'scope': 'browse', 'search': 'Secret Tactical'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = self.extract_results(response)
        returned_ids = {club['id'] for club in results}
        self.assertNotIn(hidden_club.id, returned_ids)

    def test_hidden_club_can_be_found_by_valid_code(self):
        hidden_club = Club.objects.create(
            name='Lookup Hidden Club',
            description='Lookup test.',
            creator=self.coach_user,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.HIDDEN_CODE_ONLY,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        response = self.perform_lookup(self.player_user, hidden_club.join_code)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], hidden_club.id)

    def test_hidden_club_lookup_fails_cleanly_for_invalid_code(self):
        response = self.perform_lookup(self.player_user, 'INVALID99')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('detail', response.data)

    def test_member_can_still_retrieve_hidden_club(self):
        hidden_club = Club.objects.create(
            name='Member Hidden Club',
            description='Member access should still work.',
            creator=self.coach_user,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.HIDDEN_CODE_ONLY,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        ClubMembership.objects.create(
            user=self.player_user,
            club=hidden_club,
            role=ClubMembership.Role.PLAYER,
            is_active=True,
        )

        response = self.perform_retrieve(self.player_user, hidden_club)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], hidden_club.id)

    def test_legacy_public_club_with_null_directory_visibility_still_appears_in_browse(self):
        legacy_public_club = Club.objects.create(
            name='Legacy Public Club',
            description='Legacy row should remain browseable.',
            creator=self.coach_user,
            visibility=Club.Visibility.PUBLIC,
        )

        response = self.perform_browse(self.player_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = self.extract_results(response)
        returned_ids = {club['id'] for club in results}
        self.assertIn(legacy_public_club.id, returned_ids)

class ClubWorkflowModelTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            email='owner-workflow@example.com',
            password='testpass123'
        )
        self.target_user = get_user_model().objects.create_user(
            email='target-workflow@example.com',
            password='testpass123'
        )

        self.club = Club.objects.create(
            name='Workflow Club',
            description='Workflow model tests.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

    def test_can_create_pending_join_request(self):
        join_request = ClubJoinRequest.objects.create(
            club=self.club,
            user=self.target_user,
            requested_role=ClubMembership.Role.PLAYER,
            message='I would like to join as a player.',
        )

        self.assertEqual(join_request.status, ClubJoinRequest.Status.PENDING)
        self.assertEqual(join_request.club, self.club)
        self.assertEqual(join_request.user, self.target_user)
        self.assertEqual(join_request.requested_role, ClubMembership.Role.PLAYER)

    def test_duplicate_pending_join_request_blocked(self):
        ClubJoinRequest.objects.create(
            club=self.club,
            user=self.target_user,
            requested_role=ClubMembership.Role.PLAYER,
        )

        with self.assertRaises(IntegrityError):
            ClubJoinRequest.objects.create(
                club=self.club,
                user=self.target_user,
                requested_role=ClubMembership.Role.PLAYER,
            )

    def test_non_pending_join_request_does_not_block_new_pending_request(self):
        ClubJoinRequest.objects.create(
            club=self.club,
            user=self.target_user,
            requested_role=ClubMembership.Role.PLAYER,
            status=ClubJoinRequest.Status.REJECTED,
        )

        join_request = ClubJoinRequest.objects.create(
            club=self.club,
            user=self.target_user,
            requested_role=ClubMembership.Role.PLAYER,
            status=ClubJoinRequest.Status.PENDING,
        )

        self.assertEqual(join_request.status, ClubJoinRequest.Status.PENDING)

    def test_can_create_pending_invitation(self):
        invitation = ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.target_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
            note='Join the club staff.',
        )

        self.assertEqual(invitation.status, ClubInvitation.Status.PENDING)
        self.assertEqual(invitation.club, self.club)
        self.assertEqual(invitation.invited_user, self.target_user)
        self.assertEqual(invitation.invited_by, self.owner)
        self.assertEqual(invitation.invited_role, ClubMembership.Role.COACH)

    def test_duplicate_pending_invitation_same_role_blocked(self):
        ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.target_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
        )

        with self.assertRaises(IntegrityError):
            ClubInvitation.objects.create(
                club=self.club,
                invited_user=self.target_user,
                invited_by=self.owner,
                invited_role=ClubMembership.Role.COACH,
            )

    def test_pending_invitation_for_different_role_is_allowed(self):
        ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.target_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
        )

        invitation = ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.target_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.VIEWER,
        )

        self.assertEqual(invitation.status, ClubInvitation.Status.PENDING)
        self.assertEqual(invitation.invited_role, ClubMembership.Role.VIEWER)

    def test_join_request_can_store_selected_club_player_reference(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            created_by=self.owner,
            is_active=True,
        )

        join_request = ClubJoinRequest.objects.create(
            club=self.club,
            user=self.target_user,
            requested_role=ClubMembership.Role.PLAYER,
            selected_club_player=club_player,
        )

        self.assertEqual(join_request.selected_club_player, club_player)

class ClubWorkflowTransitionTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            email='owner-b2@example.com',
            password='testpass123'
        )
        self.reviewer = get_user_model().objects.create_user(
            email='reviewer-b2@example.com',
            password='testpass123'
        )
        self.player_user = get_user_model().objects.create_user(
            email='player-b2@example.com',
            password='testpass123'
        )
        self.staff_user = get_user_model().objects.create_user(
            email='staff-b2@example.com',
            password='testpass123'
        )

        self.club = Club.objects.create(
            name='B2 Club',
            description='Workflow helper tests.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

    def test_join_request_helper_flags(self):
        join_request = ClubJoinRequest.objects.create(
            club=self.club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
        )

        self.assertTrue(join_request.is_pending())
        self.assertTrue(join_request.can_be_reviewed())
        self.assertTrue(join_request.can_be_withdrawn())

    def test_join_request_rejects_non_approval_required_club(self):
        self.club.join_policy = Club.JoinPolicy.INVITE_ONLY
        self.club.save(update_fields=['join_policy', 'updated_at'])

        with self.assertRaises(ValidationError):
            ClubJoinRequest.objects.create(
                club=self.club,
                user=self.player_user,
                requested_role=ClubMembership.Role.PLAYER,
            )

    def test_join_request_rejects_existing_active_member(self):
        ClubMembership.objects.create(
            user=self.player_user,
            club=self.club,
            role=ClubMembership.Role.PLAYER,
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            ClubJoinRequest.objects.create(
                club=self.club,
                user=self.player_user,
                requested_role=ClubMembership.Role.PLAYER,
            )

    def test_join_request_rejects_non_player_self_request_role(self):
        with self.assertRaises(ValidationError):
            ClubJoinRequest.objects.create(
                club=self.club,
                user=self.player_user,
                requested_role=ClubMembership.Role.COACH,
            )

    def test_join_request_rejects_selected_club_player_from_other_club(self):
        other_club = Club.objects.create(
            name='Other Club',
            description='Other workflow club.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        other_player = ClubPlayer.objects.create(
            club=other_club,
            first_name='Other',
            last_name='Player',
            display_name='Other Player',
            created_by=self.owner,
        )

        with self.assertRaises(ValidationError):
            ClubJoinRequest.objects.create(
                club=self.club,
                user=self.player_user,
                requested_role=ClubMembership.Role.PLAYER,
                selected_club_player=other_player,
            )

    def test_join_request_rejects_already_claimed_selected_club_player(self):
        claimed_player = ClubPlayer.objects.create(
            club=self.club,
            user=self.staff_user,
            first_name='Claimed',
            last_name='Player',
            display_name='Claimed Player',
            created_by=self.owner,
        )

        with self.assertRaises(ValidationError):
            ClubJoinRequest.objects.create(
                club=self.club,
                user=self.player_user,
                requested_role=ClubMembership.Role.PLAYER,
                selected_club_player=claimed_player,
            )

    def test_mark_approved_creates_membership(self):
        join_request = ClubJoinRequest.objects.create(
            club=self.club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
        )

        membership = join_request.mark_approved(
            reviewed_by=self.reviewer,
            review_note='Approved for the squad.',
        )

        join_request.refresh_from_db()

        self.assertEqual(join_request.status, ClubJoinRequest.Status.APPROVED)
        self.assertEqual(join_request.reviewed_by, self.reviewer)
        self.assertIsNotNone(join_request.reviewed_at)
        self.assertEqual(membership.user, self.player_user)
        self.assertEqual(membership.club, self.club)
        self.assertEqual(membership.role, ClubMembership.Role.PLAYER)

    def test_mark_approved_can_link_selected_club_player(self):
        unclaimed_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            created_by=self.owner,
        )

        join_request = ClubJoinRequest.objects.create(
            club=self.club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
        )

        join_request.mark_approved(
            reviewed_by=self.reviewer,
            selected_club_player=unclaimed_player,
            review_note='Linked to existing roster row.',
        )

        join_request.refresh_from_db()
        unclaimed_player.refresh_from_db()

        self.assertEqual(join_request.selected_club_player, unclaimed_player)
        self.assertEqual(unclaimed_player.user, self.player_user)
        self.assertIsNotNone(unclaimed_player.claimed_at)
        self.assertIsNone(unclaimed_player.claim_token)

    def test_mark_rejected_does_not_create_membership(self):
        join_request = ClubJoinRequest.objects.create(
            club=self.club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
        )

        join_request.mark_rejected(
            reviewed_by=self.reviewer,
            review_note='Not approved.',
        )

        join_request.refresh_from_db()

        self.assertEqual(join_request.status, ClubJoinRequest.Status.REJECTED)
        self.assertFalse(
            ClubMembership.objects.filter(
                user=self.player_user,
                club=self.club,
                is_active=True,
            ).exists()
        )

    def test_mark_withdrawn_changes_state(self):
        join_request = ClubJoinRequest.objects.create(
            club=self.club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
        )

        join_request.mark_withdrawn()
        join_request.refresh_from_db()

        self.assertEqual(join_request.status, ClubJoinRequest.Status.WITHDRAWN)

    def test_impossible_join_request_transition_is_blocked(self):
        join_request = ClubJoinRequest.objects.create(
            club=self.club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
            status=ClubJoinRequest.Status.REJECTED,
        )

        with self.assertRaises(ValidationError):
            join_request.mark_approved(reviewed_by=self.reviewer)

    def test_invitation_helper_flags(self):
        invitation = ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.staff_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
        )

        self.assertTrue(invitation.is_pending())
        self.assertTrue(invitation.can_be_reviewed())
        self.assertTrue(invitation.can_be_revoked())

    def test_invitation_rejects_existing_active_member(self):
        ClubMembership.objects.create(
            user=self.staff_user,
            club=self.club,
            role=ClubMembership.Role.COACH,
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            ClubInvitation.objects.create(
                club=self.club,
                invited_user=self.staff_user,
                invited_by=self.owner,
                invited_role=ClubMembership.Role.COACH,
            )

    def test_invitation_rejects_owner_role(self):
        with self.assertRaises(ValidationError):
            ClubInvitation.objects.create(
                club=self.club,
                invited_user=self.staff_user,
                invited_by=self.owner,
                invited_role=ClubMembership.Role.OWNER,
            )

    def test_mark_accepted_creates_membership(self):
        invitation = ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.staff_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
        )

        membership = invitation.mark_accepted(response_note='Accepted.')

        invitation.refresh_from_db()

        self.assertEqual(invitation.status, ClubInvitation.Status.ACCEPTED)
        self.assertIsNotNone(invitation.responded_at)
        self.assertEqual(membership.user, self.staff_user)
        self.assertEqual(membership.club, self.club)
        self.assertEqual(membership.role, ClubMembership.Role.COACH)

    def test_mark_declined_does_not_create_membership(self):
        invitation = ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.staff_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
        )

        invitation.mark_declined(response_note='No thanks.')
        invitation.refresh_from_db()

        self.assertEqual(invitation.status, ClubInvitation.Status.DECLINED)
        self.assertFalse(
            ClubMembership.objects.filter(
                user=self.staff_user,
                club=self.club,
                is_active=True,
            ).exists()
        )

    def test_mark_revoked_changes_state(self):
        invitation = ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.staff_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
        )

        invitation.mark_revoked(response_note='Invite withdrawn.')
        invitation.refresh_from_db()

        self.assertEqual(invitation.status, ClubInvitation.Status.REVOKED)

    def test_impossible_invitation_transition_is_blocked(self):
        invitation = ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.staff_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
            status=ClubInvitation.Status.DECLINED,
        )

        with self.assertRaises(ValidationError):
            invitation.mark_accepted()

class ClubWorkflowSerializerTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.owner = get_user_model().objects.create_user(
            email='owner-b3@example.com',
            password='testpass123'
        )
        self.reviewer = get_user_model().objects.create_user(
            email='reviewer-b3@example.com',
            password='testpass123'
        )
        self.player_user = get_user_model().objects.create_user(
            email='player-b3@example.com',
            password='testpass123'
        )
        self.staff_user = get_user_model().objects.create_user(
            email='staff-b3@example.com',
            password='testpass123'
        )

        self.club = Club.objects.create(
            name='Serializer Club',
            description='Serializer workflow tests.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

    def build_request(self, user):
        request = self.factory.post('/clubs/', {}, format='json')
        request.user = user
        return request

    def test_join_request_create_serializer_accepts_valid_player_request(self):
        serializer = ClubJoinRequestCreateSerializer(
            data={
                'requested_role': ClubMembership.Role.PLAYER,
                'message': 'I would like to join.',
            },
            context={
                'request': self.build_request(self.player_user),
                'club': self.club,
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        join_request = serializer.save()

        self.assertEqual(join_request.club, self.club)
        self.assertEqual(join_request.user, self.player_user)
        self.assertEqual(join_request.requested_role, ClubMembership.Role.PLAYER)
        self.assertEqual(join_request.status, ClubJoinRequest.Status.PENDING)

    def test_join_request_create_serializer_rejects_staff_self_request_role(self):
        serializer = ClubJoinRequestCreateSerializer(
            data={
                'requested_role': ClubMembership.Role.COACH,
                'message': 'Let me in as staff.',
            },
            context={
                'request': self.build_request(self.player_user),
                'club': self.club,
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('requested_role', serializer.errors)

    def test_join_request_create_serializer_rejects_invite_only_club(self):
        self.club.join_policy = Club.JoinPolicy.INVITE_ONLY
        self.club.save(update_fields=['join_policy', 'updated_at'])

        serializer = ClubJoinRequestCreateSerializer(
            data={
                'requested_role': ClubMembership.Role.PLAYER,
                'message': 'I would like to join.',
            },
            context={
                'request': self.build_request(self.player_user),
                'club': self.club,
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('club', serializer.errors)

    def test_join_request_create_serializer_rejects_duplicate_pending_request(self):
        ClubJoinRequest.objects.create(
            club=self.club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
        )

        serializer = ClubJoinRequestCreateSerializer(
            data={
                'requested_role': ClubMembership.Role.PLAYER,
            },
            context={
                'request': self.build_request(self.player_user),
                'club': self.club,
            }
        )

        self.assertFalse(serializer.is_valid())

    def test_join_request_approve_serializer_can_link_selected_club_player(self):
        join_request = ClubJoinRequest.objects.create(
            club=self.club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
        )
        club_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            created_by=self.owner,
        )

        serializer = ClubJoinRequestApproveSerializer(
            instance=join_request,
            data={
                'review_note': 'Approved and linked.',
                'selected_club_player': club_player.id,
            },
            context={'request': self.build_request(self.reviewer)}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_request = serializer.save()

        updated_request.refresh_from_db()
        club_player.refresh_from_db()

        self.assertEqual(updated_request.status, ClubJoinRequest.Status.APPROVED)
        self.assertEqual(updated_request.selected_club_player, club_player)
        self.assertEqual(club_player.user, self.player_user)
        self.assertTrue(
            ClubMembership.objects.filter(
                user=self.player_user,
                club=self.club,
                role=ClubMembership.Role.PLAYER,
                is_active=True,
            ).exists()
        )

    def test_join_request_approve_serializer_rejects_claimed_club_player(self):
        join_request = ClubJoinRequest.objects.create(
            club=self.club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
        )
        claimed_player = ClubPlayer.objects.create(
            club=self.club,
            user=self.staff_user,
            first_name='Claimed',
            last_name='Player',
            display_name='Claimed Player',
            created_by=self.owner,
        )

        serializer = ClubJoinRequestApproveSerializer(
            instance=join_request,
            data={
                'selected_club_player': claimed_player.id,
            },
            context={'request': self.build_request(self.reviewer)}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('selected_club_player', serializer.errors)

    def test_join_request_reject_serializer_marks_request_rejected(self):
        join_request = ClubJoinRequest.objects.create(
            club=self.club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
        )

        serializer = ClubJoinRequestRejectSerializer(
            instance=join_request,
            data={'review_note': 'Not approved.'},
            context={'request': self.build_request(self.reviewer)}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_request = serializer.save()

        self.assertEqual(updated_request.status, ClubJoinRequest.Status.REJECTED)
        self.assertFalse(
            ClubMembership.objects.filter(
                user=self.player_user,
                club=self.club,
                is_active=True,
            ).exists()
        )

    def test_join_request_withdraw_serializer_marks_request_withdrawn(self):
        join_request = ClubJoinRequest.objects.create(
            club=self.club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
        )

        serializer = ClubJoinRequestWithdrawSerializer(
            instance=join_request,
            data={},
            context={'request': self.build_request(self.player_user)}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_request = serializer.save()

        self.assertEqual(updated_request.status, ClubJoinRequest.Status.WITHDRAWN)

    def test_invitation_create_serializer_accepts_existing_user(self):
        serializer = ClubInvitationCreateSerializer(
            data={
                'invited_user': self.staff_user.id,
                'invited_role': ClubMembership.Role.COACH,
                'note': 'Join as coach.',
            },
            context={
                'request': self.build_request(self.owner),
                'club': self.club,
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        invitation = serializer.save()

        self.assertEqual(invitation.club, self.club)
        self.assertEqual(invitation.invited_user, self.staff_user)
        self.assertEqual(invitation.invited_by, self.owner)
        self.assertEqual(invitation.invited_role, ClubMembership.Role.COACH)
        self.assertEqual(invitation.status, ClubInvitation.Status.PENDING)

    def test_invitation_create_serializer_rejects_owner_role(self):
        serializer = ClubInvitationCreateSerializer(
            data={
                'invited_user': self.staff_user.id,
                'invited_role': ClubMembership.Role.OWNER,
            },
            context={
                'request': self.build_request(self.owner),
                'club': self.club,
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('invited_role', serializer.errors)

    def test_invitation_create_serializer_rejects_duplicate_pending_invite(self):
        ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.staff_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
        )

        serializer = ClubInvitationCreateSerializer(
            data={
                'invited_user': self.staff_user.id,
                'invited_role': ClubMembership.Role.COACH,
            },
            context={
                'request': self.build_request(self.owner),
                'club': self.club,
            }
        )

        self.assertFalse(serializer.is_valid())

    def test_invitation_accept_serializer_marks_invitation_accepted(self):
        invitation = ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.staff_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
        )

        serializer = ClubInvitationAcceptSerializer(
            instance=invitation,
            data={'response_note': 'Accepted.'},
            context={'request': self.build_request(self.staff_user)}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_invitation = serializer.save()

        self.assertEqual(updated_invitation.status, ClubInvitation.Status.ACCEPTED)
        self.assertTrue(
            ClubMembership.objects.filter(
                user=self.staff_user,
                club=self.club,
                role=ClubMembership.Role.COACH,
                is_active=True,
            ).exists()
        )

    def test_invitation_decline_serializer_marks_invitation_declined(self):
        invitation = ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.staff_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
        )

        serializer = ClubInvitationDeclineSerializer(
            instance=invitation,
            data={'response_note': 'Declined.'},
            context={'request': self.build_request(self.staff_user)}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_invitation = serializer.save()

        self.assertEqual(updated_invitation.status, ClubInvitation.Status.DECLINED)
        self.assertFalse(
            ClubMembership.objects.filter(
                user=self.staff_user,
                club=self.club,
                is_active=True,
            ).exists()
        )

    def test_invitation_revoke_serializer_marks_invitation_revoked(self):
        invitation = ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.staff_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
        )

        serializer = ClubInvitationRevokeSerializer(
            instance=invitation,
            data={'response_note': 'Invite revoked.'},
            context={'request': self.build_request(self.owner)}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_invitation = serializer.save()

        self.assertEqual(updated_invitation.status, ClubInvitation.Status.REVOKED)

class ClubWorkflowPermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.owner = self.create_user_with_roles(
            email='owner-b4@example.com',
            roles=[Role.COACH],
        )
        self.admin = self.create_user_with_roles(
            email='admin-b4@example.com',
            roles=[Role.COACH],
        )
        self.coach_member = self.create_user_with_roles(
            email='coach-member-b4@example.com',
            roles=[Role.COACH],
        )
        self.player_user = self.create_user_with_roles(
            email='player-b4@example.com',
            roles=[Role.PLAYER],
        )
        self.multi_role_user = self.create_user_with_roles(
            email='multi-role-b4@example.com',
            roles=[Role.PLAYER, Role.COACH],
        )
        self.invited_user = self.create_user_with_roles(
            email='invited-b4@example.com',
            roles=[Role.PLAYER],
        )
        self.other_user = self.create_user_with_roles(
            email='other-b4@example.com',
            roles=[Role.FAN],
        )

        self.club = Club.objects.create(
            name='Permissions Club',
            description='Permission tests.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        ClubMembership.objects.create(
            user=self.owner,
            club=self.club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.admin,
            club=self.club,
            role=ClubMembership.Role.ADMIN,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.coach_member,
            club=self.club,
            role=ClubMembership.Role.COACH,
            is_active=True,
        )

    def create_user_with_roles(self, email, roles=None):
        user = get_user_model().objects.create_user(
            email=email,
            password='testpass123'
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)

        for role in roles or []:
            UserRole.objects.create(
                user_profile=profile,
                role=role,
            )

        return user

    def build_request(self, user, method='post'):
        request_method = getattr(self.factory, method)
        request = request_method('/clubs/', {}, format='json')
        request.user = user
        return request

    def build_view(self, **kwargs):
        class DummyView:
            pass

        view = DummyView()
        view.kwargs = kwargs
        return view

    def test_can_create_join_request_allows_player_role(self):
        permission = CanCreateJoinRequest()
        request = self.build_request(self.player_user)

        self.assertTrue(permission.has_permission(request, self.build_view()))

    def test_can_create_join_request_allows_multi_role_user_with_player_capability(self):
        permission = CanCreateJoinRequest()
        request = self.build_request(self.multi_role_user)

        self.assertTrue(permission.has_permission(request, self.build_view()))

    def test_can_create_join_request_blocks_non_player_user(self):
        permission = CanCreateJoinRequest()
        request = self.build_request(self.other_user)

        self.assertFalse(permission.has_permission(request, self.build_view()))

    def test_can_review_join_request_owner_and_admin_only(self):
        join_request = ClubJoinRequest.objects.create(
            club=self.club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
        )
        permission = CanReviewClubJoinRequest()

        self.assertTrue(
            permission.has_object_permission(
                self.build_request(self.owner),
                self.build_view(),
                join_request,
            )
        )
        self.assertTrue(
            permission.has_object_permission(
                self.build_request(self.admin),
                self.build_view(),
                join_request,
            )
        )
        self.assertFalse(
            permission.has_object_permission(
                self.build_request(self.coach_member),
                self.build_view(),
                join_request,
            )
        )

    def test_can_withdraw_join_request_only_for_request_owner(self):
        join_request = ClubJoinRequest.objects.create(
            club=self.club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
        )
        permission = CanWithdrawOwnClubJoinRequest()

        self.assertTrue(
            permission.has_object_permission(
                self.build_request(self.player_user),
                self.build_view(),
                join_request,
            )
        )
        self.assertFalse(
            permission.has_object_permission(
                self.build_request(self.other_user),
                self.build_view(),
                join_request,
            )
        )

    def test_can_create_club_invitation_owner_and_admin_only(self):
        permission = CanCreateClubInvitation()
        owner_request = self.build_request(self.owner)
        admin_request = self.build_request(self.admin)
        coach_request = self.build_request(self.coach_member)

        view = self.build_view(club_pk=self.club.id)

        self.assertTrue(permission.has_permission(owner_request, view))
        self.assertTrue(permission.has_permission(admin_request, view))
        self.assertFalse(permission.has_permission(coach_request, view))

    def test_can_respond_to_club_invitation_only_for_invited_user(self):
        invitation = ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.invited_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
        )
        permission = CanRespondToClubInvitation()

        self.assertTrue(
            permission.has_object_permission(
                self.build_request(self.invited_user),
                self.build_view(),
                invitation,
            )
        )
        self.assertFalse(
            permission.has_object_permission(
                self.build_request(self.other_user),
                self.build_view(),
                invitation,
            )
        )

    def test_can_revoke_club_invitation_owner_and_admin_only(self):
        invitation = ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.invited_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
        )
        permission = CanRevokeClubInvitation()

        self.assertTrue(
            permission.has_object_permission(
                self.build_request(self.owner),
                self.build_view(),
                invitation,
            )
        )
        self.assertTrue(
            permission.has_object_permission(
                self.build_request(self.admin),
                self.build_view(),
                invitation,
            )
        )
        self.assertFalse(
            permission.has_object_permission(
                self.build_request(self.coach_member),
                self.build_view(),
                invitation,
            )
        )

    def test_direct_membership_create_endpoint_is_blocked(self):
        view = ClubMembershipViewSet.as_view({'post': 'create'})
        request = self.factory.post(
            f'/clubs/{self.club.id}/memberships/',
            {
                'user': self.player_user.id,
                'role': ClubMembership.Role.PLAYER,
                'is_active': True,
            },
            format='json'
        )
        force_authenticate(request, user=self.owner)

        response = view(request, club_pk=self.club.id)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertFalse(
            ClubMembership.objects.filter(
                user=self.player_user,
                club=self.club,
                is_active=True,
            ).exists()
        )

class ClubWorkflowApiTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.owner = self.create_user_with_roles(
            email='owner-b5@example.com',
            roles=[Role.COACH],
        )
        self.admin = self.create_user_with_roles(
            email='admin-b5@example.com',
            roles=[Role.COACH],
        )
        self.coach_member = self.create_user_with_roles(
            email='coach-member-b5@example.com',
            roles=[Role.COACH],
        )
        self.player_user = self.create_user_with_roles(
            email='player-b5@example.com',
            roles=[Role.PLAYER],
        )
        self.invited_user = self.create_user_with_roles(
            email='invited-b5@example.com',
            roles=[Role.PLAYER],
        )
        self.other_user = self.create_user_with_roles(
            email='other-b5@example.com',
            roles=[Role.FAN],
        )

        self.club = Club.objects.create(
            name='B5 Club',
            description='Workflow API tests.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        ClubMembership.objects.create(
            user=self.owner,
            club=self.club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.admin,
            club=self.club,
            role=ClubMembership.Role.ADMIN,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.coach_member,
            club=self.club,
            role=ClubMembership.Role.COACH,
            is_active=True,
        )

    def create_user_with_roles(self, email, roles=None):
        user = get_user_model().objects.create_user(
            email=email,
            password='testpass123'
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)

        for role in roles or []:
            UserRole.objects.create(
                user_profile=profile,
                role=role,
            )

        return user

    def perform(self, view, user, method='get', data=None, **kwargs):
        request_method = getattr(self.factory, method)
        request = request_method('/clubs/', data or {}, format='json')
        force_authenticate(request, user=user)
        return view(request, **kwargs)

    def test_create_join_request_endpoint(self):
        view = ClubJoinRequestViewSet.as_view({'post': 'create'})

        response = self.perform(
            view,
            self.player_user,
            method='post',
            data={
                'requested_role': ClubMembership.Role.PLAYER,
                'message': 'I would like to join.',
            },
            club_pk=self.club.id,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], ClubJoinRequest.Status.PENDING)
        self.assertTrue(
            ClubJoinRequest.objects.filter(
                club=self.club,
                user=self.player_user,
                status=ClubJoinRequest.Status.PENDING,
            ).exists()
        )

    def test_list_my_join_requests_endpoint(self):
        ClubJoinRequest.objects.create(
            club=self.club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
        )

        view = ClubJoinRequestViewSet.as_view({'get': 'mine'})
        response = self.perform(view, self.player_user, method='get')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['user'], self.player_user.id)

    def test_list_club_join_requests_endpoint_owner_allowed_coach_blocked(self):
        ClubJoinRequest.objects.create(
            club=self.club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
        )

        view = ClubJoinRequestViewSet.as_view({'get': 'list'})

        owner_response = self.perform(
            view,
            self.owner,
            method='get',
            club_pk=self.club.id,
        )
        self.assertEqual(owner_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(owner_response.data), 1)

        coach_response = self.perform(
            view,
            self.coach_member,
            method='get',
            club_pk=self.club.id,
        )
        self.assertEqual(coach_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_approve_join_request_endpoint_creates_membership(self):
        join_request = ClubJoinRequest.objects.create(
            club=self.club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
        )

        view = ClubJoinRequestViewSet.as_view({'post': 'approve'})
        response = self.perform(
            view,
            self.owner,
            method='post',
            data={'review_note': 'Approved.'},
            club_pk=self.club.id,
            pk=join_request.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        join_request.refresh_from_db()
        self.assertEqual(join_request.status, ClubJoinRequest.Status.APPROVED)
        self.assertTrue(
            ClubMembership.objects.filter(
                user=self.player_user,
                club=self.club,
                role=ClubMembership.Role.PLAYER,
                is_active=True,
            ).exists()
        )

    def test_reject_join_request_endpoint_does_not_create_membership(self):
        join_request = ClubJoinRequest.objects.create(
            club=self.club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
        )

        view = ClubJoinRequestViewSet.as_view({'post': 'reject'})
        response = self.perform(
            view,
            self.owner,
            method='post',
            data={'review_note': 'Rejected.'},
            club_pk=self.club.id,
            pk=join_request.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        join_request.refresh_from_db()
        self.assertEqual(join_request.status, ClubJoinRequest.Status.REJECTED)
        self.assertFalse(
            ClubMembership.objects.filter(
                user=self.player_user,
                club=self.club,
                is_active=True,
            ).exists()
        )

    def test_withdraw_join_request_endpoint(self):
        join_request = ClubJoinRequest.objects.create(
            club=self.club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
        )

        view = ClubJoinRequestViewSet.as_view({'post': 'withdraw'})
        response = self.perform(
            view,
            self.player_user,
            method='post',
            data={},
            club_pk=self.club.id,
            pk=join_request.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        join_request.refresh_from_db()
        self.assertEqual(join_request.status, ClubJoinRequest.Status.WITHDRAWN)

    def test_create_invitation_endpoint(self):
        view = ClubInvitationViewSet.as_view({'post': 'create'})
        response = self.perform(
            view,
            self.owner,
            method='post',
            data={
                'invited_user': self.invited_user.id,
                'invited_role': ClubMembership.Role.COACH,
                'note': 'Join as staff.',
            },
            club_pk=self.club.id,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], ClubInvitation.Status.PENDING)
        self.assertTrue(
            ClubInvitation.objects.filter(
                club=self.club,
                invited_user=self.invited_user,
                invited_role=ClubMembership.Role.COACH,
                status=ClubInvitation.Status.PENDING,
            ).exists()
        )

    def test_list_my_invitations_endpoint(self):
        ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.invited_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
        )

        view = ClubInvitationViewSet.as_view({'get': 'mine'})
        response = self.perform(view, self.invited_user, method='get')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['invited_user'], self.invited_user.id)

    def test_list_club_invitations_endpoint(self):
        ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.invited_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
        )

        view = ClubInvitationViewSet.as_view({'get': 'list'})
        response = self.perform(
            view,
            self.owner,
            method='get',
            club_pk=self.club.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_accept_invitation_endpoint_creates_membership(self):
        invitation = ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.invited_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
        )

        view = ClubInvitationViewSet.as_view({'post': 'accept'})
        response = self.perform(
            view,
            self.invited_user,
            method='post',
            data={'response_note': 'Accepted.'},
            club_pk=self.club.id,
            pk=invitation.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ClubInvitation.Status.ACCEPTED)
        self.assertTrue(
            ClubMembership.objects.filter(
                user=self.invited_user,
                club=self.club,
                role=ClubMembership.Role.COACH,
                is_active=True,
            ).exists()
        )

    def test_decline_invitation_endpoint_does_not_create_membership(self):
        invitation = ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.invited_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
        )

        view = ClubInvitationViewSet.as_view({'post': 'decline'})
        response = self.perform(
            view,
            self.invited_user,
            method='post',
            data={'response_note': 'Declined.'},
            club_pk=self.club.id,
            pk=invitation.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ClubInvitation.Status.DECLINED)
        self.assertFalse(
            ClubMembership.objects.filter(
                user=self.invited_user,
                club=self.club,
                is_active=True,
            ).exists()
        )

    def test_revoke_invitation_endpoint(self):
        invitation = ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.invited_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
        )

        view = ClubInvitationViewSet.as_view({'post': 'revoke'})
        response = self.perform(
            view,
            self.owner,
            method='post',
            data={'response_note': 'Revoked.'},
            club_pk=self.club.id,
            pk=invitation.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ClubInvitation.Status.REVOKED)

    def test_user_cannot_accept_invitation_not_addressed_to_them(self):
        invitation = ClubInvitation.objects.create(
            club=self.club,
            invited_user=self.invited_user,
            invited_by=self.owner,
            invited_role=ClubMembership.Role.COACH,
        )

        view = ClubInvitationViewSet.as_view({'post': 'accept'})
        response = self.perform(
            view,
            self.other_user,
            method='post',
            data={},
            club_pk=self.club.id,
            pk=invitation.id,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ClubWorkflowAcceptanceGapTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.owner = self.create_user_with_roles(
            email='owner-b8@example.com',
            roles=[Role.COACH],
        )
        self.admin = self.create_user_with_roles(
            email='admin-b8@example.com',
            roles=[Role.COACH],
        )
        self.player_user = self.create_user_with_roles(
            email='player-b8@example.com',
            roles=[Role.PLAYER],
        )
        self.player_only_other = self.create_user_with_roles(
            email='player-only-other-b8@example.com',
            roles=[Role.PLAYER],
        )
        self.invited_user = self.create_user_with_roles(
            email='invited-b8@example.com',
            roles=[Role.PLAYER],
        )

        self.hidden_approval_club = Club.objects.create(
            name='Hidden Approval Club',
            description='Hidden club requiring approval.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.HIDDEN_CODE_ONLY,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        self.standard_club = Club.objects.create(
            name='Standard Workflow Club',
            description='Standard workflow tests.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        self.system_club = Club.objects.create(
            name='System Managed Club',
            description='Should not open ordinary user flows.',
            creator=self.owner,
            visibility=Club.Visibility.PUBLIC,
            club_type=Club.ClubType.SYSTEM_PROFESSIONAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.SYSTEM_MANAGED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        ClubMembership.objects.create(
            user=self.owner,
            club=self.hidden_approval_club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.owner,
            club=self.standard_club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.admin,
            club=self.standard_club,
            role=ClubMembership.Role.ADMIN,
            is_active=True,
        )

    def create_user_with_roles(self, email, roles=None):
        user = get_user_model().objects.create_user(
            email=email,
            password='testpass123'
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)

        for role in roles or []:
            UserRole.objects.create(
                user_profile=profile,
                role=role,
            )

        return user

    def perform(self, view, user, method='get', data=None, **kwargs):
        request_method = getattr(self.factory, method)
        request = request_method('/clubs/', data or {}, format='json')
        force_authenticate(request, user=user)
        return view(request, **kwargs)

    def test_hidden_club_lookup_does_not_bypass_request_flow(self):
        lookup_view = ClubViewSet.as_view({'get': 'lookup_by_code'})
        lookup_request = self.factory.get(
            '/clubs/lookup-by-code/',
            {'code': self.hidden_approval_club.join_code}
        )
        force_authenticate(lookup_request, user=self.player_user)

        lookup_response = lookup_view(lookup_request)

        self.assertEqual(lookup_response.status_code, status.HTTP_200_OK)
        self.assertEqual(lookup_response.data['id'], self.hidden_approval_club.id)
        self.assertFalse(
            ClubMembership.objects.filter(
                user=self.player_user,
                club=self.hidden_approval_club,
                is_active=True,
            ).exists()
        )

        create_request_view = ClubJoinRequestViewSet.as_view({'post': 'create'})
        create_response = self.perform(
            create_request_view,
            self.player_user,
            method='post',
            data={
                'requested_role': ClubMembership.Role.PLAYER,
                'message': 'Please let me join via the normal review flow.',
            },
            club_pk=self.hidden_approval_club.id,
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data['status'], ClubJoinRequest.Status.PENDING)
        self.assertFalse(
            ClubMembership.objects.filter(
                user=self.player_user,
                club=self.hidden_approval_club,
                is_active=True,
            ).exists()
        )

    def test_system_managed_club_still_blocks_user_join_request(self):
        create_request_view = ClubJoinRequestViewSet.as_view({'post': 'create'})
        response = self.perform(
            create_request_view,
            self.player_user,
            method='post',
            data={'requested_role': ClubMembership.Role.PLAYER},
            club_pk=self.system_club.id,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            ClubJoinRequest.objects.filter(
                user=self.player_user,
                club=self.system_club,
            ).exists()
        )

    def test_approval_without_selected_club_player_does_not_auto_link_roster_row(self):
        unclaimed_player = ClubPlayer.objects.create(
            club=self.standard_club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            created_by=self.owner,
            is_active=True,
        )

        join_request = ClubJoinRequest.objects.create(
            club=self.standard_club,
            user=self.player_user,
            requested_role=ClubMembership.Role.PLAYER,
        )

        approve_view = ClubJoinRequestViewSet.as_view({'post': 'approve'})
        response = self.perform(
            approve_view,
            self.owner,
            method='post',
            data={'review_note': 'Approved without manual roster linking.'},
            club_pk=self.standard_club.id,
            pk=join_request.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        join_request.refresh_from_db()
        unclaimed_player.refresh_from_db()

        self.assertEqual(join_request.status, ClubJoinRequest.Status.APPROVED)
        self.assertIsNone(join_request.selected_club_player)
        self.assertIsNone(unclaimed_player.user)
        self.assertIsNone(unclaimed_player.claimed_at)
        self.assertTrue(
            ClubMembership.objects.filter(
                user=self.player_user,
                club=self.standard_club,
                role=ClubMembership.Role.PLAYER,
                is_active=True,
            ).exists()
        )

    def test_player_only_user_cannot_create_invitation_via_api(self):
        invite_view = ClubInvitationViewSet.as_view({'post': 'create'})
        response = self.perform(
            invite_view,
            self.player_only_other,
            method='post',
            data={
                'invited_user': self.invited_user.id,
                'invited_role': ClubMembership.Role.COACH,
                'note': 'This should be blocked.',
            },
            club_pk=self.standard_club.id,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(
            ClubInvitation.objects.filter(
                club=self.standard_club,
                invited_user=self.invited_user,
                invited_role=ClubMembership.Role.COACH,
            ).exists()
        )

    def test_player_only_user_cannot_approve_join_request_via_api(self):
        join_request = ClubJoinRequest.objects.create(
            club=self.standard_club,
            user=self.invited_user,
            requested_role=ClubMembership.Role.PLAYER,
        )

        approve_view = ClubJoinRequestViewSet.as_view({'post': 'approve'})
        response = self.perform(
            approve_view,
            self.player_only_other,
            method='post',
            data={'review_note': 'This should be blocked.'},
            club_pk=self.standard_club.id,
            pk=join_request.id,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        join_request.refresh_from_db()
        self.assertEqual(join_request.status, ClubJoinRequest.Status.PENDING)
        self.assertFalse(
            ClubMembership.objects.filter(
                user=self.invited_user,
                club=self.standard_club,
                is_active=True,
            ).exists()
        )

class ClubPlayerCanonicalLinkModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='club-link-model@example.com',
            password='testpass123',
        )
        self.club = Club.objects.create(
            name='Canonical Link Club',
            description='Club for canonical link model tests.',
            creator=self.user,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )
        self.player_a = Player.objects.create(
            first_name='Erin',
            last_name='Moore',
            display_name='Erin Moore',
            primary_position='CM',
        )
        self.player_b = Player.objects.create(
            first_name='Tara',
            last_name='Byrne',
            display_name='Tara Byrne',
            primary_position='CB',
        )

    def test_club_player_can_exist_unlinked(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Local',
            last_name='Only',
            display_name='Local Only',
            created_by=self.user,
        )

        self.assertFalse(club_player.is_linked_to_player)
        self.assertIsNone(club_player.player_id)

    def test_link_to_player_sets_explicit_link_state(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Erin',
            last_name='Moore',
            display_name='Erin Moore',
            created_by=self.user,
        )

        club_player.link_to_player(self.player_a)
        club_player.refresh_from_db()

        self.assertTrue(club_player.is_linked_to_player)
        self.assertEqual(club_player.player_id, self.player_a.id)

    def test_link_to_different_player_without_relink_is_blocked(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            player=self.player_a,
            first_name='Erin',
            last_name='Moore',
            display_name='Erin Moore',
            created_by=self.user,
        )

        with self.assertRaises(ValidationError):
            club_player.link_to_player(self.player_b)

    def test_relink_player_changes_target_safely(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            player=self.player_a,
            first_name='Erin',
            last_name='Moore',
            display_name='Erin Moore',
            created_by=self.user,
        )

        club_player.relink_player(self.player_b)
        club_player.refresh_from_db()

        self.assertEqual(club_player.player_id, self.player_b.id)

    def test_unlink_player_clears_canonical_link(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            player=self.player_a,
            first_name='Erin',
            last_name='Moore',
            display_name='Erin Moore',
            created_by=self.user,
        )

        club_player.unlink_player()
        club_player.refresh_from_db()

        self.assertFalse(club_player.is_linked_to_player)
        self.assertIsNone(club_player.player_id)

    def test_get_display_player_identity_prefers_canonical_player_when_linked(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            player=self.player_a,
            first_name='Local',
            last_name='Snapshot',
            display_name='Local Snapshot',
            created_by=self.user,
        )

        identity = club_player.get_display_player_identity()

        self.assertTrue(identity['is_linked_to_player'])
        self.assertEqual(identity['player_id'], self.player_a.id)
        self.assertEqual(identity['full_name'], self.player_a.full_name)
        self.assertEqual(identity['primary_position'], self.player_a.primary_position)

class ClubPlayerCanonicalLinkSerializerTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create_user(
            email='club-link-serializer@example.com',
            password='testpass123',
        )
        self.club = Club.objects.create(
            name='Serializer Link Club',
            description='Club for canonical link serializer tests.',
            creator=self.user,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )
        self.player_a = Player.objects.create(
            first_name='Niamh',
            last_name='Kelly',
            display_name='Niamh Kelly',
            primary_position='ST',
        )
        self.player_b = Player.objects.create(
            first_name='Paige',
            last_name='Larkin',
            display_name='Paige Larkin',
            primary_position='LW',
        )

    def build_request(self):
        request = self.factory.post('/clubs/', {}, format='json')
        request.user = self.user
        return request

    def test_read_serializer_exposes_explicit_link_state(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            player=self.player_a,
            first_name='Niamh',
            last_name='Kelly',
            display_name='Niamh Kelly',
            created_by=self.user,
        )

        data = ClubPlayerSerializer(club_player).data

        self.assertTrue(data['is_linked_to_player'])
        self.assertEqual(data['canonical_player_id'], self.player_a.id)
        self.assertEqual(data['canonical_display_name'], self.player_a.display_name)
        self.assertEqual(data['player_id'], self.player_a.id)

    def test_create_serializer_allows_local_only_club_player(self):
        serializer = ClubPlayerCreateSerializer(
            data={
                'first_name': 'Local',
                'last_name': 'Prospect',
                'display_name': 'Local Prospect',
                'primary_position': 'CM',
                'is_public': False,
            },
            context={
                'request': self.build_request(),
                'club': self.club,
            },
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        club_player = serializer.save(club=self.club, created_by=self.user)

        self.assertIsNone(club_player.player_id)
        self.assertEqual(club_player.first_name, 'Local')
        self.assertEqual(club_player.last_name, 'Prospect')

    def test_create_serializer_can_attach_explicit_canonical_player(self):
        serializer = ClubPlayerCreateSerializer(
            data={
                'canonical_player_id': self.player_a.id,
                'is_public': False,
            },
            context={
                'request': self.build_request(),
                'club': self.club,
            },
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        club_player = serializer.save(club=self.club, created_by=self.user)

        self.assertEqual(club_player.player_id, self.player_a.id)
        self.assertEqual(club_player.first_name, self.player_a.first_name)
        self.assertEqual(club_player.last_name, self.player_a.last_name)

    def test_generic_update_serializer_blocks_canonical_link_change(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            player=self.player_a,
            first_name='Niamh',
            last_name='Kelly',
            display_name='Niamh Kelly',
            created_by=self.user,
        )

        serializer = ClubPlayerUpdateSerializer(
            instance=club_player,
            data={
                'canonical_player_id': self.player_b.id,
            },
            partial=True,
            context={
                'request': self.build_request(),
                'club': self.club,
            },
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('canonical_player_id', serializer.errors)

    def test_explicit_link_serializer_links_unlinked_row(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Local',
            last_name='Only',
            display_name='Local Only',
            created_by=self.user,
        )

        serializer = ClubPlayerLinkSerializer(
            instance=club_player,
            data={'canonical_player_id': self.player_a.id},
            context={'request': self.build_request()},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()

        self.assertEqual(updated.player_id, self.player_a.id)

    def test_explicit_relink_serializer_changes_target(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            player=self.player_a,
            first_name='Niamh',
            last_name='Kelly',
            display_name='Niamh Kelly',
            created_by=self.user,
        )

        serializer = ClubPlayerRelinkSerializer(
            instance=club_player,
            data={'canonical_player_id': self.player_b.id},
            context={'request': self.build_request()},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()

        self.assertEqual(updated.player_id, self.player_b.id)

    def test_explicit_unlink_serializer_clears_target(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            player=self.player_a,
            first_name='Niamh',
            last_name='Kelly',
            display_name='Niamh Kelly',
            created_by=self.user,
        )

        serializer = ClubPlayerUnlinkSerializer(
            instance=club_player,
            data={},
            context={'request': self.build_request()},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()

        self.assertIsNone(updated.player_id)

class ClubPlayerIdentityActionPermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.owner = self.create_user_with_roles(
            email='owner-c4@example.com',
            roles=[Role.COACH],
        )
        self.admin = self.create_user_with_roles(
            email='admin-c4@example.com',
            roles=[Role.COACH],
        )
        self.coach_member = self.create_user_with_roles(
            email='coach-member-c4@example.com',
            roles=[Role.COACH],
        )
        self.player_member = self.create_user_with_roles(
            email='player-member-c4@example.com',
            roles=[Role.PLAYER],
        )

        self.club = Club.objects.create(
            name='Identity Action Club',
            description='Club identity action tests.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        ClubMembership.objects.create(
            user=self.owner,
            club=self.club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.admin,
            club=self.club,
            role=ClubMembership.Role.ADMIN,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.coach_member,
            club=self.club,
            role=ClubMembership.Role.COACH,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.player_member,
            club=self.club,
            role=ClubMembership.Role.PLAYER,
            is_active=True,
        )

        self.club_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Local',
            last_name='Prospect',
            display_name='Local Prospect',
            created_by=self.owner,
            is_active=True,
        )

        self.player_a = Player.objects.create(
            first_name='Nina',
            last_name='Doyle',
            display_name='Nina Doyle',
            primary_position='CM',
        )
        self.player_b = Player.objects.create(
            first_name='Ava',
            last_name='Byrne',
            display_name='Ava Byrne',
            primary_position='CB',
        )

    def create_user_with_roles(self, email, roles=None):
        user = get_user_model().objects.create_user(
            email=email,
            password='testpass123',
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)

        for role in roles or []:
            UserRole.objects.create(
                user_profile=profile,
                role=role,
            )

        return user

    def perform_link(self, user, club_player_id, canonical_player_id):
        view = ClubPlayerViewSet.as_view({'post': 'link'})
        request = self.factory.post(
            f'/clubs/{self.club.id}/players/{club_player_id}/link/',
            {'canonical_player_id': canonical_player_id},
            format='json',
        )
        force_authenticate(request, user=user)
        return view(request, club_pk=self.club.id, pk=club_player_id)

    def perform_unlink(self, user, club_player_id):
        view = ClubPlayerViewSet.as_view({'post': 'unlink'})
        request = self.factory.post(
            f'/clubs/{self.club.id}/players/{club_player_id}/unlink/',
            {},
            format='json',
        )
        force_authenticate(request, user=user)
        return view(request, club_pk=self.club.id, pk=club_player_id)

    def perform_relink(self, user, club_player_id, canonical_player_id):
        view = ClubPlayerViewSet.as_view({'post': 'relink'})
        request = self.factory.post(
            f'/clubs/{self.club.id}/players/{club_player_id}/relink/',
            {'canonical_player_id': canonical_player_id},
            format='json',
        )
        force_authenticate(request, user=user)
        return view(request, club_pk=self.club.id, pk=club_player_id)

    def test_owner_can_link_club_player(self):
        response = self.perform_link(self.owner, self.club_player.id, self.player_a.id)
        self.club_player.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.club_player.player_id, self.player_a.id)

    def test_admin_can_link_club_player(self):
        response = self.perform_link(self.admin, self.club_player.id, self.player_a.id)
        self.club_player.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.club_player.player_id, self.player_a.id)

    def test_coach_member_cannot_link_club_player(self):
        response = self.perform_link(self.coach_member, self.club_player.id, self.player_a.id)
        self.club_player.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIsNone(self.club_player.player_id)

    def test_player_member_cannot_link_club_player(self):
        response = self.perform_link(self.player_member, self.club_player.id, self.player_a.id)
        self.club_player.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIsNone(self.club_player.player_id)

    def test_owner_can_unlink_club_player(self):
        self.club_player.link_to_player(self.player_a)

        response = self.perform_unlink(self.owner, self.club_player.id)
        self.club_player.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(self.club_player.player_id)

    def test_owner_can_relink_club_player(self):
        self.club_player.link_to_player(self.player_a)

        response = self.perform_relink(self.owner, self.club_player.id, self.player_b.id)
        self.club_player.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.club_player.player_id, self.player_b.id)

class ClubSchedulingModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='schedule-owner@example.com',
            password='testpass123'
        )

        self.fictional_club = Club.objects.create(
            name='Scheduling Fictional Club',
            description='Fixture and event model tests.',
            creator=self.user,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        self.system_club = Club.objects.create(
            name='Scheduling System Club',
            description='System scheduling foundation test.',
            creator=self.user,
            visibility=Club.Visibility.PUBLIC,
            club_type=Club.ClubType.SYSTEM_PROFESSIONAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.SYSTEM_MANAGED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

    def test_can_create_club_event_for_user_managed_club(self):
        start_time = timezone.now() + timedelta(days=2)

        event = ClubEvent.objects.create(
            club=self.fictional_club,
            title='Tuesday Analysis Session',
            event_type=ClubEvent.EventType.ANALYSIS,
            description='Video review and prep.',
            start_datetime=start_time,
            end_datetime=start_time + timedelta(hours=2),
            location='Analysis Room',
            is_mandatory=True,
            created_by=self.user,
        )

        self.assertEqual(event.club, self.fictional_club)
        self.assertEqual(event.source_type, ClubEvent.SourceType.MANUAL)
        self.assertEqual(event.event_type, ClubEvent.EventType.ANALYSIS)
        self.assertTrue(event.is_mandatory)

    def test_can_create_fixture_for_user_managed_club(self):
        kickoff = timezone.now() + timedelta(days=5)

        fixture = Fixture.objects.create(
            club=self.fictional_club,
            opponent_name='Ranelagh United',
            venue=Fixture.Venue.HOME,
            competition='Friendly',
            match_datetime=kickoff,
            location='Main Pitch',
            created_by=self.user,
        )

        self.assertEqual(fixture.club, self.fictional_club)
        self.assertEqual(fixture.fixture_status, Fixture.FixtureStatus.SCHEDULED)
        self.assertEqual(fixture.source_type, Fixture.SourceType.MANUAL)
        self.assertEqual(fixture.venue, Fixture.Venue.HOME)

    def test_can_create_system_or_provider_fixture_for_system_club(self):
        kickoff = timezone.now() + timedelta(days=8)

        fixture = Fixture.objects.create(
            club=self.system_club,
            opponent_name='Dublin City FC',
            venue=Fixture.Venue.AWAY,
            competition='League',
            match_datetime=kickoff,
            fixture_status=Fixture.FixtureStatus.SCHEDULED,
            source_type=Fixture.SourceType.PROVIDER,
            external_fixture_id='fd-12345',
            created_by=self.user,
        )

        self.assertEqual(fixture.club, self.system_club)
        self.assertEqual(fixture.source_type, Fixture.SourceType.PROVIDER)
        self.assertEqual(fixture.external_fixture_id, 'fd-12345')

    def test_external_fixture_id_is_unique_per_club_when_present(self):
        kickoff = timezone.now() + timedelta(days=10)

        Fixture.objects.create(
            club=self.fictional_club,
            opponent_name='First Opponent',
            venue=Fixture.Venue.HOME,
            competition='League',
            match_datetime=kickoff,
            external_fixture_id='shared-id',
            created_by=self.user,
        )

        with self.assertRaises(IntegrityError):
            Fixture.objects.create(
                club=self.fictional_club,
                opponent_name='Second Opponent',
                venue=Fixture.Venue.AWAY,
                competition='League',
                match_datetime=kickoff + timedelta(days=1),
                external_fixture_id='shared-id',
                created_by=self.user,
            )

    def test_blank_external_fixture_id_does_not_block_multiple_manual_rows(self):
        kickoff = timezone.now() + timedelta(days=12)

        first_fixture = Fixture.objects.create(
            club=self.fictional_club,
            opponent_name='Northside FC',
            venue=Fixture.Venue.HOME,
            competition='Cup',
            match_datetime=kickoff,
            created_by=self.user,
        )
        second_fixture = Fixture.objects.create(
            club=self.fictional_club,
            opponent_name='Southside FC',
            venue=Fixture.Venue.AWAY,
            competition='Cup',
            match_datetime=kickoff + timedelta(days=1),
            created_by=self.user,
        )

        self.assertNotEqual(first_fixture.id, second_fixture.id)
        self.assertEqual(first_fixture.external_fixture_id, '')
        self.assertEqual(second_fixture.external_fixture_id, '')

class ClubSchedulingValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='schedule-validation@example.com',
            password='testpass123'
        )

        self.legacy_club = Club.objects.create(
            name='Legacy Scheduling Club',
            description='Legacy club without taxonomy.',
            creator=self.user,
            visibility=Club.Visibility.PRIVATE,
        )

        self.fictional_club = Club.objects.create(
            name='Managed Fictional Club',
            description='User-managed scheduling test.',
            creator=self.user,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        self.system_club = Club.objects.create(
            name='System Scheduling Club',
            description='System-managed scheduling test.',
            creator=self.user,
            visibility=Club.Visibility.PUBLIC,
            club_type=Club.ClubType.SYSTEM_PROFESSIONAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.SYSTEM_MANAGED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

    def test_club_helper_methods_are_legacy_safe(self):
        self.assertTrue(self.legacy_club.is_user_managed_club())
        self.assertTrue(self.legacy_club.allows_manual_events())
        self.assertTrue(self.legacy_club.allows_manual_fixtures())

        self.assertTrue(self.fictional_club.is_user_managed_club())
        self.assertTrue(self.fictional_club.allows_manual_events())
        self.assertTrue(self.fictional_club.allows_manual_fixtures())

        self.assertFalse(self.system_club.is_user_managed_club())
        self.assertFalse(self.system_club.allows_manual_events())
        self.assertFalse(self.system_club.allows_manual_fixtures())

    def test_manual_club_event_is_allowed_for_user_managed_club(self):
        start_time = timezone.now() + timedelta(days=2)

        event = ClubEvent.objects.create(
            club=self.fictional_club,
            title='Training Session',
            event_type=ClubEvent.EventType.TRAINING,
            start_datetime=start_time,
            end_datetime=start_time + timedelta(hours=2),
            source_type=ClubEvent.SourceType.MANUAL,
            created_by=self.user,
        )

        self.assertTrue(event.is_user_editable())
        self.assertFalse(event.is_system_managed_item())
        self.assertTrue(event.is_future_item())
        self.assertEqual(event.get_calendar_label(), 'Training Session')

    def test_manual_club_event_is_blocked_for_system_club(self):
        start_time = timezone.now() + timedelta(days=3)

        with self.assertRaises(ValidationError) as context:
            ClubEvent.objects.create(
                club=self.system_club,
                title='Manual System Event',
                event_type=ClubEvent.EventType.MEETING,
                start_datetime=start_time,
                source_type=ClubEvent.SourceType.MANUAL,
                created_by=self.user,
            )

        self.assertIn('source_type', context.exception.message_dict)

    def test_provider_club_event_is_allowed_for_system_club(self):
        start_time = timezone.now() + timedelta(days=4)

        event = ClubEvent.objects.create(
            club=self.system_club,
            title='Provider Event',
            event_type=ClubEvent.EventType.OTHER,
            start_datetime=start_time,
            source_type=ClubEvent.SourceType.PROVIDER,
        )

        self.assertTrue(event.is_system_managed_item())
        self.assertFalse(event.is_user_editable())

    def test_club_event_rejects_end_before_start(self):
        start_time = timezone.now() + timedelta(days=1)

        with self.assertRaises(ValidationError) as context:
            ClubEvent.objects.create(
                club=self.fictional_club,
                title='Broken Event',
                event_type=ClubEvent.EventType.ANALYSIS,
                start_datetime=start_time,
                end_datetime=start_time - timedelta(hours=1),
                source_type=ClubEvent.SourceType.MANUAL,
                created_by=self.user,
            )

        self.assertIn('end_datetime', context.exception.message_dict)

    def test_manual_fixture_is_allowed_for_legacy_club(self):
        kickoff = timezone.now() + timedelta(days=5)

        fixture = Fixture.objects.create(
            club=self.legacy_club,
            opponent_name='Legacy Opponent',
            venue=Fixture.Venue.HOME,
            competition='Friendly',
            match_datetime=kickoff,
            source_type=Fixture.SourceType.MANUAL,
            created_by=self.user,
        )

        self.assertTrue(fixture.is_user_editable())
        self.assertFalse(fixture.is_system_managed_item())

    def test_manual_fixture_is_blocked_for_system_club(self):
        kickoff = timezone.now() + timedelta(days=6)

        with self.assertRaises(ValidationError) as context:
            Fixture.objects.create(
                club=self.system_club,
                opponent_name='System Opponent',
                venue=Fixture.Venue.HOME,
                competition='League',
                match_datetime=kickoff,
                source_type=Fixture.SourceType.MANUAL,
                created_by=self.user,
            )

        self.assertIn('source_type', context.exception.message_dict)

    def test_provider_fixture_is_allowed_for_system_club(self):
        kickoff = timezone.now() + timedelta(days=7)

        fixture = Fixture.objects.create(
            club=self.system_club,
            opponent_name='Provider Opponent',
            venue=Fixture.Venue.AWAY,
            competition='League',
            match_datetime=kickoff,
            source_type=Fixture.SourceType.PROVIDER,
            external_fixture_id='provider-fixture-001',
        )

        self.assertTrue(fixture.is_system_managed_item())
        self.assertFalse(fixture.is_user_editable())
        self.assertEqual(fixture.get_calendar_label(), '@ Provider Opponent')

    def test_fixture_helper_methods_return_expected_values(self):
        kickoff = timezone.now() + timedelta(days=8)

        fixture = Fixture.objects.create(
            club=self.fictional_club,
            opponent_name='Weekend Opponent',
            venue=Fixture.Venue.HOME,
            competition='Cup',
            match_datetime=kickoff,
            source_type=Fixture.SourceType.MANUAL,
            created_by=self.user,
        )

        self.assertTrue(fixture.is_future_item())
        self.assertTrue(fixture.is_user_editable())
        self.assertFalse(fixture.is_system_managed_item())
        self.assertEqual(fixture.get_calendar_label(), 'vs Weekend Opponent')

class ClubEventSerializerTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create_user(
            email='club-event-serializer@example.com',
            password='testpass123',
        )

        self.fictional_club = Club.objects.create(
            name='Event Serializer Club',
            description='Club for event serializer tests.',
            creator=self.user,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        self.system_club = Club.objects.create(
            name='System Event Club',
            description='System club for event serializer tests.',
            creator=self.user,
            visibility=Club.Visibility.PUBLIC,
            club_type=Club.ClubType.SYSTEM_PROFESSIONAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.SYSTEM_MANAGED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

    def build_request(self):
        request = self.factory.post('/clubs/', {}, format='json')
        request.user = self.user
        return request

    def test_read_serializer_exposes_event_state_fields(self):
        start_time = timezone.now() + timedelta(days=2)
        event = ClubEvent.objects.create(
            club=self.fictional_club,
            title='Analysis Session',
            event_type=ClubEvent.EventType.ANALYSIS,
            description='Video review block.',
            start_datetime=start_time,
            end_datetime=start_time + timedelta(hours=2),
            location='Video room',
            is_mandatory=True,
            created_by=self.user,
        )

        data = ClubEventSerializer(event).data

        self.assertEqual(data['club_name'], self.fictional_club.name)
        self.assertEqual(data['event_type'], ClubEvent.EventType.ANALYSIS)
        self.assertEqual(data['event_type_display'], 'Analysis')
        self.assertEqual(data['source_type'], ClubEvent.SourceType.MANUAL)
        self.assertTrue(data['is_user_editable'])
        self.assertFalse(data['is_system_managed_item'])
        self.assertTrue(data['is_future_item'])
        self.assertEqual(data['calendar_label'], 'Analysis Session')

    def test_write_serializer_allows_manual_event_for_user_managed_club(self):
        start_time = timezone.now() + timedelta(days=3)

        serializer = ClubEventWriteSerializer(
            data={
                'title': 'Training Block',
                'event_type': ClubEvent.EventType.TRAINING,
                'description': 'Midweek training.',
                'start_datetime': start_time,
                'end_datetime': start_time + timedelta(hours=2),
                'location': 'Main pitch',
                'is_mandatory': True,
            },
            context={
                'request': self.build_request(),
                'club': self.fictional_club,
            },
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        event = serializer.save(
            club=self.fictional_club,
            created_by=self.user,
        )

        self.assertEqual(event.club, self.fictional_club)
        self.assertEqual(event.source_type, ClubEvent.SourceType.MANUAL)
        self.assertEqual(event.created_by, self.user)

    def test_write_serializer_rejects_manual_event_for_system_club(self):
        start_time = timezone.now() + timedelta(days=4)

        serializer = ClubEventWriteSerializer(
            data={
                'title': 'Blocked Manual Event',
                'event_type': ClubEvent.EventType.MEETING,
                'start_datetime': start_time,
                'end_datetime': start_time + timedelta(hours=1),
            },
            context={
                'request': self.build_request(),
                'club': self.system_club,
            },
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('source_type', serializer.errors)

    def test_write_serializer_rejects_editing_system_managed_event(self):
        start_time = timezone.now() + timedelta(days=5)
        event = ClubEvent.objects.create(
            club=self.system_club,
            title='Provider Event',
            event_type=ClubEvent.EventType.OTHER,
            start_datetime=start_time,
            source_type=ClubEvent.SourceType.PROVIDER,
        )

        serializer = ClubEventWriteSerializer(
            instance=event,
            data={
                'title': 'Attempted Edit',
            },
            partial=True,
            context={
                'request': self.build_request(),
                'club': self.system_club,
            },
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

    def test_write_serializer_surfaces_datetime_validation(self):
        start_time = timezone.now() + timedelta(days=6)

        serializer = ClubEventWriteSerializer(
            data={
                'title': 'Broken Timing Event',
                'event_type': ClubEvent.EventType.OTHER,
                'start_datetime': start_time,
                'end_datetime': start_time - timedelta(hours=1),
            },
            context={
                'request': self.build_request(),
                'club': self.fictional_club,
            },
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('end_datetime', serializer.errors)


class FixtureSerializerTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create_user(
            email='fixture-serializer@example.com',
            password='testpass123',
        )

        self.legacy_club = Club.objects.create(
            name='Legacy Fixture Club',
            description='Legacy club for fixture serializer tests.',
            creator=self.user,
            visibility=Club.Visibility.PRIVATE,
        )

        self.fictional_club = Club.objects.create(
            name='Fixture Serializer Club',
            description='User-managed fixture serializer tests.',
            creator=self.user,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        self.system_club = Club.objects.create(
            name='System Fixture Club',
            description='System-managed fixture serializer tests.',
            creator=self.user,
            visibility=Club.Visibility.PUBLIC,
            club_type=Club.ClubType.SYSTEM_PROFESSIONAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.SYSTEM_MANAGED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

    def build_request(self):
        request = self.factory.post('/clubs/', {}, format='json')
        request.user = self.user
        return request

    def test_read_serializer_exposes_fixture_state_fields(self):
        kickoff = timezone.now() + timedelta(days=7)
        fixture = Fixture.objects.create(
            club=self.fictional_club,
            opponent_name='Ranelagh United',
            venue=Fixture.Venue.HOME,
            competition='Friendly',
            match_datetime=kickoff,
            location='Main ground',
            fixture_status=Fixture.FixtureStatus.SCHEDULED,
            created_by=self.user,
        )

        data = FixtureSerializer(fixture).data

        self.assertEqual(data['club_name'], self.fictional_club.name)
        self.assertEqual(data['venue'], Fixture.Venue.HOME)
        self.assertEqual(data['venue_display'], 'Home')
        self.assertEqual(data['fixture_status'], Fixture.FixtureStatus.SCHEDULED)
        self.assertEqual(data['fixture_status_display'], 'Scheduled')
        self.assertEqual(data['source_type'], Fixture.SourceType.MANUAL)
        self.assertTrue(data['is_user_editable'])
        self.assertFalse(data['is_system_managed_item'])
        self.assertTrue(data['is_future_item'])
        self.assertEqual(data['calendar_label'], 'vs Ranelagh United')

    def test_write_serializer_allows_manual_fixture_for_user_managed_club(self):
        kickoff = timezone.now() + timedelta(days=8)

        serializer = FixtureWriteSerializer(
            data={
                'opponent_name': 'Tallaght Town',
                'venue': Fixture.Venue.AWAY,
                'competition': 'League',
                'match_datetime': kickoff,
                'location': 'Away ground',
                'fixture_status': Fixture.FixtureStatus.SCHEDULED,
            },
            context={
                'request': self.build_request(),
                'club': self.fictional_club,
            },
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        fixture = serializer.save(
            club=self.fictional_club,
            created_by=self.user,
        )

        self.assertEqual(fixture.club, self.fictional_club)
        self.assertEqual(fixture.source_type, Fixture.SourceType.MANUAL)
        self.assertEqual(fixture.created_by, self.user)

    def test_write_serializer_allows_manual_fixture_for_legacy_club(self):
        kickoff = timezone.now() + timedelta(days=9)

        serializer = FixtureWriteSerializer(
            data={
                'opponent_name': 'Legacy Opponent',
                'venue': Fixture.Venue.NEUTRAL,
                'competition': 'Cup',
                'match_datetime': kickoff,
                'fixture_status': Fixture.FixtureStatus.SCHEDULED,
            },
            context={
                'request': self.build_request(),
                'club': self.legacy_club,
            },
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_write_serializer_rejects_manual_fixture_for_system_club(self):
        kickoff = timezone.now() + timedelta(days=10)

        serializer = FixtureWriteSerializer(
            data={
                'opponent_name': 'Blocked Fixture',
                'venue': Fixture.Venue.HOME,
                'competition': 'League',
                'match_datetime': kickoff,
                'fixture_status': Fixture.FixtureStatus.SCHEDULED,
            },
            context={
                'request': self.build_request(),
                'club': self.system_club,
            },
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('source_type', serializer.errors)

    def test_write_serializer_rejects_editing_system_managed_fixture(self):
        kickoff = timezone.now() + timedelta(days=11)
        fixture = Fixture.objects.create(
            club=self.system_club,
            opponent_name='Provider Opponent',
            venue=Fixture.Venue.AWAY,
            competition='League',
            match_datetime=kickoff,
            fixture_status=Fixture.FixtureStatus.SCHEDULED,
            source_type=Fixture.SourceType.PROVIDER,
            external_fixture_id='provider-fixture-001',
        )

        serializer = FixtureWriteSerializer(
            instance=fixture,
            data={
                'location': 'Attempted override',
            },
            partial=True,
            context={
                'request': self.build_request(),
                'club': self.system_club,
            },
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

class ClubSchedulingApiTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.owner = self.create_user_with_roles(
            email='owner-d4@example.com',
            roles=[Role.COACH],
        )
        self.coach_member = self.create_user_with_roles(
            email='coach-member-d4@example.com',
            roles=[Role.COACH],
        )
        self.player_member = self.create_user_with_roles(
            email='player-member-d4@example.com',
            roles=[Role.PLAYER],
        )
        self.outsider = self.create_user_with_roles(
            email='outsider-d4@example.com',
            roles=[Role.FAN],
        )

        self.user_managed_club = Club.objects.create(
            name='User Managed Scheduling Club',
            description='Private user-managed scheduling club.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        self.system_club = Club.objects.create(
            name='System Scheduling Club',
            description='Public system scheduling club.',
            creator=self.owner,
            visibility=Club.Visibility.PUBLIC,
            club_type=Club.ClubType.SYSTEM_PROFESSIONAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.SYSTEM_MANAGED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        ClubMembership.objects.create(
            user=self.owner,
            club=self.user_managed_club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.coach_member,
            club=self.user_managed_club,
            role=ClubMembership.Role.COACH,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.player_member,
            club=self.user_managed_club,
            role=ClubMembership.Role.PLAYER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.coach_member,
            club=self.system_club,
            role=ClubMembership.Role.COACH,
            is_active=True,
        )

    def create_user_with_roles(self, email, roles=None):
        user = get_user_model().objects.create_user(
            email=email,
            password='testpass123'
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)

        for role in roles or []:
            UserRole.objects.create(
                user_profile=profile,
                role=role,
            )

        return user

    def test_member_can_list_private_club_events(self):
        event = ClubEvent.objects.create(
            club=self.user_managed_club,
            title='Training',
            event_type=ClubEvent.EventType.TRAINING,
            start_datetime=timezone.now() + timedelta(days=1),
            created_by=self.owner,
        )

        view = ClubEventViewSet.as_view({'get': 'list'})
        request = self.factory.get(f'/clubs/{self.user_managed_club.id}/events/')
        force_authenticate(request, user=self.coach_member)

        response = view(request, club_pk=self.user_managed_club.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], event.id)

    def test_non_member_cannot_list_private_club_events(self):
        ClubEvent.objects.create(
            club=self.user_managed_club,
            title='Private Event',
            event_type=ClubEvent.EventType.MEETING,
            start_datetime=timezone.now() + timedelta(days=1),
            created_by=self.owner,
        )

        view = ClubEventViewSet.as_view({'get': 'list'})
        request = self.factory.get(f'/clubs/{self.user_managed_club.id}/events/')
        force_authenticate(request, user=self.outsider)

        response = view(request, club_pk=self.user_managed_club.id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_coach_can_create_manual_event_for_user_managed_club(self):
        view = ClubEventViewSet.as_view({'post': 'create'})
        request = self.factory.post(
            f'/clubs/{self.user_managed_club.id}/events/',
            {
                'title': 'Analysis Session',
                'event_type': ClubEvent.EventType.ANALYSIS,
                'start_datetime': (timezone.now() + timedelta(days=2)).isoformat(),
                'end_datetime': (timezone.now() + timedelta(days=2, hours=2)).isoformat(),
                'location': 'Video room',
                'is_mandatory': True,
            },
            format='json',
        )
        force_authenticate(request, user=self.coach_member)

        response = view(request, club_pk=self.user_managed_club.id)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Analysis Session')
        self.assertEqual(response.data['source_type'], ClubEvent.SourceType.MANUAL)

    def test_player_member_cannot_create_manual_event(self):
        view = ClubEventViewSet.as_view({'post': 'create'})
        request = self.factory.post(
            f'/clubs/{self.user_managed_club.id}/events/',
            {
                'title': 'Blocked Event',
                'event_type': ClubEvent.EventType.TRAINING,
                'start_datetime': (timezone.now() + timedelta(days=2)).isoformat(),
            },
            format='json',
        )
        force_authenticate(request, user=self.player_member)

        response = view(request, club_pk=self.user_managed_club.id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_system_club_manual_event_create_is_forbidden(self):
        view = ClubEventViewSet.as_view({'post': 'create'})
        request = self.factory.post(
            f'/clubs/{self.system_club.id}/events/',
            {
                'title': 'Blocked System Event',
                'event_type': ClubEvent.EventType.MEETING,
                'start_datetime': (timezone.now() + timedelta(days=3)).isoformat(),
            },
            format='json',
        )
        force_authenticate(request, user=self.coach_member)

        response = view(request, club_pk=self.system_club.id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_non_member_can_list_public_system_fixtures(self):
        fixture = Fixture.objects.create(
            club=self.system_club,
            opponent_name='Provider Opponent',
            venue=Fixture.Venue.AWAY,
            competition='League',
            match_datetime=timezone.now() + timedelta(days=4),
            fixture_status=Fixture.FixtureStatus.SCHEDULED,
            source_type=Fixture.SourceType.PROVIDER,
            external_fixture_id='provider-fixture-200',
        )

        view = FixtureViewSet.as_view({'get': 'list'})
        request = self.factory.get(f'/clubs/{self.system_club.id}/fixtures/')
        force_authenticate(request, user=self.outsider)

        response = view(request, club_pk=self.system_club.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], fixture.id)

    def test_coach_can_create_manual_fixture_for_user_managed_club(self):
        view = FixtureViewSet.as_view({'post': 'create'})
        request = self.factory.post(
            f'/clubs/{self.user_managed_club.id}/fixtures/',
            {
                'opponent_name': 'Ranelagh United',
                'venue': Fixture.Venue.HOME,
                'competition': 'Friendly',
                'match_datetime': (timezone.now() + timedelta(days=5)).isoformat(),
                'location': 'Main pitch',
                'fixture_status': Fixture.FixtureStatus.SCHEDULED,
            },
            format='json',
        )
        force_authenticate(request, user=self.coach_member)

        response = view(request, club_pk=self.user_managed_club.id)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['opponent_name'], 'Ranelagh United')
        self.assertEqual(response.data['source_type'], Fixture.SourceType.MANUAL)

    def test_player_member_cannot_create_manual_fixture(self):
        view = FixtureViewSet.as_view({'post': 'create'})
        request = self.factory.post(
            f'/clubs/{self.user_managed_club.id}/fixtures/',
            {
                'opponent_name': 'Blocked Fixture',
                'venue': Fixture.Venue.HOME,
                'competition': 'League',
                'match_datetime': (timezone.now() + timedelta(days=6)).isoformat(),
                'fixture_status': Fixture.FixtureStatus.SCHEDULED,
            },
            format='json',
        )
        force_authenticate(request, user=self.player_member)

        response = view(request, club_pk=self.user_managed_club.id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_system_managed_fixture_cannot_be_deleted_through_ordinary_flow(self):
        fixture = Fixture.objects.create(
            club=self.system_club,
            opponent_name='Protected Provider Fixture',
            venue=Fixture.Venue.AWAY,
            competition='League',
            match_datetime=timezone.now() + timedelta(days=7),
            fixture_status=Fixture.FixtureStatus.SCHEDULED,
            source_type=Fixture.SourceType.PROVIDER,
            external_fixture_id='provider-fixture-201',
        )

        view = FixtureViewSet.as_view({'delete': 'destroy'})
        request = self.factory.delete(f'/clubs/{self.system_club.id}/fixtures/{fixture.id}/')
        force_authenticate(request, user=self.coach_member)

        response = view(request, club_pk=self.system_club.id, pk=fixture.id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Fixture.objects.filter(id=fixture.id).exists())

class ClubCalendarFeedTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.owner = self.create_user_with_roles(
            email='owner-d5@example.com',
            roles=[Role.COACH],
        )
        self.member = self.create_user_with_roles(
            email='member-d5@example.com',
            roles=[Role.COACH],
        )
        self.outsider = self.create_user_with_roles(
            email='outsider-d5@example.com',
            roles=[Role.FAN],
        )

        self.private_club = Club.objects.create(
            name='Private Calendar Club',
            description='Private club for combined calendar tests.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.HIDDEN_CODE_ONLY,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        self.public_system_club = Club.objects.create(
            name='Public System Calendar Club',
            description='Public system club for combined calendar tests.',
            creator=self.owner,
            visibility=Club.Visibility.PUBLIC,
            club_type=Club.ClubType.SYSTEM_PROFESSIONAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.SYSTEM_MANAGED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        ClubMembership.objects.create(
            user=self.owner,
            club=self.private_club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.member,
            club=self.private_club,
            role=ClubMembership.Role.COACH,
            is_active=True,
        )

    def create_user_with_roles(self, email, roles=None):
        user = get_user_model().objects.create_user(
            email=email,
            password='testpass123'
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)

        for role in roles or []:
            UserRole.objects.create(
                user_profile=profile,
                role=role,
            )

        return user

    def test_calendar_feed_serializer_returns_nested_event_and_fixture_shapes(self):
        start_time = timezone.now() + timedelta(days=1)
        event = ClubEvent.objects.create(
            club=self.private_club,
            title='Training Session',
            event_type=ClubEvent.EventType.TRAINING,
            start_datetime=start_time,
            created_by=self.owner,
        )
        fixture = Fixture.objects.create(
            club=self.private_club,
            opponent_name='Ranelagh United',
            venue=Fixture.Venue.HOME,
            competition='Friendly',
            match_datetime=start_time + timedelta(hours=4),
            fixture_status=Fixture.FixtureStatus.SCHEDULED,
            created_by=self.owner,
        )

        serializer = ClubCalendarFeedItemSerializer(
            [
                {
                    'item_type': 'event',
                    'sort_datetime': event.start_datetime,
                    'calendar_label': event.get_calendar_label(),
                    'event': event,
                    'fixture': None,
                },
                {
                    'item_type': 'fixture',
                    'sort_datetime': fixture.match_datetime,
                    'calendar_label': fixture.get_calendar_label(),
                    'event': None,
                    'fixture': fixture,
                },
            ],
            many=True,
        )

        data = serializer.data

        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['item_type'], 'event')
        self.assertIsNotNone(data[0]['event'])
        self.assertIsNone(data[0]['fixture'])
        self.assertEqual(data[1]['item_type'], 'fixture')
        self.assertIsNotNone(data[1]['fixture'])
        self.assertIsNone(data[1]['event'])

    def test_member_can_read_private_club_calendar_feed_in_chronological_order(self):
        now = timezone.now()

        later_event = ClubEvent.objects.create(
            club=self.private_club,
            title='Later Event',
            event_type=ClubEvent.EventType.MEETING,
            start_datetime=now + timedelta(days=3),
            created_by=self.owner,
        )
        earlier_fixture = Fixture.objects.create(
            club=self.private_club,
            opponent_name='Early Opponent',
            venue=Fixture.Venue.AWAY,
            competition='League',
            match_datetime=now + timedelta(days=1),
            fixture_status=Fixture.FixtureStatus.SCHEDULED,
            created_by=self.owner,
        )
        middle_event = ClubEvent.objects.create(
            club=self.private_club,
            title='Middle Event',
            event_type=ClubEvent.EventType.ANALYSIS,
            start_datetime=now + timedelta(days=2),
            created_by=self.owner,
        )

        view = ClubViewSet.as_view({'get': 'calendar'})
        request = self.factory.get(f'/clubs/{self.private_club.id}/calendar/')
        force_authenticate(request, user=self.member)

        response = view(request, pk=self.private_club.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['item_type'], 'fixture')
        self.assertEqual(response.data[0]['fixture']['id'], earlier_fixture.id)
        self.assertEqual(response.data[1]['item_type'], 'event')
        self.assertEqual(response.data[1]['event']['id'], middle_event.id)
        self.assertEqual(response.data[2]['item_type'], 'event')
        self.assertEqual(response.data[2]['event']['id'], later_event.id)

    def test_private_club_calendar_feed_blocks_non_member(self):
        ClubEvent.objects.create(
            club=self.private_club,
            title='Private Event',
            event_type=ClubEvent.EventType.TRAINING,
            start_datetime=timezone.now() + timedelta(days=1),
            created_by=self.owner,
        )

        view = ClubViewSet.as_view({'get': 'calendar'})
        request = self.factory.get(f'/clubs/{self.private_club.id}/calendar/')
        force_authenticate(request, user=self.outsider)

        response = view(request, pk=self.private_club.id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_system_club_calendar_feed_is_readable_to_authenticated_non_member(self):
        ClubEvent.objects.create(
            club=self.public_system_club,
            title='Public Provider Event',
            event_type=ClubEvent.EventType.OTHER,
            start_datetime=timezone.now() + timedelta(days=1),
            source_type=ClubEvent.SourceType.PROVIDER,
        )
        fixture = Fixture.objects.create(
            club=self.public_system_club,
            opponent_name='Provider Opponent',
            venue=Fixture.Venue.AWAY,
            competition='League',
            match_datetime=timezone.now() + timedelta(days=2),
            fixture_status=Fixture.FixtureStatus.SCHEDULED,
            source_type=Fixture.SourceType.PROVIDER,
            external_fixture_id='system-public-fixture-001',
        )

        view = ClubViewSet.as_view({'get': 'calendar'})
        request = self.factory.get(f'/clubs/{self.public_system_club.id}/calendar/')
        force_authenticate(request, user=self.outsider)

        response = view(request, pk=self.public_system_club.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        fixture_items = [item for item in response.data if item['item_type'] == 'fixture']
        self.assertEqual(len(fixture_items), 1)
        self.assertEqual(fixture_items[0]['fixture']['id'], fixture.id)

    def test_calendar_feed_limit_parameter_is_applied(self):
        base_time = timezone.now() + timedelta(days=1)

        ClubEvent.objects.create(
            club=self.private_club,
            title='Event 1',
            event_type=ClubEvent.EventType.TRAINING,
            start_datetime=base_time,
            created_by=self.owner,
        )
        ClubEvent.objects.create(
            club=self.private_club,
            title='Event 2',
            event_type=ClubEvent.EventType.MEETING,
            start_datetime=base_time + timedelta(hours=1),
            created_by=self.owner,
        )
        Fixture.objects.create(
            club=self.private_club,
            opponent_name='Event 3 Opponent',
            venue=Fixture.Venue.HOME,
            competition='Cup',
            match_datetime=base_time + timedelta(hours=2),
            fixture_status=Fixture.FixtureStatus.SCHEDULED,
            created_by=self.owner,
        )

        view = ClubViewSet.as_view({'get': 'calendar'})
        request = self.factory.get(
            f'/clubs/{self.private_club.id}/calendar/',
            {'limit': '2'},
        )
        force_authenticate(request, user=self.member)

        response = view(request, pk=self.private_club.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_calendar_feed_can_include_past_items_when_requested(self):
        ClubEvent.objects.create(
            club=self.private_club,
            title='Past Event',
            event_type=ClubEvent.EventType.SOCIAL,
            start_datetime=timezone.now() - timedelta(days=1),
            created_by=self.owner,
        )
        ClubEvent.objects.create(
            club=self.private_club,
            title='Future Event',
            event_type=ClubEvent.EventType.TRAINING,
            start_datetime=timezone.now() + timedelta(days=1),
            created_by=self.owner,
        )

        view = ClubViewSet.as_view({'get': 'calendar'})
        request = self.factory.get(
            f'/clubs/{self.private_club.id}/calendar/',
            {'include_past': 'true'},
        )
        force_authenticate(request, user=self.member)

        response = view(request, pk=self.private_club.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_calendar_feed_rejects_invalid_limit(self):
        view = ClubViewSet.as_view({'get': 'calendar'})
        request = self.factory.get(
            f'/clubs/{self.private_club.id}/calendar/',
            {'limit': 'abc'},
        )
        force_authenticate(request, user=self.member)

        response = view(request, pk=self.private_club.id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

class ClubSchedulingMutationApiTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.owner = self.create_user_with_roles(
            email='owner-d8@example.com',
            roles=[Role.COACH],
        )
        self.coach_member = self.create_user_with_roles(
            email='coach-member-d8@example.com',
            roles=[Role.COACH],
        )
        self.player_member = self.create_user_with_roles(
            email='player-member-d8@example.com',
            roles=[Role.PLAYER],
        )
        self.outsider = self.create_user_with_roles(
            email='outsider-d8@example.com',
            roles=[Role.FAN],
        )

        self.user_managed_club = Club.objects.create(
            name='D8 User Managed Club',
            description='Private user-managed club for scheduling mutation tests.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        self.system_club = Club.objects.create(
            name='D8 System Club',
            description='Public system-managed club for scheduling mutation tests.',
            creator=self.owner,
            visibility=Club.Visibility.PUBLIC,
            club_type=Club.ClubType.SYSTEM_PROFESSIONAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.SYSTEM_MANAGED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        ClubMembership.objects.create(
            user=self.owner,
            club=self.user_managed_club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.coach_member,
            club=self.user_managed_club,
            role=ClubMembership.Role.COACH,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.player_member,
            club=self.user_managed_club,
            role=ClubMembership.Role.PLAYER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.coach_member,
            club=self.system_club,
            role=ClubMembership.Role.COACH,
            is_active=True,
        )

        self.manual_event = ClubEvent.objects.create(
            club=self.user_managed_club,
            title='Manual Training',
            event_type=ClubEvent.EventType.TRAINING,
            start_datetime=timezone.now() + timedelta(days=2),
            end_datetime=timezone.now() + timedelta(days=2, hours=2),
            location='Main pitch',
            source_type=ClubEvent.SourceType.MANUAL,
            created_by=self.owner,
        )

        self.manual_fixture = Fixture.objects.create(
            club=self.user_managed_club,
            opponent_name='Ranelagh United',
            venue=Fixture.Venue.HOME,
            competition='Friendly',
            match_datetime=timezone.now() + timedelta(days=3),
            location='Main ground',
            fixture_status=Fixture.FixtureStatus.SCHEDULED,
            source_type=Fixture.SourceType.MANUAL,
            created_by=self.owner,
        )

        self.provider_event = ClubEvent.objects.create(
            club=self.system_club,
            title='Provider Event',
            event_type=ClubEvent.EventType.OTHER,
            start_datetime=timezone.now() + timedelta(days=4),
            source_type=ClubEvent.SourceType.PROVIDER,
        )

        self.provider_fixture = Fixture.objects.create(
            club=self.system_club,
            opponent_name='Provider Opponent',
            venue=Fixture.Venue.AWAY,
            competition='League',
            match_datetime=timezone.now() + timedelta(days=5),
            fixture_status=Fixture.FixtureStatus.SCHEDULED,
            source_type=Fixture.SourceType.PROVIDER,
            external_fixture_id='provider-fixture-d8-001',
        )

    def create_user_with_roles(self, email, roles=None):
        user = get_user_model().objects.create_user(
            email=email,
            password='testpass123'
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)

        for role in roles or []:
            UserRole.objects.create(
                user_profile=profile,
                role=role,
            )

        return user

    def test_coach_can_patch_manual_event_for_user_managed_club(self):
        view = ClubEventViewSet.as_view({'patch': 'partial_update'})
        request = self.factory.patch(
            f'/clubs/{self.user_managed_club.id}/events/{self.manual_event.id}/',
            {
                'title': 'Updated Training Block',
                'location': 'Indoor dome',
            },
            format='json',
        )
        force_authenticate(request, user=self.coach_member)

        response = view(
            request,
            club_pk=self.user_managed_club.id,
            pk=self.manual_event.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.manual_event.refresh_from_db()
        self.assertEqual(self.manual_event.title, 'Updated Training Block')
        self.assertEqual(self.manual_event.location, 'Indoor dome')

    def test_coach_can_delete_manual_event_for_user_managed_club(self):
        view = ClubEventViewSet.as_view({'delete': 'destroy'})
        request = self.factory.delete(
            f'/clubs/{self.user_managed_club.id}/events/{self.manual_event.id}/'
        )
        force_authenticate(request, user=self.coach_member)

        response = view(
            request,
            club_pk=self.user_managed_club.id,
            pk=self.manual_event.id,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ClubEvent.objects.filter(id=self.manual_event.id).exists())

    def test_player_member_cannot_patch_manual_event(self):
        view = ClubEventViewSet.as_view({'patch': 'partial_update'})
        request = self.factory.patch(
            f'/clubs/{self.user_managed_club.id}/events/{self.manual_event.id}/',
            {
                'title': 'Blocked Player Edit',
            },
            format='json',
        )
        force_authenticate(request, user=self.player_member)

        response = view(
            request,
            club_pk=self.user_managed_club.id,
            pk=self.manual_event.id,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.manual_event.refresh_from_db()
        self.assertEqual(self.manual_event.title, 'Manual Training')

    def test_provider_event_cannot_be_patched_through_ordinary_flow(self):
        view = ClubEventViewSet.as_view({'patch': 'partial_update'})
        request = self.factory.patch(
            f'/clubs/{self.system_club.id}/events/{self.provider_event.id}/',
            {
                'title': 'Blocked Provider Edit',
            },
            format='json',
        )
        force_authenticate(request, user=self.coach_member)

        response = view(
            request,
            club_pk=self.system_club.id,
            pk=self.provider_event.id,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.provider_event.refresh_from_db()
        self.assertEqual(self.provider_event.title, 'Provider Event')

    def test_provider_event_cannot_be_deleted_through_ordinary_flow(self):
        view = ClubEventViewSet.as_view({'delete': 'destroy'})
        request = self.factory.delete(
            f'/clubs/{self.system_club.id}/events/{self.provider_event.id}/'
        )
        force_authenticate(request, user=self.coach_member)

        response = view(
            request,
            club_pk=self.system_club.id,
            pk=self.provider_event.id,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(ClubEvent.objects.filter(id=self.provider_event.id).exists())

    def test_coach_can_patch_manual_fixture_for_user_managed_club(self):
        view = FixtureViewSet.as_view({'patch': 'partial_update'})
        request = self.factory.patch(
            f'/clubs/{self.user_managed_club.id}/fixtures/{self.manual_fixture.id}/',
            {
                'location': 'Updated Ground',
                'competition': 'League',
            },
            format='json',
        )
        force_authenticate(request, user=self.coach_member)

        response = view(
            request,
            club_pk=self.user_managed_club.id,
            pk=self.manual_fixture.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.manual_fixture.refresh_from_db()
        self.assertEqual(self.manual_fixture.location, 'Updated Ground')
        self.assertEqual(self.manual_fixture.competition, 'League')

    def test_coach_can_delete_manual_fixture_for_user_managed_club(self):
        view = FixtureViewSet.as_view({'delete': 'destroy'})
        request = self.factory.delete(
            f'/clubs/{self.user_managed_club.id}/fixtures/{self.manual_fixture.id}/'
        )
        force_authenticate(request, user=self.coach_member)

        response = view(
            request,
            club_pk=self.user_managed_club.id,
            pk=self.manual_fixture.id,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Fixture.objects.filter(id=self.manual_fixture.id).exists())

    def test_player_member_cannot_patch_manual_fixture(self):
        view = FixtureViewSet.as_view({'patch': 'partial_update'})
        request = self.factory.patch(
            f'/clubs/{self.user_managed_club.id}/fixtures/{self.manual_fixture.id}/',
            {
                'competition': 'Blocked Player Edit',
            },
            format='json',
        )
        force_authenticate(request, user=self.player_member)

        response = view(
            request,
            club_pk=self.user_managed_club.id,
            pk=self.manual_fixture.id,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.manual_fixture.refresh_from_db()
        self.assertEqual(self.manual_fixture.competition, 'Friendly')

    def test_provider_fixture_cannot_be_patched_through_ordinary_flow(self):
        view = FixtureViewSet.as_view({'patch': 'partial_update'})
        request = self.factory.patch(
            f'/clubs/{self.system_club.id}/fixtures/{self.provider_fixture.id}/',
            {
                'location': 'Blocked Provider Override',
            },
            format='json',
        )
        force_authenticate(request, user=self.coach_member)

        response = view(
            request,
            club_pk=self.system_club.id,
            pk=self.provider_fixture.id,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.provider_fixture.refresh_from_db()
        self.assertEqual(self.provider_fixture.location, '')

    def test_provider_fixture_cannot_be_deleted_through_ordinary_flow(self):
        view = FixtureViewSet.as_view({'delete': 'destroy'})
        request = self.factory.delete(
            f'/clubs/{self.system_club.id}/fixtures/{self.provider_fixture.id}/'
        )
        force_authenticate(request, user=self.coach_member)

        response = view(
            request,
            club_pk=self.system_club.id,
            pk=self.provider_fixture.id,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Fixture.objects.filter(id=self.provider_fixture.id).exists())

class ClubResourceModelTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            email='resource-owner@example.com',
            password='testpass123',
        )
        self.member = get_user_model().objects.create_user(
            email='resource-member@example.com',
            password='testpass123',
        )

        self.club = Club.objects.create(
            name='Resources Club',
            description='Club resource model tests.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        ClubMembership.objects.create(
            user=self.owner,
            club=self.club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.member,
            club=self.club,
            role=ClubMembership.Role.PLAYER,
            is_active=True,
        )

    def make_uploaded_file(
        self,
        name='match-plan.pdf',
        content=b'%PDF-1.4 club resource test',
        content_type='application/pdf',
    ):
        return SimpleUploadedFile(
            name=name,
            content=content,
            content_type=content_type,
        )

    def test_can_create_club_resource_with_expected_defaults(self):
        uploaded_file = self.make_uploaded_file()

        resource = ClubResource.objects.create(
            club=self.club,
            uploaded_by=self.owner,
            title='Match Plan',
            description='Pre-match PDF for the squad.',
            file=uploaded_file,
            original_filename='match-plan.pdf',
            mime_type='application/pdf',
            file_size_bytes=uploaded_file.size,
            file_kind=ClubResource.FileKind.PDF,
            storage_backend=ClubResource.StorageBackend.LOCAL,
            storage_key='clubs/resources/test-match-plan.pdf',
            total_pages=8,
        )

        self.assertEqual(resource.club, self.club)
        self.assertEqual(resource.uploaded_by, self.owner)
        self.assertEqual(resource.file_kind, ClubResource.FileKind.PDF)
        self.assertEqual(resource.storage_backend, ClubResource.StorageBackend.LOCAL)
        self.assertEqual(
            resource.engagement_visibility,
            ClubResource.EngagementVisibility.STAFF_ONLY,
        )
        self.assertFalse(resource.is_archived)
        self.assertEqual(resource.total_pages, 8)

    def test_can_create_club_resource_with_club_visible_engagement(self):
        uploaded_file = self.make_uploaded_file(name='poster.png', content_type='image/png')

        resource = ClubResource.objects.create(
            club=self.club,
            uploaded_by=self.owner,
            title='Match Poster',
            description='Team poster image.',
            file=uploaded_file,
            original_filename='poster.png',
            mime_type='image/png',
            file_size_bytes=uploaded_file.size,
            file_kind=ClubResource.FileKind.IMAGE,
            storage_backend=ClubResource.StorageBackend.LOCAL,
            storage_key='clubs/resources/poster.png',
            engagement_visibility=ClubResource.EngagementVisibility.CLUB_VISIBLE,
        )

        self.assertEqual(
            resource.engagement_visibility,
            ClubResource.EngagementVisibility.CLUB_VISIBLE,
        )
        self.assertEqual(resource.file_kind, ClubResource.FileKind.IMAGE)

    def test_can_create_summary_view_row_for_user_resource_pair(self):
        uploaded_file = self.make_uploaded_file()

        resource = ClubResource.objects.create(
            club=self.club,
            uploaded_by=self.owner,
            title='Session Plan',
            file=uploaded_file,
            original_filename='session-plan.pdf',
            mime_type='application/pdf',
            file_size_bytes=uploaded_file.size,
            file_kind=ClubResource.FileKind.PDF,
            storage_backend=ClubResource.StorageBackend.LOCAL,
            storage_key='clubs/resources/session-plan.pdf',
            total_pages=5,
        )

        view_summary = ClubResourceView.objects.create(
            resource=resource,
            user=self.member,
        )

        self.assertEqual(view_summary.resource, resource)
        self.assertEqual(view_summary.user, self.member)
        self.assertFalse(view_summary.opened)
        self.assertFalse(view_summary.completed)
        self.assertEqual(view_summary.total_active_seconds, 0)
        self.assertEqual(view_summary.highest_page_reached, 0)
        self.assertIsNone(view_summary.first_opened_at)
        self.assertIsNone(view_summary.last_opened_at)

    def test_unique_summary_row_is_enforced_per_user_resource_pair(self):
        uploaded_file = self.make_uploaded_file()

        resource = ClubResource.objects.create(
            club=self.club,
            uploaded_by=self.owner,
            title='Analysis Pack',
            file=uploaded_file,
            original_filename='analysis-pack.pdf',
            mime_type='application/pdf',
            file_size_bytes=uploaded_file.size,
            file_kind=ClubResource.FileKind.PDF,
            storage_backend=ClubResource.StorageBackend.LOCAL,
            storage_key='clubs/resources/analysis-pack.pdf',
        )

        ClubResourceView.objects.create(
            resource=resource,
            user=self.member,
        )

        with self.assertRaises(IntegrityError):
            ClubResourceView.objects.create(
                resource=resource,
                user=self.member,
            )

class ClubResourceModelTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            email='resource-owner@example.com',
            password='testpass123',
        )
        self.member = get_user_model().objects.create_user(
            email='resource-member@example.com',
            password='testpass123',
        )

        self.club = Club.objects.create(
            name='Resources Club',
            description='Club resource model tests.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        ClubMembership.objects.create(
            user=self.owner,
            club=self.club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.member,
            club=self.club,
            role=ClubMembership.Role.PLAYER,
            is_active=True,
        )

    def make_uploaded_file(
        self,
        name='match-plan.pdf',
        content=b'%PDF-1.4 club resource test',
        content_type='application/pdf',
    ):
        return SimpleUploadedFile(
            name=name,
            content=content,
            content_type=content_type,
        )

    def create_resource(self, **overrides):
        uploaded_file = overrides.pop('file', self.make_uploaded_file())

        data = {
            'club': self.club,
            'uploaded_by': self.owner,
            'title': 'Match Plan',
            'description': 'Pre-match resource.',
            'file': uploaded_file,
            'original_filename': uploaded_file.name,
            'mime_type': uploaded_file.content_type,
            'file_size_bytes': uploaded_file.size,
            'file_kind': ClubResource.FileKind.PDF,
            'storage_backend': ClubResource.StorageBackend.LOCAL,
            'storage_key': 'clubs/resources/test-match-plan.pdf',
            'total_pages': 8,
        }
        data.update(overrides)
        return ClubResource.objects.create(**data)

    def test_valid_pdf_resource_is_created_with_expected_defaults(self):
        resource = self.create_resource()

        self.assertEqual(resource.file_kind, ClubResource.FileKind.PDF)
        self.assertEqual(
            resource.engagement_visibility,
            ClubResource.EngagementVisibility.STAFF_ONLY,
        )
        self.assertTrue(resource.is_pdf())
        self.assertTrue(resource.can_inline_view())
        self.assertFalse(resource.is_download_only())
        self.assertFalse(resource.is_archived)

    def test_valid_image_resource_is_accepted_but_not_inline_viewable(self):
        uploaded_file = self.make_uploaded_file(
            name='poster.png',
            content=b'png-bytes',
            content_type='image/png',
        )

        resource = self.create_resource(
            file=uploaded_file,
            original_filename='poster.png',
            mime_type='image/png',
            file_size_bytes=uploaded_file.size,
            file_kind=ClubResource.FileKind.IMAGE,
            total_pages=None,
            storage_key='clubs/resources/poster.png',
        )

        self.assertTrue(resource.is_image())
        self.assertFalse(resource.is_pdf())
        self.assertFalse(resource.can_inline_view())
        self.assertTrue(resource.is_download_only())

    def test_invalid_mime_type_for_file_kind_is_rejected(self):
        uploaded_file = self.make_uploaded_file(
            name='notes.docx',
            content=b'docx-bytes',
            content_type='application/pdf',
        )

        resource = ClubResource(
            club=self.club,
            uploaded_by=self.owner,
            title='Notes',
            file=uploaded_file,
            original_filename='notes.docx',
            mime_type='application/pdf',
            file_size_bytes=uploaded_file.size,
            file_kind=ClubResource.FileKind.DOCX,
            storage_backend=ClubResource.StorageBackend.LOCAL,
            storage_key='clubs/resources/notes.docx',
        )

        with self.assertRaises(ValidationError) as context:
            resource.full_clean()

        self.assertIn('mime_type', context.exception.message_dict)

    def test_invalid_extension_for_file_kind_is_rejected(self):
        uploaded_file = self.make_uploaded_file(
            name='notes.pdf',
            content=b'%PDF fake',
            content_type='application/pdf',
        )

        resource = ClubResource(
            club=self.club,
            uploaded_by=self.owner,
            title='Spreadsheet Mismatch',
            file=uploaded_file,
            original_filename='notes.pdf',
            mime_type='application/pdf',
            file_size_bytes=uploaded_file.size,
            file_kind=ClubResource.FileKind.XLSX,
            storage_backend=ClubResource.StorageBackend.LOCAL,
            storage_key='clubs/resources/notes.pdf',
        )

        with self.assertRaises(ValidationError) as context:
            resource.full_clean()

        self.assertIn('original_filename', context.exception.message_dict)

    def test_file_size_limit_is_enforced(self):
        resource = ClubResource(
            club=self.club,
            uploaded_by=self.owner,
            title='Oversized Resource',
            file=self.make_uploaded_file(),
            original_filename='oversized.pdf',
            mime_type='application/pdf',
            file_size_bytes=ClubResource.MAX_FILE_SIZE_BYTES + 1,
            file_kind=ClubResource.FileKind.PDF,
            storage_backend=ClubResource.StorageBackend.LOCAL,
            storage_key='clubs/resources/oversized.pdf',
            total_pages=3,
        )

        with self.assertRaises(ValidationError) as context:
            resource.full_clean()

        self.assertIn('file_size_bytes', context.exception.message_dict)

    def test_total_pages_is_only_valid_for_pdf_resources(self):
        uploaded_file = self.make_uploaded_file(
            name='poster.png',
            content=b'png-bytes',
            content_type='image/png',
        )

        resource = ClubResource(
            club=self.club,
            uploaded_by=self.owner,
            title='Poster',
            file=uploaded_file,
            original_filename='poster.png',
            mime_type='image/png',
            file_size_bytes=uploaded_file.size,
            file_kind=ClubResource.FileKind.IMAGE,
            storage_backend=ClubResource.StorageBackend.LOCAL,
            storage_key='clubs/resources/poster.png',
            total_pages=2,
        )

        with self.assertRaises(ValidationError) as context:
            resource.full_clean()

        self.assertIn('total_pages', context.exception.message_dict)

    def test_archive_and_unarchive_helpers_work(self):
        resource = self.create_resource()
        self.assertFalse(resource.is_archived)

        resource.archive()
        resource.refresh_from_db()
        self.assertTrue(resource.is_archived)

        resource.unarchive()
        resource.refresh_from_db()
        self.assertFalse(resource.is_archived)

    def test_summary_view_row_defaults_are_sane(self):
        resource = self.create_resource()

        view_summary = ClubResourceView.objects.create(
            resource=resource,
            user=self.member,
        )

        self.assertFalse(view_summary.opened)
        self.assertFalse(view_summary.completed)
        self.assertEqual(view_summary.total_active_seconds, 0)
        self.assertEqual(view_summary.highest_page_reached, 0)

    def test_unique_summary_row_is_enforced_per_user_resource_pair(self):
        resource = self.create_resource()

        ClubResourceView.objects.create(
            resource=resource,
            user=self.member,
        )

        with self.assertRaises(IntegrityError):
            ClubResourceView.objects.create(
                resource=resource,
                user=self.member,
            )

    def test_pdf_progress_caps_delta_and_marks_completed_when_thresholds_met(self):
        resource = self.create_resource(total_pages=4)

        view_summary = ClubResourceView.objects.create(
            resource=resource,
            user=self.member,
        )

        view_summary.update_progress(active_seconds_delta=999, page_reached=99)
        view_summary.save()

        self.assertTrue(view_summary.opened)
        self.assertEqual(
            view_summary.total_active_seconds,
            ClubResourceView.MAX_ACTIVE_SECONDS_DELTA,
        )
        self.assertEqual(view_summary.highest_page_reached, 4)
        self.assertTrue(view_summary.completed)

    def test_pdf_completion_stays_false_without_enough_active_time(self):
        resource = self.create_resource(total_pages=5)

        view_summary = ClubResourceView.objects.create(
            resource=resource,
            user=self.member,
        )

        view_summary.update_progress(
            active_seconds_delta=ClubResourceView.MIN_PDF_COMPLETION_ACTIVE_SECONDS - 1,
            page_reached=5,
        )
        view_summary.save()

        self.assertTrue(view_summary.opened)
        self.assertFalse(view_summary.completed)

    def test_non_pdf_completion_uses_opened_plus_minimum_active_time(self):
        uploaded_file = self.make_uploaded_file(
            name='report.docx',
            content=b'docx-bytes',
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )

        resource = self.create_resource(
            file=uploaded_file,
            original_filename='report.docx',
            mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            file_size_bytes=uploaded_file.size,
            file_kind=ClubResource.FileKind.DOCX,
            total_pages=None,
            storage_key='clubs/resources/report.docx',
        )

        view_summary = ClubResourceView.objects.create(
            resource=resource,
            user=self.member,
        )

        view_summary.update_progress(
            active_seconds_delta=ClubResourceView.MIN_NON_PDF_COMPLETION_ACTIVE_SECONDS,
        )
        view_summary.save()

        self.assertTrue(view_summary.opened)
        self.assertTrue(view_summary.completed)

    def test_non_pdf_cannot_store_page_progress(self):
        uploaded_file = self.make_uploaded_file(
            name='poster.png',
            content=b'png-bytes',
            content_type='image/png',
        )

        resource = self.create_resource(
            file=uploaded_file,
            original_filename='poster.png',
            mime_type='image/png',
            file_size_bytes=uploaded_file.size,
            file_kind=ClubResource.FileKind.IMAGE,
            total_pages=None,
            storage_key='clubs/resources/poster.png',
        )

        view_summary = ClubResourceView(
            resource=resource,
            user=self.member,
            opened=True,
            first_opened_at=timezone.now(),
            last_opened_at=timezone.now(),
            highest_page_reached=1,
        )

        with self.assertRaises(ValidationError) as context:
            view_summary.full_clean()

        self.assertIn('highest_page_reached', context.exception.message_dict)

class ClubResourceSerializerTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.owner = get_user_model().objects.create_user(
            email='resource-serializer-owner@example.com',
            password='testpass123',
        )
        self.member = get_user_model().objects.create_user(
            email='resource-serializer-member@example.com',
            password='testpass123',
        )

        self.club = Club.objects.create(
            name='Serializer Resources Club',
            description='Club for resource serializer tests.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        ClubMembership.objects.create(
            user=self.owner,
            club=self.club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.member,
            club=self.club,
            role=ClubMembership.Role.PLAYER,
            is_active=True,
        )

    def build_request(self):
        request = self.factory.post('/clubs/', {}, format='multipart')
        request.user = self.owner
        return request

    def perform(self, view, user, method='get', data=None, **kwargs):
        request_method = getattr(self.factory, method)
        request = request_method('/clubs/', data or {}, format='json')
        force_authenticate(request, user=user)
        return view(request, **kwargs)

    def make_uploaded_file(
        self,
        name='resource.pdf',
        content=b'%PDF-1.4 serializer test',
        content_type='application/pdf',
    ):
        return SimpleUploadedFile(
            name=name,
            content=content,
            content_type=content_type,
        )

    def create_resource(self, **overrides):
        uploaded_file = overrides.pop(
            'file',
            self.make_uploaded_file(name='resource.pdf', content_type='application/pdf'),
        )

        data = {
            'club': self.club,
            'uploaded_by': self.owner,
            'title': 'Analysis Pack',
            'description': 'Detailed match pack.',
            'file': uploaded_file,
            'original_filename': uploaded_file.name,
            'mime_type': uploaded_file.content_type,
            'file_size_bytes': uploaded_file.size,
            'file_kind': ClubResource.FileKind.PDF,
            'storage_backend': ClubResource.StorageBackend.LOCAL,
            'storage_key': 'clubs/resources/analysis-pack.pdf',
            'total_pages': 6,
        }
        data.update(overrides)
        return ClubResource.objects.create(**data)

    @override_settings(CLUB_RESOURCES_USE_CLOUDINARY=False)
    def test_upload_serializer_derives_file_metadata_and_saves_resource(self):
        uploaded_file = self.make_uploaded_file(
            name='analysis-pack.pdf',
            content_type='application/pdf',
        )

        serializer = ClubResourceUploadSerializer(
            data={
                'title': 'Analysis Pack',
                'description': 'Pre-match PDF resource.',
                'file': uploaded_file,
                'engagement_visibility': ClubResource.EngagementVisibility.CLUB_VISIBLE,
            },
            context={
                'request': self.build_request(),
                'club': self.club,
            },
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        resource = serializer.save(
            club=self.club,
            uploaded_by=self.owner,
        )

        self.assertEqual(resource.original_filename, 'analysis-pack.pdf')
        self.assertEqual(resource.mime_type, 'application/pdf')
        self.assertEqual(resource.file_kind, ClubResource.FileKind.PDF)
        self.assertEqual(resource.file_size_bytes, uploaded_file.size)
        self.assertEqual(
            resource.engagement_visibility,
            ClubResource.EngagementVisibility.CLUB_VISIBLE,
        )

    def test_upload_serializer_rejects_unsupported_file_type(self):
        uploaded_file = self.make_uploaded_file(
            name='script.exe',
            content=b'executable-bytes',
            content_type='application/octet-stream',
        )

        serializer = ClubResourceUploadSerializer(
            data={
                'title': 'Bad Resource',
                'file': uploaded_file,
            },
            context={
                'request': self.build_request(),
                'club': self.club,
            },
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('file', serializer.errors)

    def test_read_serializers_expose_viewer_mode_and_engagement_counts(self):
        resource = self.create_resource()
        ClubResourceView.objects.create(
            resource=resource,
            user=self.member,
            opened=True,
            completed=False,
            first_opened_at=timezone.now(),
            last_opened_at=timezone.now(),
            total_active_seconds=15,
            highest_page_reached=2,
        )

        list_data = ClubResourceListSerializer(resource).data
        detail_data = ClubResourceDetailSerializer(resource).data

        self.assertEqual(list_data['viewer_mode'], 'inline')
        self.assertTrue(list_data['can_inline_view'])
        self.assertFalse(list_data['is_download_only'])
        self.assertEqual(list_data['opened_count'], 1)
        self.assertEqual(detail_data['completed_count'], 0)
        self.assertEqual(detail_data['club_name'], self.club.name)

    def test_update_serializer_only_updates_metadata_fields(self):
        resource = self.create_resource()

        serializer = ClubResourceUpdateSerializer(
            instance=resource,
            data={
                'title': 'Updated Title',
                'description': 'Updated description.',
                'engagement_visibility': ClubResource.EngagementVisibility.CLUB_VISIBLE,
            },
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_resource = serializer.save()

        self.assertEqual(updated_resource.title, 'Updated Title')
        self.assertEqual(updated_resource.description, 'Updated description.')
        self.assertEqual(
            updated_resource.engagement_visibility,
            ClubResource.EngagementVisibility.CLUB_VISIBLE,
        )

    def test_archive_serializer_toggles_archive_state(self):
        resource = self.create_resource()

        archive_serializer = ClubResourceArchiveSerializer(
            instance=resource,
            data={'is_archived': True},
        )
        self.assertTrue(archive_serializer.is_valid(), archive_serializer.errors)
        archived_resource = archive_serializer.save()
        self.assertTrue(archived_resource.is_archived)

        unarchive_serializer = ClubResourceArchiveSerializer(
            instance=archived_resource,
            data={'is_archived': False},
        )
        self.assertTrue(unarchive_serializer.is_valid(), unarchive_serializer.errors)
        restored_resource = unarchive_serializer.save()
        self.assertFalse(restored_resource.is_archived)

    def test_signed_access_serializer_exposes_stable_contract(self):
        resource = self.create_resource()

        serializer = ClubResourceSignedAccessSerializer(data={
            'resource_id': resource.id,
            'title': resource.title,
            'original_filename': resource.original_filename,
            'mime_type': resource.mime_type,
            'file_kind': resource.file_kind,
            'access_mode': 'inline',
            'can_inline_view': True,
            'is_download_only': False,
            'access_url': 'https://example.com/signed/resource.pdf',
            'expires_at': timezone.now(),
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_heartbeat_serializer_updates_pdf_summary_row(self):
        resource = self.create_resource(total_pages=4)
        view_summary = ClubResourceView.objects.create(
            resource=resource,
            user=self.member,
        )

        serializer = ClubResourceHeartbeatSerializer(
            instance=view_summary,
            data={
                'active_seconds_delta': 999,
                'page_reached': 4,
            },
            context={'resource': resource},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_summary = serializer.save()

        self.assertTrue(updated_summary.opened)
        self.assertEqual(
            updated_summary.total_active_seconds,
            ClubResourceView.MAX_ACTIVE_SECONDS_DELTA,
        )
        self.assertEqual(updated_summary.highest_page_reached, 4)

    def test_heartbeat_serializer_rejects_page_progress_for_non_pdf(self):
        uploaded_file = self.make_uploaded_file(
            name='poster.png',
            content=b'png-bytes',
            content_type='image/png',
        )
        resource = self.create_resource(
            file=uploaded_file,
            original_filename='poster.png',
            mime_type='image/png',
            file_size_bytes=uploaded_file.size,
            file_kind=ClubResource.FileKind.IMAGE,
            total_pages=None,
            storage_key='clubs/resources/poster.png',
        )
        view_summary = ClubResourceView.objects.create(
            resource=resource,
            user=self.member,
        )

        serializer = ClubResourceHeartbeatSerializer(
            instance=view_summary,
            data={
                'active_seconds_delta': 5,
                'page_reached': 1,
            },
            context={'resource': resource},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('page_reached', serializer.errors)

    def test_engagement_read_serializers_expose_view_rows(self):
        resource = self.create_resource()
        view_summary = ClubResourceView.objects.create(
            resource=resource,
            user=self.member,
            opened=True,
            completed=True,
            first_opened_at=timezone.now(),
            last_opened_at=timezone.now(),
            total_active_seconds=45,
            highest_page_reached=6,
        )

        row_data = ClubResourceViewReadSerializer(view_summary).data
        engagement_data = ClubResourceEngagementReadSerializer(resource).data

        self.assertEqual(row_data['user_email'], self.member.email)
        self.assertTrue(row_data['opened'])
        self.assertTrue(row_data['completed'])
        self.assertEqual(engagement_data['total_viewers'], 1)
        self.assertEqual(engagement_data['opened_count'], 1)
        self.assertEqual(engagement_data['completed_count'], 1)
        self.assertEqual(len(engagement_data['resource_views']), 1)

    @override_settings(
    CLUB_RESOURCES_USE_CLOUDINARY=True,
    CLOUDINARY_CLOUD_NAME='demo',
    CLOUDINARY_API_KEY='test-key',
    CLOUDINARY_API_SECRET='test-secret',
    )
    @patch('apps.clubs.views.cloudinary_resources_enabled', return_value=True)
    @patch('apps.clubs.views.build_cloudinary_signed_delivery_url')
    def test_delivery_redirects_to_signed_cloudinary_url(
        self,
        mock_build_cloudinary_signed_delivery_url,
        mock_cloudinary_enabled,
    ):
        resource = self.create_resource(
            storage_backend=ClubResource.StorageBackend.CLOUDINARY,
            storage_key='xggaffer/clubs/resources/club_1/test-resource',
        )

        mock_build_cloudinary_signed_delivery_url.return_value = (
            'https://res.cloudinary.com/demo/raw/authenticated/s--signed--/xggaffer/clubs/resources/club_1/test-resource.pdf'
        )

        access_view = ClubResourceViewSet.as_view({'get': 'access'})
        access_response = self.perform(
            access_view,
            self.member,
            method='get',
            club_pk=self.club.id,
            pk=resource.id,
        )

        self.assertEqual(access_response.status_code, status.HTTP_200_OK)
        signed_internal_url = access_response.data['access_url']
        token = signed_internal_url.split('token=')[1]

        delivery_view = ClubResourceViewSet.as_view({'get': 'delivery'})
        request = self.factory.get(
            f'/clubs/{self.club.id}/resources/{resource.id}/delivery/',
            {'token': token},
        )
        force_authenticate(request, user=self.member)

        response = delivery_view(
            request,
            club_pk=self.club.id,
            pk=resource.id,
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(
            response['Location'],
            'https://res.cloudinary.com/demo/raw/authenticated/s--signed--/xggaffer/clubs/resources/club_1/test-resource.pdf',
        )

class ClubResourceApiTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.owner = self.create_user_with_roles(
            email='resource-owner-api@example.com',
            roles=[Role.COACH],
        )
        self.coach_member = self.create_user_with_roles(
            email='resource-coach-api@example.com',
            roles=[Role.COACH],
        )
        self.player_member = self.create_user_with_roles(
            email='resource-player-api@example.com',
            roles=[Role.PLAYER],
        )
        self.other_user = self.create_user_with_roles(
            email='resource-other-api@example.com',
            roles=[Role.FAN],
        )

        self.club = Club.objects.create(
            name='Resource API Club',
            description='Club resource API tests.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        ClubMembership.objects.create(
            user=self.owner,
            club=self.club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.coach_member,
            club=self.club,
            role=ClubMembership.Role.COACH,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.player_member,
            club=self.club,
            role=ClubMembership.Role.PLAYER,
            is_active=True,
        )

    def create_user_with_roles(self, email, roles=None):
        user = get_user_model().objects.create_user(
            email=email,
            password='testpass123',
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)

        for role in roles or []:
            UserRole.objects.create(
                user_profile=profile,
                role=role,
            )

        return user

    def make_uploaded_file(
        self,
        name='resource.pdf',
        content=b'%PDF-1.4 club resource api test',
        content_type='application/pdf',
    ):
        return SimpleUploadedFile(
            name=name,
            content=content,
            content_type=content_type,
        )

    def create_resource(self, **overrides):
        uploaded_file = overrides.pop(
            'file',
            self.make_uploaded_file(),
        )

        data = {
            'club': self.club,
            'uploaded_by': self.owner,
            'title': 'Analysis Pack',
            'description': 'Detailed match resource.',
            'file': uploaded_file,
            'original_filename': uploaded_file.name,
            'mime_type': uploaded_file.content_type,
            'file_size_bytes': uploaded_file.size,
            'file_kind': ClubResource.FileKind.PDF,
            'storage_backend': ClubResource.StorageBackend.LOCAL,
            'storage_key': 'clubs/resources/analysis-pack.pdf',
            'engagement_visibility': ClubResource.EngagementVisibility.STAFF_ONLY,
            'total_pages': 4,
        }
        data.update(overrides)
        return ClubResource.objects.create(**data)

    def perform(self, view, user, method='get', data=None, **kwargs):
        request_method = getattr(self.factory, method)
        request = request_method('/clubs/', data or {}, format='json')
        force_authenticate(request, user=user)
        return view(request, **kwargs)

    @override_settings(CLUB_RESOURCES_USE_CLOUDINARY=False)
    def test_staff_member_can_upload_resource(self):
        view = ClubResourceViewSet.as_view({'post': 'create'})
        upload_file = self.make_uploaded_file(name='staff-upload.pdf')

        request = self.factory.post(
            f'/clubs/{self.club.id}/resources/',
            {
                'title': 'Staff Upload',
                'description': 'Uploaded by coach.',
                'file': upload_file,
                'engagement_visibility': ClubResource.EngagementVisibility.CLUB_VISIBLE,
            },
            format='multipart',
        )
        force_authenticate(request, user=self.coach_member)

        response = view(request, club_pk=self.club.id)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            ClubResource.objects.filter(
                club=self.club,
                title='Staff Upload',
                uploaded_by=self.coach_member,
            ).exists()
        )

    def test_player_member_cannot_upload_resource(self):
        view = ClubResourceViewSet.as_view({'post': 'create'})
        upload_file = self.make_uploaded_file(name='blocked-upload.pdf')

        request = self.factory.post(
            f'/clubs/{self.club.id}/resources/',
            {
                'title': 'Blocked Upload',
                'description': 'Should fail.',
                'file': upload_file,
            },
            format='multipart',
        )
        force_authenticate(request, user=self.player_member)

        response = view(request, club_pk=self.club.id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(
            ClubResource.objects.filter(
                club=self.club,
                title='Blocked Upload',
            ).exists()
        )

    def test_active_member_can_list_resources_but_non_member_is_blocked(self):
        visible_resource = self.create_resource(title='Visible Resource')
        archived_resource = self.create_resource(title='Archived Resource', is_archived=True)

        member_view = ClubResourceViewSet.as_view({'get': 'list'})
        member_response = self.perform(
            member_view,
            self.player_member,
            method='get',
            club_pk=self.club.id,
        )

        self.assertEqual(member_response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in member_response.data}
        self.assertIn(visible_resource.id, returned_ids)
        self.assertNotIn(archived_resource.id, returned_ids)

        non_member_response = self.perform(
            member_view,
            self.other_user,
            method='get',
            club_pk=self.club.id,
        )
        self.assertEqual(non_member_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_can_retrieve_non_archived_resource(self):
        resource = self.create_resource()

        view = ClubResourceViewSet.as_view({'get': 'retrieve'})
        response = self.perform(
            view,
            self.player_member,
            method='get',
            club_pk=self.club.id,
            pk=resource.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], resource.id)

    def test_archived_resource_detail_is_blocked_for_player_but_available_to_staff(self):
        resource = self.create_resource(is_archived=True)

        view = ClubResourceViewSet.as_view({'get': 'retrieve'})

        player_response = self.perform(
            view,
            self.player_member,
            method='get',
            club_pk=self.club.id,
            pk=resource.id,
        )
        self.assertEqual(player_response.status_code, status.HTTP_404_NOT_FOUND)

        staff_response = self.perform(
            view,
            self.owner,
            method='get',
            club_pk=self.club.id,
            pk=resource.id,
        )
        self.assertEqual(staff_response.status_code, status.HTTP_200_OK)
        self.assertEqual(staff_response.data['id'], resource.id)

    def test_access_endpoint_returns_signed_internal_url_for_member(self):
        resource = self.create_resource()

        view = ClubResourceViewSet.as_view({'get': 'access'})
        response = self.perform(
            view,
            self.player_member,
            method='get',
            club_pk=self.club.id,
            pk=resource.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('/delivery/', response.data['access_url'])
        self.assertTrue(response.data['can_inline_view'])
        self.assertFalse(response.data['is_download_only'])

    def test_delivery_endpoint_requires_valid_signed_token(self):
        resource = self.create_resource()
        access_view = ClubResourceViewSet.as_view({'get': 'access'})
        access_response = self.perform(
            access_view,
            self.player_member,
            method='get',
            club_pk=self.club.id,
            pk=resource.id,
        )

        self.assertEqual(access_response.status_code, status.HTTP_200_OK)
        signed_url = access_response.data['access_url']
        token = signed_url.split('token=')[1]

        delivery_view = ClubResourceViewSet.as_view({'get': 'delivery'})
        request = self.factory.get(
            f'/clubs/{self.club.id}/resources/{resource.id}/delivery/',
            {'token': token},
        )
        force_authenticate(request, user=self.player_member)

        response = delivery_view(
            request,
            club_pk=self.club.id,
            pk=resource.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('inline;', response['Content-Disposition'])

    def test_heartbeat_creates_summary_row_on_first_call_and_updates_on_second(self):
        resource = self.create_resource(total_pages=5)
        view = ClubResourceViewSet.as_view({'post': 'heartbeat'})

        first_response = self.perform(
            view,
            self.player_member,
            method='post',
            data={
                'active_seconds_delta': 10,
                'page_reached': 2,
            },
            club_pk=self.club.id,
            pk=resource.id,
        )

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            ClubResourceView.objects.filter(
                resource=resource,
                user=self.player_member,
            ).exists()
        )

        second_response = self.perform(
            view,
            self.player_member,
            method='post',
            data={
                'active_seconds_delta': 25,
                'page_reached': 5,
            },
            club_pk=self.club.id,
            pk=resource.id,
        )

        self.assertEqual(second_response.status_code, status.HTTP_200_OK)

        view_summary = ClubResourceView.objects.get(
            resource=resource,
            user=self.player_member,
        )
        self.assertTrue(view_summary.opened)
        self.assertGreaterEqual(view_summary.total_active_seconds, 35)
        self.assertEqual(view_summary.highest_page_reached, 5)
        self.assertTrue(view_summary.completed)

    def test_staff_only_engagement_dashboard_is_blocked_for_player(self):
        resource = self.create_resource(
            engagement_visibility=ClubResource.EngagementVisibility.STAFF_ONLY,
        )
        ClubResourceView.objects.create(
            resource=resource,
            user=self.player_member,
            opened=True,
            completed=False,
            first_opened_at=timezone.now(),
            last_opened_at=timezone.now(),
            total_active_seconds=12,
            highest_page_reached=2,
        )

        view = ClubResourceViewSet.as_view({'get': 'engagement'})

        owner_response = self.perform(
            view,
            self.owner,
            method='get',
            club_pk=self.club.id,
            pk=resource.id,
        )
        self.assertEqual(owner_response.status_code, status.HTTP_200_OK)
        self.assertEqual(owner_response.data['total_viewers'], 1)

        player_response = self.perform(
            view,
            self.player_member,
            method='get',
            club_pk=self.club.id,
            pk=resource.id,
        )
        self.assertEqual(player_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_club_visible_my_status_exposes_aggregate_counts_to_member(self):
        resource = self.create_resource(
            engagement_visibility=ClubResource.EngagementVisibility.CLUB_VISIBLE,
        )
        ClubResourceView.objects.create(
            resource=resource,
            user=self.player_member,
            opened=True,
            completed=True,
            first_opened_at=timezone.now(),
            last_opened_at=timezone.now(),
            total_active_seconds=45,
            highest_page_reached=4,
        )

        view = ClubResourceViewSet.as_view({'get': 'my_status'})
        response = self.perform(
            view,
            self.player_member,
            method='get',
            club_pk=self.club.id,
            pk=resource.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['can_view_club_status'])
        self.assertEqual(response.data['opened_count'], 1)
        self.assertEqual(response.data['completed_count'], 1)
        self.assertIsNotNone(response.data['my_view_summary'])

    def test_staff_only_my_status_hides_aggregate_counts_from_player(self):
        resource = self.create_resource(
            engagement_visibility=ClubResource.EngagementVisibility.STAFF_ONLY,
        )
        ClubResourceView.objects.create(
            resource=resource,
            user=self.player_member,
            opened=True,
            completed=False,
            first_opened_at=timezone.now(),
            last_opened_at=timezone.now(),
            total_active_seconds=12,
            highest_page_reached=2,
        )

        view = ClubResourceViewSet.as_view({'get': 'my_status'})
        response = self.perform(
            view,
            self.player_member,
            method='get',
            club_pk=self.club.id,
            pk=resource.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['can_view_club_status'])
        self.assertIsNone(response.data['opened_count'])
        self.assertIsNone(response.data['completed_count'])
        self.assertIsNotNone(response.data['my_view_summary'])

    

    @override_settings(
    CLUB_RESOURCES_USE_CLOUDINARY=True,
    CLOUDINARY_CLOUD_NAME='demo',
    CLOUDINARY_API_KEY='test-key',
        CLOUDINARY_API_SECRET='test-secret',
    )
    @patch('apps.clubs.views.cloudinary_resources_enabled', return_value=True)
    @patch('apps.clubs.views.build_cloudinary_signed_delivery_url')
    def test_delivery_redirects_to_signed_cloudinary_url(
        self,
        mock_build_cloudinary_signed_delivery_url,
        mock_cloudinary_enabled,
    ):
        resource = self.create_resource(
            storage_backend=ClubResource.StorageBackend.CLOUDINARY,
            storage_key='xggaffer/clubs/resources/club_1/test-resource',
        )

        mock_build_cloudinary_signed_delivery_url.return_value = (
            'https://res.cloudinary.com/demo/raw/authenticated/s--signed--/xggaffer/clubs/resources/club_1/test-resource.pdf'
        )

        access_view = ClubResourceViewSet.as_view({'get': 'access'})
        access_response = self.perform(
            access_view,
            self.player_member,
            method='get',
            club_pk=self.club.id,
            pk=resource.id,
        )

        self.assertEqual(access_response.status_code, status.HTTP_200_OK)
        signed_internal_url = access_response.data['access_url']
        token = signed_internal_url.split('token=')[1]

        delivery_view = ClubResourceViewSet.as_view({'get': 'delivery'})
        request = self.factory.get(
            f'/clubs/{self.club.id}/resources/{resource.id}/delivery/',
            {'token': token},
        )
        force_authenticate(request, user=self.player_member)

        response = delivery_view(
            request,
            club_pk=self.club.id,
            pk=resource.id,
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(
            response['Location'],
            'https://res.cloudinary.com/demo/raw/authenticated/s--signed--/xggaffer/clubs/resources/club_1/test-resource.pdf',
        )

    def test_non_member_cannot_request_signed_access_for_other_club_resource(self):
        other_owner = self.create_user_with_roles(
            email='other-club-owner-resource@example.com',
            roles=[Role.COACH],
        )
        other_member = self.create_user_with_roles(
            email='other-club-member-resource@example.com',
            roles=[Role.PLAYER],
        )

        other_club = Club.objects.create(
            name='Other Resource Club',
            description='Separate club for cross-club access checks.',
            creator=other_owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        ClubMembership.objects.create(
            user=other_owner,
            club=other_club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=other_member,
            club=other_club,
            role=ClubMembership.Role.PLAYER,
            is_active=True,
        )

        resource = ClubResource.objects.create(
            club=other_club,
            uploaded_by=other_owner,
            title='Other Club Pack',
            description='Should not be reachable cross-club.',
            file=self.make_uploaded_file(name='other-club-pack.pdf'),
            original_filename='other-club-pack.pdf',
            mime_type='application/pdf',
            file_size_bytes=len(b'%PDF-1.4 club resource api test'),
            file_kind=ClubResource.FileKind.PDF,
            storage_backend=ClubResource.StorageBackend.LOCAL,
            storage_key='clubs/resources/other-club-pack.pdf',
            engagement_visibility=ClubResource.EngagementVisibility.STAFF_ONLY,
            total_pages=3,
        )

        view = ClubResourceViewSet.as_view({'get': 'access'})
        response = self.perform(
            view,
            self.player_member,
            method='get',
            club_pk=other_club.id,
            pk=resource.id,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_of_other_club_cannot_send_heartbeat_to_foreign_resource(self):
        other_owner = self.create_user_with_roles(
            email='heartbeat-other-owner@example.com',
            roles=[Role.COACH],
        )
        other_player = self.create_user_with_roles(
            email='heartbeat-other-player@example.com',
            roles=[Role.PLAYER],
        )

        other_club = Club.objects.create(
            name='Other Heartbeat Club',
            description='Cross-club heartbeat checks.',
            creator=other_owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        ClubMembership.objects.create(
            user=other_owner,
            club=other_club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=other_player,
            club=other_club,
            role=ClubMembership.Role.PLAYER,
            is_active=True,
        )

        resource = ClubResource.objects.create(
            club=other_club,
            uploaded_by=other_owner,
            title='Foreign PDF',
            description='Heartbeat should stay isolated to the correct club.',
            file=self.make_uploaded_file(name='foreign-pdf.pdf'),
            original_filename='foreign-pdf.pdf',
            mime_type='application/pdf',
            file_size_bytes=len(b'%PDF-1.4 club resource api test'),
            file_kind=ClubResource.FileKind.PDF,
            storage_backend=ClubResource.StorageBackend.LOCAL,
            storage_key='clubs/resources/foreign-pdf.pdf',
            engagement_visibility=ClubResource.EngagementVisibility.STAFF_ONLY,
            total_pages=4,
        )

        view = ClubResourceViewSet.as_view({'post': 'heartbeat'})
        response = self.perform(
            view,
            self.player_member,
            method='post',
            data={
                'active_seconds_delta': 15,
                'page_reached': 2,
            },
            club_pk=other_club.id,
            pk=resource.id,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(
            ClubResourceView.objects.filter(
                resource=resource,
                user=self.player_member,
            ).exists()
        )

class ClubImportJobModelTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            email='import-owner@example.com',
            password='testpass123',
        )
        self.coach = get_user_model().objects.create_user(
            email='import-coach@example.com',
            password='testpass123',
        )

        self.club = Club.objects.create(
            name='Import Club',
            description='Club import job tests.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

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

    def make_uploaded_file(
        self,
        name='player-updates.csv',
        content=b'club_player_id,display_name\n1,Jamie Byrne\n',
        content_type='text/csv',
    ):
        return SimpleUploadedFile(
            name=name,
            content=content,
            content_type=content_type,
        )

    def create_resource(self, **overrides):
        uploaded_file = overrides.pop('file', self.make_uploaded_file())

        data = {
            'club': self.club,
            'uploaded_by': self.owner,
            'title': 'Player Update Import',
            'description': 'CSV import source.',
            'file': uploaded_file,
            'original_filename': uploaded_file.name,
            'mime_type': uploaded_file.content_type,
            'file_size_bytes': uploaded_file.size,
            'file_kind': ClubResource.FileKind.CSV,
            'storage_backend': ClubResource.StorageBackend.LOCAL,
            'storage_key': 'clubs/resources/player-updates.csv',
            'total_pages': None,
        }
        data.update(overrides)
        return ClubResource.objects.create(**data)

    def test_can_create_import_job_from_valid_csv_resource(self):
        resource = self.create_resource()

        job = ClubImportJob.objects.create(
            club=self.club,
            uploaded_by=self.owner,
            source_resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
        )

        self.assertEqual(job.club, self.club)
        self.assertEqual(job.uploaded_by, self.owner)
        self.assertEqual(job.source_resource, resource)
        self.assertEqual(
            job.import_type,
            ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
        )
        self.assertEqual(job.status, ClubImportJob.Status.UPLOADED)
        self.assertEqual(job.row_count, 0)
        self.assertEqual(job.valid_row_count, 0)
        self.assertEqual(job.imported_row_count, 0)
        self.assertEqual(job.skipped_row_count, 0)
        self.assertEqual(job.failed_row_count, 0)
        self.assertEqual(job.warning_count, 0)
        self.assertEqual(job.error_summary, {})
        self.assertEqual(job.preview_payload, {})
        self.assertEqual(job.report_payload, {})
        self.assertFalse(job.is_terminal)
        self.assertTrue(job.can_be_cancelled())

    def test_source_resource_must_belong_to_same_club(self):
        other_club = Club.objects.create(
            name='Other Club',
            description='Other club for mismatch test.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        other_resource = ClubResource.objects.create(
            club=other_club,
            uploaded_by=self.owner,
            title='Other Club Import',
            description='Wrong club resource.',
            file=self.make_uploaded_file(name='other.csv'),
            original_filename='other.csv',
            mime_type='text/csv',
            file_size_bytes=len(b'club_player_id,display_name\n1,Jamie Byrne\n'),
            file_kind=ClubResource.FileKind.CSV,
            storage_backend=ClubResource.StorageBackend.LOCAL,
            storage_key='clubs/resources/other.csv',
            total_pages=None,
        )

        job = ClubImportJob(
            club=self.club,
            uploaded_by=self.owner,
            source_resource=other_resource,
            import_type=ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
        )

        with self.assertRaises(ValidationError) as context:
            job.full_clean()

        self.assertIn('source_resource', context.exception.message_dict)

    def test_source_resource_must_be_csv_or_xlsx(self):
        pdf_file = SimpleUploadedFile(
            name='analysis-pack.pdf',
            content=b'%PDF fake',
            content_type='application/pdf',
        )

        pdf_resource = ClubResource.objects.create(
            club=self.club,
            uploaded_by=self.owner,
            title='Analysis Pack',
            description='PDF resource should be rejected for import jobs.',
            file=pdf_file,
            original_filename='analysis-pack.pdf',
            mime_type='application/pdf',
            file_size_bytes=pdf_file.size,
            file_kind=ClubResource.FileKind.PDF,
            storage_backend=ClubResource.StorageBackend.LOCAL,
            storage_key='clubs/resources/analysis-pack.pdf',
            total_pages=4,
        )

        job = ClubImportJob(
            club=self.club,
            uploaded_by=self.owner,
            source_resource=pdf_resource,
            import_type=ClubImportJob.ImportType.SQUAD_METRICS,
        )

        with self.assertRaises(ValidationError) as context:
            job.full_clean()

        self.assertIn('source_resource', context.exception.message_dict)

    def test_completed_job_requires_completed_at_and_is_terminal(self):
        resource = self.create_resource()

        job = ClubImportJob(
            club=self.club,
            uploaded_by=self.owner,
            source_resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_SEASON_STATS,
            status=ClubImportJob.Status.COMPLETED,
        )

        with self.assertRaises(ValidationError) as context:
            job.full_clean()

        self.assertIn('completed_at', context.exception.message_dict)

        job.completed_at = timezone.now()
        job.full_clean()

        self.assertTrue(job.is_terminal)
        self.assertFalse(job.can_be_cancelled())

class ClubImportValidationServiceTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            email='phasef-owner@example.com',
            password='testpass123',
        )
        self.club = Club.objects.create(
            name='Phase F Club',
            description='Structured import validation tests.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )
        ClubMembership.objects.create(
            user=self.owner,
            club=self.club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )

    def make_csv_file(
        self,
        *,
        name='import.csv',
        content='club_player_id,display_name\n1,Jamie Byrne\n',
    ):
        return SimpleUploadedFile(
            name=name,
            content=content.encode('utf-8'),
            content_type='text/csv',
        )

    def make_xlsx_file(self, *, name='import.xlsx', headers=None, rows=None):
        headers = headers or ['club_player_id', 'display_name']
        rows = rows or [[1, 'Jamie Byrne']]

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(headers)

        for row in rows:
            worksheet.append(row)

        stream = io.BytesIO()
        workbook.save(stream)
        stream.seek(0)

        return SimpleUploadedFile(
            name=name,
            content=stream.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def create_resource(self, *, uploaded_file, file_kind):
        return ClubResource.objects.create(
            club=self.club,
            uploaded_by=self.owner,
            title='Import source',
            description='Structured import source file.',
            file=uploaded_file,
            original_filename=uploaded_file.name,
            mime_type=uploaded_file.content_type,
            file_size_bytes=uploaded_file.size,
            file_kind=file_kind,
            storage_backend=ClubResource.StorageBackend.LOCAL,
            storage_key='',
            total_pages=None,
            engagement_visibility=ClubResource.EngagementVisibility.STAFF_ONLY,
        )

    def create_import_job(self, *, resource, import_type):
        return ClubImportJob.objects.create(
            club=self.club,
            uploaded_by=self.owner,
            source_resource=resource,
            import_type=import_type,
        )

    def test_player_profile_update_csv_parses_and_matches_by_explicit_id(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Old Name',
            squad_number=8,
            created_by=self.owner,
        )
        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content=(
                    'club_player_id,display_name,primary_position,is_active\n'
                    f'{club_player.id},Jamie Byrne,CM,true\n'
                )
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = self.create_import_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
        )

        result = validate_import_job(job)

        self.assertEqual(result.total_rows, 1)
        self.assertEqual(result.valid_row_count, 1)

        row = result.rows[0]
        self.assertEqual(row.status, 'matched')
        self.assertEqual(row.match_method, 'explicit_id')
        self.assertEqual(row.target_model, 'ClubPlayer')
        self.assertEqual(row.target_id, club_player.id)
        self.assertEqual(row.normalised_data['display_name'], 'Jamie Byrne')
        self.assertEqual(row.normalised_data['primary_position'], 'CM')
        self.assertTrue(row.normalised_data['is_active'])

    def test_player_profile_update_xlsx_parses_successfully(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Old Name',
            squad_number=8,
            created_by=self.owner,
        )
        resource = self.create_resource(
            uploaded_file=self.make_xlsx_file(
                headers=['club_player_id', 'display_name', 'primary_position'],
                rows=[[club_player.id, 'Jamie Byrne', 'CM']],
            ),
            file_kind=ClubResource.FileKind.XLSX,
        )
        job = self.create_import_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
        )

        result = validate_import_job(job)

        self.assertEqual(result.total_rows, 1)
        self.assertEqual(result.valid_row_count, 1)
        self.assertEqual(result.rows[0].status, 'matched')
        self.assertEqual(result.rows[0].target_id, club_player.id)

    def test_player_season_stats_missing_required_headers_fails_cleanly(self):
        linked_player = Player.objects.create(
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
        )
        ClubPlayer.objects.create(
            club=self.club,
            player=linked_player,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            squad_number=8,
            created_by=self.owner,
        )

        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content='season_label,goals\n2024/2025,5\n'
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = self.create_import_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_SEASON_STATS,
        )

        with self.assertRaises(ClubImportValidationError) as context:
            validate_import_job(job)

        self.assertIn('required schema', str(context.exception))
        self.assertIn('missing_required_headers', context.exception.details)

    def test_matching_prefers_explicit_id_and_surfaces_lower_priority_mismatch_warning(self):
        first_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            squad_number=8,
            created_by=self.owner,
        )
        ClubPlayer.objects.create(
            club=self.club,
            first_name='Lewis',
            last_name='Murphy',
            display_name='Lewis Murphy',
            squad_number=9,
            created_by=self.owner,
        )

        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content=(
                    'club_player_id,squad_number,display_name,primary_position\n'
                    f'{first_player.id},9,Not The Same Player,CM\n'
                )
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = self.create_import_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
        )

        result = validate_import_job(job)
        row = result.rows[0]

        self.assertEqual(row.status, 'matched')
        self.assertEqual(row.match_method, 'explicit_id')
        self.assertEqual(row.target_id, first_player.id)
        self.assertTrue(any('higher-priority explicit identifier' in warning for warning in row.warnings))

    def test_exact_name_ambiguity_is_surfaced(self):
        ClubPlayer.objects.create(
            club=self.club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            squad_number=8,
            created_by=self.owner,
        )
        ClubPlayer.objects.create(
            club=self.club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            squad_number=18,
            created_by=self.owner,
        )

        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content='full_name,primary_position\nJamie Byrne,CM\n'
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = self.create_import_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
        )

        result = validate_import_job(job)
        row = result.rows[0]

        self.assertEqual(row.status, 'ambiguous')
        self.assertEqual(row.match_method, 'exact_name')
        self.assertTrue(any('more than one ClubPlayer' in error for error in row.errors))

    def test_player_season_stats_unmatched_when_club_player_has_no_canonical_player(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            squad_number=8,
            created_by=self.owner,
        )

        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content=(
                    'provider,season_label,club_player_id,goals\n'
                    f'understat,2024/2025,{club_player.id},5\n'
                )
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = self.create_import_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_SEASON_STATS,
        )

        result = validate_import_job(job)
        row = result.rows[0]

        self.assertEqual(row.status, 'unmatched')
        self.assertEqual(row.match_method, 'explicit_id')
        self.assertTrue(any('not linked to a canonical Player' in error for error in row.errors))

    def test_squad_metrics_duplicate_season_row_is_flagged(self):
        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content=(
                    'provider,season_label,competition_code,matches_played,wins\n'
                    'understat,2024/2025,EPL,38,24\n'
                    'understat,2024/2025,EPL,38,25\n'
                )
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = self.create_import_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.SQUAD_METRICS,
        )

        result = validate_import_job(job)

        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.valid_row_count, 1)
        self.assertEqual(result.invalid_row_count, 1)
        self.assertEqual(result.rows[0].status, 'matched')
        self.assertEqual(result.rows[1].status, 'invalid')
        self.assertTrue(any('Duplicate season_label' in error for error in result.rows[1].errors))

class ClubImportPreviewPersistenceTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            email='preview-owner@example.com',
            password='testpass123',
        )
        self.club = Club.objects.create(
            name='Preview Club',
            description='Preview persistence tests.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )
        ClubMembership.objects.create(
            user=self.owner,
            club=self.club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )

    def make_csv_file(self, *, name='import.csv', content=''):
        return SimpleUploadedFile(
            name=name,
            content=content.encode('utf-8'),
            content_type='text/csv',
        )

    def create_resource(self, *, uploaded_file, file_kind):
        return ClubResource.objects.create(
            club=self.club,
            uploaded_by=self.owner,
            title='Import Source',
            description='Import resource.',
            file=uploaded_file,
            original_filename=uploaded_file.name,
            mime_type=uploaded_file.content_type,
            file_size_bytes=uploaded_file.size,
            file_kind=file_kind,
            storage_backend=ClubResource.StorageBackend.LOCAL,
            storage_key='',
            total_pages=None,
            engagement_visibility=ClubResource.EngagementVisibility.STAFF_ONLY,
        )

    def create_job(self, *, resource, import_type):
        return ClubImportJob.objects.create(
            club=self.club,
            uploaded_by=self.owner,
            source_resource=resource,
            import_type=import_type,
        )

    def test_successful_player_profile_preview_is_persisted_and_marks_preview_ready(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            squad_number=8,
            primary_position='CM',
            created_by=self.owner,
        )

        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content=(
                    'club_player_id,display_name,primary_position,height_cm\n'
                    f'{club_player.id},James Byrne,CM,182\n'
                )
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = self.create_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
        )

        persisted_job = persist_import_preview(job)
        persisted_job.refresh_from_db()

        self.assertEqual(persisted_job.status, ClubImportJob.Status.PREVIEW_READY)
        self.assertEqual(persisted_job.row_count, 1)
        self.assertEqual(persisted_job.valid_row_count, 1)
        self.assertEqual(persisted_job.warning_count, 1)
        self.assertTrue(persisted_job.preview_payload)
        self.assertEqual(persisted_job.preview_payload['counts']['total_rows'], 1)
        self.assertEqual(persisted_job.preview_payload['counts']['valid_rows'], 1)
        self.assertEqual(persisted_job.preview_payload['counts']['warning_count'], 1)

        preview_row = persisted_job.preview_payload['rows'][0]
        self.assertEqual(preview_row['status'], 'matched')
        self.assertEqual(preview_row['record_action'], 'update')
        self.assertEqual(preview_row['target_record_id'], club_player.id)
        self.assertIn('display_name', preview_row['proposed_changes'])
        self.assertIn('height_cm', preview_row['proposed_changes'])
        self.assertEqual(len(preview_row['warnings']), 1)
        self.assertIn('higher-priority identifier was used', preview_row['warnings'][0])

    def test_successful_player_season_preview_shows_create_action_when_record_missing(self):
        canonical_player = Player.objects.create(
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
        )
        club_player = ClubPlayer.objects.create(
            club=self.club,
            player=canonical_player,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            squad_number=8,
            created_by=self.owner,
        )

        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content=(
                    'provider,season_label,club_player_id,goals,assists\n'
                    f'understat,2024/2025,{club_player.id},9,4\n'
                )
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = self.create_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_SEASON_STATS,
        )

        persisted_job = persist_import_preview(job)
        persisted_job.refresh_from_db()

        self.assertEqual(persisted_job.status, ClubImportJob.Status.PREVIEW_READY)
        preview_row = persisted_job.preview_payload['rows'][0]

        self.assertEqual(preview_row['status'], 'matched')
        self.assertEqual(preview_row['record_action'], 'create')
        self.assertIsNone(preview_row['target_record_id'])
        self.assertIn('goals', preview_row['proposed_changes'])
        self.assertIn('assists', preview_row['proposed_changes'])

    def test_successful_squad_metrics_preview_shows_no_change_when_existing_record_matches(self):
        ClubSeasonEnrichment.objects.create(
            club=self.club,
            provider=ExternalProvider.UNDERSTAT,
            season_label='2024/2025',
            competition_code='EPL',
            matches_played=38,
            wins=24,
            draws=7,
            losses=7,
            goals_for=80,
            goals_against=38,
        )

        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content=(
                    'provider,season_label,competition_code,matches_played,wins,draws,losses,goals_for,goals_against\n'
                    'understat,2024/2025,EPL,38,24,7,7,80,38\n'
                )
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = self.create_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.SQUAD_METRICS,
        )

        persisted_job = persist_import_preview(job)
        persisted_job.refresh_from_db()

        preview_row = persisted_job.preview_payload['rows'][0]
        self.assertEqual(preview_row['status'], 'matched')
        self.assertEqual(preview_row['record_action'], 'no_change')
        self.assertEqual(preview_row['proposed_changes'], {})

    def test_unmatched_rows_are_preserved_inside_preview_payload(self):
        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content='club_player_id,display_name\n9999,Missing Player\n'
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = self.create_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
        )

        persisted_job = persist_import_preview(job)
        persisted_job.refresh_from_db()

        self.assertEqual(persisted_job.status, ClubImportJob.Status.PREVIEW_READY)
        self.assertEqual(persisted_job.preview_payload['counts']['unmatched_rows'], 1)
        preview_row = persisted_job.preview_payload['rows'][0]
        self.assertEqual(preview_row['status'], 'unmatched')
        self.assertTrue(preview_row['errors'])

    def test_failed_preview_persists_failed_status_error_summary_and_report_payload(self):
        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content='season_label,goals\n2024/2025,5\n'
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = self.create_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_SEASON_STATS,
        )

        persisted_job = persist_import_preview(job)
        persisted_job.refresh_from_db()

        self.assertEqual(persisted_job.status, ClubImportJob.Status.FAILED)
        self.assertEqual(persisted_job.error_summary['stage'], 'preview')
        self.assertTrue(persisted_job.report_payload)
        self.assertEqual(persisted_job.report_payload['stage'], 'preview')
        self.assertEqual(persisted_job.report_payload['status'], 'failed')
        self.assertEqual(persisted_job.preview_payload, {})
        self.assertIsNotNone(persisted_job.completed_at)

class ClubImportCommitTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.owner = get_user_model().objects.create_user(
            email='commit-owner@example.com',
            password='testpass123',
        )
        self.admin = get_user_model().objects.create_user(
            email='commit-admin@example.com',
            password='testpass123',
        )
        self.coach = get_user_model().objects.create_user(
            email='commit-coach@example.com',
            password='testpass123',
        )

        self.club = Club.objects.create(
            name='Commit Club',
            description='Commit path tests.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        ClubMembership.objects.create(
            user=self.owner,
            club=self.club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.admin,
            club=self.club,
            role=ClubMembership.Role.ADMIN,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.coach,
            club=self.club,
            role=ClubMembership.Role.COACH,
            is_active=True,
        )

    def build_request(self, user):
        request = self.factory.post('/clubs/import-jobs/commit/', {}, format='json')
        request.user = user
        return request

    def make_csv_file(self, *, name='import.csv', content=''):
        return SimpleUploadedFile(
            name=name,
            content=content.encode('utf-8'),
            content_type='text/csv',
        )

    def create_resource(self, *, uploaded_file, file_kind):
        return ClubResource.objects.create(
            club=self.club,
            uploaded_by=self.owner,
            title='Import Source',
            description='Commit test resource.',
            file=uploaded_file,
            original_filename=uploaded_file.name,
            mime_type=uploaded_file.content_type,
            file_size_bytes=uploaded_file.size,
            file_kind=file_kind,
            storage_backend=ClubResource.StorageBackend.LOCAL,
            storage_key='',
            total_pages=None,
            engagement_visibility=ClubResource.EngagementVisibility.STAFF_ONLY,
        )

    def create_job(self, *, resource, import_type):
        return ClubImportJob.objects.create(
            club=self.club,
            uploaded_by=self.owner,
            source_resource=resource,
            import_type=import_type,
        )

    def test_commit_serializer_requires_explicit_confirm_true(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            squad_number=8,
            created_by=self.owner,
        )
        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content=f'club_player_id,display_name\n{club_player.id},James Byrne\n'
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = self.create_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
        )
        persist_import_preview(job)
        job.refresh_from_db()

        serializer = ClubImportJobCommitSerializer(
            instance=job,
            data={'confirm': False},
            context={'request': self.build_request(self.owner)},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('confirm', serializer.errors)

    def test_commit_permission_allows_owner_and_admin_only(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            squad_number=8,
            created_by=self.owner,
        )
        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content=f'club_player_id,display_name\n{club_player.id},James Byrne\n'
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = self.create_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
        )

        permission = CanCommitClubImportJob()

        self.assertTrue(
            permission.has_object_permission(
                self.build_request(self.owner),
                type('View', (), {})(),
                job,
            )
        )
        self.assertTrue(
            permission.has_object_permission(
                self.build_request(self.admin),
                type('View', (), {})(),
                job,
            )
        )
        self.assertFalse(
            permission.has_object_permission(
                self.build_request(self.coach),
                type('View', (), {})(),
                job,
            )
        )

    def test_commit_import_job_updates_club_player_and_marks_completed(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            squad_number=8,
            primary_position='CM',
            created_by=self.owner,
        )
        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content=(
                    'club_player_id,display_name,height_cm\n'
                    f'{club_player.id},James Byrne,182\n'
                )
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = self.create_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
        )

        persist_import_preview(job)
        commit_import_job(job, confirmed_by=self.owner)

        job.refresh_from_db()
        club_player.refresh_from_db()

        self.assertEqual(job.status, ClubImportJob.Status.COMPLETED)
        self.assertEqual(job.imported_row_count, 1)
        self.assertEqual(job.skipped_row_count, 0)
        self.assertEqual(job.failed_row_count, 0)
        self.assertEqual(club_player.display_name, 'James Byrne')
        self.assertEqual(club_player.height_cm, 182)
        self.assertEqual(job.report_payload['stage'], 'commit')
        self.assertEqual(job.report_payload['status'], 'completed')
        self.assertEqual(job.report_payload['counts']['updated_rows'], 1)

    def test_commit_import_job_creates_player_season_enrichment(self):
        canonical_player = Player.objects.create(
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
        )
        club_player = ClubPlayer.objects.create(
            club=self.club,
            player=canonical_player,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            squad_number=8,
            created_by=self.owner,
        )

        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content=(
                    'provider,season_label,club_player_id,goals,assists\n'
                    f'understat,2024/2025,{club_player.id},10,6\n'
                )
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = self.create_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_SEASON_STATS,
        )

        persist_import_preview(job)
        commit_import_job(job, confirmed_by=self.owner)

        enrichment = PlayerSeasonEnrichment.objects.get(
            player=canonical_player,
            club=self.club,
            provider=ExternalProvider.UNDERSTAT,
            season_label='2024/2025',
        )

        self.assertEqual(enrichment.goals, 10)
        self.assertEqual(enrichment.assists, 6)

    def test_commit_import_job_creates_club_season_enrichment(self):
        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content=(
                    'provider,season_label,competition_code,matches_played,wins,draws,losses,goals_for,goals_against\n'
                    'understat,2024/2025,EPL,38,24,7,7,80,38\n'
                )
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = self.create_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.SQUAD_METRICS,
        )

        persist_import_preview(job)
        commit_import_job(job, confirmed_by=self.owner)

        enrichment = ClubSeasonEnrichment.objects.get(
            club=self.club,
            provider=ExternalProvider.UNDERSTAT,
            season_label='2024/2025',
            competition_code='EPL',
        )

        self.assertEqual(enrichment.matches_played, 38)
        self.assertEqual(enrichment.wins, 24)
        self.assertEqual(enrichment.goals_for, 80)

    def test_duplicate_recommit_is_blocked(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            squad_number=8,
            created_by=self.owner,
        )
        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content=f'club_player_id,display_name\n{club_player.id},James Byrne\n'
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = self.create_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
        )

        persist_import_preview(job)
        commit_import_job(job, confirmed_by=self.owner)

        with self.assertRaises(ClubImportCommitError):
            commit_import_job(job, confirmed_by=self.owner)

    def test_commit_is_atomic_and_rolls_back_partial_writes(self):
        first_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            squad_number=8,
            created_by=self.owner,
        )
        second_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Lewis',
            last_name='Murphy',
            display_name='Lewis Murphy',
            squad_number=9,
            created_by=self.owner,
        )

        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content=(
                    'club_player_id,display_name\n'
                    f'{first_player.id},James Byrne\n'
                    f'{second_player.id},Lewis M.\n'
                )
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = self.create_job(
            resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
        )

        persist_import_preview(job)

        original_apply = import_services._apply_player_profile_update_row
        call_state = {'count': 0}

        def side_effect(**kwargs):
            if call_state['count'] == 0:
                call_state['count'] += 1
                return original_apply(**kwargs)
            raise RuntimeError('forced commit failure')

        with patch(
            'apps.clubs.services.imports._apply_player_profile_update_row',
            side_effect=side_effect,
        ):
            with self.assertRaises(ClubImportCommitError):
                commit_import_job(job, confirmed_by=self.owner)

        job.refresh_from_db()
        first_player.refresh_from_db()
        second_player.refresh_from_db()

        self.assertEqual(job.status, ClubImportJob.Status.FAILED)
        self.assertEqual(job.imported_row_count, 0)
        self.assertEqual(job.failed_row_count, 2)
        self.assertEqual(first_player.display_name, 'Jamie Byrne')
        self.assertEqual(second_player.display_name, 'Lewis Murphy')
        self.assertEqual(job.report_payload['stage'], 'commit')
        self.assertEqual(job.report_payload['status'], 'failed')


class ClubImportJobApiTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.owner = get_user_model().objects.create_user(
            email='api-import-owner@example.com',
            password='testpass123',
        )
        self.admin = get_user_model().objects.create_user(
            email='api-import-admin@example.com',
            password='testpass123',
        )
        self.coach = get_user_model().objects.create_user(
            email='api-import-coach@example.com',
            password='testpass123',
        )
        self.player = get_user_model().objects.create_user(
            email='api-import-player@example.com',
            password='testpass123',
        )
        self.other_owner = get_user_model().objects.create_user(
            email='api-import-other-owner@example.com',
            password='testpass123',
        )

        self.club = Club.objects.create(
            name='API Import Club',
            description='API import endpoint tests.',
            creator=self.owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        self.other_club = Club.objects.create(
            name='Other API Import Club',
            description='Foreign club for queryset isolation checks.',
            creator=self.other_owner,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        ClubMembership.objects.create(
            user=self.owner,
            club=self.club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.admin,
            club=self.club,
            role=ClubMembership.Role.ADMIN,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.coach,
            club=self.club,
            role=ClubMembership.Role.COACH,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.player,
            club=self.club,
            role=ClubMembership.Role.PLAYER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.other_owner,
            club=self.other_club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )

    def perform(self, view, user, method='get', data=None, **kwargs):
        request_method = getattr(self.factory, method)
        request = request_method('/clubs/', data or {}, format='json')
        force_authenticate(request, user=user)
        return view(request, **kwargs)

    def make_csv_file(self, *, name='import.csv', content=''):
        return SimpleUploadedFile(
            name=name,
            content=content.encode('utf-8'),
            content_type='text/csv',
        )

    def make_xlsx_file(self, *, name='import.xlsx', headers=None, rows=None):
        headers = headers or ['club_player_id', 'display_name']
        rows = rows or [[1, 'Jamie Byrne']]

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(headers)
        for row in rows:
            worksheet.append(row)

        stream = io.BytesIO()
        workbook.save(stream)
        stream.seek(0)

        return SimpleUploadedFile(
            name=name,
            content=stream.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def create_resource(self, *, uploaded_file, file_kind, club=None):
        target_club = club or self.club
        return ClubResource.objects.create(
            club=target_club,
            uploaded_by=target_club.creator,
            title='Import source',
            description='API import source resource.',
            file=uploaded_file,
            original_filename=uploaded_file.name,
            mime_type=uploaded_file.content_type,
            file_size_bytes=uploaded_file.size,
            file_kind=file_kind,
            storage_backend=ClubResource.StorageBackend.LOCAL,
            storage_key='',
            total_pages=None,
            engagement_visibility=ClubResource.EngagementVisibility.STAFF_ONLY,
        )

    def create_preview_ready_job(self):
        next_squad_number = ClubPlayer.objects.filter(club=self.club).count() + 8
        club_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            squad_number=next_squad_number,
            created_by=self.owner,
        )
        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content=f'club_player_id,display_name\n{club_player.id},James Byrne\n'
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        job = ClubImportJob.objects.create(
            club=self.club,
            uploaded_by=self.owner,
            source_resource=resource,
            import_type=ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
        )
        persist_import_preview(job)
        job.refresh_from_db()
        return job

    def test_staff_member_can_create_import_job_from_csv_and_xlsx(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            squad_number=8,
            created_by=self.owner,
        )

        create_view = ClubImportJobViewSet.as_view({'post': 'create'})

        csv_resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content=f'club_player_id,display_name\n{club_player.id},James Byrne\n'
            ),
            file_kind=ClubResource.FileKind.CSV,
        )
        csv_response = self.perform(
            create_view,
            self.coach,
            method='post',
            data={
                'source_resource': csv_resource.id,
                'import_type': ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
            },
            club_pk=self.club.id,
        )

        self.assertEqual(csv_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(csv_response.data['status'], ClubImportJob.Status.PREVIEW_READY)
        self.assertEqual(csv_response.data['source_resource'], csv_resource.id)

        xlsx_resource = self.create_resource(
            uploaded_file=self.make_xlsx_file(
                headers=['club_player_id', 'display_name'],
                rows=[[club_player.id, 'Jamie Byrne']],
            ),
            file_kind=ClubResource.FileKind.XLSX,
        )
        xlsx_response = self.perform(
            create_view,
            self.coach,
            method='post',
            data={
                'source_resource': xlsx_resource.id,
                'import_type': ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
            },
            club_pk=self.club.id,
        )

        self.assertEqual(xlsx_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(xlsx_response.data['status'], ClubImportJob.Status.PREVIEW_READY)
        self.assertEqual(xlsx_response.data['source_resource'], xlsx_resource.id)

    def test_non_staff_member_cannot_create_import_job(self):
        club_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Jamie',
            last_name='Byrne',
            display_name='Jamie Byrne',
            squad_number=8,
            created_by=self.owner,
        )
        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content=f'club_player_id,display_name\n{club_player.id},James Byrne\n'
            ),
            file_kind=ClubResource.FileKind.CSV,
        )

        view = ClubImportJobViewSet.as_view({'post': 'create'})
        response = self.perform(
            view,
            self.player,
            method='post',
            data={
                'source_resource': resource.id,
                'import_type': ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
            },
            club_pk=self.club.id,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_returns_failed_job_with_report_payload_on_schema_failure(self):
        resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                content='season_label,goals\n2024/2025,5\n'
            ),
            file_kind=ClubResource.FileKind.CSV,
        )

        view = ClubImportJobViewSet.as_view({'post': 'create'})
        response = self.perform(
            view,
            self.coach,
            method='post',
            data={
                'source_resource': resource.id,
                'import_type': ClubImportJob.ImportType.PLAYER_SEASON_STATS,
            },
            club_pk=self.club.id,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], ClubImportJob.Status.FAILED)
        self.assertEqual(response.data['preview_payload'], {})
        self.assertEqual(response.data['report_payload']['stage'], 'preview')
        self.assertEqual(response.data['report_payload']['status'], 'failed')

    def test_staff_member_can_list_jobs_for_own_club_only(self):
        own_job = self.create_preview_ready_job()

        other_resource = self.create_resource(
            uploaded_file=self.make_csv_file(
                name='other.csv',
                content='club_player_id,display_name\n1,Someone Else\n',
            ),
            file_kind=ClubResource.FileKind.CSV,
            club=self.other_club,
        )
        ClubImportJob.objects.create(
            club=self.other_club,
            uploaded_by=self.other_owner,
            source_resource=other_resource,
            import_type=ClubImportJob.ImportType.PLAYER_PROFILE_UPDATE,
        )

        view = ClubImportJobViewSet.as_view({'get': 'list'})
        response = self.perform(
            view,
            self.coach,
            method='get',
            club_pk=self.club.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in response.data}
        self.assertIn(own_job.id, returned_ids)
        self.assertTrue(all(item['club'] == self.club.id for item in response.data))

    def test_retrieve_returns_preview_then_report_payload_after_commit(self):
        job = self.create_preview_ready_job()
        retrieve_view = ClubImportJobViewSet.as_view({'get': 'retrieve'})

        preview_response = self.perform(
            retrieve_view,
            self.coach,
            method='get',
            club_pk=self.club.id,
            pk=job.id,
        )
        self.assertEqual(preview_response.status_code, status.HTTP_200_OK)
        self.assertEqual(preview_response.data['status'], ClubImportJob.Status.PREVIEW_READY)
        self.assertTrue(preview_response.data['preview_payload'])
        self.assertEqual(preview_response.data['report_payload'], {})

        commit_view = ClubImportJobViewSet.as_view({'post': 'commit'})
        commit_response = self.perform(
            commit_view,
            self.owner,
            method='post',
            data={'confirm': True},
            club_pk=self.club.id,
            pk=job.id,
        )
        self.assertEqual(commit_response.status_code, status.HTTP_200_OK)

        report_response = self.perform(
            retrieve_view,
            self.coach,
            method='get',
            club_pk=self.club.id,
            pk=job.id,
        )
        self.assertEqual(report_response.status_code, status.HTTP_200_OK)
        self.assertEqual(report_response.data['status'], ClubImportJob.Status.COMPLETED)
        self.assertEqual(report_response.data['report_payload']['stage'], 'commit')
        self.assertEqual(report_response.data['report_payload']['status'], 'completed')

    def test_owner_and_admin_can_commit_preview_ready_job(self):
        owner_job = self.create_preview_ready_job()
        admin_job = self.create_preview_ready_job()
        commit_view = ClubImportJobViewSet.as_view({'post': 'commit'})

        owner_response = self.perform(
            commit_view,
            self.owner,
            method='post',
            data={'confirm': True},
            club_pk=self.club.id,
            pk=owner_job.id,
        )
        self.assertEqual(owner_response.status_code, status.HTTP_200_OK)
        self.assertEqual(owner_response.data['status'], ClubImportJob.Status.COMPLETED)

        admin_response = self.perform(
            commit_view,
            self.admin,
            method='post',
            data={'confirm': True},
            club_pk=self.club.id,
            pk=admin_job.id,
        )
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        self.assertEqual(admin_response.data['status'], ClubImportJob.Status.COMPLETED)

    def test_coach_cannot_commit_preview_ready_job(self):
        job = self.create_preview_ready_job()
        view = ClubImportJobViewSet.as_view({'post': 'commit'})

        response = self.perform(
            view,
            self.coach,
            method='post',
            data={'confirm': True},
            club_pk=self.club.id,
            pk=job.id,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_recommit_is_blocked_by_api_after_job_is_completed(self):
        job = self.create_preview_ready_job()
        view = ClubImportJobViewSet.as_view({'post': 'commit'})

        first_response = self.perform(
            view,
            self.owner,
            method='post',
            data={'confirm': True},
            club_pk=self.club.id,
            pk=job.id,
        )
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)

        second_response = self.perform(
            view,
            self.owner,
            method='post',
            data={'confirm': True},
            club_pk=self.club.id,
            pk=job.id,
        )

        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            'Only preview_ready import jobs can be committed.',
            str(second_response.data),
        )

    def test_commit_response_returns_completed_job_with_report_counts(self):
        job = self.create_preview_ready_job()
        view = ClubImportJobViewSet.as_view({'post': 'commit'})

        response = self.perform(
            view,
            self.owner,
            method='post',
            data={'confirm': True},
            club_pk=self.club.id,
            pk=job.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], ClubImportJob.Status.COMPLETED)
        self.assertEqual(response.data['imported_row_count'], 1)
        self.assertEqual(response.data['report_payload']['stage'], 'commit')
        self.assertEqual(response.data['report_payload']['status'], 'completed')
        self.assertEqual(response.data['report_payload']['counts']['imported_rows'], 1)