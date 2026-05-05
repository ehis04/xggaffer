from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import *
from .views_auth import *
from .views_verification import *


router = DefaultRouter()
router.register(r'profiles', UserProfileViewSet, basename='profile')
router.register(r'roles', UserRoleViewSet, basename='role')

urlpatterns = [
    path('auth/login/', CookieTokenObtainPairView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/refresh/', CookieTokenRefreshView.as_view(), name='auth-refresh'),
    path('auth/me/', CurrentUserView.as_view(), name='auth-me'),
    path('auth/csrf/', csrf_token_view),

    path('auth/password-reset/request/', RequestPasswordResetView.as_view(), name='request-password-reset'),
    path('auth/password-reset/', ResetPasswordView.as_view(), name='reset-password'),

    path('register/', UserRegisterView.as_view(), name='register'),

    path('auth/verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('auth/send-verification/', SendVerificationEmailView.as_view(), name='send-verification'),
    path('auth/resend-verification/', ResendVerificationEmailView.as_view(), name='resend-verification'),
    path('auth/verification-status/', VerificationStatusView.as_view(), name='verification-status'),

    path('profile/create/', UserCreateProfileView.as_view(), name='create-profile'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),

    path('profile/role/', UserRoleView.as_view(), name='user-role'),
    path('profile/active-role/', ActiveUserRoleView.as_view(), name='active-user-role'),

    path('profile/<str:username>/', GetProfileView.as_view(), name='get-profile'),

    path('profile/<str:username>/follow/', FollowUserView.as_view(), name='follow-user'),
    path('profile/<str:username>/follow-status/', CheckFollowStatusView.as_view(), name='follow-status'),
    path('profile/<str:username>/followers/', FollowersListView.as_view(), name='followers-list'),
    path('profile/<str:username>/following/', FollowingListView.as_view(), name='following-list'),
    path(
        'follow-requests/<int:follow_request_id>/<str:action_name>/',
        FollowRequestReviewView.as_view(),
        name='follow-request-review',
    ),

    path('', include(router.urls)),
]
