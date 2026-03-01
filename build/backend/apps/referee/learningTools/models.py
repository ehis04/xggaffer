from django.db import models
from apps.referee.Laws import LawClause, Law

class QuizType(models.TextChoices):
    MULTIPLE_CHOICE = 'MC', 'Multiple Choice'
    TRUE_FALSE = 'TF', 'True/False'
    SCENARIO = 'SC', 'Scenario Based'
    IMAGE_BASED = 'IB', 'Image Based'
    SEQUENCE = 'SQ', 'Sequence/Order'
    
class DifficultyLevel(models.TextChoices):
    EASY = "E", "Easy"
    MEDIUM = "M", "Medium"
    HARD = "H", "Hard"

class Quiz(models.Model):
    law = models.ForeignKey(Law, on_delete=models.CASCADE, related_name='quizzes')
    clause = models.ForeignKey(LawClause, on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
    quiz_type = models.CharField(max_length=2, choices=QuizType.choices)
    question = models.TextField()
    
    # For scenario-based questions
    scenario_description = models.TextField(blank=True)
    scenario_image = models.URLField(blank=True, null=True)
    
    options = models.JSONField()
    
    correct_answer = models.JSONField()  # Can be single value or array
    explanation = models.TextField()  # Why this answer is correct
    
    difficulty = models.CharField(max_length=20, choices=DifficultyLevel.choices, default='medium')
    points = models.PositiveIntegerField(default=10)  # Points awarded for correct answer
    
    # Usage tracking
    times_attempted = models.PositiveIntegerField(default=0)
    times_correct = models.PositiveIntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Quiz")
        verbose_name_plural = _("Quizzes")
        indexes = [
            models.Index(fields=['law', 'difficulty']),
            models.Index(fields=['quiz_type']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.get_quiz_type_display()} - {self.question[:50]}..."
    
    @property
    def success_rate(self):
        if self.times_attempted == 0:
            return 0
        return (self.times_correct / self.times_attempted) * 100

class ScenarioChallenge(models.Model):
    """Real-world match scenarios requiring decision-making"""
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard')
    ]
    
    law = models.ForeignKey(Law, on_delete=models.CASCADE, related_name='scenarios')
    
    title = models.CharField(max_length=200)
    description = models.TextField()  # The scenario setup
    
    # Visual context
    diagram_url = models.URLField(blank=True, null=True)
    video_clip_url = models.URLField(blank=True, null=True)
    
    # Multiple decisions can be involved
    decision_points = models.JSONField()
    
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='medium')
    points = models.PositiveIntegerField(default=20)
    
    # Tags for categorization
    tags = models.JSONField(default=list)  # e.g., ["handball", "penalty area", "VAR"]
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Scenario Challenge")
        verbose_name_plural = _("Scenario Challenges")
        indexes = [
            models.Index(fields=['law', 'difficulty']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.title
    
class DrillType(models.TextChoices):
    RAPID_FIRE = 'RF', 'Rapid Fire'
    SPOT_ERROR = 'SE', 'Spot the Error'
    MATCH_PAIRS = 'MP', 'Match Pairs'
    FILL_BLANK = 'FB', 'Fill in the Blank'


class QuickDrill(models.Model):
    """Fast-paced micro-learning exercises"""
    law = models.ForeignKey(Law, on_delete=models.CASCADE, related_name='drills')
    
    drill_type = models.CharField(max_length=2, choices=DrillType.choices)
    title = models.CharField(max_length=200)
    
    # Drill content structure
    drill_data = models.JSONField()
    """
    Match Pairs Example:
    {
        "pairs": [
            {"term": "Offside position", "definition": "Player nearer to goal than ball"},
            {"term": "Active play", "definition": "Interfering with play or opponent"}
        ]
    }
    
    Spot Error Example:
    {
        "scenario": "The goalkeeper picks up a back pass...",
        "errors": ["back pass should result in indirect free kick"],
        "correct_answer": "Indirect free kick to opposing team"
    }
    
    Fill Blank Example:
    {
        "text": "A player is offside if any part of the ___ is nearer to the goal",
        "blanks": [
            {"position": 0, "options": ["head", "hands", "jersey"], "correct": "head"}
        ]
    }
    """
    
    time_limit_seconds = models.PositiveIntegerField(default=60)
    points = models.PositiveIntegerField(default=15)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Quick Drill")
        verbose_name_plural = _("Quick Drills")
        indexes = [
            models.Index(fields=['law', 'drill_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.get_drill_type_display()} - {self.title}"
