from django.db import transaction
from rest_framework import serializers

from apps.clubs.models import ClubPlayer
from common.constants import Position
from .formations import (
    get_available_formations,
    get_formation_template,
)
from .models import Teamsheet, TeamsheetPlayer


class ChoiceSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class FormationTemplateSerializer(serializers.Serializer):
    slot = serializers.IntegerField()
    position = serializers.CharField()
    x = serializers.FloatField()
    y = serializers.FloatField()


class FormationDetailSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()
    positions = FormationTemplateSerializer(many=True)


class TeamsheetPlayerReadSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    display_number = serializers.IntegerField(read_only=True, allow_null=True)
    display_photo_url = serializers.CharField(read_only=True, allow_null=True)
    is_linked = serializers.BooleanField(read_only=True)
    club_player_name = serializers.SerializerMethodField()

    class Meta:
        model = TeamsheetPlayer
        fields = [
            'id',
            'slot_number',
            'is_substitute',
            'club_player',
            'club_player_name',
            'custom_name',
            'custom_number',
            'display_name',
            'display_number',
            'display_photo_url',
            'is_linked',
            'position_label',
            'position_x',
            'position_y',
            'created_at',
            'updated_at',
        ]

    def get_club_player_name(self, obj) -> str | None:
        if obj.club_player:
            return obj.club_player.full_name
        return None


class TeamsheetPlayerWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamsheetPlayer
        fields = [
            'id',
            'teamsheet',
            'club_player',
            'custom_name',
            'custom_number',
            'position_label',
            'position_x',
            'position_y',
            'slot_number',
            'is_substitute',
        ]

    def validate(self, attrs):
        club_player = attrs.get('club_player')
        custom_name = attrs.get('custom_name', '').strip()
        teamsheet = attrs.get('teamsheet') or getattr(self.instance, 'teamsheet', None)

        if not club_player and not custom_name:
            raise serializers.ValidationError(
                "Either 'club_player' or 'custom_name' must be provided."
            )

        if club_player and teamsheet and club_player.club_id != teamsheet.club_id:
            raise serializers.ValidationError({
                'club_player': 'Player must belong to the same club as the teamsheet.'
            })

        return attrs

    def validate_position_x(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError('Position X must be between 0 and 100.')
        return value

    def validate_position_y(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError('Position Y must be between 0 and 100.')
        return value

class TeamsheetPlayerPositionUpdateSerializer(serializers.Serializer):
    position_x = serializers.FloatField(min_value=0, max_value=100)
    position_y = serializers.FloatField(min_value=0, max_value=100)
    position_label = serializers.ChoiceField(choices=Position.choices, required=False)


class TeamsheetReadSerializer(serializers.ModelSerializer):
    players = TeamsheetPlayerReadSerializer(many=True, read_only=True)
    starter_count = serializers.IntegerField(read_only=True)
    substitute_count = serializers.IntegerField(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)
    formation_display = serializers.CharField(
        source='get_formation_display',
        read_only=True,
    )
    club_name = serializers.SerializerMethodField()
    created_by_username = serializers.SerializerMethodField()
    trashed_by = serializers.IntegerField(source='trashed_by_id', read_only=True)

    class Meta:
        model = Teamsheet
        fields = [
            'id',
            'title',
            'club',
            'club_name',
            'created_by',
            'created_by_username',
            'formation',
            'formation_display',
            'match_date',
            'opponent',
            'notes',
            'is_template',
            'is_complete',
            'starter_count',
            'substitute_count',
            'players',
            'is_trashed',
            'trashed_at',
            'trash_expires_at',
            'trashed_by',
            'created_at',
            'updated_at',
        ]

    def get_club_name(self, obj) -> str | None:
        return obj.club.name if obj.club else None

    def get_created_by_username(self, obj) -> str | None:
        return obj.created_by.email if obj.created_by else None

class TeamsheetWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teamsheet
        fields = [
            'id',
            'club',
            'title',
            'formation',
            'match_date',
            'opponent',
            'notes',
            'is_template',
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        match_date = attrs.get('match_date')
        opponent = attrs.get('opponent', '').strip()

        if match_date and not opponent:
            raise serializers.ValidationError({
                'opponent': "Opponent is required when match date is set."
            })

        return attrs

    def create(self, validated_data):
        initialize = self.context.get('initialize_from_template', True)
        teamsheet = super().create(validated_data)

        if initialize and teamsheet.formation != 'custom':
            teamsheet.initialize_from_template()

        return teamsheet

class TeamsheetListSerializer(serializers.ModelSerializer):
    formation_display = serializers.CharField(
        source='get_formation_display',
        read_only=True,
    )
    starter_count = serializers.IntegerField(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)
    club_name = serializers.SerializerMethodField()
    trashed_by = serializers.IntegerField(source='trashed_by_id', read_only=True)

    class Meta:
        model = Teamsheet
        fields = [
            'id',
            'title',
            'club',
            'club_name',
            'formation',
            'formation_display',
            'match_date',
            'opponent',
            'is_template',
            'is_complete',
            'starter_count',
            'is_trashed',
            'trashed_at',
            'trash_expires_at',
            'trashed_by',
            'created_at',
            'updated_at',
        ]

    def get_club_name(self, obj) -> str | None:
        return obj.club.name if obj.club else None

class BulkPlayerPositionUpdateSerializer(serializers.Serializer):
    class PlayerPositionItem(serializers.Serializer):
        id = serializers.IntegerField()
        position_x = serializers.FloatField(min_value=0, max_value=100)
        position_y = serializers.FloatField(min_value=0, max_value=100)
        position_label = serializers.ChoiceField(
            choices=Position.choices,
            required=False
        )

    updates = PlayerPositionItem(many=True)

    def validate_updates(self, value):
        ids = [item['id'] for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Duplicate player IDs in updates.")
        return value


class TeamsheetDuplicateSerializer(serializers.Serializer):
    new_title = serializers.CharField(max_length=100)
    include_players = serializers.BooleanField(default=True)

class TeamsheetTrashActionSerializer(serializers.Serializer):
    pass

class PlayerSlotAssignmentSerializer(serializers.Serializer):
    slot_number = serializers.IntegerField(min_value=1, max_value=18)
    club_player_id = serializers.IntegerField(required=False, allow_null=True)
    custom_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    custom_number = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=99)
    position_label = serializers.ChoiceField(choices=Position.choices)
    position_x = serializers.FloatField(min_value=0, max_value=100)
    position_y = serializers.FloatField(min_value=0, max_value=100)
    is_substitute = serializers.BooleanField(default=False)


class CreateTeamsheetWithPlayersSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100)
    formation = serializers.CharField(max_length=10)
    match_date = serializers.DateField(required=False, allow_null=True)
    opponent = serializers.CharField(required=False, allow_blank=True, max_length=100)
    notes = serializers.CharField(required=False, allow_blank=True)
    is_template = serializers.BooleanField(default=False)
    player_assignments = PlayerSlotAssignmentSerializer(many=True, required=False)

    def validate_formation(self, value):
        available = [f[0] for f in get_available_formations()]
        if value not in available and value != 'custom':
            raise serializers.ValidationError(
                f"Invalid formation. Choose from: {', '.join(available)}"
            )
        return value

    def validate(self, attrs):
        match_date = attrs.get('match_date')
        opponent = attrs.get('opponent', '').strip()

        if match_date and not opponent:
            raise serializers.ValidationError({
                'opponent': 'Opponent is required when match date is set.'
            })

        player_assignments = attrs.get('player_assignments', [])
        slot_numbers = [p['slot_number'] for p in player_assignments]
        if len(slot_numbers) != len(set(slot_numbers)):
            raise serializers.ValidationError({
                'player_assignments': 'Duplicate slot numbers found.'
            })

        for assignment in player_assignments:
            has_club_player = assignment.get('club_player_id')
            has_custom = assignment.get('custom_name', '').strip()
            if not has_club_player and not has_custom:
                raise serializers.ValidationError({
                    'player_assignments': (
                        f"Slot {assignment['slot_number']}: "
                        "Either club_player_id or custom_name is required."
                    )
                })

        return attrs

    def create(self, validated_data):
        from apps.clubs.models import ClubPlayer

        player_assignments = validated_data.pop('player_assignments', [])
        club = self.context['club']
        user = self.context.get('user')

        with transaction.atomic():
            teamsheet = Teamsheet.objects.create(
                club=club,
                created_by=user,
                **validated_data,
            )

            if not player_assignments and validated_data.get('formation') != 'custom':
                teamsheet.initialize_from_template()
                return teamsheet

            for assignment in player_assignments:
                club_player = None
                club_player_id = assignment.pop('club_player_id', None)

                if club_player_id:
                    try:
                        club_player = ClubPlayer.objects.get(
                            id=club_player_id,
                            club=club,
                        )
                    except ClubPlayer.DoesNotExist:
                        raise serializers.ValidationError({
                            'player_assignments': f'Club player {club_player_id} not found.'
                        })

                TeamsheetPlayer.objects.create(
                    teamsheet=teamsheet,
                    club_player=club_player,
                    **assignment,
                )

        return teamsheet

def get_pitch_position_choices():
    return [
        {"value": value, "label": label}
        for value, label in Position.choices
    ]


def get_formation_choices():
    return [
        {"value": value, "label": label}
        for value, label in get_available_formations()
    ]


def get_formation_with_templates():
    result = []
    for value, label in get_available_formations():
        template = get_formation_template(value)
        result.append({
            "value": value,
            "label": label,
            "positions": template,
        })
    return result