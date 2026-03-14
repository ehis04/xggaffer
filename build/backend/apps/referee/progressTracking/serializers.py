from rest_framework import serializers
from .models import UserLearningProgress, QuizAttempt, DrillAttempt


class UserLearningProgressSerializer(serializers.ModelSerializer):
    law_number = serializers.IntegerField(source='law.number', read_only=True)
    law_title = serializers.CharField(source='law.title', read_only=True)
    law_difficulty = serializers.CharField(source='law.difficulty_level', read_only=True)
    pass_rate = serializers.SerializerMethodField()

    class Meta:
        model = UserLearningProgress
        fields = [
            'id', 'law_number', 'law_title', 'law_difficulty',
            'completion_percentage', 'clauses_completed', 'clauses_total',
            'quiz_score', 'quizzes_taken', 'quizzes_passed', 'pass_rate',
            'time_spent_minutes', 'status',
            'started_at', 'completed_at', 'last_accessed',
        ]
        read_only_fields = [
            'id', 'law_number', 'law_title', 'law_difficulty',
            'quiz_score', 'quizzes_taken', 'quizzes_passed',
            'started_at', 'last_accessed',
        ]

    def get_pass_rate(self, obj):
        if obj.quizzes_taken == 0:
            return 0.0
        return round((obj.quizzes_passed / obj.quizzes_taken) * 100, 1)


class LearningDashboardSerializer(serializers.Serializer):
    """Summary stats for the user's overall learning dashboard."""
    total_laws = serializers.IntegerField()
    laws_started = serializers.IntegerField()
    laws_completed = serializers.IntegerField()
    laws_mastered = serializers.IntegerField()
    overall_completion = serializers.FloatField()
    total_quizzes_taken = serializers.IntegerField()
    average_quiz_score = serializers.FloatField()
    total_time_spent_minutes = serializers.IntegerField()
    total_points_earned = serializers.IntegerField()
    streak_days = serializers.IntegerField()
    law_progress = UserLearningProgressSerializer(many=True)


class MarkClauseReadSerializer(serializers.Serializer):
    """Used to mark a clause as read and optionally log time spent."""
    clause_id = serializers.IntegerField()
    time_spent_minutes = serializers.IntegerField(min_value=0, default=0)


class QuizAttemptSerializer(serializers.ModelSerializer):
    quiz_question = serializers.CharField(source='quiz.question', read_only=True)
    law_number = serializers.IntegerField(source='quiz.law.number', read_only=True)
    quiz_type = serializers.CharField(source='quiz.quiz_type', read_only=True)
    correct_answer = serializers.JSONField(source='quiz.correct_answer', read_only=True)
    explanation = serializers.CharField(source='quiz.explanation', read_only=True)

    class Meta:
        model = QuizAttempt
        fields = [
            'id', 'quiz', 'quiz_question', 'quiz_type', 'law_number',
            'user_answer', 'correct_answer', 'explanation',
            'is_correct', 'time_taken_seconds', 'points_earned',
            'bookmarked', 'reviewed', 'attempted_at',
        ]
        read_only_fields = [
            'id', 'quiz_question', 'quiz_type', 'law_number',
            'correct_answer', 'explanation', 'is_correct',
            'time_taken_seconds', 'points_earned', 'attempted_at',
        ]


class DrillAttemptSerializer(serializers.ModelSerializer):
    drill_title = serializers.CharField(source='drill.title', read_only=True)
    drill_type = serializers.CharField(source='drill.drill_type', read_only=True)
    law_number = serializers.IntegerField(source='drill.law.number', read_only=True)

    class Meta:
        model = DrillAttempt
        fields = [
            'id', 'drill', 'drill_title', 'drill_type', 'law_number',
            'user_answers', 'score', 'time_taken_seconds', 'completed_at',
        ]
        read_only_fields = ['id', 'drill_title', 'drill_type', 'law_number', 'completed_at']