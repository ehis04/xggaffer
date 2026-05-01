from django.conf import settings
from rest_framework import permissions

from apps.clubs.models import ClubMembership


class BypassablePermission(permissions.BasePermission):
    def should_bypass(self) -> bool:
        return getattr(settings, 'BYPASS_PERMISSIONS', False)


class TeamsheetPermission(BypassablePermission):
    message = 'You do not have permission to access teamsheets for this club.'
    creator_only_actions = {'trash', 'restore', 'permanent_delete', 'destroy'}

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

    def has_object_permission(self, request, view, obj) -> bool:
        if self.should_bypass():
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        club_id = self._resolve_club_id(obj)
        if club_id is None:
            return False

        membership = ClubMembership.objects.filter(
            user=user,
            club_id=club_id,
            is_active=True,
        ).first()

        if membership is None:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        if getattr(view, 'action', None) in self.creator_only_actions:
            creator_id = self._resolve_creator_id(obj)
            return creator_id == user.id

        return membership.can_create_content()

    def _resolve_club_id(self, obj):
        if hasattr(obj, 'club_id'):
            return obj.club_id

        if hasattr(obj, 'teamsheet'):
            return obj.teamsheet.club_id

        return None

    def _resolve_creator_id(self, obj):
        if hasattr(obj, 'created_by_id'):
            return obj.created_by_id

        if hasattr(obj, 'teamsheet'):
            return obj.teamsheet.created_by_id

        return None