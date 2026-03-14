from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Count, Q
from django.utils import timezone


@receiver(post_save, sender='referee_progressTracking.ClauseRead')
def clause_read_created(sender, instance, created, **kwargs):
    if not created:
        return

    from .models import UserLearningProgress, ClauseRead

    law = instance.clause.law
    progress, _ = UserLearningProgress.objects.get_or_create(
        user=instance.user,
        law=law,
        defaults={
            'clauses_total': law.clauses.count(),
            'started_at': timezone.now(),
            'status': 'I',
        }
    )

    completed = ClauseRead.objects.filter(
        user=instance.user,
        clause__law=law,
    ).count()

    progress.clauses_completed = completed
    progress.clauses_total = law.clauses.count()

    if not progress.started_at:
        progress.started_at = timezone.now()

    progress.update_completion_percentage()


@receiver(post_save, sender='referee_progressTracking.QuizAttempt')
def quiz_attempt_saved(sender, instance, created, **kwargs):
    if not created:
        return

    from .models import UserLearningProgress, QuizAttempt

    law = instance.quiz.law
    progress, _ = UserLearningProgress.objects.get_or_create(
        user=instance.user,
        law=law,
        defaults={
            'clauses_total': law.clauses.count(),
            'started_at': timezone.now(),
            'status': 'I',
        }
    )

    agg = QuizAttempt.objects.filter(
        user=instance.user,
        quiz__law=law,
    ).aggregate(
        total=Count('id'),
        passed=Count('id', filter=Q(is_correct=True)),
    )

    progress.quizzes_taken = agg['total'] or 0
    progress.quizzes_passed = agg['passed'] or 0
    progress.quiz_score = (
        (progress.quizzes_passed / progress.quizzes_taken) * 100
        if progress.quizzes_taken > 0 else 0.0
    )

    if not progress.started_at:
        progress.started_at = timezone.now()

    if progress.status == 'NS':
        progress.status = 'I'

    progress.save()