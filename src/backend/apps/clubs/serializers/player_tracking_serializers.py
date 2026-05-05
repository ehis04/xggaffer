from rest_framework import serializers

from ..models import ClubPlayerInjury, ClubPlayerManualStats, ClubSeasonResult


class ClubPlayerInjurySerializer(serializers.ModelSerializer):
    injury_type_display = serializers.CharField(source='get_injury_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    availability_status_display = serializers.CharField(source='get_availability_status_display', read_only=True)
    recorded_by_email = serializers.CharField(source='recorded_by.email', read_only=True)

    class Meta:
        model = ClubPlayerInjury
        fields = [
            'id',
            'club_player',
            'injury_type',
            'injury_type_display',
            'severity',
            'severity_display',
            'availability_status',
            'availability_status_display',
            'injured_at',
            'estimated_return',
            'notes',
            'is_current',
            'recorded_by',
            'recorded_by_email',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'club_player', 'recorded_by', 'created_at', 'updated_at']

    def validate(self, attrs):
        availability_status = attrs.get('availability_status', ClubPlayerInjury.AvailabilityStatus.INJURED)
        if availability_status == ClubPlayerInjury.AvailabilityStatus.AVAILABLE:
            raise serializers.ValidationError(
                {'availability_status': 'Use the resolve endpoint to mark a player available.'}
            )
        return attrs


class ClubPlayerManualStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubPlayerManualStats
        fields = [
            'id',
            'club_player',
            'season',
            'appearances',
            'minutes_played',
            'goals',
            'assists',
            'xg',
            'npxg',
            'xa',
            'shots',
            'shots_on_target',
            'key_passes',
            'dribbles_completed',
            'progressive_passes',
            'progressive_carries',
            'tackles',
            'interceptions',
            'aerials_won',
            'clearances',
            'blocks',
            'saves',
            'save_percentage',
            'clean_sheets',
            'goals_conceded',
            'last_updated',
            'created_at',
        ]
        read_only_fields = ['id', 'club_player', 'last_updated', 'created_at']


class ClubSeasonResultSerializer(serializers.ModelSerializer):
    outcome = serializers.CharField(read_only=True)
    venue_display = serializers.CharField(source='get_venue_display', read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)

    class Meta:
        model = ClubSeasonResult
        fields = [
            'id',
            'club',
            'opponent_name',
            'venue',
            'venue_display',
            'competition',
            'match_date',
            'goals_for',
            'goals_against',
            'outcome',
            'fixture',
            'notes',
            'created_by',
            'created_by_email',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'club', 'outcome', 'created_by', 'created_at', 'updated_at']
