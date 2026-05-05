from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import FitbitToken, DailyActivitySummary


@admin.register(FitbitToken)
class FitbitTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "fitbit_user_id", "connected_at", "last_synced_at", "is_expired"]
    readonly_fields = ["connected_at", "last_synced_at", "expires_at"]
    search_fields = ["user__username", "user__email", "fitbit_user_id"]

    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True


@admin.register(DailyActivitySummary)
class DailyActivitySummaryAdmin(admin.ModelAdmin):
    list_display = ["user", "date", "steps", "calories_burned", "active_minutes", "resting_heart_rate"]
    list_filter = ["date"]
    search_fields = ["user__username"]
    ordering = ["-date"]