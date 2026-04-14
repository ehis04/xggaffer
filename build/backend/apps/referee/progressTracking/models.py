from django.db import models
from django.contrib.postgres.fields import ArrayField

from apps.users.models import UserProfile
from apps.referee.Laws.models import Law, CourseItem


class UserCourseProgress(models.Model):
    STATUS_LOCKED    = 'locked'
    STATUS_ACTIVE    = 'active'
    STATUS_COMPLETED = 'completed'

    STATUS_CHOICES = [
        (STATUS_LOCKED,    'Locked'),
        (STATUS_ACTIVE,    'Active'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    user_profile  = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='course_progress',
    )
    law           = models.ForeignKey(
        Law,
        on_delete=models.CASCADE,
        related_name='user_progress',
    )
    status        = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_LOCKED,
    )
    clauses_read  = models.PositiveSmallIntegerField(default=0)
    total_clauses = models.PositiveSmallIntegerField(default=0)

    started_at    = models.DateTimeField(null=True, blank=True)
    completed_at  = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user_profile', 'law')

    @property
    def progress_percentage(self) -> int:
        if self.total_clauses == 0:
            return 0
        return round((self.clauses_read / self.total_clauses) * 100)

    def __str__(self):
        return (
            f"{self.user_profile.user.username} — "
            f"Law {self.law.law_number} ({self.status})"
        )


class UserItemProgress(models.Model):
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='item_progress',
    )
    item         = models.ForeignKey(
        CourseItem,
        on_delete=models.CASCADE,
        related_name='user_progress',
    )
    completed    = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    scenario_selected_id = models.CharField(max_length=10, blank=True)
    scenario_correct     = models.BooleanField(null=True)

    drill_answers   = models.JSONField(default=dict, blank=True)
    drill_submitted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user_profile', 'item')

    def __str__(self):
        state = 'done' if self.completed else 'pending'
        return f"{self.user_profile.user.username} — {self.item.title} ({state})"


class StudyStreak(models.Model):
    user_profile   = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='study_streak',
    )
    current_streak = models.PositiveSmallIntegerField(default=0)
    studied_dates  = ArrayField(models.DateField(), default=list, blank=True)
    last_updated   = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user_profile.user.username} — streak {self.current_streak}"


class PerformanceScore(models.Model):
    user_profile   = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='performance_score',
    )
    overall_score  = models.PositiveSmallIntegerField(default=0)
    clause_score   = models.PositiveSmallIntegerField(null=True, blank=True)
    scenario_score = models.PositiveSmallIntegerField(null=True, blank=True)
    drill_score    = models.PositiveSmallIntegerField(null=True, blank=True)
    quiz_score     = models.PositiveSmallIntegerField(null=True, blank=True)
    updated_at     = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_profile.user.username} — overall {self.overall_score}%"