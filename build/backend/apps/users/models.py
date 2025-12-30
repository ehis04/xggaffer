from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class gender_choices(models.TextChoices):
    FEMALE = 'F', 'Female'
    MALE = 'M', 'Male'
    OTHER = 'O', 'Other'
    NOT_SPECIFIED = 'NS', 'Not Specified'

class workout_goal_choices(models.TextChoices):
    LOSE_WEIGHT = 'LW', 'Lose Weight'
    BUILD_MUSCLE = 'BM', 'Build Muscle'
    MAINTAIN_WEIGHT = 'MW', 'Maintain Weight'
    GAIN_WEIGHT = 'GW', 'Gain Weight'

class ActivityLevel(models.TextChoices):
    SEDENTARY = 'SED', 'Sedentary'
    LIGHTLY_ACTIVE = 'LA', 'Lightly Active'
    MODERATELY_ACTIVE = 'MA', 'Moderately Active'
    HEAVILY_ACTIVE = 'HA', 'Heavily Active'
class User(AbstractUser):
    email = models.EmailField(_("email address"), unique=True)
    username = models.CharField(max_length=150, blank=True, null=True, unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    gender = models.CharField(max_length=8, choices=gender_choices.choices, default=gender_choices.NOT_SPECIFIED)
    weight = models.PositiveIntegerField(blank=True, null=True)
    height = models.PositiveIntegerField(blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    workout_goal = models.CharField(max_length=10, choices=workout_goal_choices.choices, default=workout_goal_choices.LOSE_WEIGHT)
    activity_level = models.CharField(max_length=3, choices=ActivityLevel.choices, default=ActivityLevel.MODERATELY_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
