"""
URL routes for the live football API

Connects competition, team, player, overview, league comparison, and saved scenario endpoints to their API views
"""

from django.urls import path

from .views import (
    CompetitionFixturesView,
    CompetitionListView,
    CompetitionPlayersView,
    CompetitionPreviousNextFixturesView,
    CompetitionScorersView,
    CompetitionTableView,
    CompetitionTeamsView,
    PlayerSearchView,
    TeamPlayersView,
    LiveFootballOverviewView,
    LeagueCompareView,
    LeagueExpectedTableView,
    LeagueSavedScenarioDetailView,
    LeagueSavedScenarioListCreateView,
    LeagueScenarioView,
    LeaguesMetaView,
)


# Live football API routes
urlpatterns = [
    # Competition directory and detail data
    path("competitions/", CompetitionListView.as_view(), name="livefootball-competition-list"),
    path("competitions/<int:competition_id>/table/", CompetitionTableView.as_view(), name="livefootball-competition-table"),
    path("competitions/<int:competition_id>/fixtures/", CompetitionFixturesView.as_view(), name="livefootball-competition-fixtures"),
    path("competitions/<int:competition_id>/fixtures/split/", CompetitionPreviousNextFixturesView.as_view(), name="livefootball-competition-fixtures-split"),
    path("competitions/<int:competition_id>/scorers/", CompetitionScorersView.as_view(), name="livefootball-competition-scorers"),
    path("competitions/<int:competition_id>/teams/", CompetitionTeamsView.as_view(), name="livefootball-competition-teams"),
    path("competitions/<int:competition_id>/players/", CompetitionPlayersView.as_view(), name="livefootball-competition-players"),

    # Team and player lookup routes
    path("teams/<int:team_id>/players/", TeamPlayersView.as_view(), name="livefootball-team-players"),
    path("players/search/", PlayerSearchView.as_view(), name="livefootball-player-search"),

    # Live football overview and league metadata routes
    path("overview/", LiveFootballOverviewView.as_view(), name="livefootball-overview"),
    path("leagues/meta/", LeaguesMetaView.as_view(), name="livefootball-leagues-meta"),

    # League prediction and comparison routes
    path("leagues/<int:competition_id>/expected-table/", LeagueExpectedTableView.as_view(), name="livefootball-league-expected-table"),
    path("leagues/<int:competition_id>/compare/", LeagueCompareView.as_view(), name="livefootball-league-compare"),
    path("leagues/<int:competition_id>/scenario/", LeagueScenarioView.as_view(), name="livefootball-league-scenario"),

    # Saved league scenario routes
    path("leagues/<int:competition_id>/saved-scenarios/", LeagueSavedScenarioListCreateView.as_view(), name="livefootball-league-saved-scenarios"),
    path("leagues/saved-scenarios/<int:scenario_id>/", LeagueSavedScenarioDetailView.as_view(), name="livefootball-league-saved-scenario-detail"),
]