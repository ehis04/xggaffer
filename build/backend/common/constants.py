from django.db import models


class Position(models.TextChoices):
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


class PreferredFoot(models.TextChoices):
    RIGHT = 'r', 'Right'
    LEFT = 'l', 'Left'
    BOTH = 'b', 'Both'