from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter

from .views import ClubViewSet, ClubMembershipViewSet, PlayerProfileViewSet
from apps.teamsheets.views import TeamsheetViewSet, TeamsheetPlayerViewSet


router = DefaultRouter()
router.register(r'', ClubViewSet, basename='club')

clubs_router = NestedDefaultRouter(router, r'', lookup='club')
clubs_router.register(r'memberships', ClubMembershipViewSet, basename='club-membership')
clubs_router.register(r'players', PlayerProfileViewSet, basename='club-player')
clubs_router.register(r'teamsheets', TeamsheetViewSet, basename='club-teamsheet')

teamsheets_router = NestedDefaultRouter(clubs_router, r'teamsheets', lookup='teamsheet')
teamsheets_router.register(r'players', TeamsheetPlayerViewSet, basename='teamsheet-player')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(clubs_router.urls)),
    path('', include(teamsheets_router.urls)),
]
