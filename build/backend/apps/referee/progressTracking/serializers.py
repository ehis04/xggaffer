from rest_framework import serializers

from .models import UserCourseProgress, StudyStreak, PerformanceScore


class LawCourseSerializer(serializers.ModelSerializer):
    law_number          = serializers.IntegerField(source='law.law_number')
    title               = serializers.CharField(source='law.title')
    description         = serializers.CharField(source='law.description')
    progress_percentage = serializers.IntegerField()

    class Meta:
        model  = UserCourseProgress
        fields = [
            'law_number', 'title', 'description', 'status',
            'progress_percentage', 'clauses_read', 'total_clauses',
        ]


class ActiveCourseSerializer(serializers.ModelSerializer):
    law_number          = serializers.IntegerField(source='law.law_number')
    title               = serializers.CharField(source='law.title')
    progress_percentage = serializers.IntegerField()

    class Meta:
        model  = UserCourseProgress
        fields = [
            'law_number', 'title', 'progress_percentage',
            'clauses_read', 'total_clauses',
        ]


class StreakSerializer(serializers.ModelSerializer):
    class Meta:
        model  = StudyStreak
        fields = ['current_streak', 'studied_dates']


class PerformanceSerializer(serializers.ModelSerializer):
    quizzes   = serializers.SerializerMethodField()
    scenarios = serializers.SerializerMethodField()
    drills    = serializers.SerializerMethodField()
    clauses   = serializers.SerializerMethodField()

    class Meta:
        model  = PerformanceScore
        fields = ['overall_score', 'quizzes', 'scenarios', 'drills', 'clauses']

    def _wrap(self, val):
        return {'score': val} if val is not None else None

    def get_quizzes(self, obj):   return self._wrap(obj.quiz_score)
    def get_scenarios(self, obj): return self._wrap(obj.scenario_score)
    def get_drills(self, obj):    return self._wrap(obj.drill_score)
    def get_clauses(self, obj):   return self._wrap(obj.clause_score)


class MarkItemCompleteSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()