from rest_framework import serializers

from apps.teamsheets.formations import get_formation_template


class FromTeamsheetBoardActionSerializer(serializers.Serializer):
    teamsheet_id = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=120)


class AddOpponentFormationActionSerializer(serializers.Serializer):
    formation = serializers.CharField(max_length=10)

    def validate_formation(self, value):
        formation = value.strip()
        if not get_formation_template(formation):
            raise serializers.ValidationError('Invalid formation code.')
        return formation


class DuplicateFrameActionSerializer(serializers.Serializer):
    pass


class DuplicateBoardActionSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)