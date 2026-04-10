from django.db import IntegrityError
from django.shortcuts import get_object_or_404

from rest_framework import serializers
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

from .models import PlayerProfile
from .serializers import PlayerProfileSerializer, PlayerProfileUpdateSerializer
from apps.users.models import UserProfile
from apps.users.permissions import IsPlayer


class CreatePlayerProfileView(CreateAPIView):
    permission_classes = [IsAuthenticated, IsPlayer]
    serializer_class = PlayerProfileSerializer

    def perform_create(self, serializer):
        try:
            user_profile = self.request.user.profile
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError(
                "You have to create a user profile before creating a Player profile."
            )

        if PlayerProfile.objects.filter(user_profile=user_profile).exists():
            raise serializers.ValidationError(
                "Player profile already exists for this user."
            )

        try:
            serializer.save(user_profile=user_profile)
        except IntegrityError:
            raise serializers.ValidationError(
                "Player profile already exists for this user."
            )


class PlayerProfileView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, IsPlayer]

    def get_object(self):
        try:
            user_profile = self.request.user.profile
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError(
                "You have to create a user profile first."
            )

        return get_object_or_404(PlayerProfile, user_profile=user_profile)

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return PlayerProfileUpdateSerializer
        return PlayerProfileSerializer