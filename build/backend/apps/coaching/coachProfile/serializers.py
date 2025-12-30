from .models import CoachProfile
from rest_framework import serializers
from apps.users.serializers import UserProfileSerializer

class CoachProfileSerializer(serializers.ModelSerializer):
    user_profile = UserProfileSerializer(read_only=True)
    class Meta:
        model = CoachProfile
        fields = ['id', 'user_profile', 'experience_level', 'formation_preferences',
                'years_experience', 'club_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user_profile', 'created_at', 'updated_at']

class CoachProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoachProfile
        fields = ['experience_level', 'formation_preferences',
                'years_experience', 'club_name']