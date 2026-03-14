"""
apps/referee/progress/models.py

Extends the existing models with ClauseRead for tracking
which specific clauses a user has read.
"""
from django.db import models
from apps.users.models import User
from apps.referee.Laws.models import Law, LawClause
from apps.referee.learningTools.models import Quiz, QuickDrill


class StatusChoices(models.TextChoices):
    NOT_STARTED = 'NS', 'Not Started'
    IN_PROGRESS = 'I', 'In Progress'
    COMPLETED = 'C', 'Completed'
    MASTERED = 'M', 'Mastered'


class UserLearningProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='law_progress')
    law = models.ForeignKey(Law, on_delete=models.CASCADE, related_name='user_progress')

    completion_percentage = models.FloatField(default=0.0)
    clauses_completed = models.PositiveIntegerField(default=0)
    clauses_total = models.PositiveIntegerField(default=0)

    quiz_score = models.FloatField(default=0.0)
    quizzes_taken = models.PositiveIntegerField(default=0)
    quizzes_passed = models.PositiveIntegerField(default=0)

    time_spent_minutes = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.NOT_STARTED,
    )

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'law']
        verbose_name = 'User Learning Progress'
        verbose_name_plural = 'User Learning Progress'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', '-last_accessed']),
        ]

    def __str__(self):
        return f"{self.user.username} - Law {self.law.number} ({self.completion_percentage:.0f}%)"

    def update_completion_percentage(self):
        from django.utils import timezone

        if self.clauses_total == 0:
            self.completion_percentage = 0.0
        else:
            self.completion_percentage = (self.clauses_completed / self.clauses_total) * 100

        if self.completion_percentage == 0:
            self.status = StatusChoices.NOT_STARTED
        elif self.completion_percentage >= 100:
            if self.quiz_score >= 90:
                self.status = StatusChoices.MASTERED
                if not self.completed_at:
                    self.completed_at = timezone.now()
            else:
                self.status = StatusChoices.COMPLETED
                if not self.completed_at:
                    self.completed_at = timezone.now()
        else:
            self.status = StatusChoices.IN_PROGRESS

        self.save()


class ClauseRead(models.Model):
    """
    Tracks which specific clauses a user has read.
    One record per user per clause — idempotent.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clauses_read')
    clause = models.ForeignKey(LawClause, on_delete=models.CASCADE, related_name='read_by')
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'clause']
        verbose_name = 'Clause Read'
        verbose_name_plural = 'Clauses Read'
        indexes = [
            models.Index(fields=['user', 'clause']),
        ]

    def __str__(self):
        return f"{self.user.username} read {self.clause}"


class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')

    user_answer = models.JSONField()
    is_correct = models.BooleanField()

    time_taken_seconds = models.PositiveIntegerField()
    points_earned = models.PositiveIntegerField()

    reviewed = models.BooleanField(default=False)
    bookmarked = models.BooleanField(default=False)

    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Quiz Attempt'
        verbose_name_plural = 'Quiz Attempts'
        indexes = [
            models.Index(fields=['user', '-attempted_at']),
            models.Index(fields=['quiz', 'is_correct']),
            models.Index(fields=['user', 'bookmarked']),
        ]

    def __str__(self):
        mark = '✓' if self.is_correct else '✗'
        return f"{mark} {self.user.username} - Quiz {self.quiz.id}"


class DrillAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='drill_attempts')
    drill = models.ForeignKey(QuickDrill, on_delete=models.CASCADE, related_name='attempts')

    user_answers = models.JSONField()
    score = models.PositiveIntegerField()
    time_taken_seconds = models.PositiveIntegerField()

    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Drill Attempt'
        verbose_name_plural = 'Drill Attempts'
        indexes = [
            models.Index(fields=['user', '-completed_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.drill.title}"