from django.contrib import admin

from .models import (
    Competition,
    CompetitionFixture,
    CompetitionTableRow,
    CompetitionTableSnapshot,
    CompetitionTopScorer,
    PlayerDirectoryEntry,
    TeamDirectoryEntry,
)


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "code",
        "provider",
        "area_name",
        "current_season_label",
        "current_matchday",
        "last_synced_at",
    )
    list_filter = ("provider", "area_name", "current_season_label")
    search_fields = ("name", "code", "area_name", "external_id")
    ordering = ("name", "provider", "id")


@admin.register(TeamDirectoryEntry)
class TeamDirectoryEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "competition",
        "season_label",
        "provider",
        "tla",
        "area_name",
        "last_synced_at",
    )
    list_filter = ("provider", "season_label", "competition")
    search_fields = (
        "name",
        "short_name",
        "tla",
        "external_id",
        "competition__name",
    )
    autocomplete_fields = ("competition",)
    ordering = ("competition", "name", "id")


@admin.register(PlayerDirectoryEntry)
class PlayerDirectoryEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "player_name",
        "team",
        "provider",
        "primary_position",
        "squad_number",
        "nationality",
        "is_active",
        "canonical_player",
        "last_synced_at",
    )
    list_filter = (
        "provider",
        "is_active",
        "primary_position",
        "team__competition",
        "team__season_label",
    )
    search_fields = (
        "player_name",
        "first_name",
        "last_name",
        "external_player_id",
        "team__name",
        "team__competition__name",
        "canonical_player__first_name",
        "canonical_player__last_name",
    )
    autocomplete_fields = ("team", "canonical_player")
    ordering = ("team", "player_name", "id")


class CompetitionTableRowInline(admin.TabularInline):
    model = CompetitionTableRow
    extra = 0
    fields = (
        "position",
        "team",
        "team_name",
        "played",
        "won",
        "drawn",
        "lost",
        "goals_for",
        "goals_against",
        "goal_difference",
        "points",
        "form",
    )
    autocomplete_fields = ("team",)
    ordering = ("position",)
    show_change_link = True


@admin.register(CompetitionTableSnapshot)
class CompetitionTableSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "competition",
        "season_label",
        "snapshot_label",
        "matchday",
        "fetched_at",
        "synced_at",
    )
    list_filter = ("competition", "season_label", "snapshot_label")
    search_fields = ("competition__name", "season_label", "snapshot_label")
    autocomplete_fields = ("competition",)
    inlines = (CompetitionTableRowInline,)
    ordering = ("competition", "-season_label", "-synced_at", "-id")


@admin.register(CompetitionTableRow)
class CompetitionTableRowAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "snapshot",
        "position",
        "team_name",
        "played",
        "won",
        "drawn",
        "lost",
        "goal_difference",
        "points",
    )
    list_filter = (
        "snapshot__competition",
        "snapshot__season_label",
        "snapshot__snapshot_label",
    )
    search_fields = (
        "team_name",
        "external_team_id",
        "snapshot__competition__name",
    )
    autocomplete_fields = ("snapshot", "team")
    ordering = ("snapshot", "position", "id")


@admin.register(CompetitionFixture)
class CompetitionFixtureAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "competition",
        "season_label",
        "matchday",
        "home_team_name",
        "away_team_name",
        "status",
        "kickoff_at",
        "home_score",
        "away_score",
        "synced_at",
    )
    list_filter = ("competition", "season_label", "status")
    search_fields = (
        "home_team_name",
        "away_team_name",
        "external_match_id",
        "competition__name",
        "home_external_team_id",
        "away_external_team_id",
    )
    autocomplete_fields = ("competition", "home_team", "away_team")
    ordering = ("competition", "kickoff_at", "id")


@admin.register(CompetitionTopScorer)
class CompetitionTopScorerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "competition",
        "season_label",
        "rank",
        "player_name",
        "team_name",
        "goals",
        "penalties",
        "canonical_player",
        "synced_at",
    )
    list_filter = ("competition", "season_label")
    search_fields = (
        "player_name",
        "team_name",
        "external_player_id",
        "external_team_id",
        "competition__name",
        "canonical_player__first_name",
        "canonical_player__last_name",
    )
    autocomplete_fields = ("competition", "team", "canonical_player")
    ordering = ("competition", "season_label", "rank", "id")