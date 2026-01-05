from django.contrib import admin
from .models import User, UserProfile
from django.contrib import admin
from .models import User, UserProfile, UserRole, Follow

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'display_name', 'gender', 'followers_count', 'following_count', 'visibility', 'created_at']
    list_filter = ['gender', 'visibility', 'created_at']
    search_fields = ['user__username', 'user__email', 'display_name', 'bio']
    readonly_fields = ['followers_count', 'following_count', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'display_name')
        }),
        ('Profile Details', {
            'fields': ('bio', 'gender', 'date_of_birth', 'visibility')
        }),
        ('Statistics', {
            'fields': ('followers_count', 'following_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user_profile', 'role', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['user_profile__user__username', 'user_profile__user__email']
    ordering = ['-created_at']

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ['follower', 'following', 'created_at']
    list_filter = ['created_at']
    search_fields = [
        'follower__user__username', 
        'follower__user__email',
        'following__user__username',
        'following__user__email'
    ]
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'follower__user',
            'following__user'
        )