from rest_framework import serializers

from .models import RefereeProfile
from apps.users.serializers import UserProfileSerializer


class RefereeProfileSerializer(serializers.ModelSerializer):
    user_profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = RefereeProfile
        fields = [
            "id",
            "user_profile",
            "experience_level",
            "years_experience",
            "certification_level",
            "certification_date",
            "next_certification_date",
            "total_matches_officiates",
            "matches_this_season",
            "primary_position",
            "preferred_learning_time",
            "certification_goal",
            "target_completion_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user_profile", "created_at", "updated_at"]


class RefereeProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefereeProfile
        fields = [
            "experience_level",
            "years_experience",
            "certification_level",
            "certification_date",
            "next_certification_date",
            "total_matches_officiates",
            "matches_this_season",
            "primary_position",
            "preferred_learning_time",
            "certification_goal",
            "target_completion_date",
        ]
