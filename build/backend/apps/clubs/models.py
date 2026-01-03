from django.db import models
from django.conf import settings


class Club(models.Model):
    # Visibility options 
    class Visibility(models.TextChoices):
        PRIVATE = 'private', 'Private'
        PUBLIC = 'public', 'Public'
    
    # Identity
    name = models.CharField(max_length=100)
    description = models.TextField(blank=False)
    badge = models.ImageField(
        upload_to='../media/clubs/badges/', 
        blank=True, 
        null=True
    )
    
    # Ownership + Privacy 
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  
        related_name='created_clubs'
    )
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.PRIVATE
    )
    
    # Location
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(
        max_length=2,  
        blank=True,
        help_text="ISO 3166-1 alpha-2 code"
    )
    stadium = models.CharField(max_length=100, blank=True)
    
    # Competition  
    division = models.CharField(
        max_length=100, 
        blank=True,
        help_text="League or division name"
    )
    
    # Achievements  
    achievements = models.TextField(
        blank=True,
        help_text="Trophies, notable accomplishments"
    )
    
    # Metadata 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['creator']),
            models.Index(fields=['visibility']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.description:
            self.description = f"{self.creator.email}'s club"
        super().save(*args, **kwargs)
    
    # Convenience Properties 
    @property
    def is_private(self):
        return self.visibility == self.Visibility.PRIVATE
    
    @property
    def member_count(self):
        return self.memberships.filter(is_active=True).count()
    
    @property
    def player_count(self):
        return self.player_profiles.count()

class ClubMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'          
        ADMIN = 'admin', 'Admin'          
        COACH = 'coach', 'Coach'         
        PLAYER = 'player', 'Player'       
        VIEWER = 'viewer', 'Viewer'        
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='club_memberships'
    )
    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.VIEWER
    )
    
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_club_invites'
    )
    
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'club']  
        ordering = ['club', 'role', 'joined_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['club', 'role']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.club.name} ({self.role})"
    
    def can_edit_club(self):
        return self.role in [self.Role.OWNER, self.Role.ADMIN]
    
    def can_manage_members(self):
        return self.role in [self.Role.OWNER, self.Role.ADMIN]
    
    def can_create_content(self):
        return self.role in [self.Role.OWNER, self.Role.ADMIN, self.Role.COACH]
    
    def can_view_all_players(self):
        return self.role != self.Role.PLAYER  


class ClubPlayer(models.Model):
    class Position(models.TextChoices):
        GOALKEEPER = 'GK', 'Goalkeeper'
        DEFENDER = 'DEF', 'Defender'
        MIDFIELDER = 'MID', 'Midfielder'
        FORWARD = 'FWD', 'Forward'
    
    # === Club Relationship ===
    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='player_profiles'
    )
    
    # === User Link (Optional - for claimable profiles) ===
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,  # Keep profile if user deleted
        null=True,
        blank=True,
        related_name='player_profiles'
    )
    
    # === Player Info (stored here, not on User) ===
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    display_name = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Nickname or preferred name"
    )
    
    # === Football-Specific ===
    squad_number = models.PositiveSmallIntegerField(null=True, blank=True)
    position = models.CharField(
        max_length=3,
        choices=Position.choices,
        blank=True
    )
    secondary_position = models.CharField(
        max_length=3,
        choices=Position.choices,
        blank=True
    )
    preferred_foot = models.CharField(
        max_length=5,
        choices=[('left', 'Left'), ('right', 'Right'), ('both', 'Both')],
        blank=True
    )
    
    # === Physical Attributes ===
    date_of_birth = models.DateField(null=True, blank=True)
    height_cm = models.PositiveSmallIntegerField(null=True, blank=True)
    
    # === Profile Image ===
    photo = models.ImageField(
        upload_to='players/photos/',
        blank=True,
        null=True
    )
    
    # === Status ===
    is_active = models.BooleanField(
        default=True,
        help_text="Active in current squad"
    )
    is_public = models.BooleanField(
        default=False,
        help_text="If true, this player profile can be used by other public clubs"
    )
       
    # === Claim Tracking ===
    claim_token = models.CharField(
        max_length=64,
        blank=True,
        unique=True,
        null=True,
        help_text="Token for claiming this profile"
    )
    claimed_at = models.DateTimeField(null=True, blank=True)
    
    # === Metadata ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_player_profiles'
    )

    class Meta:
        ordering = ['squad_number', 'last_name']
        indexes = [
            models.Index(fields=['club', 'is_active']),
            models.Index(fields=['user']),
            models.Index(fields=['claim_token']),
        ]
        constraints = [
            # Squad number unique within club
            models.UniqueConstraint(
                fields=['club', 'squad_number'],
                condition=models.Q(squad_number__isnull=False),
                name='unique_squad_number_per_club'
            )
        ]
    
    def __str__(self):
        name = self.display_name or f"{self.first_name} {self.last_name}"
        return f"{name} ({self.club.name})"
    
    @property
    def is_claimed(self):
        return self.user is not None
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def generate_claim_token(self):
        """Generate a unique token for claiming this profile."""
        import secrets
        self.claim_token = secrets.token_urlsafe(32)
        self.save(update_fields=['claim_token'])
        return self.claim_token
    
    def claim(self, user):
        """
        Link this profile to a user account.
        Called when a user accepts an invitation.
        """
        from django.utils import timezone
        
        self.user = user
        self.claimed_at = timezone.now()
        self.claim_token = None  # Invalidate token
        self.save(update_fields=['user', 'claimed_at', 'claim_token'])
        
        # Also create club membership if doesn't exist
        ClubMembership.objects.get_or_create(
            user=user,
            club=self.club,
            defaults={'role': ClubMembership.Role.PLAYER}
        )


# clubs/models/season.py

from django.db import models


class Season(models.Model):
    """
    Represents a football season for a club.
    Stats and records are tied to seasons.
    """
    
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
    
    # === Aggregate Stats (denormalized for quick access) ===
    matches_played = models.PositiveSmallIntegerField(default=0)
    wins = models.PositiveSmallIntegerField(default=0)
    draws = models.PositiveSmallIntegerField(default=0)
    losses = models.PositiveSmallIntegerField(default=0)
    goals_for = models.PositiveSmallIntegerField(default=0)
    goals_against = models.PositiveSmallIntegerField(default=0)
    
    class Meta:
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
        # Ensure only one current season per club
        if self.is_current:
            Season.objects.filter(
                club=self.club, 
                is_current=True
            ).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class PlayerSeasonStats(models.Model):
    """
    Player statistics for a specific season.
    This is where ML features get pulled from.
    """
    
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
    
    # === Appearance Stats ===
    appearances = models.PositiveSmallIntegerField(default=0)
    starts = models.PositiveSmallIntegerField(default=0)
    minutes_played = models.PositiveIntegerField(default=0)
    
    # === Attacking Stats ===
    goals = models.PositiveSmallIntegerField(default=0)
    assists = models.PositiveSmallIntegerField(default=0)
    shots = models.PositiveSmallIntegerField(default=0)
    shots_on_target = models.PositiveSmallIntegerField(default=0)
    
    # === Defensive Stats ===
    tackles = models.PositiveSmallIntegerField(default=0)
    interceptions = models.PositiveSmallIntegerField(default=0)
    clearances = models.PositiveSmallIntegerField(default=0)
    
    # === Discipline ===
    yellow_cards = models.PositiveSmallIntegerField(default=0)
    red_cards = models.PositiveSmallIntegerField(default=0)
    
    # === Passing (for ML features) ===
    passes_attempted = models.PositiveIntegerField(default=0)
    passes_completed = models.PositiveIntegerField(default=0)
    
    class Meta:
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


"""
=== COMMENTED OUT: DUPLICATE/FUTURE MODELS ===
The following models are commented out to prevent Django registration warnings.
They are kept for reference but will be implemented in separate apps.

# clubs/models/fixture.py

from django.db import models


class Fixture(models.Model):
    \"\"\"
    A match involving the club.
    Can be historical (with results) or upcoming.
    \"\"\"
    
    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        POSTPONED = 'postponed', 'Postponed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    class Venue(models.TextChoices):
        HOME = 'home', 'Home'
        AWAY = 'away', 'Away'
        NEUTRAL = 'neutral', 'Neutral'
    
    # === Club & Season ===
    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='fixtures'
    )
    season = models.ForeignKey(
        'Season',
        on_delete=models.CASCADE,
        related_name='fixtures'
    )
    
    # === Match Info ===
    opponent_name = models.CharField(max_length=100)
    venue = models.CharField(
        max_length=10,
        choices=Venue.choices
    )
    competition = models.CharField(
        max_length=100,
        blank=True,
        help_text="League, Cup, Friendly, etc."
    )
    
    # === Schedule ===
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    
    # === Result (filled after match) ===
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.SCHEDULED
    )
    goals_for = models.PositiveSmallIntegerField(null=True, blank=True)
    goals_against = models.PositiveSmallIntegerField(null=True, blank=True)
    
    # === Metadata ===
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date', 'time']
        indexes = [
            models.Index(fields=['club', 'date']),
            models.Index(fields=['season', 'status']),
        ]
    
    def __str__(self):
        vs = "vs" if self.venue == self.Venue.HOME else "@"
        return f"{self.club.name} {vs} {self.opponent_name} ({self.date})"
    
    @property
    def result(self):
        if self.goals_for is None:
            return None
        if self.goals_for > self.goals_against:
            return 'W'
        elif self.goals_for < self.goals_against:
            return 'L'
        return 'D'
    
    @property
    def score_display(self):
        if self.goals_for is None:
            return "vs"
        return f"{self.goals_for} - {self.goals_against}"

# clubs/models/events.py

from django.db import models
from django.conf import settings


class ClubEvent(models.Model):
    \"\"\"
    Any club event - training, meeting, social event, etc.
    These populate the club calendar.
    \"\"\"
    
    class EventType(models.TextChoices):
        TRAINING = 'training', 'Training'
        MEETING = 'meeting', 'Meeting'
        SOCIAL = 'social', 'Social Event'
        OTHER = 'other', 'Other'
    
    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='events'
    )
    
    title = models.CharField(max_length=200)
    event_type = models.CharField(
        max_length=15,
        choices=EventType.choices,
        default=EventType.OTHER
    )
    description = models.TextField(blank=True)
    
    # === Schedule ===
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=False)
    
    # === Location ===
    location = models.CharField(max_length=200, blank=True)
    
    # === Attendance ===
    is_mandatory = models.BooleanField(default=False)
    
    # === Metadata ===
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_club_events'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['club', 'start_datetime']),
            models.Index(fields=['event_type']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.club.name}"

# users/models.py (or a new integrations app)

from django.db import models
from django.conf import settings


class GoogleCalendarIntegration(models.Model):
    \"\"\"
    Stores a user's Google Calendar connection.
    One per user - they can sync their clubs' events to their calendar.
    \"\"\"
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='google_calendar'
    )
    
    # OAuth tokens (encrypted in production)
    access_token = models.TextField()
    refresh_token = models.TextField()
    token_expiry = models.DateTimeField()
    
    # The dedicated calendar we created for iFoot events
    ifoot_calendar_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Google Calendar ID for the iFoot calendar"
    )
    
    # User preferences
    sync_enabled = models.BooleanField(default=True)
    sync_fixtures = models.BooleanField(default=True)
    sync_training = models.BooleanField(default=True)
    sync_meetings = models.BooleanField(default=True)
    
    # Status tracking
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_error = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Google Calendar - {self.user.email}"
    
    @property
    def is_token_expired(self):
        from django.utils import timezone
        return timezone.now() >= self.token_expiry

# clubs/models/events.py (additions)

class ClubEvent(models.Model):
    # ... existing fields ...
    
    # === Google Calendar Sync ===
    google_event_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Event ID in Google Calendar (for updates/deletes)"
    )
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('synced', 'Synced'),
            ('failed', 'Failed'),
            ('not_applicable', 'Not Applicable'),
        ],
        default='pending'
    )
    last_synced_at = models.DateTimeField(null=True, blank=True)


class Fixture(models.Model):
    # ... existing fields ...
    
    # Same sync fields
    google_event_id = models.CharField(max_length=255, blank=True)
    sync_status = models.CharField(max_length=20, default='pending')
    last_synced_at = models.DateTimeField(null=True, blank=True)
"""


