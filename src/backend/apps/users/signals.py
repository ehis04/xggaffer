from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import F
from .models import UserProfile, Follow

# Increases or decreases the followers_count value for the profile being followed
def _bump_follower_count(profile_id, delta: int):
    if not profile_id:
        return
    
    UserProfile.objects.filter(pk=profile_id).update(
        followers_count=F('followers_count') + delta
    )

# Increases or decreases the following_count value for the profile that started following someone
def _bump_following_count(profile_id, delta: int):
    if not profile_id:
        return
    
    UserProfile.objects.filter(pk=profile_id).update(
        following_count=F('following_count') + delta
    )

# runs after a Follow row is created and increments both users social counters
@receiver(post_save, sender=Follow)
def follow_created(sender, instance, created: bool, **kwargs):
    if not created:
        return
        
    _bump_follower_count(instance.following_id, 1)
    _bump_following_count(instance.follower_id, 1)

# Runs after a Follow row is deleted and decrements both users social counters
  
@receiver(post_delete, sender=Follow)
def follow_deleted(sender, instance: Follow, **kwargs):
    _bump_follower_count(instance.following_id, -1)
    _bump_following_count(instance.follower_id, -1)