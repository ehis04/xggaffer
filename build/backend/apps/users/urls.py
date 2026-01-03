from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import *

urlpatterns = [
    # user login and registration endpoints
    path("register/", UserRegisterView.as_view(), name="register"),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # profile management endpoints
    path("profile/create/", UserCreateProfileView.as_view(), name='create-profile-view'),
    path("profile/", UserProfileView.as_view(), name='user-profile-view'),
    path("profile/<str:username>", GetProfileView.as_view(), name='get-profile-view'),
    
    # Follow/Unfollow endpoints
    path("profile/<str:username>/follow/", FollowUserView.as_view(), name='follow-user-view'),
    path("profile/<str:username>/follow-status/", CheckFollowStatusView.as_view(), name='follow-status-view'),
    
    # Followers/Following list
    path("profile/<str:username>/followers/", FollowersListView.as_view(), name='followers-list-view'),
    path("profile/<str:username>/following/", FollowingListView.as_view(), name='following-list-view'),
    
    # roles management
    path("profile/role/", UserRoleView.as_view(), name='user-role-view'),
]