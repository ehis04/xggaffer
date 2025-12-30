from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.views import APIView
from .serializers import RegisterSerializer, UserProfileSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import UserProfile
from rest_framework.generics import CreateAPIView, RetrieveAPIView, RetrieveUpdateAPIView
from django.shortcuts import get_object_or_404

# Create your views here.

class UserRegisterView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        
        safe_user_data = {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
        return Response({
            "user": safe_user_data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "message": "User registered successfully"
        }, status=status.HTTP_201_CREATED)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Successfully logged out"}, status=status.HTTP_205_RESET_CONTENT)
        except TokenError:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
        except KeyError:
            return Response({"error": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)
# This view allows users to create their own profile
class UserCreateProfileView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    
    def perform_create(self, serializer):
        if UserProfile.objects.filter(user=self.request.user).exists():
            raise serializers.ValidationError("Profile already exists for this user.")
        serializer.save(user=self.request.user)
       
# This view allows users to view and edit their own profile (to edit one or multiple fields use: Patch, to edit all fields use: Put)
class UserProfileView(RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return get_object_or_404(UserProfile, user=self.request.user)

# This view allows users to view another user's (that is not a superuser) profile
class GetProfileView(RetrieveAPIView):
    queryset = UserProfile.objects.select_related("user")
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'user__username'
    lookup_url_kwarg = "username"
    
    def get_queryset(self):
        return super().get_queryset().filter(user__is_superuser=False)