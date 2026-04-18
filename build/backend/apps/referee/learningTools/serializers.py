from rest_framework import serializers


class SubmitScenarioSerializer(serializers.Serializer):
    item_id     = serializers.IntegerField()
    selected_id = serializers.CharField(max_length=10)


class SubmitDrillSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    answers = serializers.DictField(
        child=serializers.ChoiceField(choices=['true', 'false'])
    )

    def validate_answers(self, value):
        for key in value:
            if not key.isdigit():
                raise serializers.ValidationError(
                    f"Answer keys must be non-negative integer strings, got '{key}'."
                )
        return value