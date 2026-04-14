from rest_framework import serializers
from .models import CourseSection, CourseItem


class CourseItemSerializer(serializers.ModelSerializer):
    type     = serializers.CharField(source='item_type')
    status   = serializers.SerializerMethodField()
    clause   = serializers.SerializerMethodField()
    scenario = serializers.SerializerMethodField()
    drill    = serializers.SerializerMethodField()

    qc  = serializers.IntegerField(source='quiz_question_count', allow_null=True)
    qid = serializers.CharField(source='quiz_id', allow_blank=True)

    class Meta:
        model  = CourseItem
        fields = [
            'id', 'type', 'title', 'status', 'mins',
            'clause', 'scenario', 'drill', 'qc', 'qid',
        ]

    def get_status(self, obj) -> str:
        completed_ids  = self.context.get('completed_ids', set())
        active_item_id = self.context.get('active_item_id')
        if obj.pk in completed_ids:
            return 'completed'
        if obj.pk == active_item_id:
            return 'active'
        return 'locked'

    def get_clause(self, obj):
        if obj.item_type != 'clause':
            return None
        return {
            'n':   obj.clause_number,
            'txt': obj.clause_text,
        }

    def get_scenario(self, obj):
        if obj.item_type != 'scenario':
            return None
        return {
            'sit':  obj.scenario_situation,
            'opts': obj.scenario_options,
            'cor':  obj.scenario_correct_id,
            'expl': obj.scenario_explanation,
        }

    def get_drill(self, obj):
        if obj.item_type != 'drill':
            return None
        return {
            'desc':  obj.drill_description,
            'items': obj.drill_items,
        }


class CourseSectionSerializer(serializers.ModelSerializer):
    items = CourseItemSerializer(many=True)

    class Meta:
        model  = CourseSection
        fields = ['id', 'title', 'items']

    def to_representation(self, instance):
        self.fields['items'].context.update(self.context)
        return super().to_representation(instance)