from django.contrib import admin

from .models import TrainingBlock, TrainingSession, TrainingSessionPlayer


class TrainingBlockInline(admin.TabularInline):
    model = TrainingBlock
    extra = 0


class TrainingSessionPlayerInline(admin.TabularInline):
    model = TrainingSessionPlayer
    extra = 0


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'club', 'status', 'session_type', 'start_datetime', 'created_by']
    list_filter = ['status', 'session_type', 'intensity', 'club']
    search_fields = ['title', 'club__name', 'main_objective', 'linked_opponent']
    inlines = [TrainingBlockInline, TrainingSessionPlayerInline]


@admin.register(TrainingBlock)
class TrainingBlockAdmin(admin.ModelAdmin):
    list_display = ['title', 'session', 'order', 'block_type', 'duration_minutes']
    list_filter = ['block_type']
    search_fields = ['title', 'session__title']


@admin.register(TrainingSessionPlayer)
class TrainingSessionPlayerAdmin(admin.ModelAdmin):
    list_display = ['session', 'club_player', 'attendance_status', 'rpe_score']
    list_filter = ['attendance_status']
    search_fields = ['session__title', 'club_player__first_name', 'club_player__last_name']
