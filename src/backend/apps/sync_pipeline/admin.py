from django.contrib import admin
from django.utils import timezone

from apps.sync_pipeline.models import PublishedSnapshot, SourceHealth, SyncRun
from common.constants import SyncStatus


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    """One row per provider/dataset/scope execution attempt."""

    list_display = [
        'provider', 'dataset', 'scope_key', 'status',
        'started_at', 'finished_at', 'rows_seen', 'rows_changed', 'triggered_by',
    ]
    list_filter = ['status', 'provider', 'dataset']
    search_fields = ['scope_key', 'error_summary']
    date_hierarchy = 'started_at'
    ordering = ['-started_at']
    readonly_fields = [
        'provider', 'dataset', 'scope_key', 'status', 'started_at',
        'finished_at', 'rows_seen', 'rows_changed', 'error_summary',
        'retry_count', 'triggered_by',
    ]
    actions = ['mark_selected_as_failed']

    @admin.action(description='Mark selected runs as FAILED (for stuck RUNNING rows)')
    def mark_selected_as_failed(self, request, queryset):
        updated = queryset.filter(status=SyncStatus.RUNNING).update(
            status=SyncStatus.FAILED,
            finished_at=timezone.now(),
            error_summary='Manually marked FAILED via admin.',
        )
        self.message_user(request, f'{updated} run(s) marked as FAILED.')


@admin.register(PublishedSnapshot)
class PublishedSnapshotAdmin(admin.ModelAdmin):
    """Active published version per surface. Only one row per surface should be is_active=True."""

    list_display = ['surface', 'version', 'status', 'is_active', 'published_at', 'built_at']
    list_filter = ['surface', 'is_active', 'status']
    search_fields = ['surface', 'version']
    ordering = ['-published_at']
    readonly_fields = [
        'surface', 'version', 'status', 'source_provider_set',
        'source_max_fetched_at', 'built_at', 'published_at', 'invalidated_at',
        'is_active', 'metadata',
    ]


@admin.register(SourceHealth)
class SourceHealthAdmin(admin.ModelAdmin):
    """Per-provider health: quota window, consecutive failures, SofaScore session state."""

    list_display = [
        'provider', 'requests_used', 'requests_limit', 'consecutive_failures',
        'session_valid', 'last_error_at', 'last_throttled_at',
    ]
    ordering = ['-consecutive_failures']
    readonly_fields = [
        'provider', 'window_started_at', 'requests_used', 'requests_limit',
        'last_throttled_at', 'last_error_at', 'consecutive_failures',
    ]
    actions = ['reset_sofascore_session']

    @admin.action(description='Reset session_valid=True for SofaScore (use after manual cookie renewal)')
    def reset_sofascore_session(self, request, queryset):
        updated = queryset.filter(provider='sofascore').update(session_valid=True)
        self.message_user(request, f'{updated} SofaScore health row(s) marked session_valid=True.')