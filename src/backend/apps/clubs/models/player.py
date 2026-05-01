import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.players.models import ExternalProvider, Player
from common.constants import Position, PreferredFoot


class ClubPlayer(models.Model):
    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='club_players'
    )

    player = models.ForeignKey(
        'players.Player',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='club_memberships'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='club_players'
    )

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    display_name = models.CharField(
        max_length=50,
        blank=True,
        help_text="Nickname or preferred name"
    )

    squad_number = models.PositiveSmallIntegerField(null=True, blank=True)
    primary_position = models.CharField(max_length=4, choices=Position.choices, blank=True)
    secondary_position = models.CharField(max_length=4, choices=Position.choices, blank=True)
    preferred_foot = models.CharField(max_length=1, choices=PreferredFoot.choices, blank=True)

    date_of_birth = models.DateField(null=True, blank=True)
    height_cm = models.PositiveSmallIntegerField(null=True, blank=True)

    photo = models.ImageField(
        upload_to='players/photos/',
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Active in current squad"
    )
    is_public = models.BooleanField(
        default=False,
        help_text="If true, this player profile can be used by other public clubs"
    )

    claim_token = models.CharField(
        max_length=64,
        blank=True,
        unique=True,
        null=True,
        help_text="Token for claiming this profile"
    )
    claimed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_club_players'
    )

    class Meta:
        app_label = 'clubs'
        ordering = ['squad_number', 'last_name', 'first_name', 'id']
        indexes = [
            models.Index(fields=['club', 'is_active']),
            models.Index(fields=['user']),
            models.Index(fields=['claim_token']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['club', 'squad_number'],
                name='unique_squad_number_per_club'
            )
        ]

    def __str__(self):
        if self.player_id:
            name = self.player.display_name or self.player.full_name
        else:
            name = self.display_name or f"{self.first_name} {self.last_name}".strip()
        return f"{name} ({self.club.name})"

    @property
    def is_claimed(self):
        return self.user is not None

    @property
    def full_name(self):
        if self.player_id:
            return self.player.full_name
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_linked_to_player(self):
        return self.player_id is not None

    def can_link_to_player(self, player, *, allow_relink=False):
        if player is None:
            raise ValidationError({'player': 'A canonical Player is required.'})

        if not isinstance(player, Player):
            raise ValidationError({'player': 'Expected a canonical Player instance.'})

        if self.player_id and self.player_id != player.id and not allow_relink:
            raise ValidationError({
                'player': (
                    'This club player is already linked to a different canonical Player. '
                    'Use an explicit relink flow.'
                )
            })

        return True

    def link_to_player(self, player, *, commit=True):
        self.can_link_to_player(player)

        if self.player_id == player.id:
            return self

        self.player = player

        if commit:
            self.save(update_fields=['player', 'updated_at'])

        return self

    def unlink_player(self, *, commit=True):
        if not self.player_id:
            return self

        self.player = None

        if commit:
            self.save(update_fields=['player', 'updated_at'])

        return self

    def relink_player(self, player, *, commit=True):
        self.can_link_to_player(player, allow_relink=True)

        if self.player_id == player.id:
            return self

        self.player = player

        if commit:
            self.save(update_fields=['player', 'updated_at'])

        return self

    def get_display_player_identity(self):
        if self.player_id:
            return {
                'is_linked_to_player': True,
                'player_id': self.player_id,
                'first_name': self.player.first_name,
                'last_name': self.player.last_name,
                'full_name': self.player.full_name,
                'display_name': self.player.display_name or '',
                'primary_position': self.player.primary_position or '',
                'secondary_positions': list(self.player.secondary_positions or []),
                'preferred_foot': self.player.preferred_foot or '',
                'date_of_birth': self.player.date_of_birth,
                'height_cm': self.player.height_cm,
                'nationality': self.player.nationality or '',
                'photo': self.player.photo,
            }

        return {
            'is_linked_to_player': False,
            'player_id': None,
            'first_name': self.first_name or '',
            'last_name': self.last_name or '',
            'full_name': f'{self.first_name} {self.last_name}'.strip(),
            'display_name': self.display_name or '',
            'primary_position': self.primary_position or '',
            'secondary_positions': [self.secondary_position] if self.secondary_position else [],
            'preferred_foot': self.preferred_foot or '',
            'date_of_birth': self.date_of_birth,
            'height_cm': self.height_cm,
            'nationality': '',
            'photo': self.photo,
        }

    def generate_claim_token(self):
        self.claim_token = secrets.token_urlsafe(32)
        self.save(update_fields=['claim_token'])
        return self.claim_token

    def claim(self, user):
        from .membership import ClubMembership

        self.user = user
        self.claimed_at = timezone.now()
        self.claim_token = None
        self.save(update_fields=['user', 'claimed_at', 'claim_token'])

        ClubMembership.objects.get_or_create(
            user=user,
            club=self.club,
            defaults={'role': ClubMembership.Role.PLAYER}
        )


class ClubExternalIdentity(models.Model):
    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name="external_identities",
    )
    provider = models.CharField(
        max_length=50,
        choices=ExternalProvider.choices,
    )
    external_id = models.CharField(max_length=100)
    provider_display_name = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=100, blank=True)
    competition_context = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'clubs'
        ordering = ["provider", "external_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_id"],
                name="uniq_club_ext_identity_provider_external_id",
            ),
        ]
        indexes = [
            models.Index(fields=["club", "provider"]),
            models.Index(fields=["provider", "external_id"]),
        ]

    def __str__(self):
        return f"{self.provider}:{self.external_id} -> {self.club}"
