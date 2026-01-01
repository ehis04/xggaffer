from django.db import models
from apps.users.models import UserProfile


# Create your models here.

class Positions(models.TextChoices):
    NONE = 'n/a', 'N/A'
    GK = 'gk', 'Goal Keeper'
    CB = 'cb', 'Center-Backs'
    FB = 'fb', 'Full Backs'
    WB = 'wb', 'Wide Backs'
    SW = 'sw', 'Sweepers'
    DM = 'dm', 'Defensive Midfielder'
    CM = 'cm', 'Central Midfielder'
    WM = 'wm', 'Wide Midefielder/Winger'
    CF = 'cf', 'Centre Forward/Striker'
    SS = 'ss', 'Second Striker/Support Striker'
    ST = 'st', 'Striker'
    
class DominantFoot(models.TextChoices):
    RIGHT = 'r', 'Right'
    LEFT = 'l', 'Left'
    BOTH = 'b', 'Both'

class PlayerProfile(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='player_profile')
    primary_position = models.CharField(max_length=30, choices=Positions.choices, default=Positions.NONE)
    secondary_position = models.CharField(max_length=30, choices=Positions.choices, default=Positions.NONE)
    dominant_foot = models.CharField(max_length=8, choices=DominantFoot.choices, default=DominantFoot.RIGHT)
    height_cm = models.PositiveIntegerField(default=0)
    weight_kg = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user_profile.user.username}'s Player Profile"
