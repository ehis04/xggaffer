from rest_framework import serializers
from .models import LawEdition, Law, LawClause, LawChange, KeyConcept, ParsingJob


class KeyConceptSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeyConcept
        fields = ['id', 'term', 'definition', 'example', 'is_critical']


class LawClauseSerializer(serializers.ModelSerializer):
    key_concepts = KeyConceptSerializer(many=True, read_only=True)

    class Meta:
        model = LawClause
        fields = [
            'id', 'clause_id', 'heading', 'content',
            'examples', 'notes', 'bullet_points',
            'diagram_url', 'video_url', 'order',
            'key_concepts',
        ]


class LawListSerializer(serializers.ModelSerializer):
    clause_count = serializers.IntegerField(source='clauses.count', read_only=True)
    quiz_count = serializers.SerializerMethodField()

    class Meta:
        model = Law
        fields = [
            'id', 'number', 'title', 'description', 'icon',
            'difficulty_level', 'estimated_time_minutes',
            'clause_count', 'quiz_count',
        ]

    def get_quiz_count(self, obj):
        return obj.quizzes.filter(is_active=True).count()


class LawDetailSerializer(serializers.ModelSerializer):
    clauses = LawClauseSerializer(many=True, read_only=True)
    key_concepts = KeyConceptSerializer(many=True, read_only=True)
    quiz_count = serializers.SerializerMethodField()
    scenario_count = serializers.SerializerMethodField()
    drill_count = serializers.SerializerMethodField()

    class Meta:
        model = Law
        fields = [
            'id', 'number', 'title', 'description', 'icon',
            'difficulty_level', 'estimated_time_minutes',
            'full_content', 'clauses', 'key_concepts',
            'quiz_count', 'scenario_count', 'drill_count',
            'created_at', 'updated_at',
        ]

    def get_quiz_count(self, obj):
        return obj.quizzes.filter(is_active=True).count()

    def get_scenario_count(self, obj):
        return obj.scenarios.filter(is_active=True).count()

    def get_drill_count(self, obj):
        return obj.drills.filter(is_active=True).count()


class LawEditionListSerializer(serializers.ModelSerializer):
    law_count = serializers.IntegerField(source='laws.count', read_only=True)

    class Meta:
        model = LawEdition
        fields = ['id', 'year', 'publication_date', 'is_current', 'law_count']


class LawEditionDetailSerializer(serializers.ModelSerializer):
    laws = LawListSerializer(many=True, read_only=True)
    law_count = serializers.IntegerField(source='laws.count', read_only=True)

    class Meta:
        model = LawEdition
        fields = ['id', 'year', 'publication_date', 'is_current', 'pdf_url', 'law_count', 'laws', 'created_at']


class LawChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LawChange
        fields = ['id', 'law_number', 'clause_id', 'change_type', 'description', 'old_content', 'new_content']


class ParsingJobSerializer(serializers.ModelSerializer):
    edition_year = serializers.CharField(source='edition.year', read_only=True)

    class Meta:
        model = ParsingJob
        fields = ['id', 'edition', 'edition_year', 'status', 'started_at', 'completed_at', 'error_message', 'created_at']
        read_only_fields = ['id', 'started_at', 'completed_at', 'error_message', 'created_at']


class KeyConceptDetailSerializer(serializers.ModelSerializer):
    law_number = serializers.IntegerField(source='law.number', read_only=True)
    law_title = serializers.CharField(source='law.title', read_only=True)
    clause_heading = serializers.CharField(source='clause.heading', read_only=True, allow_null=True)

    class Meta:
        model = KeyConcept
        fields = ['id', 'term', 'definition', 'example', 'is_critical', 'law_number', 'law_title', 'clause_heading']