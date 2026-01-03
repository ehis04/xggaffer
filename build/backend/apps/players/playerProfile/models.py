from django.db import models
from apps.users.models import UserProfile


# Create your models here.

class Positions(models.TextChoices):
    NONE = '', 'Not Specified'

    GK = 'GK', 'Goalkeeper'

    RB = 'RB', 'Right Back'
    RWB = 'RWB', 'Right Wing Back'
    CB = 'CB', 'Centre Back'
    RCB = 'RCB', 'Right Centre Back'
    CCB = 'CCB', 'Central Centre Back'
    LCB = 'LCB', 'Left Centre Back'
    LB = 'LB', 'Left Back'
    LWB = 'LWB', 'Left Wing Back'

    RDM = 'RDM', 'Right Defensive Midfielder'
    CDM = 'CDM', 'Central Defensive Midfielder'
    LDM = 'LDM', 'Left Defensive Midfielder'
    CM = 'CM', 'Central Midfielder'
    RM = 'RM', 'Right Midfielder'
    LM = 'LM', 'Left Midfielder'

    RAM = 'RAM', 'Right Attacking Midfielder'
    CAM = 'CAM', 'Central Attacking Midfielder'
    LAM = 'LAM', 'Left Attacking Midfielder'
    RW = 'RW', 'Right Winger'
    LW = 'LW', 'Left Winger'
    CF = 'CF', 'Centre Forward'
    ST = 'ST', 'Striker'
    
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
