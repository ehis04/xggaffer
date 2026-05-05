from django.conf import settings
from django.db import models


class ClubPlayerInjury(models.Model):

    class InjuryType(models.TextChoices):
        MUSCLE = 'muscle', 'Muscle'
        LIGAMENT = 'ligament', 'Ligament'
        BONE = 'bone', 'Bone/Fracture'
        TENDON = 'tendon', 'Tendon'
        CARTILAGE = 'cartilage', 'Cartilage'
        HEAD = 'head', 'Head/Concussion'
        ILLNESS = 'illness', 'Illness'
        SUSPENSION = 'suspension', 'Suspension'
        OTHER = 'other', 'Other'

    class Severity(models.TextChoices):
        MINOR = 'minor', 'Minor'
        MODERATE = 'moderate', 'Moderate'
        SEVERE = 'severe', 'Severe'

    class AvailabilityStatus(models.TextChoices):
        AVAILABLE = 'AV', 'Available'
        INJURED = 'IN', 'Injured'
        IN_DOUBT = 'DO', 'In Doubt'
        SUSPENDED = 'SU', 'Suspended'

    club_player = models.ForeignKey(
        'ClubPlayer',
        on_delete=models.CASCADE,
        related_name='injuries',
    )
    injury_type = models.CharField(
        max_length=20,
        choices=InjuryType.choices,
        default=InjuryType.OTHER,
    )
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.MINOR,
    )
    availability_status = models.CharField(
        max_length=2,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.INJURED,
    )
    injured_at = models.DateField()
    estimated_return = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_current = models.BooleanField(
        default=True,
        help_text='Only one injury record per player should be current at a time',
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_injuries',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'clubs'
        ordering = ['-injured_at', '-created_at']
        indexes = [
            models.Index(fields=['club_player', 'is_current']),
            models.Index(fields=['club_player', '-injured_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['club_player'],
                name='unique_current_injury_per_club_player',
            )
        ]

    def __str__(self):
        return f'{self.club_player} — {self.get_injury_type_display()} ({self.get_severity_display()})'

    def resolve(self):
        self.is_current = False
        self.save(update_fields=['is_current', 'updated_at'])


class ClubPlayerManualStats(models.Model):

    club_player = models.ForeignKey(
        'ClubPlayer',
        on_delete=models.CASCADE,
        related_name='manual_stats',
    )
    season = models.CharField(
        max_length=10,
        help_text="e.g. '2024/25'",
    )

    appearances = models.PositiveSmallIntegerField(null=True, blank=True)
    minutes_played = models.PositiveSmallIntegerField(null=True, blank=True)
    goals = models.PositiveSmallIntegerField(null=True, blank=True)
    assists = models.PositiveSmallIntegerField(null=True, blank=True)

    xg = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    npxg = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    xa = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    shots = models.PositiveSmallIntegerField(null=True, blank=True)
    shots_on_target = models.PositiveSmallIntegerField(null=True, blank=True)
    key_passes = models.PositiveSmallIntegerField(null=True, blank=True)
    dribbles_completed = models.PositiveSmallIntegerField(null=True, blank=True)
    progressive_passes = models.PositiveSmallIntegerField(null=True, blank=True)
    progressive_carries = models.PositiveSmallIntegerField(null=True, blank=True)

    tackles = models.PositiveSmallIntegerField(null=True, blank=True)
    interceptions = models.PositiveSmallIntegerField(null=True, blank=True)
    aerials_won = models.PositiveSmallIntegerField(null=True, blank=True)
    clearances = models.PositiveSmallIntegerField(null=True, blank=True)
    blocks = models.PositiveSmallIntegerField(null=True, blank=True)

    saves = models.PositiveSmallIntegerField(null=True, blank=True)
    save_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    clean_sheets = models.PositiveSmallIntegerField(null=True, blank=True)
    goals_conceded = models.PositiveSmallIntegerField(null=True, blank=True)

    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'clubs'
        ordering = ['-season']
        indexes = [
            models.Index(fields=['club_player', 'season']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['club_player', 'season'],
                name='unique_manual_stats_per_player_season',
            )
        ]

    def __str__(self):
        return f'{self.club_player} — {self.season} manual stats'


class ClubSeasonResult(models.Model):

    class Venue(models.TextChoices):
        HOME = 'home', 'Home'
        AWAY = 'away', 'Away'
        NEUTRAL = 'neutral', 'Neutral'

    club = models.ForeignKey(
        'Club',
        on_delete=models.CASCADE,
        related_name='season_results',
    )
    opponent_name = models.CharField(max_length=100)
    venue = models.CharField(
        max_length=10,
        choices=Venue.choices,
        default=Venue.HOME,
    )
    competition = models.CharField(max_length=100, blank=True)
    match_date = models.DateField()
    goals_for = models.PositiveSmallIntegerField()
    goals_against = models.PositiveSmallIntegerField()

    fixture = models.OneToOneField(
        'Fixture',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='season_result',
        help_text='Linked fixture if one exists in the calendar',
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_season_results',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'clubs'
        ordering = ['-match_date', '-created_at']
        indexes = [
            models.Index(fields=['club', '-match_date']),
            models.Index(fields=['club', 'competition']),
        ]

    def __str__(self):
        return f'{self.club.name} vs {self.opponent_name} ({self.match_date}) {self.goals_for}-{self.goals_against}'

    @property
    def outcome(self) -> str:
        if self.goals_for > self.goals_against:
            return 'W'
        if self.goals_for < self.goals_against:
            return 'L'
        return 'D'


class ProClubProviderLink(models.Model):
    club = models.OneToOneField(
        'clubs.Club',
        on_delete=models.CASCADE,
        related_name='provider_link',
    )
    provider = models.CharField(max_length=32)
    provider_team_id = models.CharField(max_length=128)
    provider_competition_id = models.CharField(max_length=128, blank=True)
    last_provider_sync_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'clubs'

    def __str__(self):
        return f'ProClubProviderLink({self.club.name}, {self.provider}, {self.provider_team_id})'
