from django.db import models
from ..Laws.models import LawClause, Law

class QuizType(models.TextChoices):
    MULTIPLE_CHOICE = 'MC', 'Multiple Choice'
    TRUE_FALSE = 'TF', 'True/False'


class TrueOrFalse(models.TextChoices):
    TRUE = 'T', 'True'
    FALSE = 'F', 'False'


class DifficultyLevel(models.TextChoices):
    EASY = 'E', 'Easy'
    MEDIUM = 'M', 'Medium'
    HARD = 'H', 'Hard'

class Quiz(models.Model):
    law = models.ForeignKey(Law, on_delete=models.CASCADE, related_name='quizzes')
    clause = models.ForeignKey(
        LawClause, on_delete=models.SET_NULL,
        related_name='quizzes', null=True, blank=True
    )

    title = models.CharField(max_length=200)
    description = models.TextField()
    difficulty = models.CharField(max_length=1, choices=DifficultyLevel.choices, default=DifficultyLevel.MEDIUM)
    points = models.PositiveIntegerField(default=10)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Quiz'
        verbose_name_plural = 'Quizzes'
        indexes = [
            models.Index(fields=['law', 'difficulty']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.title

class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question = models.TextField()
    explanation = models.TextField()
    difficulty = models.CharField(
        max_length=1,
        choices=DifficultyLevel.choices,
        default=DifficultyLevel.MEDIUM,
    )
    points = models.PositiveIntegerField(default=10)
    question_type = models.CharField(max_length=10, choices=QuizType, default=QuizType.MULTIPLE_CHOICE)

    times_attempted = models.PositiveIntegerField(default=0)
    times_correct = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Quiz Question'
        verbose_name_plural = 'Quiz Questions'
        indexes = [
            models.Index(fields=['difficulty']),
        ]

    def __str__(self):
        return f"{self.question[:60]}..."

    @property
    def success_rate(self):
        if self.times_attempted == 0:
            return 0.0
        return round((self.times_correct / self.times_attempted) * 100, 1)

    def get_correct_answer(self):
        if self.question_type == QuizType.MULTIPLE_CHOICE:
            return self.mcq_options.filter(is_correct=True).first()
        elif self.question_type == QuizType.TRUE_FALSE:
            return getattr(self, 'tf_answer', None)
        return None

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.question_type == QuizType.MULTIPLE_CHOICE:
            pass


class MCQOption(models.Model):
    question = models.ForeignKey(
        QuizQuestion, on_delete=models.CASCADE,
        related_name='mcq_options',
        limit_choices_to={'question_type': QuizType.MULTIPLE_CHOICE},
    )
    answer = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0, help_text="Display order of this option.")

    class Meta:
        verbose_name = 'MCQ Option'
        verbose_name_plural = 'MCQ Options'
        ordering = ['order']

    def __str__(self):
        marker = '✓' if self.is_correct else '✗'
        return f"{marker} {self.answer[:60]}"

#add scenarios

class TrueFalseAnswer(models.Model):
    question = models.OneToOneField(
        QuizQuestion, on_delete=models.CASCADE,
        related_name='tf_answer',
        limit_choices_to={'question_type': QuizType.TRUE_FALSE},
    )
    correct_answer = models.CharField(
        max_length=1,
        choices=TrueOrFalse.choices,
    )

    class Meta:
        verbose_name = 'True/False Answer'
        verbose_name_plural = 'True/False Answers'

    def __str__(self):
        return f"Q{self.question_id}: {self.get_correct_answer_display()}"
    
class DrillType(models.TextChoices):
    RAPID_FIRE = 'RF', 'Rapid Fire'
    SPOT_ERROR = 'SE', 'Spot the Error'
    MATCH_PAIRS = 'MP', 'Match Pairs'
    FILL_BLANK = 'FB', 'Fill in the Blank'


class QuickDrill(models.Model):
    law = models.ForeignKey(Law, on_delete=models.CASCADE, related_name='drills')
    
    drill_type = models.CharField(max_length=2, choices=DrillType.choices)
    title = models.CharField(max_length=200)
    
    drill_data = models.JSONField()
    
    time_limit_seconds = models.PositiveIntegerField(default=60)
    points = models.PositiveIntegerField(default=15)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = ("Quick Drill")
        verbose_name_plural = ("Quick Drills")
        indexes = [
            models.Index(fields=['law', 'drill_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.get_drill_type_display()} - {self.title}"
