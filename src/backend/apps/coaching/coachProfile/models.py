from django.db import models
from apps.users.models import UserProfile

class ExperienceLevels(models.TextChoices):
    beginner = 'B', 'Beginner'
    intermediate = 'I', 'Intermediate'
    professional = 'P', 'Professional'

class FormationPreferences(models.TextChoices):
    NONE = "n/a", "N/A"

    THREE_ONE_FOUR_TWO = "3-1-4-2", "3-1-4-2"
    THREE_FOUR_ONE_TWO = "3-4-1-2", "3-4-1-2"
    THREE_FOUR_TWO_ONE = "3-4-2-1", "3-4-2-1"
    THREE_FOUR_THREE = "3-4-3", "3-4-3"
    THREE_FIVE_ONE_ONE = "3-5-1-1", "3-5-1-1"

    FOUR_ONE_TWO_ONE_TWO = "4-1-2-1-2", "4-1-2-1-2"
    FOUR_ONE_TWO_THREE = "4-1-2-3", "4-1-2-3"
    FOUR_ONE_THREE_TWO = "4-1-3-2", "4-1-3-2"
    FOUR_ONE_FOUR_ONE = "4-1-4-1", "4-1-4-1"

    FOUR_TWO_ONE_THREE = "4-2-1-3", "4-2-1-3"
    FOUR_TWO_TWO_TWO = "4-2-2-2", "4-2-2-2"
    FOUR_TWO_THREE_ONE = "4-2-3-1", "4-2-3-1"
    FOUR_TWO_FOUR = "4-2-4", "4-2-4"

    FOUR_THREE_ONE_TWO = "4-3-1-2", "4-3-1-2"
    FOUR_THREE_TWO_ONE = "4-3-2-1", "4-3-2-1"
    FOUR_THREE_THREE = "4-3-3", "4-3-3"

    FOUR_FOUR_ONE_ONE = "4-4-1-1", "4-4-1-1"
    FOUR_FOUR_TWO = "4-4-2", "4-4-2"
    FOUR_FIVE_ONE = "4-5-1", "4-5-1"

    FIVE_TWO_ONE_TWO = "5-2-1-2", "5-2-1-2"
    FIVE_TWO_TWO_ONE = "5-2-2-1", "5-2-2-1"
    FIVE_TWO_THREE = "5-2-3", "5-2-3"
    FIVE_THREE_TWO = "5-3-2", "5-3-2"
    FIVE_FOUR_ONE = "5-4-1", "5-4-1"

class CoachProfile(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='coach_profile')
    experience_level = models.CharField(max_length=15, choices=ExperienceLevels.choices, default=ExperienceLevels.beginner)
    formation_preferences = models.CharField(max_length=15, choices=FormationPreferences.choices, default=FormationPreferences.NONE)
    years_experience = models.PositiveIntegerField(default=0)
    club_name = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user_profile.user.username}'s Coach Profile"
    