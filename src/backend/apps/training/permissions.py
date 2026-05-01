from rest_framework import permissions

from apps.clubs.models import ClubMembership
from apps.clubs.permissions import should_bypass_permissions


class TrainingSessionPermission(permissions.BasePermission):
    message = 'You do not have permission to access training sessions for this club.'

    def has_permission(self, request, view):
        if should_bypass_permissions():
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

        return membership.can_create_content()

    def has_object_permission(self, request, view, obj):
        if should_bypass_permissions():
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

        return membership.can_create_content()

    def _resolve_club_id(self, obj):
        if hasattr(obj, 'club_id'):
            return obj.club_id
        if hasattr(obj, 'session'):
            return obj.session.club_id
        return None

