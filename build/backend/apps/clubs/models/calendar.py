from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Season(models.Model):
    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='seasons'
    )

    name = models.CharField(
        max_length=20,
        help_text="e.g., '2024/2025'"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    matches_played = models.PositiveSmallIntegerField(default=0)
    wins = models.PositiveSmallIntegerField(default=0)
    draws = models.PositiveSmallIntegerField(default=0)
    losses = models.PositiveSmallIntegerField(default=0)
    goals_for = models.PositiveSmallIntegerField(default=0)
    goals_against = models.PositiveSmallIntegerField(default=0)

    class Meta:
        app_label = 'clubs'
        ordering = ['-start_date']
        unique_together = ['club', 'name']
        indexes = [
            models.Index(fields=['club', 'is_current']),
        ]

    def __str__(self):
        return f"{self.club.name} - {self.name}"

    @property
    def goal_difference(self):
        return self.goals_for - self.goals_against

    @property
    def points(self):
        return (self.wins * 3) + self.draws

    def save(self, *args, **kwargs):
        if self.is_current:
            Season.objects.filter(
                club=self.club,
                is_current=True
            ).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class PlayerSeasonStats(models.Model):
    player = models.ForeignKey(
        'ClubPlayer',
        on_delete=models.CASCADE,
        related_name='season_stats'
    )
    season = models.ForeignKey(
        'Season',
        on_delete=models.CASCADE,
        related_name='player_stats'
    )

    appearances = models.PositiveSmallIntegerField(default=0)
    starts = models.PositiveSmallIntegerField(default=0)
    minutes_played = models.PositiveIntegerField(default=0)

    goals = models.PositiveSmallIntegerField(default=0)
    assists = models.PositiveSmallIntegerField(default=0)
    shots = models.PositiveSmallIntegerField(default=0)
    shots_on_target = models.PositiveSmallIntegerField(default=0)

    tackles = models.PositiveSmallIntegerField(default=0)
    interceptions = models.PositiveSmallIntegerField(default=0)
    clearances = models.PositiveSmallIntegerField(default=0)

    yellow_cards = models.PositiveSmallIntegerField(default=0)
    red_cards = models.PositiveSmallIntegerField(default=0)

    passes_attempted = models.PositiveIntegerField(default=0)
    passes_completed = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = 'clubs'
        unique_together = ['player', 'season']
        ordering = ['-season__start_date']

    def __str__(self):
        return f"{self.player} - {self.season.name}"

    @property
    def pass_completion_rate(self):
        if self.passes_attempted == 0:
            return 0.0
        return round(self.passes_completed / self.passes_attempted * 100, 1)

    @property
    def minutes_per_goal(self):
        if self.goals == 0:
            return None
        return round(self.minutes_played / self.goals, 1)


class ClubEvent(models.Model):
    class EventType(models.TextChoices):
        TRAINING = 'training', 'Training'
        MEETING = 'meeting', 'Meeting'
        SOCIAL = 'social', 'Social'
        ANALYSIS = 'analysis', 'Analysis'
        OTHER = 'other', 'Other'

    class SourceType(models.TextChoices):
        MANUAL = 'manual', 'Manual'
        SYSTEM = 'system', 'System'
        PROVIDER = 'provider', 'Provider'

    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='events'
    )
    title = models.CharField(max_length=200)
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        default=EventType.OTHER
    )
    description = models.TextField(blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=False)
    location = models.CharField(max_length=200, blank=True)
    is_mandatory = models.BooleanField(default=False)
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.MANUAL
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_club_events'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'clubs'
        ordering = ['start_datetime', 'id']
        indexes = [
            models.Index(fields=['club', 'start_datetime']),
            models.Index(fields=['club', 'source_type']),
            models.Index(fields=['event_type']),
        ]

    def __str__(self):
        return f'{self.title} - {self.club.name}'

    @classmethod
    def can_be_manually_created_for_club(cls, club):
        return bool(club and club.allows_manual_events())

    def is_system_managed_item(self):
        return self.source_type in {
            self.SourceType.SYSTEM,
            self.SourceType.PROVIDER,
        }

    def is_user_editable(self):
        return (
            self.source_type == self.SourceType.MANUAL and
            self.club.allows_manual_events()
        )

    def is_future_item(self):
        return self.start_datetime >= timezone.now()

    def get_calendar_label(self):
        return self.title

    def clean(self):
        super().clean()

        errors = {}

        if self.title and not self.title.strip():
            errors['title'] = 'title cannot be blank or whitespace only.'

        if self.end_datetime and self.end_datetime < self.start_datetime:
            errors['end_datetime'] = 'end_datetime must be after start_datetime.'

        if self.source_type == self.SourceType.MANUAL and not self.club.allows_manual_events():
            errors['source_type'] = (
                'Manual club events are only allowed for user-managed clubs.'
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean(validate_constraints=False)
        return super().save(*args, **kwargs)


class Fixture(models.Model):
    class Venue(models.TextChoices):
        HOME = 'home', 'Home'
        AWAY = 'away', 'Away'
        NEUTRAL = 'neutral', 'Neutral'

    class FixtureStatus(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        COMPLETED = 'completed', 'Completed'
        POSTPONED = 'postponed', 'Postponed'
        CANCELLED = 'cancelled', 'Cancelled'

    class SourceType(models.TextChoices):
        MANUAL = 'manual', 'Manual'
        SYSTEM = 'system', 'System'
        PROVIDER = 'provider', 'Provider'

    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='fixtures'
    )
    opponent_name = models.CharField(max_length=100)
    venue = models.CharField(
        max_length=10,
        choices=Venue.choices
    )
    competition = models.CharField(
        max_length=100,
        blank=True,
        help_text='League, cup, friendly, or other competition label.'
    )
    match_datetime = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    fixture_status = models.CharField(
        max_length=20,
        choices=FixtureStatus.choices,
        default=FixtureStatus.SCHEDULED
    )
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.MANUAL
    )
    external_fixture_id = models.CharField(
        max_length=100,
        blank=True,
        help_text='Provider or system fixture identifier for future sync paths.'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_club_fixtures'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'clubs'
        ordering = ['match_datetime', 'id']
        indexes = [
            models.Index(fields=['club', 'match_datetime']),
            models.Index(fields=['club', 'fixture_status']),
            models.Index(fields=['club', 'source_type']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['club', 'external_fixture_id'],
                name='unique_nonblank_external_fixture_id_per_club',
            ),
        ]

    def __str__(self):
        connector = 'vs'
        if self.venue == self.Venue.AWAY:
            connector = '@'
        return f'{self.club.name} {connector} {self.opponent_name} ({self.match_datetime:%Y-%m-%d %H:%M})'

    @classmethod
    def can_be_manually_created_for_club(cls, club):
        return bool(club and club.allows_manual_fixtures())

    def is_system_managed_item(self):
        return self.source_type in {
            self.SourceType.SYSTEM,
            self.SourceType.PROVIDER,
        }

    def is_user_editable(self):
        return (
            self.source_type == self.SourceType.MANUAL and
            self.club.allows_manual_fixtures()
        )

    def is_future_item(self):
        return self.match_datetime >= timezone.now()

    def get_calendar_label(self):
        if self.venue == self.Venue.HOME:
            return f'vs {self.opponent_name}'
        if self.venue == self.Venue.AWAY:
            return f'@ {self.opponent_name}'
        return f'vs {self.opponent_name}'

    def clean(self):
        super().clean()

        errors = {}

        if self.opponent_name and not self.opponent_name.strip():
            errors['opponent_name'] = 'opponent_name cannot be blank or whitespace only.'

        if self.source_type == self.SourceType.MANUAL and not self.club.allows_manual_fixtures():
            errors['source_type'] = (
                'Manual fixtures are only allowed for user-managed clubs.'
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean(validate_constraints=False)
        return super().save(*args, **kwargs)
