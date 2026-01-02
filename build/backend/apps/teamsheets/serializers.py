from rest_framework import serializers
from django.db import transaction
from .models import Teamsheet, TeamsheetPlayer, PitchPosition
from .formations import get_formation_template, FORMATION_TEMPLATES, get_available_formations


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
    player_profile_name = serializers.SerializerMethodField()
    
    class Meta:
        model = TeamsheetPlayer
        fields = [
            'id',
            'slot_number',
            'is_substitute',
            'player_profile',
            'player_profile_name',
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
    
    def get_player_profile_name(self, obj) -> str | None:
        if obj.player_profile:
            return obj.player_profile.full_name
        return None


class TeamsheetPlayerWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamsheetPlayer
        fields = [
            'id',
            'teamsheet',
            'player_profile',
            'custom_name',
            'custom_number',
            'position_label',
            'position_x',
            'position_y',
            'slot_number',
            'is_substitute',
        ]
    
    def validate(self, attrs):
        player_profile = attrs.get('player_profile')
        custom_name = attrs.get('custom_name', '').strip()
        teamsheet = attrs.get('teamsheet')

        if not player_profile and not custom_name:
            raise serializers.ValidationError(
                "Either 'player_profile' or 'custom_name' must be provided."
            )

        if player_profile and teamsheet:
            if player_profile.club_id != teamsheet.club_id:
                raise serializers.ValidationError({
                    'player_profile': "Player must belong to the same club as the teamsheet."
                })
        
        return attrs
    
    def validate_position_x(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError("Position X must be between 0 and 100.")
        return value
    
    def validate_position_y(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError("Position Y must be between 0 and 100.")
        return value


class TeamsheetPlayerPositionUpdateSerializer(serializers.Serializer):
    position_x = serializers.FloatField(min_value=0, max_value=100)
    position_y = serializers.FloatField(min_value=0, max_value=100)
    position_label = serializers.ChoiceField(
        choices=PitchPosition.choices,
        required=False  
    )


class TeamsheetReadSerializer(serializers.ModelSerializer):
    players = TeamsheetPlayerReadSerializer(many=True, read_only=True)
    starter_count = serializers.IntegerField(read_only=True)
    substitute_count = serializers.IntegerField(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)
    formation_display = serializers.CharField(
        source='get_formation_display',
        read_only=True
    )
    club_name = serializers.SerializerMethodField()
    created_by_username = serializers.SerializerMethodField()
    
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
            'created_at',
            'updated_at',
        ]
    
    def get_club_name(self, obj) -> str:
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
        read_only=True
    )
    starter_count = serializers.IntegerField(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)
    club_name = serializers.SerializerMethodField()
    
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
            'updated_at',
        ]
    
    def get_club_name(self, obj) -> str:
        return obj.club.name if obj.club else None


class BulkPlayerPositionUpdateSerializer(serializers.Serializer):
    
    class PlayerPositionItem(serializers.Serializer):
        id = serializers.IntegerField()
        position_x = serializers.FloatField(min_value=0, max_value=100)
        position_y = serializers.FloatField(min_value=0, max_value=100)
        position_label = serializers.ChoiceField(
            choices=PitchPosition.choices,
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


class PlayerSlotAssignmentSerializer(serializers.Serializer):
    slot_number = serializers.IntegerField(min_value=1, max_value=18)
    player_profile_id = serializers.IntegerField(required=False, allow_null=True)
    custom_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    custom_number = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=99)
    position_label = serializers.ChoiceField(choices=PitchPosition.choices)
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
            raise serializers.ValidationError(f"Invalid formation. Choose from: {', '.join(available)}")
        return value
    
    def validate(self, attrs):
        match_date = attrs.get('match_date')
        opponent = attrs.get('opponent', '').strip()
        
        if match_date and not opponent:
            raise serializers.ValidationError({
                'opponent': "Opponent is required when match date is set."
            })
        
        player_assignments = attrs.get('player_assignments', [])
        slot_numbers = [p['slot_number'] for p in player_assignments]
        if len(slot_numbers) != len(set(slot_numbers)):
            raise serializers.ValidationError({
                'player_assignments': "Duplicate slot numbers found."
            })
        
        for assignment in player_assignments:
            has_profile = assignment.get('player_profile_id')
            has_custom = assignment.get('custom_name', '').strip()
            if not has_profile and not has_custom:
                raise serializers.ValidationError({
                    'player_assignments': f"Slot {assignment['slot_number']}: Either player_profile_id or custom_name required."
                })
        
        return attrs
    
    def create(self, validated_data):
        from apps.clubs.models import PlayerProfile
        
        player_assignments = validated_data.pop('player_assignments', [])
        club = self.context['club']
        user = self.context['user']
        
        with transaction.atomic():
            teamsheet = Teamsheet.objects.create(
                club=club,
                created_by=user if user and user.is_authenticated else None,
                #created_by=user,
                title=validated_data['title'],
                formation=validated_data['formation'],
                match_date=validated_data.get('match_date'),
                opponent=validated_data.get('opponent', ''),
                notes=validated_data.get('notes', ''),
                is_template=validated_data.get('is_template', False),
            )
            
            if player_assignments:
                for assignment in player_assignments:
                    player_profile = None
                    if assignment.get('player_profile_id'):
                        try:
                            player_profile = PlayerProfile.objects.get(
                                id=assignment['player_profile_id']
                            )
                        except PlayerProfile.DoesNotExist:
                            pass
                    
                    TeamsheetPlayer.objects.create(
                        teamsheet=teamsheet,
                        slot_number=assignment['slot_number'],
                        player_profile=player_profile,
                        custom_name=assignment.get('custom_name', ''),
                        custom_number=assignment.get('custom_number'),
                        position_label=assignment['position_label'],
                        position_x=assignment['position_x'],
                        position_y=assignment['position_y'],
                        is_substitute=assignment.get('is_substitute', False),
                    )
            else:
                teamsheet.initialize_from_template()
        
        return teamsheet


def get_pitch_position_choices():
    return [
        {"value": value, "label": label}
        for value, label in PitchPosition.choices
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