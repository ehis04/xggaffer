"""
Action serializers for tactics board custom endpoints

Validates request payloads for teamsheet imports, opponent formations, frame duplication, and board duplication
"""

from rest_framework import serializers

from apps.teamsheets.formations import get_formation_template


# Serializer for creating a tactics board from a teamsheet
class FromTeamsheetBoardActionSerializer(serializers.Serializer):
    teamsheet_id = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=120)


# Serializer for adding an opponent formation to a board
class AddOpponentFormationActionSerializer(serializers.Serializer):
    formation = serializers.CharField(max_length=10)

    # Validate that the requested formation exists
    def validate_formation(self, value):
        formation = value.strip()
        if not get_formation_template(formation):
            raise serializers.ValidationError('Invalid formation code.')
        return formation


# Serializer for duplicating a tactics board frame
class DuplicateFrameActionSerializer(serializers.Serializer):
    pass


# Serializer for duplicating a full tactics board
class DuplicateBoardActionSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)