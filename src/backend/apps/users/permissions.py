from rest_framework.permissions import BasePermission
from .models import UserRole, Role

# Defines role-based permission classes used to restrict API access by user role

message = "You have the incorrect role to access this resource."

# Allows access only to coaches
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

# Allows access only to players
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

# Allows access only to referees
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

# Allows access only to fans
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