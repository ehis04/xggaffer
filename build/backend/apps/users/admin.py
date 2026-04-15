from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import User, UserProfile, UserRole, Follow, Role


def active_role_choices():
    return [('', 'No active role')] + list(Role.choices)


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)
    active_role = forms.ChoiceField(choices=active_role_choices(), required=False)

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name')

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            active_role = self.cleaned_data.get('active_role') or None
            profile, _ = UserProfile.objects.get_or_create(user=user)
            if active_role:
                UserRole.objects.get_or_create(user_profile=profile, role=active_role)
            profile.active_role = active_role
            profile.save(update_fields=['active_role', 'updated_at'])
        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()
    active_role = forms.ChoiceField(choices=active_role_choices(), required=False)

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'password', 'active_role', 'is_active', 'is_staff', 'is_superuser')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = getattr(self.instance, 'profile', None)
        if profile and profile.active_role:
            self.fields['active_role'].initial = profile.active_role

    def save(self, commit=True):
        user = super().save(commit=commit)

        if commit:
            active_role = self.cleaned_data.get('active_role') or None
            profile, _ = UserProfile.objects.get_or_create(user=user)
            if active_role:
                UserRole.objects.get_or_create(user_profile=profile, role=active_role)
            profile.active_role = active_role
            profile.save(update_fields=['active_role', 'updated_at'])

        return user

    def clean_password(self):
        return self.initial['password']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ['username', 'email', 'first_name', 'last_name', 'active_role', 'is_active', 'date_joined', 'is_staff', 'is_superuser']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    readonly_fields = ('date_joined',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username', 'first_name', 'last_name', 'active_role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('date_joined',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'active_role', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser'),
        }),
    )

    filter_horizontal = ()

    @admin.display(description='Active role')
    def active_role(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.get_active_role_display() if profile and profile.active_role else '-'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'display_name', 'active_role', 'gender', 'followers_count', 'following_count', 'visibility', 'created_at']
    list_filter = ['gender', 'visibility', 'created_at']
    search_fields = ['user__username', 'user__email', 'display_name', 'bio']
    readonly_fields = ['followers_count', 'following_count', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'display_name')
        }),
        ('Profile Details', {
            'fields': ('bio', 'gender', 'date_of_birth', 'visibility', 'active_role')
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

# @admin.register(FollowRequest)
# class FollowRequestAdmin(admin.ModelAdmin):
#     list_display = ["follower", "following", "created_at"]
#     list_filter = ["created_at"]
#     search_fields = [
#         "follower__user__username",
#         "following__user__username",
#     ]
#     ordering = ["-created_at"]
#     raw_id_fields = ["follower", "following"]

#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related("follower__user", "following__user")


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