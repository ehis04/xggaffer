from django.shortcuts import render, get_object_or_404
from .serializers import CoachProfileSerializer, CoachProfileUpdateSerializer
from .models import CoachProfile
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from apps.users.permissions import IsCoach
from rest_framework.generics import CreateAPIView, RetrieveAPIView, RetrieveUpdateAPIView, ListAPIView
from apps.users.models import UserProfile


# Create your views here.

class CreateCoachProfileView(CreateAPIView):
    permission_classes = [IsAuthenticated, IsCoach]
    serializer_class = CoachProfileSerializer
    
    def perform_create(self, serializer):
        try:
            user_profile = self.request.user.profile
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError(
                "You have to create a user profile before creating a coach profile."
            )
        
        if hasattr(user_profile, 'coach_profile'):
            raise serializers.ValidationError(
                "Coach profile already exists for this user."
            )

        serializer.save(user_profile=user_profile)

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
        print(CoachProfileSerializer) # debug statement
        return CoachProfileSerializer
        
    
    