from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.clubs.models import ClubPlayer

from .models import TrainingBlock, TrainingSession, TrainingSessionPlayer


def _raise_drf_validation_error(exc):
    if hasattr(exc, 'message_dict'):
        raise serializers.ValidationError(exc.message_dict)
    if hasattr(exc, 'messages'):
        raise serializers.ValidationError(exc.messages)
    raise serializers.ValidationError(str(exc))


class TrainingBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingBlock
        fields = [
            'id',
            'session',
            'order',
            'title',
            'block_type',
            'duration_minutes',
            'description',
            'coaching_points',
            'equipment',
            'player_group',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'session', 'created_at', 'updated_at']

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError('Title cannot be blank.')
        return value.strip()


class TrainingSessionPlayerSerializer(serializers.ModelSerializer):
    player_name = serializers.SerializerMethodField()
    squad_number = serializers.IntegerField(source='club_player.squad_number', read_only=True)
    primary_position = serializers.CharField(source='club_player.primary_position', read_only=True)
    is_active = serializers.BooleanField(source='club_player.is_active', read_only=True)

    class Meta:
        model = TrainingSessionPlayer
        fields = [
            'id',
            'session',
            'club_player',
            'player_name',
            'squad_number',
            'primary_position',
            'is_active',
            'attendance_status',
            'rpe_score',
            'coach_notes',
            'injury_note',
            'performance_note',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'session', 'player_name', 'squad_number', 'primary_position', 'is_active', 'created_at', 'updated_at']

    def get_player_name(self, obj):
        player = obj.club_player
        return player.display_name or player.full_name

    def validate_club_player(self, value):
        session = self.context.get('session')
        if session and value.club_id != session.club_id:
            raise serializers.ValidationError('Player must belong to this club.')
        return value


class TrainingSessionListSerializer(serializers.ModelSerializer):
    assigned_player_count = serializers.IntegerField(read_only=True)
    attended_count = serializers.IntegerField(read_only=True)
    block_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    session_type_display = serializers.CharField(source='get_session_type_display', read_only=True)
    intensity_display = serializers.CharField(source='get_intensity_display', read_only=True)

    class Meta:
        model = TrainingSession
        fields = [
            'id',
            'club',
            'created_by',
            'title',
            'status',
            'status_display',
            'session_type',
            'session_type_display',
            'intensity',
            'intensity_display',
            'start_datetime',
            'end_datetime',
            'location',
            'is_mandatory',
            'main_objective',
            'linked_opponent',
            'linked_teamsheet',
            'assigned_player_count',
            'attended_count',
            'block_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_block_count(self, obj):
        if hasattr(obj, 'prefetched_blocks'):
            return len(obj.prefetched_blocks)
        return obj.blocks.count()


class TrainingSessionDetailSerializer(TrainingSessionListSerializer):
    blocks = TrainingBlockSerializer(many=True, read_only=True)
    players = TrainingSessionPlayerSerializer(many=True, read_only=True)

    class Meta(TrainingSessionListSerializer.Meta):
        fields = TrainingSessionListSerializer.Meta.fields + [
            'secondary_objectives',
            'match_context',
            'notes',
            'what_went_well',
            'needs_improvement',
            'next_focus',
            'squad_notes',
            'calendar_event',
            'blocks',
            'players',
        ]


class TrainingSessionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingSession
        fields = [
            'id',
            'title',
            'status',
            'session_type',
            'intensity',
            'start_datetime',
            'end_datetime',
            'location',
            'is_mandatory',
            'main_objective',
            'secondary_objectives',
            'match_context',
            'linked_opponent',
            'linked_teamsheet',
            'notes',
            'what_went_well',
            'needs_improvement',
            'next_focus',
            'squad_notes',
        ]
        read_only_fields = ['id']

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError('Title cannot be blank.')
        return value.strip()

    def validate_linked_teamsheet(self, value):
        club = self.context.get('club')
        if value and club and value.club_id != club.id:
            raise serializers.ValidationError('Linked teamsheet must belong to this club.')
        return value

    def validate(self, attrs):
        instance = self.instance or TrainingSession()
        for key, value in attrs.items():
            setattr(instance, key, value)
        club = self.context.get('club')
        if club:
            instance.club = club
        try:
            instance.clean()
        except DjangoValidationError as exc:
            _raise_drf_validation_error(exc)
        return attrs

    def create(self, validated_data):
        club = self.context['club']
        request = self.context.get('request')
        session = TrainingSession(
            club=club,
            created_by=request.user if request and request.user.is_authenticated else None,
            **validated_data,
        )
        try:
            session.full_clean()
        except DjangoValidationError as exc:
            _raise_drf_validation_error(exc)
        session.save()
        return session

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            _raise_drf_validation_error(exc)
        instance.save()
        return instance


class TrainingSessionAssignPlayersSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=['all', 'selected'])
    club_player_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        if attrs['mode'] == 'selected' and 'club_player_ids' not in attrs:
            raise serializers.ValidationError({'club_player_ids': 'Select at least one player or use all active players.'})
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        session = self.context['session']
        club = self.context['club']
        mode = self.validated_data['mode']

        if mode == 'all':
            player_ids = list(
                ClubPlayer.objects.filter(club=club, is_active=True).values_list('id', flat=True)
            )
        else:
            requested_ids = set(self.validated_data.get('club_player_ids', []))
            player_ids = list(
                ClubPlayer.objects.filter(
                    club=club,
                    id__in=requested_ids,
                ).values_list('id', flat=True)
            )
            missing_ids = requested_ids - set(player_ids)
            if missing_ids:
                raise serializers.ValidationError({'club_player_ids': 'One or more players do not belong to this club.'})

        TrainingSessionPlayer.objects.filter(session=session).exclude(
            club_player_id__in=player_ids,
        ).delete()

        existing_ids = set(
            TrainingSessionPlayer.objects.filter(session=session).values_list('club_player_id', flat=True)
        )
        TrainingSessionPlayer.objects.bulk_create([
            TrainingSessionPlayer(session=session, club_player_id=club_player_id)
            for club_player_id in player_ids
            if club_player_id not in existing_ids
        ])

        return session


class TrainingAttendanceItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    club_player = serializers.IntegerField(required=False)
    attendance_status = serializers.ChoiceField(choices=TrainingSessionPlayer.AttendanceStatus.choices)
    rpe_score = serializers.IntegerField(min_value=1, max_value=10, required=False, allow_null=True)
    coach_notes = serializers.CharField(required=False, allow_blank=True)
    injury_note = serializers.CharField(required=False, allow_blank=True)
    performance_note = serializers.CharField(required=False, allow_blank=True)


class TrainingAttendanceBulkSerializer(serializers.Serializer):
    players = TrainingAttendanceItemSerializer(many=True)

    @transaction.atomic
    def save(self, **kwargs):
        session = self.context['session']
        assignments = {
            assignment.id: assignment
            for assignment in TrainingSessionPlayer.objects.filter(session=session)
        }
        assignments_by_player = {
            assignment.club_player_id: assignment
            for assignment in assignments.values()
        }

        for item in self.validated_data['players']:
            assignment = None
            if item.get('id') is not None:
                assignment = assignments.get(item['id'])
            elif item.get('club_player') is not None:
                assignment = assignments_by_player.get(item['club_player'])

            if assignment is None:
                raise serializers.ValidationError('Attendance update contains an unassigned player.')

            for field in ['attendance_status', 'rpe_score', 'coach_notes', 'injury_note', 'performance_note']:
                if field in item:
                    setattr(assignment, field, item[field])
            assignment.full_clean()
            assignment.save()

        return session
