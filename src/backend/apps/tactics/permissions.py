"""
Permissions for tactics board access

Controls club membership access, content creation permissions, creator-only trash actions, and optional development bypass behaviour
"""

from rest_framework import permissions

from django.conf import settings

from apps.clubs.models import ClubMembership


# Permission base class with optional settings-based bypass
class BypassablePermission(permissions.BasePermission):

    # Check whether permission checks should be bypassed
    def should_bypass(self) -> bool:
        return getattr(settings, 'BYPASS_PERMISSIONS', False)


# Permission class for tactics board club access and creator-only actions
class TacticsBoardPermission(BypassablePermission):
    message = 'You do not have permission to access tactics boards for this club.'
    creator_only_actions = {'trash', 'restore', 'permanent_delete'}

    # Check general access to tactics board routes
    def has_permission(self, request, view) -> bool:
        if self.should_bypass():
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        club_pk = view.kwargs.get('club_pk')
        if not club_pk:
            return False

        membership = ClubMembership.objects.filter(
            user=user,
            club_id=club_pk,
            is_active=True,
        ).first()

        if membership is None:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        if getattr(view, 'action', None) in self.creator_only_actions:
            return True

        return membership.can_create_content()

    # Check object-level access to a tactics board, frame, or item
    def has_object_permission(self, request, view, obj) -> bool:
        if self.should_bypass():
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        club = self._resolve_club(obj)
        if club is None:
            return False

        membership = ClubMembership.objects.filter(
            user=user,
            club=club,
            is_active=True,
        ).first()

        if membership is None:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        if getattr(view, 'action', None) in self.creator_only_actions:
            return getattr(obj, 'created_by_id', None) == user.id

        return membership.can_create_content()

    # Resolve the owning club from a board, frame, or item object
    def _resolve_club(self, obj):
        if hasattr(obj, 'club'):
            return obj.club

        if hasattr(obj, 'board') and hasattr(obj.board, 'club'):
            return obj.board.club

        if (
            hasattr(obj, 'frame')
            and hasattr(obj.frame, 'board')
            and hasattr(obj.frame.board, 'club')
        ):
            return obj.frame.board.club

        return None