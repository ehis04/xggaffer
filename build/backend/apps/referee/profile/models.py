from django.db import models
from apps.users.models import UserProfile

# Create your models here.
class RefereeExperienceLevel(models.TextChoices):
    BEGINNER = 'B', 'Beginner'
    INTERMEDIATE = 'I', 'Intermediate'
    EXPERIENCED = 'E', 'Experienced'
    PROFESSIONAL = 'P', 'Professional'

class RefereeCertificationLevel(models.TextChoices):
    NONE = 'NON', 'No Certification'
    ENTRY = 'EL', 'Entry Level'
    REGIONAL = 'REG', 'Regional'
    NATIONAL = 'NAT', 'National'
    FIFA = 'FIFA', 'FIFA Listed'

class RefereePositions(models.TextChoices):
    REFEREE = "R", "Referee"
    ASSISTANT = "A", "Assistant"
    FOURTH = "F", "Fourth"
    VAR = "V", "Var"
    
class LearningTime(models.TextChoices):
    MORNING = "M", "Morning"
    AFTERNOON = "A", "Afternoon"
    EVENING = "E", "Evening"
    NIGHT = "N", "Night"

class RefereeProfile(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='referee_profile')
    experience_level = models.CharField(max_length=3, choices=RefereeExperienceLevel.choices, default=RefereeExperienceLevel.BEGINNER)
    years_experience = models.PositiveIntegerField(default=0)
    certification_level = models.CharField(max_length=15, choices=RefereeCertificationLevel.choices, default=RefereeCertificationLevel.NONE)
    certification_date = models.DateField(null=True, blank=True)
    next_certification_date = models.DateField(null=True, blank=True)
    total_matches_officiates = models.PositiveIntegerField(default=0)
    matches_this_season = models.PositiveIntegerField(default=0)
    competition_levels = models.JSONField(default=list)
    primary_position = models.CharField(max_length=10, choices=RefereePositions.choices, default=RefereePositions.REFEREE)
    preferred_learning_time = models.CharField(max_length=20, choices=LearningTime.choices, blank=True)
    certification_goal = models.CharField(max_length=15, choices=RefereeCertificationLevel.choices, blank=True)
    target_completion_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user_profile.user.username}'s Referee Profile"
    
    @property
    def recommended_difficulty(self):
        if self.experience_level == RefereeExperienceLevel.BEGINNER:
            return ['beginner']
        elif self.experience_level == RefereeExperienceLevel.INTERMEDIATE:
            return ['beginner', 'intermediate']
        elif self.experience_level == RefereeExperienceLevel.EXPERIENCED:
            return ['intermediate', 'advanced']
        else:
            return ['intermediate', 'advanced']
    