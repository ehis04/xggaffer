from django.db import models
from apps.users.models import UserProfile
from common.constants import *


class PlayerProfile(models.Model):
    user_profile = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='player_profile',
    )
    primary_position = models.CharField(max_length=4, choices=Position.choices, blank=True)
    secondary_position = models.CharField(max_length=4, choices=Position.choices, blank=True)
    preferred_foot = models.CharField(max_length=1, choices=PreferredFoot.choices, blank=True)
    height_cm = models.PositiveIntegerField(default=0)
    weight_kg = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_profile.user.username}'s Player Profile"
