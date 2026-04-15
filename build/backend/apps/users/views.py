from django.shortcuts import render, get_object_or_404
from rest_framework import status, viewsets, mixins
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.decorators import action
from .serializers import *
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import UserProfile, Follow, UserRole, User
from rest_framework.generics import CreateAPIView, RetrieveAPIView, RetrieveUpdateAPIView, ListAPIView
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from .services.cookie_service import set_auth_cookies

class UserRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        user_data = {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        }

        response = Response({
            'user': user_data,
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)

        set_auth_cookies(response, access_token, refresh_token, remember_me=True)

        return response


class UserCreateProfileView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def create(self, request, *args, **kwargs):
        existing_profile = UserProfile.objects.filter(user=request.user).first()
        if existing_profile:
            serializer = self.get_serializer(existing_profile)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class UserProfileView(RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(UserProfile, user=self.request.user)

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserProfileUpdateSerializer
        return UserProfileSerializer

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

        following_profile = get_object_or_404(
            UserProfile.objects.select_related("user"), user__username=username
        )

        if follower_profile.id == following_profile.id:
            return Response({"error": "You can't follow yourself"}, status=status.HTTP_400_BAD_REQUEST)

        follow, created = Follow.objects.get_or_create(
            follower=follower_profile,
            following=following_profile,
        )

        if created:
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
            following=following_profile,
        ).delete()

        if deleted_count > 0:
            return Response(
                {
                    "message": f"You have unfollowed {following_profile.user.username}",
                    "following": False,
                    "follow_request_pending": False,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "message": f"No active follow or pending request for {following_profile.user.username}",
                "following": False,
                "follow_request_pending": False,
            },
            status=status.HTTP_200_OK,
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
            following=target_profile,
        ).exists()

        followed_by = Follow.objects.filter(
            follower=target_profile,
            following=requester_profile,
        ).exists()

        # follow_request_pending = FollowRequest.objects.filter(
        #     follower=requester_profile,
        #     following=target_profile,
        # ).exists()

        return Response(
            {
                "is_following": is_following,
                "followed_by": followed_by,
                "follow_request_pending": follow_request_pending,
                "username": username,
            }
        )

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
        # Debug logging to help diagnose 405/POST issues
        try:
            print(f"UserRoleView POST called. User: {getattr(request.user, 'id', None)}, Authenticated: {request.user.is_authenticated}")
            print(f"Request data: {request.data}")
            print(f"Request method: {request.method}, Headers: { {k: v for k, v in request.headers.items() if k in ['Content-Type', 'X-CSRFToken', 'Origin', 'Referer']} }")
        except Exception:
            pass

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

        if created and not profile.active_role:
            profile.active_role = role
            profile.save(update_fields=['active_role', 'updated_at'])

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
                if profile.active_role == role:
                    profile.active_role = None
                    profile.save(update_fields=['active_role', 'updated_at'])
                return Response({"message": "Role removed successfully"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Role not found"}, status=status.HTTP_404_NOT_FOUND)


class ActiveUserRoleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response({"error": "Couldn't get profile"}, status=status.HTTP_400_BAD_REQUEST)

        roles = list(UserRole.objects.filter(user_profile=profile).values_list('role', flat=True))
        active_role_display = profile.get_active_role_display() if profile.active_role else None

        return Response({
            "active_role": profile.active_role,
            "active_role_display": active_role_display,
            "available_roles": roles,
        }, status=status.HTTP_200_OK)

    def put(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response({"error": "Couldn't get profile"}, status=status.HTTP_400_BAD_REQUEST)

        requested_role = request.data.get("role")

        if requested_role in [None, ""]:
            profile.active_role = None
            profile.save(update_fields=['active_role', 'updated_at'])
            return Response({
                "active_role": None,
                "active_role_display": None,
                "message": "Active role cleared",
            }, status=status.HTTP_200_OK)

        if not UserRole.objects.filter(user_profile=profile, role=requested_role).exists():
            return Response({
                "error": "Role is not assigned to your account"
            }, status=status.HTTP_400_BAD_REQUEST)

        profile.active_role = requested_role
        profile.save(update_fields=['active_role', 'updated_at'])

        return Response({
            "active_role": profile.active_role,
            "active_role_display": profile.get_active_role_display(),
            "message": "Active role updated",
        }, status=status.HTTP_200_OK)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")

        if not token:
            return Response({
                "error": "Verification token is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(verification_token=token)
        except User.DoesNotExist:
            return Response({
                "error": "Invalid verification token"
            }, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_token_valid():
            return Response({
                "error": "Verification token has expired. Please request a new one."
            }, status=status.HTTP_400_BAD_REQUEST)

        user.verify_email()

        return Response({
            "message": "Email verified successfully"
        }, status=status.HTTP_200_OK)


class ResendVerificationEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response({
                "error": "Email is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                "error": "User with this email does not exist"
            }, status=status.HTTP_404_NOT_FOUND)

        if user.email_verified:
            return Response({
                "message": "Email is already verified"
            }, status=status.HTTP_200_OK)

        token = user.generate_verification_token()

        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        send_mail(
            subject='Verify your email address',
            message=f'Please verify your email by clicking the following link: {verification_url}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response({
            "message": "Verification email sent successfully"
        }, status=status.HTTP_200_OK)


class UserProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    lookup_field = 'user__username'
    lookup_url_kwarg = 'username'

    def get_queryset(self):
        if self.action == 'list':
            return UserProfile.objects.filter(user=self.request.user).select_related('user')
        return UserProfile.objects.select_related('user').filter(user__is_superuser=False)

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return UserProfileUpdateSerializer
        return UserProfileSerializer

    def get_object(self):
        if self.action in ['update', 'partial_update']:
            return get_object_or_404(UserProfile, user=self.request.user)
        return super().get_object()

    def create(self, request, *args, **kwargs):
        existing_profile = UserProfile.objects.filter(user=request.user).first()
        if existing_profile:
            serializer = self.get_serializer(existing_profile)
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post', 'delete'], url_path='follow')
    def follow(self, request, username=None):
        try:
            follower_profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "You have to create a profile before following users."},
                status=status.HTTP_400_BAD_REQUEST
            )

        following_profile = get_object_or_404(
            UserProfile.objects.select_related("user"),
            user__username=username
        )

        if follower_profile.id == following_profile.id:
            return Response(
                {"error": "You can't follow yourself"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.method == 'POST':
            follow, created = Follow.objects.get_or_create(
                follower=follower_profile,
                following=following_profile
            )

            if created:
                return Response({
                    "message": f"You have followed {following_profile.user.username}",
                    "following": True
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    "message": f"You have already followed {following_profile.user.username}",
                    "following": True
                }, status=status.HTTP_200_OK)

        elif request.method == 'DELETE':
            deleted_count, _ = Follow.objects.filter(
                follower=follower_profile,
                following=following_profile
            ).delete()

            if deleted_count > 0:
                return Response({
                    "message": f"You have unfollowed {following_profile.user.username}",
                    "following": False
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "message": f"You are not following {following_profile.user.username}",
                    "following": False
                }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='follow-status')
    def follow_status(self, request, username=None):
        try:
            requester_profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "You have to create a profile first."},
                status=status.HTTP_400_BAD_REQUEST
            )

        target_profile = get_object_or_404(
            UserProfile.objects.select_related("user"),
            user__username=username
        )

        is_following = Follow.objects.filter(
            follower=requester_profile,
            following=target_profile
        ).exists()

        followed_by = Follow.objects.filter(
            follower=target_profile,
            following=requester_profile
        ).exists()

        return Response({
            "is_following": is_following,
            "followed_by": followed_by,
            "username": username
        })

    @action(detail=True, methods=['get'], url_path='followers')
    def followers(self, request, username=None):
        profile = get_object_or_404(
            UserProfile.objects.select_related('user'),
            user__username=username
        )

        followers_ids = Follow.objects.filter(
            following=profile
        ).values_list('follower_id', flat=True)

        followers = UserProfile.objects.filter(
            id__in=followers_ids
        ).select_related('user').order_by('-followers_count')

        serializer = FollowerListSerializer(followers, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='following')
    def following(self, request, username=None):
        profile = get_object_or_404(
            UserProfile.objects.select_related('user'),
            user__username=username
        )

        following_ids = Follow.objects.filter(
            follower=profile
        ).values_list('following_id', flat=True)

        following = UserProfile.objects.filter(
            id__in=following_ids
        ).select_related('user').order_by('-followers_count')

        serializer = FollowerListSerializer(following, many=True, context={'request': request})
        return Response(serializer.data)


class UserRoleViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        try:
            profile = request.user.profile
            roles = UserRole.objects.filter(user_profile=profile)
            serializer = UserRoleSerializer(roles, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Couldn't get profile"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def create(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Couldn't get profile"},
                status=status.HTTP_400_BAD_REQUEST
            )

        role = request.data.get("role")
        if not role:
            return Response(
                {"error": "Role is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        role_obj, created = UserRole.objects.get_or_create(
            user_profile=profile,
            role=role
        )

        if created and not profile.active_role:
            profile.active_role = role
            profile.save(update_fields=['active_role', 'updated_at'])

        serializer = UserRoleSerializer(role_obj)

        if created:
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "message": "Role has already been assigned",
                "role": serializer.data
            }, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Couldn't get profile"},
                status=status.HTTP_400_BAD_REQUEST
            )

        role = request.data.get("role")
        if not role:
            return Response(
                {"error": "Role is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        deleted_count, _ = UserRole.objects.filter(
            user_profile=profile,
            role=role
        ).delete()

        if deleted_count > 0:
            if profile.active_role == role:
                profile.active_role = None
                profile.save(update_fields=['active_role', 'updated_at'])
            return Response(
                {"message": "Role removed successfully"},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "Role not found"},
                status=status.HTTP_404_NOT_FOUND
            )
