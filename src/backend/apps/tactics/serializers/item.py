"""
Serializers for tactics board frame items

Validates player markers, balls, arrows, lines, zones, and text items before they are stored on a tactics board frame
"""

from apps.clubs.models import ClubPlayer
from apps.tactics.models import TacticsBoardItem
from rest_framework import serializers


# ---------------------------------------------------------------------------
# Item validation configuration
# ---------------------------------------------------------------------------

ARROW_LIKE_ITEM_TYPES = {
    TacticsBoardItem.ItemType.ARROW,
    TacticsBoardItem.ItemType.LINE,
}
ZONE_ITEM_TYPES = {
    TacticsBoardItem.ItemType.ZONE,
}
LABEL_OPTIONAL_ITEM_TYPES = {
    TacticsBoardItem.ItemType.PLAYER,
    TacticsBoardItem.ItemType.ARROW,
}
LABEL_REQUIRED_ITEM_TYPES = {
    TacticsBoardItem.ItemType.TEXT,
}
PLAYER_ONLY_FIELDS = {
    'linked_player',
    'shirt_number',
    'position_label',
}
ARROW_ONLY_FIELDS = {
    'end_x',
    'end_y',
}
ZONE_ONLY_FIELDS = {
    'width',
    'height',
}
TEXTUAL_FIELDS = {
    'label',
}
TEAM_SIDE_RULES = {
    TacticsBoardItem.ItemType.PLAYER: {
        TacticsBoardItem.TeamSide.HOME,
        TacticsBoardItem.TeamSide.AWAY,
    },
    TacticsBoardItem.ItemType.BALL: {
        TacticsBoardItem.TeamSide.NEUTRAL,
    },
    TacticsBoardItem.ItemType.ARROW: {
        TacticsBoardItem.TeamSide.HOME,
        TacticsBoardItem.TeamSide.AWAY,
        TacticsBoardItem.TeamSide.NEUTRAL,
    },
    TacticsBoardItem.ItemType.LINE: {
        TacticsBoardItem.TeamSide.HOME,
        TacticsBoardItem.TeamSide.AWAY,
        TacticsBoardItem.TeamSide.NEUTRAL,
    },
    TacticsBoardItem.ItemType.ZONE: {
        TacticsBoardItem.TeamSide.HOME,
        TacticsBoardItem.TeamSide.AWAY,
        TacticsBoardItem.TeamSide.NEUTRAL,
    },
    TacticsBoardItem.ItemType.TEXT: {
        TacticsBoardItem.TeamSide.NEUTRAL,
    },
}


# ---------------------------------------------------------------------------
# Item serializers
# ---------------------------------------------------------------------------

# Serializer for a compact linked club player summary
class LinkedClubPlayerSummarySerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = ClubPlayer
        fields = [
            'id',
            'display_name',
            'full_name',
            'squad_number',
            'primary_position',
            'photo',
        ]


# Serializer for reading tactics board items
class TacticsBoardItemSerializer(serializers.ModelSerializer):
    player_summary = serializers.SerializerMethodField()

    class Meta:
        model = TacticsBoardItem
        fields = [
            'id',
            'frame',
            'item_type',
            'team_side',
            'stable_id',
            'linked_player',
            'label',
            'shirt_number',
            'position_label',
            'x',
            'y',
            'end_x',
            'end_y',
            'width',
            'height',
            'rotation',
            'z_index',
            'style',
            'player_summary',
        ]

    # Return a compact linked player summary when the item is linked to a club player
    def get_player_summary(self, obj):
        if not obj.linked_player:
            return None
        return LinkedClubPlayerSummarySerializer(obj.linked_player).data


# Serializer for creating and updating tactics board items
class TacticsBoardItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TacticsBoardItem
        fields = [
            'id',
            'frame',
            'item_type',
            'team_side',
            'stable_id',
            'linked_player',
            'label',
            'shirt_number',
            'position_label',
            'x',
            'y',
            'end_x',
            'end_y',
            'width',
            'height',
            'rotation',
            'z_index',
            'style',
        ]
        read_only_fields = ['id', 'stable_id']
        extra_kwargs = {
            'frame': {'required': False},
        }

    # Validate item-specific required fields and remove fields not used by the selected item type
    def validate(self, attrs):
        attrs = super().validate(attrs)

        instance = getattr(self, 'instance', None)

        item_type = attrs.get('item_type', getattr(instance, 'item_type', None))
        team_side = attrs.get('team_side', getattr(instance, 'team_side', None))

        if not item_type:
            raise serializers.ValidationError({
                'item_type': 'This field is required.',
            })

        if not team_side:
            raise serializers.ValidationError({
                'team_side': 'This field is required.',
            })

        effective_values = {
            'x': attrs.get('x', getattr(instance, 'x', None)),
            'y': attrs.get('y', getattr(instance, 'y', None)),
            'end_x': attrs.get('end_x', getattr(instance, 'end_x', None)),
            'end_y': attrs.get('end_y', getattr(instance, 'end_y', None)),
            'width': attrs.get('width', getattr(instance, 'width', None)),
            'height': attrs.get('height', getattr(instance, 'height', None)),
            'label': attrs.get('label', getattr(instance, 'label', '')),
        }

        allowed_team_sides = TEAM_SIDE_RULES[item_type]
        if team_side not in allowed_team_sides:
            raise serializers.ValidationError({
                'team_side': (
                    f"'{team_side}' is not valid for item type '{item_type}'."
                ),
            })

        errors = {}

        if effective_values['x'] is None:
            errors['x'] = 'This field is required.'
        if effective_values['y'] is None:
            errors['y'] = 'This field is required.'

        if item_type in ARROW_LIKE_ITEM_TYPES:
            if effective_values['end_x'] is None:
                errors['end_x'] = 'This field is required.'
            if effective_values['end_y'] is None:
                errors['end_y'] = 'This field is required.'

        if item_type in ZONE_ITEM_TYPES:
            if effective_values['width'] is None:
                errors['width'] = 'This field is required.'
            if effective_values['height'] is None:
                errors['height'] = 'This field is required.'

        if item_type in LABEL_REQUIRED_ITEM_TYPES:
            label_value = effective_values['label']
            if label_value is None or not str(label_value).strip():
                errors['label'] = 'This field is required.'

        if errors:
            raise serializers.ValidationError(errors)

        if item_type not in ARROW_LIKE_ITEM_TYPES:
            attrs.pop('end_x', None)
            attrs.pop('end_y', None)

        if item_type not in ZONE_ITEM_TYPES:
            attrs.pop('width', None)
            attrs.pop('height', None)

        if item_type != TacticsBoardItem.ItemType.PLAYER:
            for field_name in PLAYER_ONLY_FIELDS:
                attrs.pop(field_name, None)

        if (
            item_type not in LABEL_OPTIONAL_ITEM_TYPES
            and item_type not in LABEL_REQUIRED_ITEM_TYPES
        ):
            attrs.pop('label', None)

        self._validate_nested_context(attrs)

        return attrs

    # Validate that the item belongs to the nested frame and board context
    def _validate_nested_context(self, attrs):
        board = self.context.get('board')
        frame = self.context.get('frame')
        serializer_frame = attrs.get('frame')
        instance = getattr(self, 'instance', None)

        resolved_frame = serializer_frame or frame or getattr(instance, 'frame', None)

        if frame is not None and serializer_frame is not None and serializer_frame != frame:
            raise serializers.ValidationError({
                'frame': 'Frame does not match the nested route context.',
            })

        if resolved_frame is None:
            raise serializers.ValidationError({
                'frame': 'Frame context is required.',
            })

        if board is not None and resolved_frame is not None and resolved_frame.board_id != board.id:
            raise serializers.ValidationError({
                'frame': 'Frame does not belong to the specified board.',
            })