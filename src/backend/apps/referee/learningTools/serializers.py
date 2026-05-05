from rest_framework import serializers

# Validates a user's selected option for a scenario item
class SubmitScenarioSerializer(serializers.Serializer):
    item_id     = serializers.IntegerField()
    selected_id = serializers.CharField(max_length=10)

# Validates a user's true or false answers for a drill item
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