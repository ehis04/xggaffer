from rest_framework import serializers
from .models import PlayerProfile
from apps.users.serializers import UserProfileSerializer

class PlayerProfileSerializer(serializers.ModelSerializer):
    user_profile = UserProfileSerializer(read_only=True)
    class Meta:
        model = PlayerProfile
        fields = ['id', 'user_profile', 'primary_position', 'secondary_position', 'preferred_foot', 'height_cm', 'weight_kg', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user_profile', 'created_at', 'updated_at']

class PlayerProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerProfile
        fields = [
            'primary_position', 
            'secondary_position',
            'preferred_foot',
            'height_cm',
            'weight_kg'
        ]