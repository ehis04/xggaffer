import re
from rest_framework import serializers
from .models import Club, ClubMembership, ClubPlayer


class ClubSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)
    player_count = serializers.IntegerField(read_only=True)
    creator_username = serializers.CharField(source='creator.email', read_only=True)

    class Meta:
        model = Club
        fields = [
            'id',
            'name',
            'description',
            'badge',
            'creator',
            'creator_username',
            'visibility',
            'city',
            'country',
            'stadium',
            'division',
            'achievements',
            'member_count',
            'player_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['creator', 'created_at', 'updated_at']


class ClubMembershipSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.email', read_only=True)
    club_name = serializers.CharField(source='club.name', read_only=True)

    class Meta:
        model = ClubMembership
        fields = [
            'id',
            'user',
            'username',
            'club',
            'club_name',
            'role',
            'is_active',
            'invited_by',
            'joined_at',
            'updated_at',
        ]
        read_only_fields = ['joined_at', 'updated_at']


class ClubPlayerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    is_claimed = serializers.BooleanField(read_only=True)
    club_name = serializers.CharField(source='club.name', read_only=True)

    class Meta:
        model = ClubPlayer
        fields = [
            'id',
            'club',
            'club_name',
            'user',
            'first_name',
            'last_name',
            'full_name',
            'display_name',
            'squad_number',
            'position',
            'secondary_position',
            'preferred_foot',
            'date_of_birth',
            'height_cm',
            'photo',
            'is_active',
            'is_claimed',
            'is_public',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['user', 'is_claimed', 'claimed_at', 'created_at', 'updated_at']


class ClubPlayerListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = ClubPlayer
        fields = [
            'id',
            'first_name',
            'last_name',
            'full_name',
            'display_name',
            'squad_number',
            'position',
            'photo',
            'is_active',
            'is_public',
        ]


class ClubPlayerCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubPlayer
        fields = [
            'id',
            'club',
            'first_name',
            'last_name',
            'display_name',
            'squad_number',
            'position',
            'secondary_position',
            'preferred_foot',
            'date_of_birth',
            'height_cm',
            'photo',
            'is_public',
        ]
    
    def validate(self, attrs):
        is_public = attrs.get('is_public', False)
        first_name = attrs.get('first_name', '').strip()
        last_name = attrs.get('last_name', '').strip()
        club = attrs.get('club')
        position = attrs.get('position', '')
        squad_number = attrs.get('squad_number')

        if is_public:
            if first_name or last_name:
                if not self._is_generic_name(first_name, last_name, club, position, squad_number):
                    raise serializers.ValidationError({
                        'is_public': (
                            "Public profiles cannot use real names. "
                            "Use format like '{club_name}'s {position} #{number}' "
                            "or leave name fields empty."
                        )
                    })
        
        return attrs
    
    def _is_generic_name(self, first_name, last_name, club, position, squad_number):
        if not first_name and not last_name:
            return True
        
        club_name = club.name.lower() if club else ''
        full_name = f"{first_name} {last_name}".lower().strip()
        
        generic_patterns = [
            rf"^{re.escape(club_name)}.*{re.escape(position.lower())}",
            rf"^{re.escape(position.lower())}.*#?\d+",
            rf"^player\s*#?\d+",
            rf"^{re.escape(club_name)}.*#?\d+",
        ]
        
        for pattern in generic_patterns:
            if re.search(pattern, full_name):
                return True
        
        return False
    
    def create(self, validated_data):
        is_public = validated_data.get('is_public', False)
        
        if is_public and not validated_data.get('display_name'):
            club = validated_data.get('club')
            position = validated_data.get('position', 'Player')
            squad_number = validated_data.get('squad_number', '')
            
            club_name = club.name if club else 'Team'
            number_str = f" #{squad_number}" if squad_number else ''
            validated_data['display_name'] = f"{club_name}'s {position}{number_str}"
        
        return super().create(validated_data)


class AvailablePlayerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    source_type = serializers.SerializerMethodField()
    
    class Meta:
        model = ClubPlayer
        fields = [
            'id',
            'first_name',
            'last_name',
            'full_name',
            'display_name',
            'squad_number',
            'position',
            'photo',
            'club',
            'is_public',
            'source_type',
        ]
    
    def get_source_type(self, obj):
        request_club_id = self.context.get('club_id')
        if obj.club_id == request_club_id:
            return 'club_member'
        elif obj.is_public:
            return 'public'
        return 'unknown'