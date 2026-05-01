from django.urls import path
from .views import (
    AvailableLineupTeamsView,
    AvailableTacticalTeamsView,
    AvailableTeamsView,
    AvailabilityWidgetView,
    ChatQueryView,
    EloHistoryView,
    EloRankingView,
    LineupWidgetView,
    MatchPredictionWidgetView,
    ModelInfoView,
    OddsAccuracyView,
    ModelTrustWidgetView,
    OddsComparisonView,
    OddsFixtureListView,
    OddsTeamsView,
    PredictLineupView,
    PredictMatchView,
    PredictAvailabilityView,
    ProjectedTableWidgetView,
    ScorePredictionView,
    ScorelineWidgetView,
    SimulationView,
    TacticalAnalysisView,
    TacticalSummaryWidgetView,
    WhatIfSimulationView,
)

urlpatterns = [
    path('predict/', PredictMatchView.as_view(), name='predict-match'),
    path('odds/compare/', OddsComparisonView.as_view(), name='odds-comparison'),
    path('odds/fixtures/', OddsFixtureListView.as_view(), name='odds-fixture-list'),
    path('odds/teams/', OddsTeamsView.as_view(), name='odds-teams'),
    path('odds/accuracy/', OddsAccuracyView.as_view(), name='odds-accuracy'),
    path('teams/', AvailableTeamsView.as_view(), name='available-teams'),
    path('model-info/', ModelInfoView.as_view(), name='model-info'),

    path('chat/', ChatQueryView.as_view(), name='chat-query'),

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

    path('widget/match-prediction/', MatchPredictionWidgetView.as_view(), name='widget-match-prediction'),
    path('widget/scoreline/', ScorelineWidgetView.as_view(), name='widget-scoreline'),
    path('widget/projected-table/', ProjectedTableWidgetView.as_view(), name='widget-projected-table'),
    path('widget/availability/', AvailabilityWidgetView.as_view(), name='widget-availability'),
    path('widget/predicted-lineup/', LineupWidgetView.as_view(), name='widget-predicted-lineup'),
    path('widget/tactical-summary/', TacticalSummaryWidgetView.as_view(), name='widget-tactical-summary'),
    path('widget/model-trust/', ModelTrustWidgetView.as_view(), name='widget-model-trust'),
]