"""
Serializers for tactics board list, write, detail, and trash actions

Controls how tactics boards are created, updated, listed, returned with frames, and handled by trash endpoints
"""

from apps.tactics.models import TacticsBoard
from rest_framework import serializers


# ---------------------------------------------------------------------------
# Board serializers
# ---------------------------------------------------------------------------

# Serializer for compact tactics board list responses
class TacticsBoardListSerializer(serializers.ModelSerializer):
    trashed_by = serializers.IntegerField(source='trashed_by_id', read_only=True)

    class Meta:
        model = TacticsBoard
        fields = [
            'id',
            'club',
            'created_by',
            'title',
            'description',
            'board_type',
            'pitch_orientation',
            'linked_teamsheet',
            'home_formation',
            'away_formation',
            'home_colour',
            'away_colour',
            'is_template',
            'is_trashed',
            'trashed_at',
            'trash_expires_at',
            'trashed_by',
            'created_at',
            'updated_at',
        ]


# Serializer for creating and updating tactics boards
class TacticsBoardWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TacticsBoard
        fields = [
            'id',
            'club',
            'created_by',
            'title',
            'description',
            'board_type',
            'pitch_orientation',
            'linked_teamsheet',
            'home_formation',
            'away_formation',
            'home_colour',
            'away_colour',
            'is_template',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'club',
            'created_by',
            'created_at',
            'updated_at',
        ]

    # Validate that linked teamsheets belong to the active club
    def validate_linked_teamsheet(self, value):
        if value is None:
            return value

        club = self.context.get('club')
        if club is not None and value.club_id != club.id:
            raise serializers.ValidationError(
                'Linked teamsheet must belong to the same club.'
            )

        return value


# Serializer for detailed tactics board responses with frames
class TacticsBoardDetailSerializer(serializers.ModelSerializer):
    frames = serializers.SerializerMethodField()
    trashed_by = serializers.IntegerField(source='trashed_by_id', read_only=True)

    class Meta:
        model = TacticsBoard
        fields = [
            'id',
            'club',
            'created_by',
            'title',
            'description',
            'board_type',
            'pitch_orientation',
            'linked_teamsheet',
            'home_formation',
            'away_formation',
            'home_colour',
            'away_colour',
            'is_template',
            'is_trashed',
            'trashed_at',
            'trash_expires_at',
            'trashed_by',
            'created_at',
            'updated_at',
            'frames',
        ]

    # Return prefetched frames where available to avoid extra queries
    def get_frames(self, obj):
        from apps.tactics.serializers.frame import TacticsBoardFrameSerializer

        frames = getattr(obj, 'prefetched_frames', None)
        if frames is None:
            frames = obj.frames.order_by('frame_index', 'id')

        return TacticsBoardFrameSerializer(frames, many=True).data


# Serializer for tactics board trash actions
class TacticsBoardTrashActionSerializer(serializers.Serializer):
    pass