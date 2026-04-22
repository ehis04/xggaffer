from django.db import models
from apps.users.models import User, UserProfile
from django.db.models import Q, F
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


#& Choices
class Visibility(models.TextChoices):
    PUBLIC = "PB", "Public"
    FOLLOWERS = "F", "Followers"
    PRIVATE = "PR", "Private"

class ModerationStatus(models.TextChoices):
    OK = "OK", "Ok"
    UNDER_REVIEW = "UR", "Under Review"
    REMOVED = "R", "Removed"
    
class TargetType(models.TextChoices):
    POST = "P", "Post"
    COMMENT = "C", "Comment"

class NotificationType(models.TextChoices):
    FOLLOW_REQUEST = "FR", "Follow Request"
    FOLLOW_ACCEPTED = "FA", "Follow Accepted"
    NEW_FOLLOWER = "NF", "New Follower"
    MENTION = "M", "Mention"
    LIKE = "L", "Like"
    COMMENT = "C", "Comment"
    REPLY = "RY", "Reply"
    REPOST = "R", "Repost"

#& Functions
def function_targets():
    return (
        models.Q(app_label="community", model="post")
        | models.Q(app_label="community", model="comment")
        | models.Q(app_label="users", model="followrequest")
    )

#& Community Models
class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts", db_index=True)
    text_body = models.TextField(blank=True, default="")
    attachments_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    no_of_likes = models.PositiveIntegerField(default=0)
    no_of_comments = models.PositiveIntegerField(default=0)
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)
    moderation_status = models.CharField(max_length=15, choices=ModerationStatus.choices, default=ModerationStatus.OK)
    
    # Include workout_plan and meal_plan once they are created
    # Include images once cloud storage is set up
    
    def __str__(self):
        return f"Post {self.id} Created by {self.author.username}"

class PostView(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_views", db_index=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="post_views", db_index=True)
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Post View")
        verbose_name_plural = _("Post Views")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "post"],
                name="unique_post_view_per_user",
            )
        ]
        indexes = [
            models.Index(fields=["user", "-viewed_at"]),
            models.Index(fields=["post", "-viewed_at"]),
        ]
        ordering = ("-viewed_at",)

    def __str__(self):
        return f"{self.user.username} viewed post {self.post.id}"

    def get_absolute_url(self):
        return reverse("PostView_detail", kwargs={"pk": self.pk})

class Comment(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments", db_index=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name="comments", db_index=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    text_body = models.TextField(blank=True, default="")
    no_of_likes = models.PositiveIntegerField(default=0)
    no_of_replies = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    moderation_status = models.CharField(max_length=15, choices=ModerationStatus.choices, default=ModerationStatus.OK)

    class Meta:
        verbose_name = _("Comment")
        verbose_name_plural = _("Comments")
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["post", "-created_at"]),
            models.Index(fields=["author", "-created_at"]),
            models.Index(fields=["moderation_status"]),
        ]

    def __str__(self):
        if self.parent_id:
            return f"Reply {self.pk} by @{self.author.username} on @{self.parent.author.username}'s Post"
        return f"Comment {self.pk} by @{self.author.username} on @{self.post.author.username}'s Post"

    def get_absolute_url(self):
        return reverse("comment_detail", kwargs={"pk": self.pk})
    
    def is_reply(self) -> bool:
        return self.parent_id is not None
    
    def clean(self):
        if self.parent_id is None and self.post_id is None:
            raise ValidationError(_("Comment must belong to a post."))
        
        if self.parent_id and self.post_id is None:
            self.post_id = self.parent.post_id

        if self.parent_id and self.parent and self.parent.post_id != self.post_id:
            raise ValidationError(_("Parent comment belongs to a different post."))
        
        if self.parent_id is not None and self.pk is not None:
            if self.parent_id == self.pk:
                raise ValidationError(_("A comment cannot be its own parent."))
    
    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="likes", db_index=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, limit_choices_to=function_targets,)
    object_id = models.PositiveIntegerField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        verbose_name = _("Like")
        verbose_name_plural = _("Likes")
        
        constraints = [
            models.UniqueConstraint(
                fields=["user", "content_type", "object_id"],
                name="unique_like_per_user_per_object",
            )
        ]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["user", "-created_at"]),
        ]
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user.username} Liked {self.content_object}"

    def get_absolute_url(self):
        return reverse("like_detail", kwargs={"pk": self.pk})

class HashTag(models.Model):

    body = models.CharField(max_length=100)
    usage_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _("HashTag")
        verbose_name_plural = _("HashTags")
        indexes = [models.Index(fields=["body"])]
        
    def save(self, *args, **kwargs):
        if self.body:
            self.body = self.body.strip().lstrip("#").lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"#{self.body}"

    def get_absolute_url(self):
        return reverse("hashTag_detail", kwargs={"pk": self.pk})

class PostTag(models.Model):

    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name="post_tags", db_index=True)
    hashtag = models.ForeignKey(HashTag, on_delete=models.CASCADE, related_name="post_tags", db_index=True)

    class Meta:
        verbose_name = _("PostTag")
        verbose_name_plural = _("PostTags")
        
        constraints = [
            models.UniqueConstraint(fields=["post", "hashtag"], name="uniq_post_hashtag")
        ]
        indexes = [
            models.Index(fields=["hashtag", "post"]),
        ]

    def __str__(self):
        return f"{self.hashtag.body} has been used on {self.post.author.username}'s post"

    def get_absolute_url(self):
        return reverse("postTag_detail", kwargs={"pk": self.pk})
    
class Mention(models.Model):
    user_mentioned = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mention", db_index=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name="mention", db_index=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name="mention", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Mention")
        verbose_name_plural = _("Mentions")
        
        ordering = ("-created_at",)

    def __str__(self):
        return f"@{self.user_mentioned.username} has been mentioned"

    def get_absolute_url(self):
        return reverse("mention_detail", kwargs={"pk": self.pk})

class Notification(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notification", db_index=True)
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.MENTION)
    triggered_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notification_triggered", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, limit_choices_to=function_targets,)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")
    is_read = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")

    def __str__(self):
        if self.notification_type == NotificationType.MENTION:
            return f"@{self.triggered_by.username} has mentioned @{self.user.username}"
        elif self.notification_type == NotificationType.LIKE:
            return f"@{self.triggered_by.username} has liked @{self.user.username}'s {self.content_type.name}"
        elif self.notification_type == NotificationType.COMMENT:
            return f"@{self.triggered_by.username} has commented on @{self.user.username}'s {self.content_type.name}"
        elif self.notification_type == NotificationType.REPLY:
            return f"@{self.triggered_by.username} has replied to @{self.user.username}'s {self.content_type.name}"
        elif self.notification_type == NotificationType.NEW_FOLLOWER:
            return f"@{self.triggered_by.username} followed @{self.user.username}'s"
        elif self.notification_type == NotificationType.FOLLOW_REQUEST:
            return f"@{self.triggered_by.username} requested to follow @{self.user.username}'s"
        elif self.notification_type == NotificationType.FOLLOW_ACCEPTED:
            return f"@{self.triggered_by.username} accepted @{self.user.username}'s follow request"
        return f"{self.triggered_by.username} has notified {self.user.username}"

    def get_absolute_url(self):
        return reverse("notification_detail", kwargs={"pk": self.pk})


class Block(models.Model):

    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name="block_initiated", db_index=True)
    blocked_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="block_received", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Block")
        verbose_name_plural = _("Blocks")
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked_user"], name="uniq_blocker_blocked"),
            models.CheckConstraint(check=~Q(blocker=F("blocked_user")), name="no_self_block"),
        ]
        indexes = [models.Index(fields=["blocker", "blocked_user"])]

    def __str__(self):
        return f"{self.blocker.username} has blocked {self.blocked_user.username}"

    def get_absolute_url(self):
        return reverse("block_detail", kwargs={"pk": self.pk})

#! Things to add
#^ Follow

#& User Interest Model

class UserInterestProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='interest_profile')
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Interest Profile"

class UserHashtagInterest(models.Model):
    profile = models.ForeignKey(UserInterestProfile, on_delete=models.CASCADE, related_name='hashtag_interests')
    hashtag = models.ForeignKey(HashTag, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)
    last_interaction = models.DateTimeField()
    
    class Meta:
        unique_together = ['profile', 'hashtag']
        indexes = [models.Index(fields=['profile', '-score'])]
    
    def __str__(self):
        return f"{self.profile.user.username} -> #{self.hashtag.body} ({self.score})"

class UserAuthorInterest(models.Model):
    profile = models.ForeignKey(UserInterestProfile, on_delete=models.CASCADE, related_name='author_interests')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)
    last_interaction = models.DateTimeField()
    
    class Meta:
        unique_together = ['profile', 'author']
        indexes = [models.Index(fields=['profile', '-score'])]
    
    def __str__(self):
        return f"{self.profile.user.username} -> @{self.author.username} ({self.score})"

class PostUserInterestScore(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, db_index=True)
    hashtag_interest_score = models.FloatField(default=0.0) # Max hashtag interest match
    author_interest_score = models.FloatField(default=0.0) # author interest match
    combined_interest_score = models.FloatField(default=0.0) # final combined score
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'post']
        indexes = [
            models.Index(fields=['user', '-combined_interest_score']),
            models.Index(fields=['post', 'user']),
            models.Index(fields=['-created_at']),
        ]
        
        ordering = ['-created_at']
        
        verbose_name = _("PostUserInterestScore")
        verbose_name_plural = _("PostUserInterestScores")

    def __str__(self):
        return f"{self.user.username} -> Post {self.post.id} (score: {self.combined_interest_score:.2f})"

    def get_absolute_url(self):
        return reverse("PostUserInterestScore_detail", kwargs={"pk": self.pk})

    