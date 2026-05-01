from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from common.constants import *
from .formations import get_available_formations, get_formation_template


class Teamsheet(models.Model):
    club = models.ForeignKey(
        'clubs.Club',
        on_delete=models.CASCADE,
        related_name='teamsheets',
        help_text='The club this teamsheet belongs to',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_teamsheets',
        help_text='User who created this teamsheet',
    )
    title = models.CharField(
        max_length=100,
        help_text="e.g. 'vs Arsenal - Home' or 'Default 4-3-3'",
    )
    formation = models.CharField(
        max_length=10,
        choices=get_available_formations(),
        default='442',
        help_text='Base formation for this teamsheet',
    )
    notes = models.TextField(
        blank=True,
        help_text='Tactical notes, pre-match thoughts, etc.',
    )
    match_date = models.DateField(
        null=True,
        blank=True,
        help_text='If this teamsheet is for a specific match',
    )
    opponent = models.CharField(
        max_length=100,
        blank=True,
        help_text='Name of the opposing team',
    )
    is_template = models.BooleanField(
        default=False,
        help_text='If True, this is a reusable formation template',
    )

    is_trashed = models.BooleanField(default=False)
    trashed_at = models.DateTimeField(null=True, blank=True)
    trash_expires_at = models.DateTimeField(null=True, blank=True)
    trashed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trashed_teamsheets',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['club', '-updated_at']),
            models.Index(fields=['club', 'is_template']),
            models.Index(fields=['created_by']),
            models.Index(fields=['club', 'is_trashed']),
            models.Index(fields=['created_by', 'is_trashed']),
            models.Index(fields=['is_trashed', 'trash_expires_at']),
        ]

    def __str__(self):
        return f'{self.title} - {self.get_formation_display()}'

    def clean(self):
        super().clean()

        if self.match_date and not self.opponent:
            raise ValidationError({
                'opponent': 'Opponent is required when match date is set.',
            })

    @property
    def starter_count(self) -> int:
        return self.players.filter(is_substitute=False).count()

    @property
    def substitute_count(self) -> int:
        return self.players.filter(is_substitute=True).count()

    @property
    def is_complete(self) -> bool:
        return self.starter_count == 11

    def get_formation_defaults(self) -> list[dict]:
        return get_formation_template(self.formation)

    def initialize_from_template(self):
        template = self.get_formation_defaults()
        for slot_data in template:
            TeamsheetPlayer.objects.create(
                teamsheet=self,
                slot_number=slot_data['slot'],
                position_label=slot_data['position'],
                position_x=slot_data['x'],
                position_y=slot_data['y'],
                is_substitute=False,
            )

    def can_be_trashed_by(self, user) -> bool:
        return bool(
            user
            and user.is_authenticated
            and self.created_by_id is not None
            and self.created_by_id == user.id
        )

    def can_be_restored_by(self, user) -> bool:
        return self.can_be_trashed_by(user)

    def can_be_permanently_deleted_by(self, user) -> bool:
        return self.can_be_trashed_by(user)

    def is_trash_expired(self) -> bool:
        return bool(
            self.is_trashed
            and self.trash_expires_at is not None
            and self.trash_expires_at <= timezone.now()
        )

    def _get_trash_limit(self) -> int:
        return int(getattr(settings, 'TEAMSHEET_TRASH_LIMIT_PER_USER', 50))

    def _validate_trash_limit(self):
        limit = self._get_trash_limit()
        active_trashed_count = Teamsheet.objects.filter(
            created_by_id=self.created_by_id,
            is_trashed=True,
        ).exclude(pk=self.pk).count()

        if active_trashed_count >= limit:
            raise ValidationError(
                f'You have reached the teamsheet trash limit of {limit} items.'
            )

    def move_to_trash(self, user, commit=True):
        if not self.can_be_trashed_by(user):
            raise ValidationError('Only the teamsheet creator can move this teamsheet to trash.')

        if self.is_trashed:
            return self

        self._validate_trash_limit()

        now = timezone.now()
        retention_days = int(getattr(settings, 'TRASH_RETENTION_DAYS', 7))

        self.is_trashed = True
        self.trashed_at = now
        self.trash_expires_at = now + timedelta(days=retention_days)
        self.trashed_by = user

        if commit and self.pk:
            self.save(
                update_fields=[
                    'is_trashed',
                    'trashed_at',
                    'trash_expires_at',
                    'trashed_by',
                    'updated_at',
                ]
            )

        return self

    def restore_from_trash(self, user=None, commit=True):
        if user is not None and not self.can_be_restored_by(user):
            raise ValidationError('Only the teamsheet creator can restore this teamsheet.')

        self.is_trashed = False
        self.trashed_at = None
        self.trash_expires_at = None
        self.trashed_by = None

        if commit and self.pk:
            self.save(
                update_fields=[
                    'is_trashed',
                    'trashed_at',
                    'trash_expires_at',
                    'trashed_by',
                    'updated_at',
                ]
            )

        return self


class TeamsheetPlayer(models.Model):
    teamsheet = models.ForeignKey(
        Teamsheet,
        on_delete=models.CASCADE,
        related_name='players',
    )
    club_player = models.ForeignKey(
        'clubs.ClubPlayer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teamsheet_appearances',
        help_text='Link to a club player row in the club roster',
    )
    custom_name = models.CharField(
        max_length=50,
        blank=True,
        help_text='Custom player name when no club player is linked',
    )
    custom_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(99)],
        help_text='Custom squad number overriding the linked club player number',
    )
    position_label = models.CharField(
        max_length=3,
        choices=Position.choices,
        help_text='Tactical position label',
    )
    position_x = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Horizontal position (0=left, 100=right)',
    )
    position_y = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Vertical position (0=own goal, 100=opponent goal)',
    )
    slot_number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        help_text='Order in the lineup (1-11 for starters, 12+ for substitutes)',
    )
    is_substitute = models.BooleanField(
        default=False,
        help_text='If True, the player is on the bench',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['is_substitute', 'slot_number']
        indexes = [
            models.Index(fields=['teamsheet', 'is_substitute']),
            models.Index(fields=['club_player']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['teamsheet', 'slot_number'],
                name='unique_slot_per_teamsheet',
            ),
            models.UniqueConstraint(
                fields=['teamsheet', 'club_player'],
                name='unique_club_player_per_teamsheet',
            ),
        ]

    def __str__(self):
        name = self.display_name or f'Slot {self.slot_number}'
        return f'{name} ({self.position_label})'

    def clean(self):
        super().clean()

        if not self.club_player and not self.custom_name.strip():
            raise ValidationError(
                "Either club_player or custom_name must be provided."
            )

        if self.club_player and self.club_player.club_id != self.teamsheet.club_id:
            raise ValidationError({
                'club_player': 'Player must belong to the same club as the teamsheet.',
            })

    @property
    def display_name(self) -> str:
        if self.custom_name.strip():
            return self.custom_name.strip()

        if self.club_player:
            return (self.club_player.display_name or self.club_player.full_name).strip()

        return ''

    @property
    def display_number(self) -> int | None:
        if self.custom_number is not None:
            return self.custom_number

        if self.club_player:
            return self.club_player.squad_number

        return None

    @property
    def display_photo_url(self) -> str | None:
        if not self.club_player:
            return None

        photo = getattr(self.club_player, 'photo', None)
        if not photo:
            return None

        return getattr(photo, 'url', str(photo))

    @property
    def is_linked(self) -> bool:
        return self.club_player_id is not None