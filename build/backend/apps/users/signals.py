from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import F
from .models import UserProfile, Follow

def _bump_follower_count(profile_id, delta: int):
    if not profile_id:
        return
    
    UserProfile.objects.filter(pk=profile_id).update(
        followers_count=F('followers_count') + delta
    )

def _bump_following_count(profile_id, delta: int):
    if not profile_id:
        return
    
    UserProfile.objects.filter(pk=profile_id).update(
        following_count=F('following_count') + delta
    )

@receiver(post_save, sender=Follow)
def follow_created(sender, instance, created: bool, **kwargs):
    if not created:
        return
        
    _bump_follower_count(instance.following_id, 1)
    _bump_following_count(instance.follower_id, 1)
    
@receiver(post_delete, sender=Follow)
def follow_deleted(sender, instance: Follow, **kwargs):
    _bump_follower_count(instance.following_id, -1)
    _bump_following_count(instance.follower_id, -1)