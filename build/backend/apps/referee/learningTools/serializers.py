from rest_framework import serializers
from .models import Quiz, QuizQuestion, MCQOption, TrueFalseAnswer, QuickDrill

class MCQOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCQOption
        fields = ['id', 'answer', 'order']


class MCQOptionResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCQOption
        fields = ['id', 'answer', 'order', 'is_correct']

class QuizQuestionSerializer(serializers.ModelSerializer):
    mcq_options = MCQOptionSerializer(many=True, read_only=True)
    is_true_false = serializers.SerializerMethodField()

    class Meta:
        model = QuizQuestion
        fields = [
            'id', 'question_type', 'question',
            'mcq_options', 'is_true_false',
            'points',
        ]

    def get_is_true_false(self, obj):
        return obj.question_type == 'TF'


class QuizQuestionResultSerializer(serializers.ModelSerializer):
    mcq_options = MCQOptionResultSerializer(many=True, read_only=True)
    correct_tf_answer = serializers.SerializerMethodField()
    is_correct = serializers.SerializerMethodField()
    user_answer = serializers.SerializerMethodField()

    class Meta:
        model = QuizQuestion
        fields = [
            'id', 'question_type', 'question', 'explanation',
            'mcq_options', 'correct_tf_answer',
            'is_correct', 'user_answer', 'points',
        ]

    def get_correct_tf_answer(self, obj):
        if obj.question_type == 'TF':
            tf = getattr(obj, 'tf_answer', None)
            return tf.correct_answer if tf else None
        return None

    def get_is_correct(self, obj):
        answers = self.context.get('graded_answers', {})
        return answers.get(obj.id, {}).get('is_correct', False)

    def get_user_answer(self, obj):
        answers = self.context.get('graded_answers', {})
        return answers.get(obj.id, {}).get('user_answer')

class QuizListSerializer(serializers.ModelSerializer):
    law_number = serializers.IntegerField(source='law.number', read_only=True)
    law_title = serializers.CharField(source='law.title', read_only=True)
    clause_heading = serializers.CharField(source='clause.heading', read_only=True, allow_null=True)
    question_count = serializers.IntegerField(read_only=True)
    total_points = serializers.IntegerField(read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'id', 'title', 'description', 'difficulty',
            'law_number', 'law_title', 'clause_heading',
            'question_count', 'total_points', 'is_active',
        ]


class QuizDetailSerializer(serializers.ModelSerializer):
    law_number = serializers.IntegerField(source='law.number', read_only=True)
    law_title = serializers.CharField(source='law.title', read_only=True)
    clause_heading = serializers.CharField(source='clause.heading', read_only=True, allow_null=True)
    questions = QuizQuestionSerializer(many=True, read_only=True)
    total_points = serializers.IntegerField(read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'id', 'title', 'description', 'difficulty',
            'law_number', 'law_title', 'clause_heading',
            'questions', 'total_points', 'is_active',
            'created_at', 'updated_at',
        ]

class QuizSubmitSerializer(serializers.Serializer):
    answers = serializers.DictField(
        child=serializers.JSONField(),
        help_text="Map of question_id (str) to the user's answer.",
    )
    time_taken_seconds = serializers.IntegerField(min_value=0)

    def validate_answers(self, value):
        if not value:
            raise serializers.ValidationError("answers cannot be empty.")
        return value


class QuizResultSerializer(serializers.Serializer):
    score = serializers.IntegerField()
    max_score = serializers.IntegerField()
    percentage = serializers.FloatField()
    points_earned = serializers.IntegerField()
    questions_correct = serializers.IntegerField()
    questions_total = serializers.IntegerField()
    question_results = QuizQuestionResultSerializer(many=True)
    attempt_id = serializers.IntegerField()

class QuickDrillListSerializer(serializers.ModelSerializer):
    law_number = serializers.IntegerField(source='law.number', read_only=True)
    law_title = serializers.CharField(source='law.title', read_only=True)

    class Meta:
        model = QuickDrill
        fields = [
            'id', 'title', 'drill_type', 'time_limit_seconds',
            'points', 'law_number', 'law_title', 'is_active',
        ]


class QuickDrillDetailSerializer(serializers.ModelSerializer):
    law_number = serializers.IntegerField(source='law.number', read_only=True)
    law_title = serializers.CharField(source='law.title', read_only=True)

    class Meta:
        model = QuickDrill
        fields = [
            'id', 'title', 'drill_type', 'drill_data',
            'time_limit_seconds', 'points',
            'law_number', 'law_title',
        ]


class DrillSubmitSerializer(serializers.Serializer):
    user_answers = serializers.JSONField()
    time_taken_seconds = serializers.IntegerField(min_value=0)


class DrillResultSerializer(serializers.Serializer):
    score = serializers.IntegerField()
    max_score = serializers.IntegerField()
    percentage = serializers.FloatField()
    attempt_id = serializers.IntegerField()