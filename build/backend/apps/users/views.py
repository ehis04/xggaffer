from django.shortcuts import render, get_object_or_404
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from .serializers import *
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import UserProfile, Follow, UserRole
from rest_framework.generics import CreateAPIView, RetrieveAPIView, RetrieveUpdateAPIView, ListAPIView
from .services.cookie_service import set_auth_cookies

ROLE_CODE_BY_KEY = {
    "C": "C",
    "COACH": "C",
    "P": "P",
    "PLAYER": "P",
    "R": "R",
    "REFEREE": "R",
    "F": "F",
    "FAN": "F",
}


def normalise_role(role):
    if not role:
        return role
    return ROLE_CODE_BY_KEY.get(str(role).upper(), role)


def role_aliases(role):
    normalised_role = normalise_role(role)
    if not normalised_role:
        return []

    aliases = [
        key for key, value in ROLE_CODE_BY_KEY.items()
        if value == normalised_role
    ]
    if normalised_role not in aliases:
        aliases.append(normalised_role)
    return aliases


role_required_message = "Role is required"
# Handles new user registration and automatically logs the user in
class UserRegisterView(APIView):
    permission_classes = [AllowAny]
    
    # Validates registration data, creates the user, sends verification email, and sets auth cookies
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        from .services.email_service import send_verification_email
        send_verification_email(user)

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        user_data = UserSerializer(user).data

        response = Response({
            'user': user_data,
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)

        set_auth_cookies(response, access_token, refresh_token, remember_me=True)
        return response

# Creates a profile for the authenticated user if one does not already exist
class UserCreateProfileView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    
    # Returns the existing profile instead of creating a duplicate profile for the same user
    def create(self, request, *args, **kwargs):
        existing_profile = UserProfile.objects.filter(user=request.user).first()
        if existing_profile:
            serializer = self.get_serializer(existing_profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return super().create(request, *args, **kwargs)
    
    # Saves the new profile and attaches it to the currently authenticated user
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# Retrieves and updates the user's own profile
class UserProfileView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self):
        return get_object_or_404(UserProfile, user=self.request.user)

    # Returns the current user's full profile data
    def get(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = UserProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)
    
    # Partially updates the current user's editable profile fields and returns the full updated profile
    def patch(self, request, *args, **kwargs):
        profile = self.get_object()

        # Uses the slim update serializer
        # it only exposes the fields the user is allowed to change.
        update_serializer = UserProfileUpdateSerializer(
            profile,
            data=request.data,
            partial=True,
        )

        if not update_serializer.is_valid():
            return Response(update_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        update_serializer.save()

        # Returns the full profile so the frontend state is complete.
        response_serializer = UserProfileSerializer(profile, context={'request': request})
        return Response(response_serializer.data)

    # Blocks full profile replacement because this endpoint only supports partial profile updates
    def put(self, request, *args, **kwargs):
        return Response(
            {'detail': 'Method "PUT" not allowed. Use PATCH.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


# Retrieves another user's public profile by username
class GetProfileView(RetrieveAPIView):
    queryset = UserProfile.objects.select_related("user")
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'user__username'
    lookup_url_kwarg = "username"
    
    # Excludes superuser profiles from normal profile lookup responses
    def get_queryset(self):
        return super().get_queryset().filter(user__is_superuser=False)

# Handles following and unfollowing another user by username
class FollowUserView(APIView):
    permission_classes = [IsAuthenticated]
    
    # Creates a follow relationship between the current user and the target username
    def post(self, request, username):
        try:
            follower_profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "You have to create a profile before following users."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        following_profile = get_object_or_404(
            UserProfile.objects.select_related("user"), user__username=username
        )

        if follower_profile.id == following_profile.id:
            return Response(
                {"error": "You can't follow yourself"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        follow, created = Follow.objects.get_or_create(
            follower=follower_profile,
            following=following_profile,
        )

        if created:
            return Response(
                {"message": f"You are now following {username}", "following": True},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"message": f"You are already following {username}", "following": True},
            status=status.HTTP_200_OK,
        )
        
    # Deletes the follow relationship between the current user and the target username
    def delete(self, request, username):
        try:
            follower_profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "You have to create a profile before unfollowing users."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        following_profile = get_object_or_404(
            UserProfile.objects.select_related("user"), user__username=username
        )

        deleted_count, _ = Follow.objects.filter(
            follower=follower_profile,
            following=following_profile,
        ).delete()

        if deleted_count > 0:
            return Response(
                {"message": f"You have unfollowed {username}", "following": False,
                 "follow_request_pending": False},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"message": f"No active follow for {username}", "following": False,
             "follow_request_pending": False},
            status=status.HTTP_200_OK,
        )

# Lists the profiles that follow a selected user
class FollowersListView(ListAPIView):
    serializer_class = FollowerListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        username = self.kwargs.get('username')
        profile = get_object_or_404(
            UserProfile.objects.select_related('user'), user__username=username
        )
        followers_ids = Follow.objects.filter(
            following=profile
        ).values_list('follower_id', flat=True)
        return UserProfile.objects.filter(
            id__in=followers_ids
        ).select_related('user').order_by('followers_count')

# Lists the profiles that a selected user is following
class FollowingListView(ListAPIView):
    serializer_class = FollowerListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        username = self.kwargs.get('username')
        profile = get_object_or_404(
            UserProfile.objects.select_related('user'), user__username=username
        )
        following_ids = Follow.objects.filter(
            follower=profile
        ).values_list('following_id', flat=True)
        return UserProfile.objects.filter(
            id__in=following_ids
        ).select_related('user').order_by('followers_count')

# Checks the follow relationship between the current user and another user
class CheckFollowStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, username):
        try:
            requester_profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "You have to create a profile first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_profile = get_object_or_404(
            UserProfile.objects.select_related("user"), user__username=username
        )

        is_following = Follow.objects.filter(
            follower=requester_profile, following=target_profile
        ).exists()

        followed_by = Follow.objects.filter(
            follower=target_profile, following=requester_profile
        ).exists()

        return Response({
            "is_following": is_following,
            "followed_by": followed_by,
            "follow_request_pending": False,
            "username": username,
        })

# Handles listing, adding, and removing roles from the current user's profile
class UserRoleView(APIView):
    permission_classes = [IsAuthenticated]

    # Reads the role from the request body first and falls back to query parameters for clients that do not support DELETE bodies
    def _get_role_from_request(self, request):
        """
        Read the role value from the request body first, then fall back to
        query params. This handles HTTP clients that strip DELETE bodies.
        """
        role = request.data.get("role") or request.query_params.get("role")
        return normalise_role(role)

        return request.data.get("role") or request.query_params.get("role")
    
    # Returns all roles currently assigned to the authenticated user's profile
    def get(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Couldn't get profile"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        roles = UserRole.objects.filter(user_profile=profile)
        serializer = UserRoleSerializer(roles, many=True)
        return Response(serializer.data)

    # Adds a role to the authenticated user's profile and sets it as active if no active role exists
    def post(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Couldn't get profile"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        role = self._get_role_from_request(request)
        if not role:
            return Response(
                {"error": role_required_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        role_obj = UserRole.objects.filter(
            user_profile=profile,
            role__in=role_aliases(role),
        ).first()
        created = role_obj is None

        if created:
            role_obj = UserRole.objects.create(user_profile=profile, role=role)
        elif role_obj.role != role:
            role_obj.role = role
            role_obj.save(update_fields=['role'])

        if created and not profile.active_role:
            profile.active_role = role
            profile.save(update_fields=['active_role', 'updated_at'])

        serializer = UserRoleSerializer(role_obj)

        if created:
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(
            {"message": "Role already assigned", "role": serializer.data},
            status=status.HTTP_200_OK,
        )

    # Removes a role from the authenticated user's profile and clears active_role if that role was active
    def delete(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Couldn't get profile"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Accepts the role from either the body or query parameters because DELETE request bodies are not always preserved
        role = self._get_role_from_request(request)
        if not role:
            return Response(
                {"error": role_required_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted_count, _ = UserRole.objects.filter(
            user_profile=profile, role__in=role_aliases(role)
        ).delete()

        if deleted_count > 0:
            if profile.active_role in role_aliases(role):
                profile.active_role = None
                profile.save(update_fields=['active_role', 'updated_at'])
            return Response(
                {"message": "Role removed successfully"},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"error": f"Role '{role}' not found on your profile"},
            status=status.HTTP_404_NOT_FOUND,
        )

# Handles reading and updating the current user's active role
class ActiveUserRoleView(APIView):
    permission_classes = [IsAuthenticated]
    
    # Returns the current active role, its display label, and all roles assigned to the profile
    def get(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Couldn't get profile"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        roles = list(UserRole.objects.filter(
            user_profile=profile
        ).values_list('role', flat=True))

        active_role_display = (
            profile.get_active_role_display() if profile.active_role else None
        )

        return Response({
            "active_role": profile.active_role,
            "active_role_display": active_role_display,
            "available_roles": roles,
        })
    
    # Sets the current user's active role or clears it when an empty role is provided
    def put(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Couldn't get profile"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        requested_role = normalise_role(request.data.get("role"))

        if requested_role in (None, ""):
            profile.active_role = None
            profile.save(update_fields=['active_role', 'updated_at'])
            return Response({
                "active_role": None,
                "active_role_display": None,
                "message": "Active role cleared",
            })

        if not UserRole.objects.filter(
            user_profile=profile, role__in=role_aliases(requested_role)
        ).exists():
            return Response(
                {"error": "Role is not assigned to your account"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile.active_role = requested_role
        profile.save(update_fields=['active_role', 'updated_at'])
        return Response({
            "active_role": profile.active_role,
            "active_role_display": profile.get_active_role_display(),
            "message": "Active role updated",
        })

# ViewSet version of the profile API with retrieve, update, follow, followers, and following actions
class UserProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    lookup_field = 'user__username'
    lookup_url_kwarg = 'username'

    # Returns only the current user's profile for list requests and non-superuser profiles for detail requests
    def get_queryset(self):
        if self.action == 'list':
            return UserProfile.objects.filter(
                user=self.request.user
            ).select_related('user')
        return UserProfile.objects.select_related('user').filter(
            user__is_superuser=False
        )

    # Uses the slimmer update serializer for profile update actions and the full serializer for read actions
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return UserProfileUpdateSerializer
        return UserProfileSerializer

    # Forces update actions to operate only on the authenticated user's own profile
    def get_object(self):
        if self.action in ['update', 'partial_update']:
            return get_object_or_404(UserProfile, user=self.request.user)
        return super().get_object()
    # Creates the current user's profile or returns their existing profile if one already exists
    def create(self, request, *args, **kwargs):
        existing_profile = UserProfile.objects.filter(user=request.user).first()
        if existing_profile:
            serializer = self.get_serializer(existing_profile)
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    # Follows or unfollows the selected user depending on whether the request method is POST or DELETE
    @action(detail=True, methods=['post', 'delete'], url_path='follow')
    def follow(self, request, username=None):
        try:
            follower_profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "You have to create a profile before following users."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        following_profile = get_object_or_404(
            UserProfile.objects.select_related("user"), user__username=username
        )

        if follower_profile.id == following_profile.id:
            return Response(
                {"error": "You can't follow yourself"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.method == 'POST':
            follow, created = Follow.objects.get_or_create(
                follower=follower_profile, following=following_profile
            )
            if created:
                return Response(
                    {"message": f"You have followed {username}", "following": True},
                    status=status.HTTP_201_CREATED,
                )
            return Response(
                {"message": f"Already following {username}", "following": True},
                status=status.HTTP_200_OK,
            )

        elif request.method == 'DELETE':
            deleted_count, _ = Follow.objects.filter(
                follower=follower_profile, following=following_profile
            ).delete()
            if deleted_count > 0:
                return Response(
                    {"message": f"Unfollowed {username}", "following": False},
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"message": f"Not following {username}", "following": False},
                status=status.HTTP_200_OK,
            )
            
    # Returns whether the authenticated user follows the selected user and whether the selected user follows them back
    @action(detail=True, methods=['get'], url_path='follow-status')
    def follow_status(self, request, username=None):
        try:
            requester_profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "You have to create a profile first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_profile = get_object_or_404(
            UserProfile.objects.select_related("user"), user__username=username
        )

        is_following = Follow.objects.filter(
            follower=requester_profile, following=target_profile
        ).exists()
        followed_by = Follow.objects.filter(
            follower=target_profile, following=requester_profile
        ).exists()

        return Response({
            "is_following": is_following,
            "followed_by": followed_by,
            "username": username,
        })

    @action(detail=True, methods=['get'], url_path='followers')
    def followers(self, request, username=None):
        profile = get_object_or_404(
            UserProfile.objects.select_related('user'), user__username=username
        )
        followers_ids = Follow.objects.filter(
            following=profile
        ).values_list('follower_id', flat=True)
        followers = UserProfile.objects.filter(
            id__in=followers_ids
        ).select_related('user').order_by('-followers_count')
        serializer = FollowerListSerializer(
            followers, many=True, context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='following')
    def following(self, request, username=None):
        profile = get_object_or_404(
            UserProfile.objects.select_related('user'), user__username=username
        )
        following_ids = Follow.objects.filter(
            follower=profile
        ).values_list('following_id', flat=True)
        following = UserProfile.objects.filter(
            id__in=following_ids
        ).select_related('user').order_by('-followers_count')
        serializer = FollowerListSerializer(
            following, many=True, context={'request': request}
        )
        return Response(serializer.data)

# ViewSet version of the user role API for listing, assigning, and removing profile roles
class UserRoleViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    # Lists all roles assigned to the authenticated user's profile
    def list(self, request):
        try:
            profile = request.user.profile
            roles = UserRole.objects.filter(user_profile=profile)
            serializer = UserRoleSerializer(roles, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Couldn't get profile"},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
    # Adds a new role to the authenticated user's profile and sets it active if no active role exists
    def create(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Couldn't get profile"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        role = normalise_role(request.data.get("role"))
        if not role:
            return Response(
                {"error": role_required_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        role_obj = UserRole.objects.filter(
            user_profile=profile,
            role__in=role_aliases(role),
        ).first()
        created = role_obj is None

        if created:
            role_obj = UserRole.objects.create(user_profile=profile, role=role)
        elif role_obj.role != role:
            role_obj.role = role
            role_obj.save(update_fields=['role'])

        if created and not profile.active_role:
            profile.active_role = role
            profile.save(update_fields=['active_role', 'updated_at'])

        serializer = UserRoleSerializer(role_obj)

        if created:
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(
            {"message": "Role has already been assigned", "role": serializer.data},
            status=status.HTTP_200_OK,
        )
        
    # Removes a role from the authenticated user's profile and clears active_role if the removed role was active
    def destroy(self, request, pk=None):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Couldn't get profile"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        role = normalise_role(
            request.data.get("role") or request.query_params.get("role")
        )
        if not role:
            return Response(
                {"error": role_required_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted_count, _ = UserRole.objects.filter(
            user_profile=profile, role__in=role_aliases(role)
        ).delete()

        if deleted_count > 0:
            if profile.active_role in role_aliases(role):
                profile.active_role = None
                profile.save(update_fields=['active_role', 'updated_at'])
            return Response(
                {"message": "Role removed successfully"},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"error": "Role not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

