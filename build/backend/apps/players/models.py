from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from common.constants import Position, PreferredFoot
from apps.players.playerProfile.models import PlayerProfile  


class ExternalProvider(models.TextChoices):
    FOOTBALL_DATA = "football_data", "football-data.org"
    UNDERSTAT = "understat", "Understat"
    SOFASCORE = "sofascore", "Sofascore"


class ProviderSyncStatus(models.TextChoices):
    STARTED = "started", "Started"
    SUCCESS = "success", "Success"
    PARTIAL = "partial", "Partial"
    FAILED = "failed", "Failed"


class Player(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    display_name = models.CharField(
        max_length=50,
        blank=True,
        help_text="Nickname or preferred name",
    )
    date_of_birth = models.DateField(blank=True, null=True)
    nationality = models.CharField(
        max_length=2,
        blank=True,
        help_text="ISO 3166-1 alpha-2 code",
    )
    height_cm = models.PositiveSmallIntegerField(blank=True, null=True)
    preferred_foot = models.CharField(
        max_length=1,
        choices=PreferredFoot.choices,
        blank=True,
    )
    primary_position = models.CharField(
        max_length=4,
        choices=Position.choices,
        blank=True,
    )
    secondary_positions = ArrayField(
        base_field=models.CharField(max_length=4, choices=Position.choices),
        default=list,
        blank=True,
        help_text="List of secondary positions",
    )
    photo = models.ImageField(
        upload_to="players/photos/",
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name", "id"]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.display_name or self.full_name


class PlayerExternalIdentity(models.Model):
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name="external_identities",
    )
    provider = models.CharField(
        max_length=50,
        choices=ExternalProvider.choices,
    )
    external_id = models.CharField(max_length=100)
    provider_display_name = models.CharField(max_length=255, blank=True)
    provider_position = models.CharField(max_length=50, blank=True)
    external_team_id = models.CharField(max_length=100, blank=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    is_manual_override = models.BooleanField(default=False)
    link_confidence = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Confidence score between 0.000 and 1.000",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["provider", "external_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_id"],
                name="uniq_player_ext_identity_provider_external_id",
            ),
        ]
        indexes = [
            models.Index(fields=["player", "provider"]),
            models.Index(fields=["provider", "external_id"]),
        ]

    def __str__(self):
        return f"{self.provider}:{self.external_id} -> {self.player}"


class ProviderSyncJob(models.Model):
    provider = models.CharField(
        max_length=50,
        choices=ExternalProvider.choices,
    )
    resource_type = models.CharField(max_length=50)
    resource_external_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=30,
        choices=ProviderSyncStatus.choices,
        default=ProviderSyncStatus.STARTED,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    records_processed = models.PositiveIntegerField(default=0)
    records_created = models.PositiveIntegerField(default=0)
    records_updated = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    raw_error_summary = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="provider_sync_jobs_triggered",
    )

    class Meta:
        ordering = ["-started_at", "-id"]
        indexes = [
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["provider", "resource_type"]),
        ]

    def __str__(self):
        resource = self.resource_external_id or "n/a"
        return f"{self.provider} {self.resource_type} {resource} [{self.status}]"

