from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Q, F

class gender_choices(models.TextChoices):
    FEMALE = 'F', 'Female'
    MALE = 'M', 'Male'
    OTHER = 'O', 'Other'
    NOT_SPECIFIED = 'NS', 'Not Specified'

class Visibility(models.TextChoices):
    public = 'PB', 'Public'
    private = 'PR', 'Private'

class Roles(models.TextChoices):
    coach = 'C', 'Coach'
    player = 'P', 'Player'
    referee = 'R', 'Referee'
    fan = 'F', 'Fan'

class User(AbstractUser):
    email = models.EmailField(_("email address"), unique=True)
    username = models.CharField(max_length=150, blank=True, null=True, unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=150, blank=True)
    # profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    bio = models.TextField(blank=True)
    gender = models.CharField(max_length=8, choices=gender_choices.choices, default=gender_choices.NOT_SPECIFIED)
    date_of_birth = models.DateField(blank=True, null=True)
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.public)
    followers_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['-followers_count']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def get_display_name(self):
        if self.display_name:
            return self.display_name
        
        f_name = self.user.first_name or ""
        l_name = self.user.last_name or ""
        return f"{f_name} {l_name}".strip() or self.user.username
    
class UserRole(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='roles')
    role = models.CharField(max_length=10, choices=Roles.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'
        unique_together = ('user_profile', 'role')
        indexes = [
            models.Index(fields=['user_profile', 'role']),
        ]
        
    def __str__(self):
        return f"{self.user_profile.user.username} - {self.get_role_display()}"

class Follow(models.Model):
    follower = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Follow'
        verbose_name_plural = 'Follows'
        unique_together = ('follower', 'following')
        constraints = [
            models.CheckConstraint(
                check=~Q(follower=F("following")),
                name='prevent_self_follow'
            )
        ]
        indexes = [
            models.Index(fields=['follower', '-created_at']),
            models.Index(fields=['following', '-created_at']),
        ]
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.follower.user.username} followed {self.following.user.username} "
    
    def clean(self):
        if self.follower == self.following:
            raise ValidationError("You can't follow yourself.")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
        
