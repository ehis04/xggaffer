from rest_framework import serializers

from apps.sync_pipeline.models import PublishedSnapshot, SourceHealth, SyncRun


class SyncRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncRun
        fields = [
            'id', 'provider', 'dataset', 'scope_key', 'status',
            'started_at', 'finished_at', 'rows_seen', 'rows_changed',
            'error_summary', 'retry_count', 'triggered_by',
        ]


class PublishedSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublishedSnapshot
        fields = [
            'id', 'surface', 'version', 'status', 'source_provider_set',
            'source_max_fetched_at', 'built_at', 'published_at',
            'invalidated_at', 'is_active', 'metadata',
        ]


class SourceHealthSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceHealth
        fields = [
            'provider', 'window_started_at', 'requests_used', 'requests_limit',
            'last_throttled_at', 'last_error_at', 'consecutive_failures', 'session_valid',
        ]


class SurfaceHealthSummarySerializer(serializers.Serializer):
    surface = serializers.CharField()
    is_stale = serializers.BooleanField()
    is_degraded = serializers.BooleanField()
    snapshot_published_at = serializers.DateTimeField(allow_null=True)
    active_version = serializers.CharField(allow_null=True)
    consecutive_failures = serializers.IntegerField()
    last_successful_run_at = serializers.DateTimeField(allow_null=True)