from django.contrib import admin

from apps.players.models import (
    Player,
    PlayerExternalIdentity,
    PlayerProfile,
    ProviderSyncJob,
)


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "display_name",
        "full_name",
        "primary_position",
        "is_active",
        "is_verified",
        "created_at",
    )
    search_fields = ("first_name", "last_name", "display_name", "nationality")
    list_filter = ("primary_position", "preferred_foot", "is_active", "is_verified")
    ordering = ("last_name", "first_name", "id")


@admin.register(PlayerExternalIdentity)
class PlayerExternalIdentityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "provider",
        "external_id",
        "player",
        "provider_display_name",
        "last_synced_at",
        "is_primary",
        "is_manual_override",
    )
    search_fields = (
        "external_id",
        "provider_display_name",
        "player__first_name",
        "player__last_name",
        "player__display_name",
    )
    list_filter = ("provider", "is_primary", "is_manual_override")
    ordering = ("provider", "external_id", "id")


@admin.register(ProviderSyncJob)
class ProviderSyncJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "provider",
        "resource_type",
        "resource_external_id",
        "status",
        "started_at",
        "finished_at",
        "records_processed",
        "error_count",
    )
    search_fields = ("resource_type", "resource_external_id", "raw_error_summary")
    list_filter = ("provider", "status", "resource_type")
    ordering = ("-started_at", "-id")


@admin.register(PlayerProfile)
class PlayerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_profile",
        "primary_position",
        "secondary_position",
        "preferred_foot",
        "height_cm",
        "weight_kg",
        "created_at",
    )
    search_fields = ("user_profile__user__username",)
    list_filter = ("primary_position", "secondary_position", "preferred_foot")
    ordering = ("-created_at",)