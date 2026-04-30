from django.db import IntegrityError
from django.shortcuts import get_object_or_404

from rest_framework import serializers, status
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.models import UserProfile
from apps.users.permissions import IsReferee
from .models import RefereeProfile
from .serializers import RefereeProfileSerializer, RefereeProfileUpdateSerializer


class CreateRefereeProfileView(CreateAPIView):
    permission_classes = [IsAuthenticated, IsReferee]
    serializer_class = RefereeProfileSerializer

    def create(self, request, *args, **kwargs):
        try:
            user_profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "You have to create a user profile before creating a referee profile."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_profile = RefereeProfile.objects.filter(user_profile=user_profile).first()
        if existing_profile:
            serializer = self.get_serializer(existing_profile)
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save(user_profile=user_profile)
        except IntegrityError:
            raise serializers.ValidationError(
                "Referee profile already exists for this user."
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RefereeProfileView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, IsReferee]

    def get_object(self):
        try:
            user_profile = self.request.user.profile
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError("You have to create a user profile first.")

        return get_object_or_404(RefereeProfile, user_profile=user_profile)

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return RefereeProfileUpdateSerializer
        return RefereeProfileSerializer
