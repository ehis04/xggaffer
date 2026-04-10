from django.urls import path
from .views import (
    AvailableLineupTeamsView,
    AvailableTacticalTeamsView,
    AvailableTeamsView,
    EloHistoryView,
    EloRankingView,
    ModelInfoView,
    PredictLineupView,
    PredictMatchView,
    PredictAvailabilityView,
    ScorePredictionView,
    SimulationView,
    TacticalAnalysisView,
    WhatIfSimulationView,
)

urlpatterns = [
    path('predict/', PredictMatchView.as_view(), name='predict-match'),
    path('teams/', AvailableTeamsView.as_view(), name='available-teams'),
    path('model-info/', ModelInfoView.as_view(), name='model-info'),

    path('elo/rankings/<str:league>/', EloRankingView.as_view(), name='elo-rankings'),
    path('elo/history/<str:team>/', EloHistoryView.as_view(), name='elo-history'),

    path('score/', ScorePredictionView.as_view(), name='score-prediction'),

    path('simulation/<str:league>/<str:season>/', SimulationView.as_view(), name='simulation'),
    path('simulation/<str:league>/<str:season>/what-if/', WhatIfSimulationView.as_view(), name='simulation-what-if'),
    path('lineup/', PredictLineupView.as_view(), name='predict-lineup'),
    path('lineup/teams/', AvailableLineupTeamsView.as_view(), name='available-lineup-teams'),
    path('availability/', PredictAvailabilityView.as_view(), name='predict-availability'),

    path('tactical/', TacticalAnalysisView.as_view(), name='tactical-analysis'),
    path('tactical/teams/', AvailableTacticalTeamsView.as_view(), name='available-tactical-teams'),
]