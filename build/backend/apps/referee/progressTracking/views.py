"""
apps/referee/progress/views.py

Progress tracking endpoints:
- Dashboard: summary of all law progress
- Per-law progress: completion, quiz scores
- Mark clause as read: increments completion
- Attempt history: quiz / scenario / drill attempts
- Bookmarks: bookmark/unbookmark quiz attempts
"""
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Avg, Count
from django.utils import timezone

from apps.referee.Laws.models import Law, LawClause, LawEdition
from .models import UserLearningProgress, QuizAttempt, DrillAttempt
from .serializers import (
    UserLearningProgressSerializer, LearningDashboardSerializer,
    MarkClauseReadSerializer,
    QuizAttemptSerializer, DrillAttemptSerializer,
)


# ─────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────

class LearningDashboardView(APIView):
    """
    GET /progress/dashboard/
    Returns comprehensive learning stats and per-law progress.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        current_edition = LawEdition.objects.filter(is_current=True).first()

        all_laws = Law.objects.filter(
            edition=current_edition
        ).order_by('number') if current_edition else Law.objects.none()

        total_laws = all_laws.count()

        # Ensure progress records exist for all laws
        for law in all_laws:
            UserLearningProgress.objects.get_or_create(
                user=user,
                law=law,
                defaults={'clauses_total': law.clauses.count()}
            )

        progress_qs = UserLearningProgress.objects.filter(
            user=user, law__in=all_laws
        ).select_related('law').order_by('law__number')

        # Aggregate stats
        agg = progress_qs.aggregate(
            total_time=Sum('time_spent_minutes'),
            avg_quiz_score=Avg('quiz_score'),
            total_quizzes=Sum('quizzes_taken'),
        )

        laws_started = progress_qs.filter(status__in=['I', 'C', 'M']).count()
        laws_completed = progress_qs.filter(status__in=['C', 'M']).count()
        laws_mastered = progress_qs.filter(status='M').count()

        completion_values = list(progress_qs.values_list('completion_percentage', flat=True))
        overall_completion = round(
            sum(completion_values) / len(completion_values), 1
        ) if completion_values else 0.0

        total_points = QuizAttempt.objects.filter(user=user, is_correct=True).aggregate(
            total=Sum('points_earned')
        )['total'] or 0

        streak = _calculate_streak(user)

        data = {
            'total_laws': total_laws,
            'laws_started': laws_started,
            'laws_completed': laws_completed,
            'laws_mastered': laws_mastered,
            'overall_completion': overall_completion,
            'total_quizzes_taken': agg['total_quizzes'] or 0,
            'average_quiz_score': round(agg['avg_quiz_score'] or 0.0, 1),
            'total_time_spent_minutes': agg['total_time'] or 0,
            'total_points_earned': total_points,
            'streak_days': streak,
            'law_progress': progress_qs,
        }

        serializer = LearningDashboardSerializer(data)
        return Response(serializer.data)


# ─────────────────────────────────────────────
# Per-Law Progress
# ─────────────────────────────────────────────

class LawProgressView(RetrieveUpdateAPIView):
    """
    GET  /progress/law/{law_id}/    -> progress for a single law
    PATCH /progress/law/{law_id}/   -> update time_spent_minutes or status
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserLearningProgressSerializer

    def get_object(self):
        law = get_object_or_404(Law, pk=self.kwargs['law_id'])
        progress, _ = UserLearningProgress.objects.get_or_create(
            user=self.request.user,
            law=law,
            defaults={'clauses_total': law.clauses.count()}
        )
        return progress


class AllLawProgressView(ListAPIView):
    """
    GET /progress/laws/   -> all law progress for the current user
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserLearningProgressSerializer

    def get_queryset(self):
        return UserLearningProgress.objects.filter(
            user=self.request.user
        ).select_related('law').order_by('law__number')


# ─────────────────────────────────────────────
# Mark Clause as Read
# ─────────────────────────────────────────────

class MarkClauseReadView(APIView):
    """
    POST /progress/law/{law_id}/clause/read/
    Body: { "clause_id": 42, "time_spent_minutes": 5 }

    Marks a clause as completed and updates the law's completion percentage.
    Idempotent — calling again won't double-count.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, law_id):
        serializer = MarkClauseReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        law = get_object_or_404(Law, pk=law_id)
        clause = get_object_or_404(LawClause, pk=serializer.validated_data['clause_id'], law=law)
        time_spent = serializer.validated_data['time_spent_minutes']

        progress, _ = UserLearningProgress.objects.get_or_create(
            user=request.user,
            law=law,
            defaults={
                'clauses_total': law.clauses.count(),
                'started_at': timezone.now(),
                'status': 'I',
            }
        )

        # Track which clause IDs have been read (stored in law's full_content or a simple set)
        # We use a dedicated tracking model via the clause ID list in a JSON field
        # For simplicity, we re-compute from a ClauseRead model
        clause_read, created = ClauseRead.objects.get_or_create(
            user=request.user,
            clause=clause,
        )

        if created:
            # First time reading this clause
            progress.clauses_completed = min(
                progress.clauses_completed + 1,
                progress.clauses_total
            )

        # Always add time spent
        progress.time_spent_minutes += time_spent

        # Ensure started_at is set
        if not progress.started_at:
            progress.started_at = timezone.now()

        if progress.status == 'NS':
            progress.status = 'I'

        progress.update_completion_percentage()  # Calls save() internally

        return Response({
            'clauses_completed': progress.clauses_completed,
            'clauses_total': progress.clauses_total,
            'completion_percentage': progress.completion_percentage,
            'status': progress.status,
        })


# ─────────────────────────────────────────────
# Attempt History
# ─────────────────────────────────────────────

class AttemptPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class QuizAttemptHistoryView(ListAPIView):
    """
    GET /progress/attempts/quizzes/
    Query params: law_id, is_correct, bookmarked
    """
    permission_classes = [IsAuthenticated]
    serializer_class = QuizAttemptSerializer
    pagination_class = AttemptPagination

    def get_queryset(self):
        qs = QuizAttempt.objects.filter(
            user=self.request.user
        ).select_related('quiz', 'quiz__law').order_by('-attempted_at')

        law_id = self.request.query_params.get('law')
        if law_id:
            qs = qs.filter(quiz__law_id=law_id)

        is_correct = self.request.query_params.get('correct')
        if is_correct is not None:
            qs = qs.filter(is_correct=is_correct.lower() == 'true')

        bookmarked = self.request.query_params.get('bookmarked')
        if bookmarked is not None:
            qs = qs.filter(bookmarked=bookmarked.lower() == 'true')

        return qs


class ToggleBookmarkView(APIView):
    """
    POST /progress/attempts/quizzes/{attempt_id}/bookmark/
    Toggles the bookmarked flag on a quiz attempt.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, attempt_id):
        attempt = get_object_or_404(QuizAttempt, pk=attempt_id, user=request.user)
        attempt.bookmarked = not attempt.bookmarked
        attempt.save(update_fields=['bookmarked'])
        return Response({'bookmarked': attempt.bookmarked})


class MarkAttemptReviewedView(APIView):
    """
    POST /progress/attempts/quizzes/{attempt_id}/reviewed/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, attempt_id):
        attempt = get_object_or_404(QuizAttempt, pk=attempt_id, user=request.user)
        attempt.reviewed = True
        attempt.save(update_fields=['reviewed'])
        return Response({'reviewed': True})


class DrillAttemptHistoryView(ListAPIView):
    """GET /progress/attempts/drills/"""
    permission_classes = [IsAuthenticated]
    serializer_class = DrillAttemptSerializer
    pagination_class = AttemptPagination

    def get_queryset(self):
        return DrillAttempt.objects.filter(
            user=self.request.user
        ).select_related('drill', 'drill__law').order_by('-completed_at')


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _calculate_streak(user) -> int:
    """
    Returns the number of consecutive days the user has attempted
    at least one quiz, scenario, or drill.
    """
    from django.db.models.functions import TruncDate

    quiz_dates = set(
        QuizAttempt.objects.filter(user=user)
        .annotate(d=TruncDate('attempted_at'))
        .values_list('d', flat=True)
    )
    drill_dates = set(
        DrillAttempt.objects.filter(user=user)
        .annotate(d=TruncDate('completed_at'))
        .values_list('d', flat=True)
    )

    all_dates = sorted(quiz_dates | drill_dates, reverse=True)

    if not all_dates:
        return 0

    from datetime import timedelta, date

    streak = 0
    today = date.today()
    expected = today

    for d in all_dates:
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        elif d < expected:
            break

    return streak


# ─────────────────────────────────────────────
# ClauseRead — simple through model (needs to be in models.py)
# ─────────────────────────────────────────────
# Import here to avoid circular issues
from .models import ClauseRead  # noqa: E402 (defined below in models.py)