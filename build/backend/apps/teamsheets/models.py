from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

POSITIONS = [
    ('GK', 'Goalkeeper'),
    ('RB', 'Right Back'),
    ('CB', 'Centre Back'),
    ('LB', 'Left Back'),
    ('CM', 'Centre Midfield'),
    ('DM', 'Defensive Midfield'),
    ('LM', 'Left Midfield'),
    ('RM', 'Right Midfield'),
    ('AM', 'Attacking Midfield'),
    ('LW', 'Left Wing'),
    ('RW', 'Right Wing'),
    ('ST', 'Striker'),
]

FORMATIONS = [
    ('442', '4-4-2'),
    ('433', '4-3-3'),
    ('352', '3-5-2'),
    ('4231', '4-2-3-1'),
    ('343', '3-4-3'),
    ('532', '5-3-2'),
]

class Teamsheet(models.Model):
    title = models.CharField(max_length=50, blank=False, null=False)
    formation = models.CharField(max_length=10, choices=FORMATIONS)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title



class TeamsheetPlayer(models.Model):
    teamsheet = models.ForeignKey(Teamsheet, on_delete=models.CASCADE, related_name='players')
    name = models.CharField(max_length=50, blank=False, null=False)
    number = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(99)], blank=True, null=True)
    position = models.CharField(max_length=3,choices=POSITIONS)

    def __str__(self):
        return f"{self.name} - {self.position}"

