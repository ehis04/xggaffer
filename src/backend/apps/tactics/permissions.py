from rest_framework import permissions

from django.conf import settings

from apps.clubs.models import ClubMembership


class BypassablePermission(permissions.BasePermission):
    def should_bypass(self) -> bool:
        return getattr(settings, 'BYPASS_PERMISSIONS', False)


class TacticsBoardPermission(BypassablePermission):
    message = 'You do not have permission to access tactics boards for this club.'
    creator_only_actions = {'trash', 'restore', 'permanent_delete'}

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