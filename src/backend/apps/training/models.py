from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class TrainingSession(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    class SessionType(models.TextChoices):
        TECHNICAL = 'technical', 'Technical'
        TACTICAL = 'tactical', 'Tactical'
        FITNESS = 'fitness', 'Fitness'
        SET_PIECES = 'set_pieces', 'Set pieces'
        RECOVERY = 'recovery', 'Recovery'
        MATCH_PREPARATION = 'match_preparation', 'Match preparation'
        GOALKEEPER = 'goalkeeper', 'Goalkeeper'
        OTHER = 'other', 'Other'

    class Intensity(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'

    club = models.ForeignKey(
        'clubs.Club',
        on_delete=models.CASCADE,
        related_name='training_sessions',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_training_sessions',
    )
    calendar_event = models.OneToOneField(
        'clubs.ClubEvent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='training_session',
    )
    linked_teamsheet = models.ForeignKey(
        'teamsheets.Teamsheet',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='training_sessions',
    )

    title = models.CharField(max_length=160)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    session_type = models.CharField(max_length=24, choices=SessionType.choices, default=SessionType.TACTICAL)
    intensity = models.CharField(max_length=12, choices=Intensity.choices, default=Intensity.MEDIUM)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    is_mandatory = models.BooleanField(default=True)

    main_objective = models.CharField(max_length=240, blank=True)
    secondary_objectives = models.TextField(blank=True)
    match_context = models.TextField(blank=True)
    linked_opponent = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)

    what_went_well = models.TextField(blank=True)
    needs_improvement = models.TextField(blank=True)
    next_focus = models.TextField(blank=True)
    squad_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_datetime', 'id']
        indexes = [
            models.Index(fields=['club', 'status', 'start_datetime']),
            models.Index(fields=['club', 'session_type']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return f'{self.title} - {self.club.name}'

    def clean(self):
        super().clean()
        errors = {}
        if self.title and not self.title.strip():
            errors['title'] = 'Title cannot be blank.'
        if self.end_datetime and self.end_datetime <= self.start_datetime:
            errors['end_datetime'] = 'End time must be after start time.'
        if self.linked_teamsheet_id and self.club_id and self.linked_teamsheet.club_id != self.club_id:
            errors['linked_teamsheet'] = 'Linked teamsheet must belong to the same club.'
        if errors:
            raise ValidationError(errors)

    @property
    def assigned_player_count(self):
        return self.players.count()

    @property
    def attended_count(self):
        return self.players.filter(attendance_status=TrainingSessionPlayer.AttendanceStatus.ATTENDED).count()


class TrainingBlock(models.Model):
    class BlockType(models.TextChoices):
        WARM_UP = 'warm_up', 'Warm-up'
        TECHNICAL = 'technical', 'Technical drill'
        TACTICAL = 'tactical', 'Tactical drill'
        CONDITIONED_GAME = 'conditioned_game', 'Conditioned game'
        SET_PIECES = 'set_pieces', 'Set pieces'
        FITNESS = 'fitness', 'Fitness'
        RECOVERY = 'recovery', 'Recovery'
        COOL_DOWN = 'cool_down', 'Cool-down'
        REVIEW = 'review', 'Review'
        OTHER = 'other', 'Other'

    session = models.ForeignKey(
        TrainingSession,
        on_delete=models.CASCADE,
        related_name='blocks',
    )
    order = models.PositiveSmallIntegerField(default=1)
    title = models.CharField(max_length=160)
    block_type = models.CharField(max_length=24, choices=BlockType.choices, default=BlockType.OTHER)
    duration_minutes = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(240)],
    )
    description = models.TextField(blank=True)
    coaching_points = models.TextField(blank=True)
    equipment = models.TextField(blank=True)
    player_group = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        constraints = [
            models.UniqueConstraint(fields=['session', 'order'], name='unique_training_block_order'),
        ]

    def __str__(self):
        return f'{self.order}. {self.title}'


class TrainingSessionPlayer(models.Model):
    class AttendanceStatus(models.TextChoices):
        INVITED = 'invited', 'Invited'
        ATTENDED = 'attended', 'Attended'
        ABSENT = 'absent', 'Absent'
        LATE = 'late', 'Late'
        EXCUSED = 'excused', 'Excused'
        INJURED = 'injured', 'Injured'
        NOT_SELECTED = 'not_selected', 'Not selected'

    session = models.ForeignKey(
        TrainingSession,
        on_delete=models.CASCADE,
        related_name='players',
    )
    club_player = models.ForeignKey(
        'clubs.ClubPlayer',
        on_delete=models.CASCADE,
        related_name='training_assignments',
    )
    attendance_status = models.CharField(
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.INVITED,
    )
    rpe_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    coach_notes = models.TextField(blank=True)
    injury_note = models.TextField(blank=True)
    performance_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['club_player__squad_number', 'club_player__last_name', 'id']
        constraints = [
            models.UniqueConstraint(fields=['session', 'club_player'], name='unique_training_session_player'),
        ]

    def clean(self):
        super().clean()
        if self.session_id and self.club_player_id and self.club_player.club_id != self.session.club_id:
            raise ValidationError({'club_player': 'Player must belong to the session club.'})

    def __str__(self):
        return f'{self.club_player} - {self.session}'
