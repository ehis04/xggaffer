from django.shortcuts import render, get_object_or_404
from .serializers import CoachProfileSerializer, CoachProfileUpdateSerializer
from .models import CoachProfile
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.users.permissions import IsCoach
from rest_framework.generics import CreateAPIView, RetrieveAPIView, RetrieveUpdateAPIView, ListAPIView
from apps.users.models import UserProfile


class CreateCoachProfileView(CreateAPIView):
    permission_classes = [IsAuthenticated, IsCoach]
    serializer_class = CoachProfileSerializer

    def create(self, request, *args, **kwargs):
        try:
            user_profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "You have to create a user profile before creating a coach profile."},
                status=status.HTTP_400_BAD_REQUEST
            )

        existing_profile = CoachProfile.objects.filter(user_profile=user_profile).first()
        if existing_profile:
            serializer = self.get_serializer(existing_profile)
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user_profile=user_profile)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CoachProfileView(RetrieveUpdateAPIView):
    serializer_class = CoachProfileSerializer
    permission_classes = [IsAuthenticated, IsCoach]
    
    def get_object(self):
        try:
            user_profile = self.request.user.profile
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError(
                "You have to create a user profile first."
            )
        return get_object_or_404(CoachProfile, user_profile=user_profile)
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return CoachProfileUpdateSerializer
        print(CoachProfileSerializer) 
        return CoachProfileSerializer