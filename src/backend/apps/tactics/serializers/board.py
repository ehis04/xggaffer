from apps.tactics.models import TacticsBoard
from rest_framework import serializers


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

    def validate_linked_teamsheet(self, value):
        if value is None:
            return value

        club = self.context.get('club')
        if club is not None and value.club_id != club.id:
            raise serializers.ValidationError(
                'Linked teamsheet must belong to the same club.'
            )

        return value


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

    def get_frames(self, obj):
        from apps.tactics.serializers.frame import TacticsBoardFrameSerializer

        frames = getattr(obj, 'prefetched_frames', None)
        if frames is None:
            frames = obj.frames.order_by('frame_index', 'id')

        return TacticsBoardFrameSerializer(frames, many=True).data


class TacticsBoardTrashActionSerializer(serializers.Serializer):
    pass