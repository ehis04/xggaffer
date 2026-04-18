from rest_framework.permissions import BasePermission
from .models import UserRole, Role

message = "You have the incorrect role to access this resource."

class IsCoach(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        try:
            return UserRole.objects.filter(
                user_profile=request.user.profile,
                role=Role.COACH
            ).exists()
        except:
            return False

class IsPlayer(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        try:
            return UserRole.objects.filter(
                user_profile=request.user.profile,
                role=Role.PLAYER
            ).exists()
        except:
            return False

class IsReferee(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        try:
            return UserRole.objects.filter(
                user_profile=request.user.profile,
                role=Role.REFEREE
            ).exists()
        except:
            return False

class IsFan(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        try:
            return UserRole.objects.filter(
                user_profile=request.user.profile,
                role=Role.FAN
            ).exists()
        except:
            return False