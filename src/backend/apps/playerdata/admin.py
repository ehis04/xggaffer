"""
Admin configuration for player data enrichment models

Adds searchable and filterable admin views for club and player season enrichment records
"""

from django.contrib import admin

from .models import ClubSeasonEnrichment, PlayerSeasonEnrichment


# Admin view for club season enrichment records
@admin.register(ClubSeasonEnrichment)
class ClubSeasonEnrichmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "club",
        "provider",
        "season_label",
        "competition_code",
        "matches_played",
        "xg",
        "xga",
        "last_synced_at",
    )
    list_filter = ("provider", "season_label", "competition_code")
    search_fields = ("club__name", "competition_code", "competition_name", "external_team_id")


# Admin view for player season enrichment records
@admin.register(PlayerSeasonEnrichment)
class PlayerSeasonEnrichmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "player",
        "club",
        "provider",
        "season_label",
        "competition_code",
        "matches_played",
        "goals",
        "assists",
        "xg",
        "xa",
        "last_synced_at",
    )
    list_filter = ("provider", "season_label", "competition_code")
    search_fields = (
        "player__first_name",
        "player__last_name",
        "club__name",
        "competition_code",
        "competition_name",
        "external_player_id",
        "external_team_id",
    )