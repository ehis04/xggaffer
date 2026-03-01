from django.db import models
from apps.users.models import User
from apps.referee.Laws.models import Law
from apps.referee.learningTools.models import Quiz

class StatusChoices(models.TextChoices):
    NOT_STARTED = 'NS', 'Not Started'
    IN_PROGRESS = 'I', 'In Progress'
    COMPLETED = 'C', 'Completed'
    MASTERED = 'M', 'Mastered'
    
class UserLearningProgress(models.Model):
    """Track user's overall progress through laws"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='law_progress')
    law = models.ForeignKey(Law, on_delete=models.CASCADE, related_name='user_progress')
    
    # Progress metrics
    completion_percentage = models.FloatField(default=0.0)  # 0-100
    clauses_completed = models.PositiveIntegerField(default=0)
    clauses_total = models.PositiveIntegerField(default=0)
    
    # Performance
    quiz_score = models.FloatField(default=0.0)  # Average quiz score
    quizzes_taken = models.PositiveIntegerField(default=0)
    quizzes_passed = models.PositiveIntegerField(default=0)
    
    # Time tracking
    time_spent_minutes = models.PositiveIntegerField(default=0)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.NOT_STARTED
    )
    
    # Dates
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'law']
        verbose_name = _("User Learning Progress")
        verbose_name_plural = _("User Learning Progress")
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', '-last_accessed']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Law {self.law.number} ({self.completion_percentage}%)"
    
    def update_completion_percentage(self):
        """Calculate and update completion percentage"""
        if self.clauses_total == 0:
            self.completion_percentage = 0.0
        else:
            self.completion_percentage = (self.clauses_completed / self.clauses_total) * 100
        
        # Update status based on completion
        if self.completion_percentage == 0:
            self.status = 'not_started'
        elif self.completion_percentage == 100:
            if self.quiz_score >= 90:
                self.status = 'mastered'
            else:
                self.status = 'completed'
        else:
            self.status = 'in_progress'
        
        self.save()

class QuizAttempt(models.Model):
    """Individual quiz attempt records"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    
    user_answer = models.JSONField()  # User's selected answer(s)
    is_correct = models.BooleanField()
    
    time_taken_seconds = models.PositiveIntegerField()
    points_earned = models.PositiveIntegerField()
    
    # Review tracking
    reviewed = models.BooleanField(default=False)
    bookmarked = models.BooleanField(default=False)  # User wants to review later
    
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Quiz Attempt")
        verbose_name_plural = _("Quiz Attempts")
        indexes = [
            models.Index(fields=['user', '-attempted_at']),
            models.Index(fields=['quiz', 'is_correct']),
            models.Index(fields=['user', 'bookmarked']),
        ]
    
    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{status} {self.user.username} - Quiz {self.quiz.id}"

class ScenarioAttempt(models.Model):
    """Track scenario challenge attempts"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scenario_attempts')
    scenario = models.ForeignKey(ScenarioChallenge, on_delete=models.CASCADE, related_name='attempts')
    
    answers = models.JSONField()  # User's answers to all decision points
    score = models.PositiveIntegerField()  # Points earned
    time_taken_seconds = models.PositiveIntegerField()
    
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Scenario Attempt")
        verbose_name_plural = _("Scenario Attempts")
        indexes = [
            models.Index(fields=['user', '-completed_at']),
            models.Index(fields=['scenario']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.scenario.title} ({self.score} pts)"


class DrillAttempt(models.Model):
    """Track quick drill attempts"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='drill_attempts')
    drill = models.ForeignKey(QuickDrill, on_delete=models.CASCADE, related_name='attempts')
    
    user_answers = models.JSONField()  # User's responses
    score = models.PositiveIntegerField()  # Points earned
    time_taken_seconds = models.PositiveIntegerField()
    
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Drill Attempt")
        verbose_name_plural = _("Drill Attempts")
        indexes = [
            models.Index(fields=['user', '-completed_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.drill.title}"