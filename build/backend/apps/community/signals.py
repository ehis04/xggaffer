from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import F
from .models import Like, Post, Comment, HashTag, PostTag, Mention, Notification, NotificationType
from apps.users.models import User
import re
from django.db.models.functions import Lower

#^ Comment Count Signals
# Increases or decreases the number of comments stored on a post
def _bump_comment_count(post_id, delta: int):
    if not post_id:
        return
    
    Post.objects.filter(pk=post_id).update(no_of_comments=F("no_of_comments") + delta)

# Increases or decreases the number of replies stored on a parent comment
def _bump_parent_reply_count(parent_id, delta: int):
    if not parent_id:
        return
    Comment.objects.filter(pk=parent_id).update(no_of_replies=F("no_of_replies") + delta)

# Creates a notification for a comment or reply
def _send_comment_notification(target, initiator, actor, notification_type: NotificationType):
    if not target:
        return
    if initiator.id == actor.id:
        return
    
    Notification.objects.create(triggered_by=actor, user=initiator, notification_type=notification_type, content_object=target)

# Runs when a comment is created and updates post comment counts, reply counts, and notifications
@receiver(post_save, sender=Comment)
def comment_created(sender, instance: Comment, created: bool, **kwargs):
    if not created:
        return
    
    actor = instance.author
    post_author = instance.post.author
    # parent_author = instance.parent.author
    
    _bump_comment_count(instance.post_id, +1)
    if instance.parent_id is None:
        _send_comment_notification(instance, post_author, actor, NotificationType.COMMENT)
    else:
        parent_author = instance.parent.author
        _bump_parent_reply_count(instance.parent_id, +1)
        _send_comment_notification(instance, parent_author, actor, NotificationType.REPLY)

# Runs when a comment is deleted and reduces post comment counts and parent reply counts
@receiver(post_delete, sender=Comment)
def comment_deleted(sender, instance: Comment, **kwargs):
    _bump_comment_count(instance.post_id, -1)
    if instance.parent_id:
        _bump_parent_reply_count(instance.parent_id, -1)

#^ Like Count Signals
# Increases or decreases the like count on any object that stores no_of_likes
def _bump_like_count(target, delta: int):
    if not target:
        return
    
    model = target.__class__
    
    if hasattr(target, "no_of_likes"):
        model.objects.filter(pk=target.pk).update(no_of_likes=F("no_of_likes") + delta)

# Creates a like notification for the owner of the liked post or comment
def _send_like_notification(target, initiator):
    if not target:
        return

    target_author = getattr(target, "author", None)
    if not target_author or target_author.id == initiator.id:
        return

    Notification.objects.create(triggered_by=initiator, user=target_author, notification_type=NotificationType.LIKE, content_object=target)

# Runs when a like is created and updates the liked object's like count
@receiver(post_save, sender=Like)
def like_created(sender, instance: Like, created: bool, **kwargs):
    if not created:
        return
    user = instance.user
    _bump_like_count(instance.content_object, +1)
    _send_like_notification(instance.content_object, user)

# Runs when a like is deleted and reduces the liked object's like count
@receiver(post_delete, sender=Like)
def like_deleted(sender, instance: Like, **kwargs):
    _bump_like_count(instance.content_object, -1)

#^ Hashtag Creation and Count signals

# Matches hashtag values in text
TAG_RE = re.compile(r'(?<!\w)#(\w{1,100})')
#& (?<!\w) = negative lookbehind: the # must not be preceded by a word character

# Normalises a hashtag by removing the hash symbol, trimming spaces, and converting to lowercase
def normalise_tag(body: str) -> str:
    return body.strip().lstrip("#").lower()

#* Finds all hashtags in a body of text with TAG_RE.finditer(...)
#* m.group(1) pulls the captured body (the part after #).
def extract_hashtags(text: str) -> set[str]:
    return {normalise_tag(m.group(1)) for m in TAG_RE.finditer(text or "")}

# Runs when a post is saved and synchronises PostTag rows with the hashtags currently in the post text
@receiver(post_save, sender=Post)
def sync_post_hashtags(sender, instance: Post, created: bool, **kwargs):
    #* Extract hashtags from the posts body
    wanted = extract_hashtags(instance.text_body)
    
    current = set(
        PostTag.objects.filter(post_id=instance.pk)
        .select_related("hashtag")
        .values_list("hashtag__body", flat=True)
    )
    
    to_add = wanted - current
    to_remove = current - wanted
    
    for body in to_add:
        ht, _ = HashTag.objects.get_or_create(body=body)
        PostTag.objects.get_or_create(post_id=instance.pk, hashtag=ht)
        
    if to_remove:
        PostTag.objects.filter(
            post_id=instance.pk, hashtag__body__in=list(to_remove)
        ).delete()

# Runs when a post is linked to a hashtag and increments that hashtag's usage count
@receiver(post_save, sender=PostTag)
def hashtag_link_created(sender, instance: PostTag, created: bool, **kwargs):
    if created:
        HashTag.objects.filter(pk=instance.hashtag_id).update(
            usage_count=F("usage_count") + 1
        )

# Runs when a post hashtag link is deleted and decrements that hashtag's usage count
@receiver(post_delete, sender=PostTag)
def hashtag_link_deleted(sender, instance: PostTag, **kwargs):
    HashTag.objects.filter(pk=instance.hashtag_id).update(
            usage_count=F("usage_count") - 1
        )

#^ Mention Creation signal

# Matches username mentions in text
MENTION_RE = re.compile(r'(?<!\w)@(\w{1,100})')

# Normalises a mention by removing the @ symbol, trimming spaces, and converting to lowercase
def _normalise_mention(body: str) -> str:
    return body.strip().lstrip("@").lower()

# Extracts all mentions from a text body
def extract_mention(text: str) -> set[str]:
    return {_normalise_mention(m.group(1)) for m in MENTION_RE.finditer(text or "")}

# Finds users whose usernames match the extracted mention values
def find_user(mentions: set[str]) -> dict[str]:
    if not mentions:
        return {}
    
    qs = (
        User.objects
        .annotate(username_lower=Lower("username"))
        .filter(username_lower__in=list(mentions))
        .only("id", "username")
    )
    return {u.username.lower(): u for u in qs}

# Synchronises Mention rows and mention notifications for a saved post
def _sync_post_mentions(post: Post):
    wanted = extract_mention(post.text_body)
    
    current = set(
        post.mention.select_related("user_mentioned")
        .values_list("user_mentioned__username", flat=True)
    )
    current = {u.lower() for u in current}
    
    to_add = wanted - current
    to_remove = current - wanted
    
    users_map = find_user(to_add)
    
    for mention in to_add:
        user = users_map.get(mention)
        if user:
            Mention.objects.get_or_create(post=post, user_mentioned=user)
            Notification.objects.create(user=user, triggered_by=post.author, notification_type=NotificationType.MENTION, content_object=post)
            
    if to_remove:
        Mention.objects.filter(post=post, user_mentioned__username__in=list(to_remove),).delete()

# Runs when a post is saved and updates its extracted mentions

@receiver(post_save, sender=Post)
def sync_post_mentions(sender, instance: Post, **kwargs):
    _sync_post_mentions(instance)
    