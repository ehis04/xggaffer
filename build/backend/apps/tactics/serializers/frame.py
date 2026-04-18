from apps.tactics.models import TacticsBoardFrame
from rest_framework import serializers


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

    def get_items(self, obj):
        from apps.tactics.serializers.item import TacticsBoardItemSerializer

        items = getattr(obj, 'prefetched_items', None)
        if items is None:
            items = obj.items.select_related('linked_player').order_by('z_index', 'id')

        return TacticsBoardItemSerializer(items, many=True).data


class TacticsBoardFrameWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TacticsBoardFrame
        fields = [
            'id',
            'board',
            'frame_index',
            'label',
            'duration_ms',
            'notes',
        ]
        read_only_fields = ['id', 'frame_index']
        extra_kwargs = {
            'board': {'required': False},
        }

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