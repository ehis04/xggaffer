from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import *
from .views_auth import *


router = DefaultRouter()
router.register(r'profiles', UserProfileViewSet, basename='profile')
router.register(r'roles', UserRoleViewSet, basename='role')

urlpatterns = [
    path('auth/login/', CookieTokenObtainPairView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/refresh/', CookieTokenRefreshView.as_view(), name='auth-refresh'),
    path('auth/me/', CurrentUserView.as_view(), name='auth-me'),

    path('register/', UserRegisterView.as_view(), name='register'),

    path('auth/verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('auth/resend-verification/', ResendVerificationEmailView.as_view(), name='resend-verification'),

    path('profile/create/', UserCreateProfileView.as_view(), name='create-profile'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),

    # Explicit role endpoint must be before the dynamic username route so that
    # '/profile/role/' isn't interpreted as a username == 'role'.
    path('profile/role/', UserRoleView.as_view(), name='user-role'),

    path('profile/<str:username>/', GetProfileView.as_view(), name='get-profile'),

    path('profile/<str:username>/follow/', FollowUserView.as_view(), name='follow-user'),
    path('profile/<str:username>/follow-status/', CheckFollowStatusView.as_view(), name='follow-status'),
    path('profile/<str:username>/followers/', FollowersListView.as_view(), name='followers-list'),
    path('profile/<str:username>/following/', FollowingListView.as_view(), name='following-list'),

    path('', include(router.urls)),
]