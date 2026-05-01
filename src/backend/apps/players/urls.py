from django.urls import path
from apps.players.playerProfile.views import CreatePlayerProfileView, PlayerProfileView

urlpatterns = [
    path('profile/create/', CreatePlayerProfileView.as_view(), name='create-player-profile'),
    path('profile/', PlayerProfileView.as_view(), name='player-profile'),
]