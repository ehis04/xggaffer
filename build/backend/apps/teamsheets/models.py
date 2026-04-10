from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from .formations import get_formation_template, FORMATION_TEMPLATES, get_available_formations
from common.constants import *

class Teamsheet(models.Model):
    club = models.ForeignKey(
        'clubs.Club',
        on_delete=models.CASCADE,
        related_name='teamsheets',
        help_text="The club this teamsheet belongs to"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_teamsheets',
        help_text="User who created this teamsheet"
    )
    title = models.CharField(
        max_length=100,
        help_text="e.g., 'vs Arsenal - Home' or 'Default 4-3-3'"
    )
    formation = models.CharField(
        max_length=10,
        choices=get_available_formations(),
        default='442',
        help_text="Base formation for this teamsheet"
    )
    notes = models.TextField(
        blank=True,
        help_text="Tactical notes, pre-match thoughts, etc."
    )
    match_date = models.DateField(
        null=True,
        blank=True,
        help_text="If this teamsheet is for a specific match"
    )
    opponent = models.CharField(
        max_length=100,
        blank=True,
        help_text="Name of the opposing team"
    )
    is_template = models.BooleanField(
        default=False,
        help_text="If True, this is a reusable formation template"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['club', '-updated_at']),
            models.Index(fields=['club', 'is_template']),
            models.Index(fields=['created_by']),
        ]
    
#    def __str__(self):
#        if self.opponent:
#            return f"{self.title} ({self.formation})"
#        return f"{self.title} - {self.get_formation_display()}"

    def __str__(self):
        return f"{self.title} - {self.get_formation_display()}"
    
    def clean(self):
        super().clean()
        
        if self.match_date and not self.opponent:
            raise ValidationError({
                'opponent': "Opponent is required when match date is set."
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

class TeamsheetPlayer(models.Model):
    teamsheet = models.ForeignKey(
        Teamsheet,
        on_delete=models.CASCADE,
        related_name='players'
    )
    club_player = models.ForeignKey(
        'clubs.ClubPlayer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teamsheet_appearances',
        help_text="Link to an actual player in the club roster"
    )
    custom_name = models.CharField(
        max_length=50,
        blank=True,
        help_text="Custom player name (used if no club_player linked)"
    )
    custom_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(99)],
        help_text="Custom squad number (overrides club player number if set)"
    )
    position_label = models.CharField(
        max_length=3,
        choices=Position.choices,
        help_text="Tactical position label (GK, CB, CM, etc.)"
    )
    position_x = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Horizontal position (0=left, 100=right)"
    )
    position_y = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Vertical position (0=own goal, 100=opponent goal)"
    )
    slot_number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Order in the lineup (1-11 for starters, 12+ for subs)"
    )
    is_substitute = models.BooleanField(
        default=False,
        help_text="If True, player is on the bench"
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
                name='unique_slot_per_teamsheet'
            ),
            models.UniqueConstraint(
                fields=['teamsheet', 'club_player'],
                condition=models.Q(club_player__isnull=False),
                name='unique_player_per_teamsheet'
            ),
        ]

    def __str__(self):
        name = self.display_name or f"Slot {self.slot_number}"
        return f"{name} ({self.position_label})"

    def clean(self):
        super().clean()

        if not self.club_player and not self.custom_name:
            raise ValidationError(
                "Either club_player or custom_name must be provided."
            )

        if self.club_player:
            if self.club_player.club_id != self.teamsheet.club_id:
                raise ValidationError({
                    'club_player': "Player must belong to the same club as the teamsheet."
                })

    @property
    def display_name(self) -> str:
        if self.custom_name:
            return self.custom_name

        if self.club_player:
            if self.club_player.display_name:
                return self.club_player.display_name
            return self.club_player.full_name

        return ""

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

        if self.club_player.player and self.club_player.player.photo:
            return self.club_player.player.photo.url

        if self.club_player.photo:
            return self.club_player.photo.url

        return None

    @property
    def is_linked(self) -> bool:
        return self.club_player is not None
        
    @property
    def display_number(self) -> int | None:
        if self.custom_number is not None:
            return self.custom_number
        if self.club_player:
            return self.club_player.squad_number
        return None


    @property
    def is_linked(self) -> bool:
        return self.club_player is not None