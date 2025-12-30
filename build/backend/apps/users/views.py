from django.shortcuts import render, get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.views import APIView
from .serializers import *
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import UserProfile, Follow, UserRole
from rest_framework.generics import CreateAPIView, RetrieveAPIView, RetrieveUpdateAPIView, ListAPIView
from django.db.models import Q

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
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserProfileUpdateSerializer
        return UserProfileSerializer

# This view allows users to view another user's (that is not a superuser) profile
class GetProfileView(RetrieveAPIView):
    queryset = UserProfile.objects.select_related("user")
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'user__username'
    lookup_url_kwarg = "username"
    
    def get_queryset(self):
        return super().get_queryset().filter(user__is_superuser=False)
    
class FollowUserView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, username):
        try:
            follower_profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response({"error": "You have to create a profile before following users."}, status=status.HTTP_400_BAD_REQUEST)
        
        # gets the profile of the user to follow
        following_profile = get_object_or_404(
            UserProfile.objects.select_related("user"), user__username=username
        )
        
        if follower_profile.id == following_profile.id:
            return Response({"error": "You can't follow yourself"}, status=status.HTTP_400_BAD_REQUEST)
        
        follow, created = Follow.objects.get_or_create(
            follower=follower_profile,
            following=following_profile
        )
        
        if created:
            return Response({"message": f"You have followed {following_profile.user.username}",
                            "following": True
                            },
                            status=status.HTTP_201_CREATED)
        else:
            return Response(
                {
                    "message": f"You have already followed {following_profile.user.username}",
                    "following": True
                }, status=status.HTTP_200_OK
            )
        
    def delete(self, request, username):
        try:
            follower_profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response({"error": "You have to create a profile before unfollowing users."}, status=status.HTTP_400_BAD_REQUEST)
        
        following_profile = get_object_or_404(
            UserProfile.objects.select_related("user"), user__username=username
        )
        
        deleted_count, _ = Follow.objects.filter(
            follower=follower_profile,
            following=following_profile
        ).delete()

        if deleted_count > 0:
            return Response(
                {
                    "message": f"You have unfollowed {following_profile.user.username}",
                    "following": False
                }, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {
                    "message": f"You are not following {following_profile.user.username}",
                    "following": False
                }, status=status.HTTP_200_OK
            )

class FollowersListView(ListAPIView):
    serializer_class = FollowerListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        username = self.kwargs.get('username')
        profile = get_object_or_404(
            UserProfile.objects.select_related('user'),
            user__username=username
        )
        
        followers_ids = Follow.objects.filter(
            following=profile
        ).values_list('follower_id', flat=True)
        
        return UserProfile.objects.filter(
            id__in=followers_ids
        ).select_related('user').order_by('followers_count')

class FollowingListView(ListAPIView):
    serializer_class = FollowerListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        username = self.kwargs.get('username')
        profile = get_object_or_404(
            UserProfile.objects.select_related('user'),
            user__username=username
        )

        following_ids = Follow.objects.filter(
            follower=profile
        ).values_list('following_id', flat=True)

        return UserProfile.objects.filter(
            id__in=following_ids
        ).select_related('user').order_by('followers_count')
        
class CheckFollowStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, username):
        try:
            requester_profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response({"error": "You have to create a profile first."}, status=status.HTTP_400_BAD_REQUEST)
        
        target_profile = get_object_or_404(
            UserProfile.objects.select_related("user"), user__username=username
        )
        
        is_following = Follow.objects.filter(
            follower=requester_profile,
            following=target_profile
        ).exists()
        
        followed_by = Follow.objects.filter(
            follower=target_profile,
            following=requester_profile
        ).exists()
        
        return Response(
            {
                "is_following": is_following,
                "followed_by": followed_by,
                "username": username
            }
        )

# TODO search for users profiles view (class SearchUsersView(ListAPIView):)

class UserRoleView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            profile = request.user.profile
            role = UserRole.objects.filter(user_profile=profile)
            serializer = UserRoleSerializer(role, many=True)
            
            return Response(serializer.data)
        
        except UserProfile.DoesNotExist:
            return Response({"error": "Couldn't get profile"}, status=status.HTTP_400_BAD_REQUEST)
        
    def post(self, request):
        try:
            profile = request.user.profile
        
        except UserProfile.DoesNotExist:
            return Response({"error": "Couldn't get profile"}, status=status.HTTP_400_BAD_REQUEST)
        
        role = request.data.get("role")
        if not role:
            return Response({
                "error": "Role is required"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        role_obj, created = UserRole.objects.get_or_create(
            user_profile=profile,
            role=role
        )
        
        serializer = UserRoleSerializer(role_obj)
        
        if created:
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {
                    "message": "Role has already been assigned",
                    "role": serializer.data
                }, status=status.HTTP_200_OK
            )
            
        def delete(self, request):
            try:
                profile = request.user.profile
            except UserProfile.DoesNotExist:
                return Response({"error": "Couldn't get profile"}, status=status.HTTP_400_BAD_REQUEST)
            
            role = request.data.get("role")
            
            if not role:
                return Response({
                    "error": "Role is required"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            deleted_count, _ = UserRole.objects.filter(
                user_profile=profile,
                role=role
            ).delete()
            
            if deleted_count > 0:
                return Response({"message": "Role removed successfully"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Role not found"}, status=status.HTTP_404_NOT_FOUND)