"""
Serializers for tactics board frames

Returns frames with nested items and validates frame creation, frame updates, and optional item copying from another frame
"""

from apps.tactics.models import TacticsBoardFrame
from rest_framework import serializers


# Serializer for reading tactics board frames with their items
class TacticsBoardFrameSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = TacticsBoardFrame
        fields = [
            'id',
            'board',
            'frame_index',
            'label',
            'duration_ms',
            'notes',
            'items',
        ]

    # Return prefetched frame items where available to avoid extra queries
    def get_items(self, obj):
        from apps.tactics.serializers.item import TacticsBoardItemSerializer

        items = getattr(obj, 'prefetched_items', None)
        if items is None:
            items = obj.items.select_related('linked_player').order_by('z_index', 'id')

        return TacticsBoardItemSerializer(items, many=True).data


# Serializer for creating and updating tactics board frames
class TacticsBoardFrameWriteSerializer(serializers.ModelSerializer):
    copy_items_from_frame_index = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = TacticsBoardFrame
        fields = [
            'id',
            'board',
            'frame_index',
            'label',
            'duration_ms',
            'notes',
            'copy_items_from_frame_index',
        ]
        read_only_fields = ['id', 'frame_index']
        extra_kwargs = {
            'board': {'required': False},
        }

    # Validate that the frame belongs to the nested board context
    def validate(self, attrs):
        attrs = super().validate(attrs)

        board = self.context.get('board')
        serializer_board = attrs.get('board')
        instance = getattr(self, 'instance', None)
        resolved_board = serializer_board or board or getattr(instance, 'board', None)

        if board is not None and serializer_board is not None and serializer_board != board:
            raise serializers.ValidationError({
                'board': 'Board does not match the nested route context.',
            })

        if resolved_board is None:
            raise serializers.ValidationError({
                'board': 'Board context is required.',
            })

        return attrs

    # Validate that the source frame exists before copying items
    def validate_copy_items_from_frame_index(self, value):
        if value is None:
            return value

        board = self.context.get('board')
        if board is None:
            return value

        if not board.frames.filter(frame_index=value).exists():
            raise serializers.ValidationError(
                f'Frame index {value} does not exist on this board.'
            )

        return value

    # Create a frame through the tactics service layer
    def create(self, validated_data):
        copy_from_index = validated_data.pop('copy_items_from_frame_index', None)
        board = self.context.get('board')

        from apps.tactics.services import create_frame_for_board

        frame = create_frame_for_board(
            board=board,
            label=validated_data.get('label', ''),
            duration_ms=validated_data.get('duration_ms'),
            notes=validated_data.get('notes', ''),
            copy_items_from_frame_index=copy_from_index,
        )

        return frame