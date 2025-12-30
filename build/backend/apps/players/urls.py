from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.players.playerProfile.views import CreatePlayerProfileView, PlayerProfileView

urlpatterns = [
    path('profile/create/', CreatePlayerProfileView.as_view(), name='create-player-profile'),
    path('profile/', PlayerProfileView.as_view(), name='player-profile'),
]