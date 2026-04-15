from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


COORDINATE_MIN = 0
COORDINATE_MAX = 100
DEFAULT_HOME_COLOUR = '#1E40AF'
DEFAULT_AWAY_COLOUR = '#DC2626'
DEFAULT_FRAME_DURATION_MS = 1500

COORDINATE_VALIDATORS = [
    MinValueValidator(COORDINATE_MIN),
    MaxValueValidator(COORDINATE_MAX),
]

SIZE_VALIDATORS = [
    MinValueValidator(COORDINATE_MIN),
    MaxValueValidator(COORDINATE_MAX),
]


class TacticsBoard(models.Model):
    class BoardType(models.TextChoices):
        STATIC = 'static', 'Static'
        ANIMATED = 'animated', 'Animated'

    class PitchOrientation(models.TextChoices):
        VERTICAL = 'vertical', 'Vertical'
        HORIZONTAL = 'horizontal', 'Horizontal'

    club = models.ForeignKey(
        'clubs.Club',
        on_delete=models.CASCADE,
        related_name='tactics_boards',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tactics_boards',
    )
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    board_type = models.CharField(
        max_length=10,
        choices=BoardType.choices,
        default=BoardType.STATIC,
    )
    pitch_orientation = models.CharField(
        max_length=10,
        choices=PitchOrientation.choices,
        default=PitchOrientation.VERTICAL,
    )
    linked_teamsheet = models.ForeignKey(
        'teamsheets.Teamsheet',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tactics_boards',
    )
    home_formation = models.CharField(max_length=10, blank=True)
    away_formation = models.CharField(max_length=10, blank=True)
    home_colour = models.CharField(max_length=7, default=DEFAULT_HOME_COLOUR)
    away_colour = models.CharField(max_length=7, default=DEFAULT_AWAY_COLOUR)
    is_template = models.BooleanField(default=False)

    is_trashed = models.BooleanField(default=False)
    trashed_at = models.DateTimeField(null=True, blank=True)
    trash_expires_at = models.DateTimeField(null=True, blank=True)
    trashed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trashed_tactics_boards',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['club', '-updated_at']),
            models.Index(fields=['created_by']),
            models.Index(fields=['linked_teamsheet']),
            models.Index(fields=['club', 'is_trashed']),
            models.Index(fields=['created_by', 'is_trashed']),
            models.Index(fields=['is_trashed', 'trash_expires_at']),
        ]

    def __str__(self) -> str:
        return f'{self.title} ({self.club.name})'

    def clean(self):
        super().clean()

        if (
            self.linked_teamsheet_id
            and self.club_id
            and self.linked_teamsheet.club_id != self.club_id
        ):
            raise ValidationError({
                'linked_teamsheet': 'Linked teamsheet must belong to the same club.',
            })

    def update_board_type(self, save: bool = True) -> str:
        frame_count = self.frames.count()
        next_type = (
            self.BoardType.ANIMATED
            if frame_count > 1
            else self.BoardType.STATIC
        )

        if self.board_type != next_type:
            self.board_type = next_type
            if save and self.pk:
                self.save(update_fields=['board_type', 'updated_at'])

        return self.board_type

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
        return int(getattr(settings, 'TACTICS_BOARD_TRASH_LIMIT_PER_USER', 50))

    def _validate_trash_limit(self):
        limit = self._get_trash_limit()
        active_trashed_count = TacticsBoard.objects.filter(
            created_by_id=self.created_by_id,
            is_trashed=True,
        ).exclude(pk=self.pk).count()

        if active_trashed_count >= limit:
            raise ValidationError(
                f'You have reached the tactics board trash limit of {limit} items.'
            )

    def move_to_trash(self, user, commit=True):
        if not self.can_be_trashed_by(user):
            raise ValidationError('Only the tactics board creator can move this board to trash.')

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
            raise ValidationError('Only the tactics board creator can restore this board.')

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


class TacticsBoardFrame(models.Model):
    board = models.ForeignKey(
        TacticsBoard,
        on_delete=models.CASCADE,
        related_name='frames',
    )
    frame_index = models.PositiveSmallIntegerField()
    label = models.CharField(max_length=60, blank=True)
    duration_ms = models.PositiveIntegerField(default=DEFAULT_FRAME_DURATION_MS)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['frame_index', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['board', 'frame_index'],
                name='unique_tactics_frame_index_per_board',
            ),
        ]
        indexes = [
            models.Index(fields=['board', 'frame_index']),
        ]

    def __str__(self) -> str:
        return f'{self.board.title} - Frame {self.frame_index}'

    def _validate_not_last_frame(self) -> None:
        if not self.board_id:
            return

        remaining_frame_count = self.board.frames.exclude(pk=self.pk).count()
        if remaining_frame_count == 0:
            raise ValidationError('A tactics board must always have at least one frame.')

    def delete(self, *args, **kwargs):
        self._validate_not_last_frame()
        return super().delete(*args, **kwargs)


class TacticsBoardItem(models.Model):
    class ItemType(models.TextChoices):
        PLAYER = 'player', 'Player'
        BALL = 'ball', 'Ball'
        ARROW = 'arrow', 'Arrow'
        LINE = 'line', 'Line'
        ZONE = 'zone', 'Zone'
        TEXT = 'text', 'Text'

    class TeamSide(models.TextChoices):
        HOME = 'home', 'Home'
        AWAY = 'away', 'Away'
        NEUTRAL = 'neutral', 'Neutral'

    frame = models.ForeignKey(
        TacticsBoardFrame,
        on_delete=models.CASCADE,
        related_name='items',
    )
    item_type = models.CharField(max_length=10, choices=ItemType.choices)
    team_side = models.CharField(max_length=10, choices=TeamSide.choices)
    stable_id = models.UUIDField(default=uuid4, editable=False, db_index=True)
    linked_player = models.ForeignKey(
        'clubs.ClubPlayer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tactics_items',
    )
    label = models.CharField(max_length=40, blank=True)
    shirt_number = models.PositiveSmallIntegerField(null=True, blank=True)
    position_label = models.CharField(max_length=5, blank=True)
    x = models.FloatField(validators=COORDINATE_VALIDATORS)
    y = models.FloatField(validators=COORDINATE_VALIDATORS)
    end_x = models.FloatField(
        null=True,
        blank=True,
        validators=COORDINATE_VALIDATORS,
    )
    end_y = models.FloatField(
        null=True,
        blank=True,
        validators=COORDINATE_VALIDATORS,
    )
    width = models.FloatField(
        null=True,
        blank=True,
        validators=SIZE_VALIDATORS,
    )
    height = models.FloatField(
        null=True,
        blank=True,
        validators=SIZE_VALIDATORS,
    )
    rotation = models.FloatField(default=0)
    z_index = models.PositiveSmallIntegerField(default=0)
    style = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['z_index', 'id']
        indexes = [
            models.Index(fields=['frame', 'item_type']),
            models.Index(fields=['frame', 'team_side']),
            models.Index(fields=['stable_id']),
        ]

    def __str__(self) -> str:
        return f'{self.item_type} on frame {self.frame_id}'

    def clean(self):
        super().clean()

        if (
            self.linked_player_id
            and self.frame_id
            and self.linked_player.club_id != self.frame.board.club_id
        ):
            raise ValidationError({
                'linked_player': 'Linked player must belong to the same club as the tactics board.',
            })