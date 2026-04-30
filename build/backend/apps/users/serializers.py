from rest_framework import serializers
from .models import User, UserProfile, UserRole, Follow, Visibility
from django.contrib.auth import get_user_model
from apps.community.models import ModerationStatus, Post

UserModel = get_user_model()

# handles creating a new user account
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    username = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    class Meta:
        model = UserModel
        fields = ['username', 'email', 'first_name', 'last_name', 'password']
    # creates a new user using the custom UserManager and falls back to email when no username is provided
    def create(self, validated_data):
        username = validated_data.get("username") or validated_data["email"]
        user = UserModel.objects.create_user(
            username=username,
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password'],
        )
        user.save()
        return user

# serializes a single role attached to a user profile
class UserRoleSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = UserRole
        fields = ['id', 'role', 'role_display', 'created_at']
        read_only_fields = ['id', 'created_at']

# serializes user account fields used inside profile responses
class UserSerializer(serializers.ModelSerializer):
    active_role = serializers.SerializerMethodField()
    active_role_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'email_verified',
            'active_role', 'active_role_display'
        ]
        read_only_fields = ['id', 'username', 'email', 'email_verified']
    # returns the user's currently selected active role from their profile
    def get_active_role(self, obj):
        profile = getattr(obj, 'profile', None)
        return getattr(profile, 'active_role', None)

    # returns the label for the user's currently  selected active role
    def get_active_role_display(self, obj):
        profile = getattr(obj, 'profile', None)
        if profile and profile.active_role:
            return profile.get_active_role_display()
        return None

# serializes full profile details
class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    roles = UserRoleSerializer(many=True, read_only=True)
    is_following = serializers.SerializerMethodField()
    followed_by = serializers.SerializerMethodField()
    active_role_display = serializers.CharField(source='get_active_role_display', read_only=True)
    posts_count = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    
    # the complete profile response returned by profile detail endpoints
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'display_name', 'profile_image', 'bio', 'gender',
                  'date_of_birth', 'visibility', 'followers_count', 
                  'following_count', 'created_at', 'updated_at', 
                  'roles', 'active_role', 'active_role_display', 'is_following', 'followed_by','posts_count']
        read_only_fields = [
            'id', 'user', 'followers_count', 'following_count', 'created_at', 'updated_at', 'posts_count',
            'active_role', 'active_role_display'
        ]
    # returns the profile's preferred display name using the model helper    
    def get_user_display_name(self, obj):
        return obj.get_display_name()
    # checks whether the requesting user follows this profile
    def get_profile_image(self, obj):
        if not obj.profile_picture:
            return None

        try:
            return obj.profile_picture.url
        except Exception:
            return str(obj.profile_picture) or None

    def get_is_following(self, obj):
        request = self.context.get('request')
        
        if not request or not request.user.is_authenticated:
            return False
        
        try:
            requester_profile = request.user.profile
            return Follow.objects.filter(follower=requester_profile, following=obj).exists()
        except UserProfile.DoesNotExist:
            return False
        
    # checks whether this profile follows the requesting user
    def get_followed_by(self, obj):
        request = self.context.get('request')
        
        if not request or not request.user.is_authenticated:
            return False
        
        try:
            requester_profile = request.user.profile
            return Follow.objects.filter(follower=obj, following=requester_profile).exists()
        except UserProfile.DoesNotExist:
            return False
        
    # counts the user's public community posts that have passed moderation
    def get_posts_count(self, obj):
        return Post.objects.filter(
            author=obj.user,
            moderation_status=ModerationStatus.OK,
            visibility=Visibility.PUBLIC
        ).count()

# handles profile update requests for editable profile fields only
     
class UserProfileUpdateSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = UserProfile
        fields = [
            'display_name', 'profile_picture', 'bio', 'gender',
            'date_of_birth', 'visibility'
        ]

    def validate_profile_picture(self, value):
        if value is None:
            return value

        max_size = 5 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("Profile picture must be 5MB or smaller.")

        allowed_types = {"image/jpeg", "image/png", "image/webp"}
        content_type = getattr(value, "content_type", "")
        if content_type not in allowed_types:
            raise serializers.ValidationError("Upload a JPEG, PNG, or WebP image.")

        return value

    def to_internal_value(self, data):
        data = data.copy()

        if data.get("gender") == "":
            data["gender"] = "NS"

        if data.get("date_of_birth") == "":
            data["date_of_birth"] = None

        legacy_visibility = {
            "PUBLIC": "PB",
            "PRIVATE": "PR",
            "FOLLOWERS": "PB",
        }
        visibility = data.get("visibility")
        if visibility in legacy_visibility:
            data["visibility"] = legacy_visibility[visibility]

        return super().to_internal_value(data)

# serializes a follow relationship between two user profiles

class FollowSerializer(serializers.ModelSerializer):
    follower = UserProfileSerializer(read_only=True)
    following = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = Follow
        fields = ['id', 'follower', 'following', 'created_at']
        read_only_fields = ['id', 'follower', 'following', 'created_at']

# serializes profiles returned in a follower list
class FollowerListSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    is_following = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'bio', 'followers_count', 'following_count', 'is_following', 'created_at']
        read_only_fields = fields

     # Checks whether the requesting user follows this follower profile
    def get_is_following(self, obj):
        request = self.context.get('request')
        
        if not request or not request.user.is_authenticated:
            return False
        
        try:
            requester_profile = request.user.profile
            return Follow.objects.filter(follower=requester_profile, following=obj).exists()
        except UserProfile.DoesNotExist:
            return False
        
# class FollowRequestIncomingSerializer(serializers.ModelSerializer):
#     user_id = serializers.IntegerField(source="follower.user.id", read_only=True)
#     username = serializers.CharField(source="follower.user.username", read_only=True)

#     class Meta:
#         model = FollowRequest
#         fields = ["id", "user_id", "username", "created_at"]
#         read_only_fields = fields


# class FollowRequestOutgoingSerializer(serializers.ModelSerializer):
#     user_id = serializers.IntegerField(source="following.user.id", read_only=True)
#     username = serializers.CharField(source="following.user.username", read_only=True)

#     class Meta:
#         model = FollowRequest
#         fields = ["id", "user_id", "username", "created_at"]
#         read_only_fields = fields

# serializes profiles returned in a following list
class FollowingListSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    is_following = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'bio', 'followers_count', 'following_count', 'is_following', 'created_at']
        read_only_fields = fields
        
    def get_is_following(self, obj):
        request = self.context.get('request')
        
        if not request or not request.user.is_authenticated:
            return False
        
        try:
            requester_profile = request.user.profile
            return Follow.objects.filter(follower=requester_profile, following=obj).exists()
        except UserProfile.DoesNotExist:
            return False
