"""
URL routes for the player data API

Connects player summaries, club summaries, player overviews, comparisons, and enriched player lists to their API views
"""

from django.urls import path

from .views import (
    ClubSeasonSummaryView,
    EnrichedPlayerListView,
    PlayerComparisonView,
    PlayerOverviewComparisonView,
    PlayerOverviewView,
    PlayerSeasonSummaryView,
)

app_name = "playerdata"


urlpatterns = [
    # Summary routes
    path("players/<int:player_id>/season-summary/", PlayerSeasonSummaryView.as_view(), name="player-season-summary"),
    path("clubs/<int:club_id>/season-summary/", ClubSeasonSummaryView.as_view(), name="club-season-summary"),

    # Overview and comparison routes
    path("players/<int:player_id>/overview/", PlayerOverviewView.as_view(), name="player-overview"),
    path("players/compare/", PlayerComparisonView.as_view(), name="player-compare"),
    path("players/overview-compare/", PlayerOverviewComparisonView.as_view(), name="player-overview-compare"),

    # Enriched player listing route
    path("players/enriched/", EnrichedPlayerListView.as_view(), name="player-enriched-list"),
]