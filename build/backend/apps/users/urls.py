from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import UserRegisterView, GetProfileView, UserProfileView, UserCreateProfileView

urlpatterns = [
    path("register/", UserRegisterView.as_view(), name="register"),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("profile/create/", UserCreateProfileView.as_view(), name='create-profile-view'),
    path("profile/", UserProfileView.as_view(), name='user-profile-view'),
    path("profile/<str:username>", GetProfileView.as_view(), name='get-profile-view'),
]