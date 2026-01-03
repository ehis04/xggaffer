from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db.models import Q, F
from .managers import UserManager


class Gender(models.TextChoices):
    FEMALE = 'F', 'Female'
    MALE = 'M', 'Male'
    OTHER = 'O', 'Other'
    NOT_SPECIFIED = 'NS', 'Not Specified'


class Visibility(models.TextChoices):
    PUBLIC = 'PB', 'Public'
    PRIVATE = 'PR', 'Private'


class Role(models.TextChoices):
    COACH = 'C', 'Coach'
    PLAYER = 'P', 'Player'
    REFEREE = 'R', 'Referee'
    FAN = 'F', 'Fan'


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, blank=True, null=True, unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'users'
        verbose_name = 'user'
        verbose_name_plural = 'users'
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.email
    
    def get_short_name(self):
        return self.first_name or self.email.split('@')[0]


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=150, blank=True)
    bio = models.TextField(blank=True)
    gender = models.CharField(
        max_length=8,
        choices=Gender.choices,
        default=Gender.NOT_SPECIFIED
    )
    date_of_birth = models.DateField(blank=True, null=True)
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.PUBLIC
    )
    followers_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        indexes = [
            models.Index(fields=['-followers_count']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        identifier = self.user.username or self.user.email
        return f"{identifier}'s Profile"
    
    def get_display_name(self):
        if self.display_name:
            return self.display_name
        
        full_name = f"{self.user.first_name} {self.user.last_name}".strip()
        return full_name or self.user.username or self.user.email


class UserRole(models.Model):
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='roles'
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'
        constraints = [
            models.UniqueConstraint(
                fields=['user_profile', 'role'],
                name='unique_user_role'
            )
        ]
        indexes = [
            models.Index(fields=['user_profile', 'role']),
        ]
    
    def __str__(self):
        identifier = self.user_profile.user.username or self.user_profile.user.email
        return f"{identifier} - {self.get_role_display()}"


class Follow(models.Model):
    follower = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='following'
    )
    following = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='followers'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Follow'
        verbose_name_plural = 'Follows'
        constraints = [
            models.UniqueConstraint(
                fields=['follower', 'following'],
                name='unique_follow_relationship'
            ),
            models.CheckConstraint(
                condition=~Q(follower=F('following')),
                name='prevent_self_follow'
            )
        ]
        indexes = [
            models.Index(fields=['follower', '-created_at']),
            models.Index(fields=['following', '-created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        follower_name = self.follower.user.username or self.follower.user.email
        following_name = self.following.user.username or self.following.user.email
        return f"{follower_name} followed {following_name}"
    
    def clean(self):
        if self.follower == self.following:
            raise ValidationError("You can't follow yourself.")
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        self.full_clean()
        super().save(*args, **kwargs)
        
        if is_new:
            UserProfile.objects.filter(pk=self.follower_id).update(
                following_count=F('following_count') + 1
            )
            UserProfile.objects.filter(pk=self.following_id).update(
                followers_count=F('followers_count') + 1
            )
    
    def delete(self, *args, **kwargs):
        follower_id = self.follower_id
        following_id = self.following_id
        super().delete(*args, **kwargs)
        
        UserProfile.objects.filter(pk=follower_id).update(
            following_count=F('following_count') - 1
        )
        UserProfile.objects.filter(pk=following_id).update(
            followers_count=F('followers_count') - 1
        )