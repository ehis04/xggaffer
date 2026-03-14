from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Prefetch

from .models import Quiz, QuizQuestion, QuizType, MCQOption, QuickDrill
from .serializers import (
    QuizListSerializer, QuizDetailSerializer,
    QuizSubmitSerializer, QuizQuestionResultSerializer,
    QuickDrillListSerializer, QuickDrillDetailSerializer,
    DrillSubmitSerializer, DrillResultSerializer,
)


def _questions_with_answers(quiz_qs):
    return quiz_qs.prefetch_related(
        Prefetch(
            'questions',
            queryset=(
                QuizQuestion.objects
                .prefetch_related('mcq_options')
                .select_related('tf_answer')
            ),
        )
    )

class QuizViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET  /quizzes/                   -> list (filter by law, difficulty)
    GET  /quizzes/{id}/              -> quiz with all questions and answer options
    POST /quizzes/{id}/submit/       -> submit all answers, receive graded results
    GET  /quizzes/random/            -> random quiz with questions and answers
    GET  /quizzes/spaced_repetition/ -> prioritised review queue
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'description']

    def get_queryset(self):
        qs = Quiz.objects.filter(is_active=True).select_related('law', 'clause')

        law_id = self.request.query_params.get('law')
        if law_id:
            qs = qs.filter(law_id=law_id)

        law_number = self.request.query_params.get('law_number')
        if law_number:
            qs = qs.filter(law__number=law_number)

        difficulty = self.request.query_params.get('difficulty')
        if difficulty:
            qs = qs.filter(difficulty=difficulty)

        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return QuizDetailSerializer
        return QuizListSerializer

    def retrieve(self, request, *args, **kwargs):
        qs = _questions_with_answers(
            Quiz.objects.filter(pk=kwargs['pk']).select_related('law', 'clause')
        )
        instance = qs.get()
        serializer = QuizDetailSerializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        quiz = _questions_with_answers(
            Quiz.objects.filter(pk=pk).select_related('law')
        ).get()

        serializer = QuizSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_answers = serializer.validated_data['answers']
        time_taken = serializer.validated_data['time_taken_seconds']

        questions = list(quiz.questions.all())
        graded_answers = {}
        total_score = 0
        questions_correct = 0

        for question in questions:
            raw_answer = user_answers.get(str(question.id))
            is_correct = _grade_question(question, raw_answer)

            graded_answers[question.id] = {
                'is_correct': is_correct,
                'user_answer': raw_answer,
            }
            if is_correct:
                total_score += question.points
                questions_correct += 1

        max_score = sum(q.points for q in questions)
        percentage = round((total_score / max_score * 100) if max_score else 0, 1)

        with transaction.atomic():
            from apps.referee.progress.models import QuizAttempt
            attempt = QuizAttempt.objects.create(
                user=request.user,
                quiz=quiz,
                user_answer=user_answers,
                is_correct=questions_correct == len(questions),
                time_taken_seconds=time_taken,
                points_earned=total_score,
            )

            for question in questions:
                grade = graded_answers[question.id]
                QuizQuestion.objects.filter(pk=question.pk).update(
                    times_attempted=question.times_attempted + 1,
                    times_correct=question.times_correct + (1 if grade['is_correct'] else 0),
                )

            _update_quiz_progress(request.user, quiz, questions_correct, len(questions))

        question_results = QuizQuestionResultSerializer(
            questions,
            many=True,
            context={'graded_answers': graded_answers},
        )

        return Response({
            'score': total_score,
            'max_score': max_score,
            'percentage': percentage,
            'points_earned': total_score,
            'questions_correct': questions_correct,
            'questions_total': len(questions),
            'question_results': question_results.data,
            'attempt_id': attempt.id,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def random(self, request):
        """Return a random quiz with all questions and answer options."""
        quiz = _questions_with_answers(
            self.get_queryset().order_by('?')
        ).first()

        if not quiz:
            return Response(
                {'error': 'No quizzes found matching criteria.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(QuizDetailSerializer(quiz).data)

    @action(detail=False, methods=['get'])
    def spaced_repetition(self, request):
        from apps.referee.progress.models import QuizAttempt

        user = request.user
        limit = int(request.query_params.get('limit', 10))

        failed_ids = (
            QuizAttempt.objects.filter(user=user, is_correct=False)
            .values_list('quiz_id', flat=True).distinct()
        )
        bookmarked_ids = (
            QuizAttempt.objects.filter(user=user, bookmarked=True)
            .values_list('quiz_id', flat=True).distinct()
        )
        attempted_ids = (
            QuizAttempt.objects.filter(user=user)
            .values_list('quiz_id', flat=True).distinct()
        )

        base_qs = Quiz.objects.filter(is_active=True)
        law_id = request.query_params.get('law')
        if law_id:
            base_qs = base_qs.filter(law_id=law_id)

        bookmarked = list(base_qs.filter(pk__in=bookmarked_ids).select_related('law')[:limit])
        remaining = limit - len(bookmarked)

        failed = []
        if remaining > 0:
            failed = list(
                base_qs.filter(pk__in=failed_ids)
                .exclude(pk__in=[q.pk for q in bookmarked])
                .select_related('law')[:remaining]
            )
            remaining -= len(failed)

        unattempted = []
        if remaining > 0:
            unattempted = list(
                base_qs.exclude(pk__in=attempted_ids)
                .select_related('law')[:remaining]
            )

        all_quizzes = bookmarked + failed + unattempted
        return Response({
            'count': len(all_quizzes),
            'bookmarked': len(bookmarked),
            'failed': len(failed),
            'unattempted': len(unattempted),
            'results': QuizListSerializer(all_quizzes, many=True).data,
        })

# ─────────────────────────────────────────────
# Quick Drill
# ─────────────────────────────────────────────

class QuickDrillViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = QuickDrill.objects.filter(is_active=True).select_related('law')

        law_id = self.request.query_params.get('law')
        if law_id:
            qs = qs.filter(law_id=law_id)

        drill_type = self.request.query_params.get('type')
        if drill_type:
            qs = qs.filter(drill_type=drill_type)

        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return QuickDrillDetailSerializer
        return QuickDrillListSerializer

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        drill = self.get_object()
        serializer = DrillSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_answers = serializer.validated_data['user_answers']
        time_taken = serializer.validated_data['time_taken_seconds']
        score, max_score = _grade_drill(drill, user_answers)

        with transaction.atomic():
            from apps.referee.progress.models import DrillAttempt
            attempt = DrillAttempt.objects.create(
                user=request.user,
                drill=drill,
                user_answers=user_answers,
                score=score,
                time_taken_seconds=time_taken,
            )

        percentage = round((score / max_score * 100) if max_score else 0, 1)
        result = DrillResultSerializer({
            'score': score,
            'max_score': max_score,
            'percentage': percentage,
            'attempt_id': attempt.id,
        })
        return Response(result.data)

def _grade_question(question: QuizQuestion, user_answer) -> bool:
    if user_answer is None:
        return False

    if question.question_type == QuizType.MULTIPLE_CHOICE:
        try:
            chosen_id = int(user_answer)
        except (TypeError, ValueError):
            return False
        correct_ids = set(
            question.mcq_options.filter(is_correct=True).values_list('id', flat=True)
        )
        return chosen_id in correct_ids

    elif question.question_type == QuizType.TRUE_FALSE:
        tf = getattr(question, 'tf_answer', None)
        if not tf:
            return False
        return str(user_answer).strip().upper() == tf.correct_answer

    return False


def _grade_drill(drill: QuickDrill, user_answers) -> tuple[int, int]:
    data = drill.drill_data
    drill_type = drill.drill_type

    if drill_type == 'MP':
        pairs = data.get('pairs', [])
        max_score = len(pairs) * 5
        score = 0
        for i, pair in enumerate(pairs):
            user_match = user_answers.get(str(i)) or user_answers.get(pair.get('term', ''))
            if user_match and str(user_match).lower() == str(pair.get('definition', '')).lower():
                score += 5
        return score, max_score

    elif drill_type == 'SE':
        correct = str(data.get('correct_answer', '')).lower()
        user = str(user_answers.get('answer', '')).lower()
        return (drill.points, drill.points) if user == correct else (0, drill.points)

    elif drill_type == 'FB':
        blanks = data.get('blanks', [])
        max_score = len(blanks) * 5
        score = 0
        for i, blank in enumerate(blanks):
            if str(user_answers.get(str(i), '')).lower() == str(blank.get('correct', '')).lower():
                score += 5
        return score, max_score

    elif drill_type == 'RF':
        questions = data.get('questions', [])
        max_score = len(questions) * 5
        score = 0
        for i, q in enumerate(questions):
            if str(user_answers.get(str(i), '')).lower() == str(q.get('answer', '')).lower():
                score += 5
        return score, max_score

    return 0, drill.points


def _update_quiz_progress(user, quiz: Quiz, questions_correct: int, questions_total: int):
    try:
        from django.utils import timezone
        from apps.referee.progress.models import UserLearningProgress

        progress, _ = UserLearningProgress.objects.get_or_create(
            user=user,
            law=quiz.law,
            defaults={
                'clauses_total': quiz.law.clauses.count(),
                'started_at': timezone.now(),
            }
        )
        progress.quizzes_taken += 1
        if questions_correct == questions_total:
            progress.quizzes_passed += 1

        if progress.quizzes_taken > 0:
            progress.quiz_score = (progress.quizzes_passed / progress.quizzes_taken) * 100

        if progress.status == 'NS':
            progress.status = 'I'
            progress.started_at = progress.started_at or timezone.now()

        progress.save()
    except Exception:
        pass