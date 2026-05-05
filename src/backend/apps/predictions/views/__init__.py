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
from apps.predictions.services.odds.service import OddsComparisonService
from apps.predictions.services.prediction_helper import build_match_prediction_payload
from apps.predictions.models import HistoricalMarketBenchmark
from .availability_widget import AvailabilityWidgetView
from .lineup_widget import LineupWidgetView
from .match_prediction_widget import MatchPredictionWidgetView
from .model_trust_widget import ModelTrustWidgetView
from .projected_table_widget import ProjectedTableWidgetView
from .scoreline_widget import ScorelineWidgetView
from .tactical_widget import TacticalSummaryWidgetView

__all__ = [
    "AvailableLineupTeamsView",
    "AvailableTacticalTeamsView",
    "AvailableTeamsView",
    "AvailabilityWidgetView",
    "build_match_prediction_payload",
    "ChatQueryView",
    "EloHistoryView",
    "EloRankingView",
    "HistoricalMarketBenchmark",
    "LineupWidgetView",
    "MatchPredictionWidgetView",
    "ModelInfoView",
    "ModelTrustWidgetView",
    "OddsAccuracyView",
    "OddsComparisonService",
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
    "TacticalSummaryWidgetView",
    "WhatIfSimulationView",
]