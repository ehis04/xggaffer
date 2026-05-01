from django.db import models
from django.db.models import Q

from common.constants import DatasetName, FreshnessStatus, ProviderName, PublishStatus, SyncStatus


class SyncRun(models.Model):
    provider = models.CharField(max_length=32, choices=ProviderName.choices)
    dataset = models.CharField(max_length=64, choices=DatasetName.choices)
    scope_key = models.CharField(max_length=128)
    status = models.CharField(max_length=16, choices=SyncStatus.choices, default=SyncStatus.PENDING)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    rows_seen = models.PositiveIntegerField(null=True, blank=True)
    rows_changed = models.PositiveIntegerField(null=True, blank=True)
    error_summary = models.TextField(blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    triggered_by = models.CharField(max_length=32)

    class Meta:
        indexes = [
            models.Index(fields=['provider', 'dataset', 'scope_key', 'started_at']),
            models.Index(fields=['status', 'started_at']),
        ]

    def __str__(self):
        return f'{self.provider}/{self.dataset}/{self.scope_key} [{self.status}]'


class PublishedSnapshot(models.Model):
    surface = models.CharField(max_length=64)
    version = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=PublishStatus.choices)
    source_provider_set = models.JSONField(default=list)
    source_max_fetched_at = models.DateTimeField(null=True, blank=True)
    built_at = models.DateTimeField()
    published_at = models.DateTimeField(null=True, blank=True)
    invalidated_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=['surface', 'is_active']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['surface'],
                condition=Q(is_active=True),
                name='uniq_active_snapshot_per_surface',
            ),
        ]

    def __str__(self):
        active = 'ACTIVE' if self.is_active else self.status
        return f'{self.surface} v{self.version} [{active}]'


class SourceHealth(models.Model):
    provider = models.CharField(max_length=32, choices=ProviderName.choices, unique=True)
    window_started_at = models.DateTimeField()
    requests_used = models.PositiveIntegerField(default=0)
    requests_limit = models.PositiveIntegerField(null=True, blank=True)
    last_throttled_at = models.DateTimeField(null=True, blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    consecutive_failures = models.PositiveSmallIntegerField(default=0)
    session_valid = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.provider} [used={self.requests_used}, failures={self.consecutive_failures}]'
