from django.contrib import admin

from .models import ClubSeasonEnrichment, PlayerSeasonEnrichment


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