from __future__ import annotations

from ..views_core import (
    AvailableLineupTeamsView,
    AvailableTacticalTeamsView,
    AvailableTeamsView,
    ChatQueryView,
    EloHistoryView,
    EloRankingView,
    ModelInfoView,
    OddsAccuracyView,
    OddsComparisonView,
    OddsFixtureListView,
    OddsTeamsView,
    PredictAvailabilityView,
    PredictLineupView,
    PredictMatchView,
    ScorePredictionView,
    SimulationView,
    TacticalAnalysisView,
    WhatIfSimulationView,
)
from .match_prediction_widget import MatchPredictionWidgetView
from .projected_table_widget import ProjectedTableWidgetView
from .scoreline_widget import ScorelineWidgetView

__all__ = [
    "AvailableLineupTeamsView",
    "AvailableTacticalTeamsView",
    "AvailableTeamsView",
    "ChatQueryView",
    "EloHistoryView",
    "EloRankingView",
    "MatchPredictionWidgetView",
    "ModelInfoView",
    "OddsAccuracyView",
    "OddsComparisonView",
    "OddsFixtureListView",
    "OddsTeamsView",
    "PredictAvailabilityView",
    "PredictLineupView",
    "PredictMatchView",
    "ProjectedTableWidgetView",
    "ScorelineWidgetView",
    "ScorePredictionView",
    "SimulationView",
    "TacticalAnalysisView",
    "WhatIfSimulationView",
]