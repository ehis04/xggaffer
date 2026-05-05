from django.db import models
from apps.users.models import User, UserProfile
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Create your models here.

class FitbitToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="fitbit_token", db_index=True)
    fitbit_user_id = models.CharField(max_length=100, blank=True)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField()
    scope = models.CharField(max_length=500, blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Fitbit Token"
        verbose_name_plural = "Fitbit Tokens"
    
    def __str__(self):
        return f"Fitbit Token for {self.user.username}"
    
    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at - timezone.timedelta(seconds=60)
    
    @property
    def is_connected(self) -> bool:
        return bool(self.access_token and self.refresh_token)
    

class DailyActivitySummary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="daily_activity_summaries", db_index=True)
    date = models.DateField()
    
    steps = models.PositiveIntegerField(default=0)
    calories_burned = models.PositiveIntegerField(default=0)
    active_minutes = models.PositiveIntegerField(default=0)
    distance_km = models.FloatField(default=0.0)
    
    resting_heart_rate = models.PositiveIntegerField(null=True, blank=True)
    
    heart_rate_zones = models.JSONField(null=True, blank=True)
    
    synced_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Daily Activity Summary"
        verbose_name_plural = "Daily Activity Summaries"
        unique_together = ("user", "date")
        indexes = [
            models.Index(fields=["user", "-date"]),
            models.Index(fields=["-date"]),
        ]
        ordering = ["-date"]
        
    def __str__(self):
        return f"Daily Activity Summary for {self.user.username} on {self.date}"
    
    #TODO: Add function to use daily activity summary in a user post

