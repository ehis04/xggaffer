from django.conf import settings
from rest_framework.permissions import BasePermission

from apps.users.models import Role, UserRole
from .models import Club, ClubMembership, ClubResource


def should_bypass_permissions():
    return getattr(settings, 'BYPASS_PERMISSIONS', False)


def get_user_profile(user):
    if not user or not user.is_authenticated:
        return None

    try:
        return user.profile
    except Exception:
        return None


def user_has_platform_role(user, role):
    if should_bypass_permissions():
        return True

    profile = get_user_profile(user)
    if profile is None:
        return False

    return UserRole.objects.filter(
        user_profile=profile,
        role=role,
    ).exists()


def get_active_club_membership(user, club=None, club_id=None):
    if should_bypass_permissions():
        return None

    if not user or not user.is_authenticated:
        return None

    if club is None and club_id is None:
        return None

    if club_id is None:
        club_id = club.id

    return ClubMembership.objects.filter(
        user=user,
        club_id=club_id,
        is_active=True,
    ).first()


def user_has_club_creation_capability(user):
    if not user or not user.is_authenticated:
        return False

    if user.is_staff or user.is_superuser:
        return True

    return user_has_platform_role(user, Role.COACH)


def user_can_commit_club_import_jobs(user, club):
    if should_bypass_permissions():
        return True

    membership = get_active_club_membership(user, club=club)
    return membership is not None and membership.can_manage_members()

def user_can_create_requested_club_type(user, club_type):
    if should_bypass_permissions():
        return True

    if not user_has_club_creation_capability(user):
        return False

    if club_type == Club.ClubType.SYSTEM_PROFESSIONAL:
        return bool(user.is_staff or user.is_superuser)

    return True


def user_can_request_player_membership(user):
    if should_bypass_permissions():
        return True

    if not user or not user.is_authenticated:
        return False

    return user_has_platform_role(user, Role.PLAYER)


def user_can_review_join_requests(user, club):
    if should_bypass_permissions():
        return True

    membership = get_active_club_membership(user, club=club)
    return membership is not None and membership.can_manage_members()


def user_can_manage_club_invitations(user, club):
    if should_bypass_permissions():
        return True

    membership = get_active_club_membership(user, club=club)
    return membership is not None and membership.can_manage_members()

def user_can_manage_club_player_identity(user, club):
    if should_bypass_permissions():
        return True

    return user_can_review_join_requests(user, club)

def user_can_view_club_scheduling(user, club):
    if should_bypass_permissions():
        return True

    if club.visibility == Club.Visibility.PUBLIC:
        return True

    membership = get_active_club_membership(user, club=club)
    return membership is not None


def user_can_manage_manual_club_scheduling(user, club):
    if should_bypass_permissions():
        return True

    membership = get_active_club_membership(user, club=club)
    return (
        membership is not None and
        membership.can_create_content() and
        club.is_user_managed_club()
    )

class CanCreateClub(BasePermission):
    message = 'You do not have permission to create this club.'

    def has_permission(self, request, view):
        if should_bypass_permissions():
            return True

        if getattr(view, 'action', None) != 'create':
            return True

        user = request.user
        if not user or not user.is_authenticated:
            self.message = 'Authentication is required to create a club.'
            return False

        if not user_has_club_creation_capability(user):
            self.message = 'Only coach-capable users can create clubs.'
            return False

        requested_club_type = request.data.get('club_type')
        if (
            requested_club_type == Club.ClubType.SYSTEM_PROFESSIONAL and
            not (user.is_staff or user.is_superuser)
        ):
            self.message = (
                'system_professional clubs are system-managed and cannot be '
                'created through ordinary user flows.'
            )
            return False

        return True


class CanCreateJoinRequest(BasePermission):
    message = 'Only player-capable authenticated users can create join requests.'

    def has_permission(self, request, view):
        if should_bypass_permissions():
            return True

        return user_can_request_player_membership(request.user)

class CanManageClubPlayerIdentity(BasePermission):
    message = 'Only owner/admin reviewers can manage canonical player alignment for this club.'

    def has_permission(self, request, view):
        if should_bypass_permissions():
            return True

        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if should_bypass_permissions():
            return True

        return user_can_manage_club_player_identity(request.user, obj.club)

class CanAccessClubScheduling(BasePermission):
    message = 'You do not have permission to access or manage scheduling for this club.'

    def _get_club(self, view):
        club_pk = view.kwargs.get('club_pk')
        if not club_pk:
            return None
        try:
            return Club.objects.get(pk=club_pk)
        except Club.DoesNotExist:
            return None

    def has_permission(self, request, view):
        if should_bypass_permissions():
            return True

        club = self._get_club(view)
        if club is None:
            return False

        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return user_can_view_club_scheduling(request.user, club)

        return user_can_manage_manual_club_scheduling(request.user, club)

    def has_object_permission(self, request, view, obj):
        if should_bypass_permissions():
            return True

        club = getattr(obj, 'club', None)
        if club is None:
            return False

        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return user_can_view_club_scheduling(request.user, club)

        membership = get_active_club_membership(request.user, club=club)
        return (
            membership is not None and
            membership.can_create_content() and
            obj.is_user_editable()
        )

class CanCommitClubImportJob(BasePermission):
    message = 'Only owner/admin members can confirm and commit club import jobs.'

    def has_permission(self, request, view):
        if should_bypass_permissions():
            return True

        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if should_bypass_permissions():
            return True

        return user_can_commit_club_import_jobs(request.user, obj.club)

class CanReviewClubJoinRequest(BasePermission):
    message = 'Only owner/admin members can review join requests for this club.'

    def has_permission(self, request, view):
        if should_bypass_permissions():
            return True

        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if should_bypass_permissions():
            return True

        return user_can_review_join_requests(request.user, obj.club)


class CanWithdrawOwnClubJoinRequest(BasePermission):
    message = 'You can only withdraw your own pending join requests.'

    def has_permission(self, request, view):
        if should_bypass_permissions():
            return True

        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if should_bypass_permissions():
            return True

        return obj.user_id == request.user.id


class CanCreateClubInvitation(BasePermission):
    message = 'Only owner/admin members can create invitations for this club.'

    def has_permission(self, request, view):
        if should_bypass_permissions():
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        club_pk = view.kwargs.get('club_pk')
        if not club_pk:
            return False

        membership = get_active_club_membership(user, club_id=club_pk)
        return membership is not None and membership.can_manage_members()


class CanRespondToClubInvitation(BasePermission):
    message = 'You can only respond to invitations addressed to your account.'

    def has_permission(self, request, view):
        if should_bypass_permissions():
            return True

        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if should_bypass_permissions():
            return True

        return obj.invited_user_id == request.user.id


class CanRevokeClubInvitation(BasePermission):
    message = 'Only owner/admin members can revoke invitations for this club.'

    def has_permission(self, request, view):
        if should_bypass_permissions():
            return True

        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if should_bypass_permissions():
            return True

        return user_can_manage_club_invitations(request.user, obj.club)

def user_can_access_club_resources(user, club):
    if should_bypass_permissions():
        return True

    membership = get_active_club_membership(user, club=club)
    return membership is not None


def user_can_manage_club_resources(user, club):
    if should_bypass_permissions():
        return True

    membership = get_active_club_membership(user, club=club)
    return membership is not None and membership.can_create_content()


def user_can_view_club_resource_engagement_dashboard(user, club):
    if should_bypass_permissions():
        return True

    membership = get_active_club_membership(user, club=club)
    return membership is not None and membership.can_create_content()


def user_can_view_club_visible_resource_status(user, resource):
    if should_bypass_permissions():
        return True

    membership = get_active_club_membership(user, club=resource.club)
    if membership is None:
        return False

    return (
        membership.can_create_content() or
        resource.engagement_visibility == ClubResource.EngagementVisibility.CLUB_VISIBLE
    )


class CanAccessClubResources(BasePermission):
    message = 'You must be an active club member to access club resources.'

    def _get_club(self, view):
        club_pk = view.kwargs.get('club_pk')
        if not club_pk:
            return None
        try:
            return Club.objects.get(pk=club_pk)
        except Club.DoesNotExist:
            return None

    def has_permission(self, request, view):
        if should_bypass_permissions():
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        club = self._get_club(view)
        if club is None:
            return False

        return user_can_access_club_resources(request.user, club)

    def has_object_permission(self, request, view, obj):
        if should_bypass_permissions():
            return True

        club = obj.club if hasattr(obj, 'club') else None
        if club is None:
            return False

        return user_can_access_club_resources(request.user, club)


class CanManageClubResources(BasePermission):
    message = 'Only owner/admin/coach members can manage club resources.'

    def _get_club(self, view):
        club_pk = view.kwargs.get('club_pk')
        if not club_pk:
            return None
        try:
            return Club.objects.get(pk=club_pk)
        except Club.DoesNotExist:
            return None

    def has_permission(self, request, view):
        if should_bypass_permissions():
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        club = self._get_club(view)
        if club is None:
            return False

        return user_can_manage_club_resources(request.user, club)

    def has_object_permission(self, request, view, obj):
        if should_bypass_permissions():
            return True

        club = obj.club if hasattr(obj, 'club') else None
        if club is None:
            return False

        return user_can_manage_club_resources(request.user, club)


class CanViewClubResourceEngagementDashboard(BasePermission):
    message = 'Only owner/admin/coach members can view club resource engagement data.'

    def has_permission(self, request, view):
        if should_bypass_permissions():
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        club_pk = view.kwargs.get('club_pk')
        if not club_pk:
            return False

        try:
            club = Club.objects.get(pk=club_pk)
        except Club.DoesNotExist:
            return False

        return user_can_view_club_resource_engagement_dashboard(request.user, club)

    def has_object_permission(self, request, view, obj):
        if should_bypass_permissions():
            return True

        return user_can_view_club_resource_engagement_dashboard(request.user, obj.club)


class CanViewClubResourceStatus(BasePermission):
    message = 'You do not have permission to view engagement status for this resource.'

    def has_permission(self, request, view):
        if should_bypass_permissions():
            return True

        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if should_bypass_permissions():
            return True

        return user_can_view_club_visible_resource_status(request.user, obj)

def user_can_manage_club_import_jobs(user, club):
    if should_bypass_permissions():
        return True

    membership = get_active_club_membership(user, club=club)
    return membership is not None and membership.can_create_content()


class CanAccessClubImportJobs(BasePermission):
    message = 'Only authorised club staff can access club import jobs.'

    def has_permission(self, request, view):
        if should_bypass_permissions():
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        club_pk = view.kwargs.get('club_pk')
        if not club_pk:
            return False

        membership = get_active_club_membership(user, club_id=club_pk)
        return membership is not None and membership.can_create_content()

    def has_object_permission(self, request, view, obj):
        if should_bypass_permissions():
            return True

        return user_can_manage_club_import_jobs(request.user, obj.club)