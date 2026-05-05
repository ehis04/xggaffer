from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from .views import (
    ClubViewSet,
    ClubMembershipViewSet,
    ClubPlayerViewSet,
    ClubJoinRequestViewSet,
    ClubInvitationViewSet,
    ClubEventViewSet,
    FixtureViewSet,
    ClubResourceViewSet,
    ClubImportJobViewSet,
    ClubPlayerInjuryView,
    ClubPlayerInjuryResolveView,
    ClubPlayerManualStatsView,
    ClubSeasonResultView,
    ClubSeasonResultDetailView,
)
from apps.tactics.urls import register_tactics_routes
from apps.training.urls import register_training_routes
from apps.teamsheets.views import TeamsheetViewSet, TeamsheetPlayerViewSet


router = DefaultRouter()
router.register(r'', ClubViewSet, basename='club')


clubs_router = NestedDefaultRouter(router, r'', lookup='club')
clubs_router.register(r'events', ClubEventViewSet, basename='club-event')
clubs_router.register(r'fixtures', FixtureViewSet, basename='club-fixture')
clubs_router.register(r'memberships', ClubMembershipViewSet, basename='club-membership')
clubs_router.register(r'players', ClubPlayerViewSet, basename='club-player')
clubs_router.register(r'teamsheets', TeamsheetViewSet, basename='club-teamsheet')
clubs_router.register(r'join-requests', ClubJoinRequestViewSet, basename='club-join-request')
clubs_router.register(r'invitations', ClubInvitationViewSet, basename='club-invitation')
clubs_router.register(r'resources', ClubResourceViewSet, basename='club-resource')
clubs_router.register(r'import-jobs', ClubImportJobViewSet, basename='club-import-job')

tactics_routers = register_tactics_routes(clubs_router)
training_routers = register_training_routes(clubs_router)

teamsheets_router = NestedDefaultRouter(clubs_router, r'teamsheets', lookup='teamsheet')
teamsheets_router.register(r'players', TeamsheetPlayerViewSet, basename='teamsheet-player')

urlpatterns = [
    path('my-join-requests/', ClubJoinRequestViewSet.as_view({'get': 'mine'}), name='club-my-join-requests'),
    path('my-invitations/', ClubInvitationViewSet.as_view({'get': 'mine'}), name='club-my-invitations'),
    path('', include(router.urls)),
    path('', include(clubs_router.urls)),
    path('', include(teamsheets_router.urls)),
    path(
        '<int:club_id>/players/<int:player_id>/injuries/',
        ClubPlayerInjuryView.as_view(),
        name='club-player-injuries',
    ),
    path(
        '<int:club_id>/players/<int:player_id>/injuries/<int:injury_id>/resolve/',
        ClubPlayerInjuryResolveView.as_view(),
        name='club-player-injury-resolve',
    ),
    path(
        '<int:club_id>/players/<int:player_id>/stats/',
        ClubPlayerManualStatsView.as_view(),
        name='club-player-manual-stats',
    ),
    path(
        '<int:club_id>/season-results/',
        ClubSeasonResultView.as_view(),
        name='club-season-results',
    ),
    path(
        '<int:club_id>/season-results/<int:result_id>/',
        ClubSeasonResultDetailView.as_view(),
        name='club-season-result-detail',
    ),
    *[path('', include(tactics_router.urls)) for tactics_router in tactics_routers],
    *[path('', include(training_router.urls)) for training_router in training_routers],
]
