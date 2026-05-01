"""
Models for player and club season enrichment data

Stores provider-backed football metrics linked to internal clubs and players without replacing canonical identity records
"""

from django.db import models

from apps.clubs.models import Club
from apps.players.models import ExternalProvider, Player


# Season-level provider-backed team metrics linked to an internal club
class ClubSeasonEnrichment(models.Model):
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="season_enrichments",
    )
    provider = models.CharField(
        max_length=50,
        choices=ExternalProvider.choices,
    )
    season_label = models.CharField(max_length=20)
    competition_code = models.CharField(max_length=50, blank=True)
    competition_name = models.CharField(max_length=255, blank=True)
    external_team_id = models.CharField(max_length=100, blank=True)

    matches_played = models.PositiveSmallIntegerField(default=0)
    wins = models.PositiveSmallIntegerField(default=0)
    draws = models.PositiveSmallIntegerField(default=0)
    losses = models.PositiveSmallIntegerField(default=0)
    goals_for = models.PositiveSmallIntegerField(default=0)
    goals_against = models.PositiveSmallIntegerField(default=0)

    xg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    xga = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    npxg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    ppda = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Passes allowed per defensive action, if available from the provider.",
    )

    last_synced_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    raw_snapshot = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["club", "provider", "season_label", "competition_code", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["club", "provider", "season_label", "competition_code"],
                name="uniq_club_season_enrichment",
            ),
        ]
        indexes = [
            models.Index(
                fields=["club", "provider", "season_label"],
                name="pdat_club_season_idx",
            ),
            models.Index(
                fields=["provider", "season_label", "competition_code"],
                name="pdat_club_comp_idx",
            ),
        ]

    # Return a readable club season enrichment label
    def __str__(self) -> str:
        competition = f" {self.competition_code}" if self.competition_code else ""
        return f"{self.club} | {self.provider} | {self.season_label}{competition}"


# Season-level provider-backed player metrics linked to a canonical player
class PlayerSeasonEnrichment(models.Model):
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name="season_enrichments",
    )
    club = models.ForeignKey(
        Club,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="player_season_enrichments",
    )
    provider = models.CharField(
        max_length=50,
        choices=ExternalProvider.choices,
    )
    season_label = models.CharField(max_length=20)
    competition_code = models.CharField(max_length=50, blank=True)
    competition_name = models.CharField(max_length=255, blank=True)
    external_player_id = models.CharField(max_length=100, blank=True)
    external_team_id = models.CharField(max_length=100, blank=True)

    matches_played = models.PositiveSmallIntegerField(default=0)
    minutes_played = models.PositiveIntegerField(default=0)
    goals = models.PositiveSmallIntegerField(default=0)
    assists = models.PositiveSmallIntegerField(default=0)
    shots = models.PositiveSmallIntegerField(default=0)

    xg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    xa = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    npg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    npxg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    xg_chain = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    xg_buildup = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    yellow_cards = models.PositiveSmallIntegerField(default=0)
    red_cards = models.PositiveSmallIntegerField(default=0)
    key_passes = models.PositiveSmallIntegerField(default=0)

    last_synced_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    raw_snapshot = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["player", "provider", "season_label", "competition_code", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "player",
                    "provider",
                    "season_label",
                    "competition_code",
                    "external_team_id",
                ],
                name="uniq_player_season_enrichment",
            ),
        ]
        indexes = [
            models.Index(
                fields=["player", "provider", "season_label"],
                name="pdat_player_season_idx",
            ),
            models.Index(
                fields=["club", "provider", "season_label"],
                name="pdat_player_club_idx",
            ),
            models.Index(
                fields=["provider", "external_player_id"],
                name="pdat_player_ext_idx",
            ),
        ]

    # Return a readable player season enrichment label
    def __str__(self) -> str:
        competition = f" {self.competition_code}" if self.competition_code else ""
        return f"{self.player} | {self.provider} | {self.season_label}{competition}"


# Snapshot marker for published player enrichment data scopes
class PlayerEnrichmentSnapshot(models.Model):
    scope_key = models.CharField(max_length=128)
    is_active = models.BooleanField(default=False)
    published_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['scope_key', 'is_active']),
        ]

    # Return a readable player enrichment snapshot label
    def __str__(self):
        active = 'active' if self.is_active else 'inactive'
        return f'PlayerEnrichmentSnapshot({self.scope_key}, {active}, {self.published_at})'