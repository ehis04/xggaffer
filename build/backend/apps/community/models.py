from django.db import models
from apps.users.models import User
from django.db.models import Q, F
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


#& Choices
# visibility options for posts
class Visibility(models.TextChoices):
    PUBLIC = "PB", "Public"
    FOLLOWERS = "F", "Followers"
    PRIVATE = "PR", "Private"

# moderation choices for posts
class ModerationStatus(models.TextChoices):
    OK = "OK", "Ok"
    UNDER_REVIEW = "UR", "Under Review"
    REMOVED = "R", "Removed"

# content type choics
class TargetType(models.TextChoices):
    POST = "P", "Post"
    COMMENT = "C", "Comment"

# the different notification types a user can receive
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
# limits generic relations to posts comments, and follow requests
def function_targets():
    return (
        models.Q(app_label="community", model="post")
        | models.Q(app_label="community", model="comment")
        | models.Q(app_label="users", model="followrequest")
    )

#& Community Models
# stores a community post created by a user

class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts", db_index=True)
    text_body = models.TextField(blank=True, default="")
    attachments_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    no_of_likes = models.PositiveIntegerField(default=0)
    no_of_comments = models.PositiveIntegerField(default=0)
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)
    moderation_status = models.CharField(max_length=15, choices=ModerationStatus.choices, default=ModerationStatus.OK)
    
    # Include images once cloud storage is set up
    
    def __str__(self):
        return f"Post {self.id} Created by {self.author.username}"


# stores words or phrases that automatically send a post to moderation review
class BannedWord(models.Model):
    term = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Banned Word")
        verbose_name_plural = _("Banned Words")
        ordering = ("term",)
        indexes = [models.Index(fields=["is_active", "term"])]

    def save(self, *args, **kwargs):
        if self.term:
            self.term = self.term.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.term


# stores user reports against posts and prevents duplicate reports from a user
class PostReport(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reports", db_index=True)
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_reports", db_index=True)
    reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Post Report")
        verbose_name_plural = _("Post Reports")
        constraints = [
            models.UniqueConstraint(fields=["post", "reporter"], name="unique_post_report_per_user"),
        ]
        indexes = [
            models.Index(fields=["post", "-created_at"]),
            models.Index(fields=["reporter", "-created_at"]),
        ]
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.reporter.username} reported post {self.post_id}"

# tracks that a user has viewed a specific post
class PostView(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_views", db_index=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="post_views", db_index=True)
    viewed_at = models.DateTimeField(auto_now_add=True)
    
 # prevents duplicate post view records for the same user and post
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

    # returns the detail URL for this post view record
    def get_absolute_url(self):
        return reverse("PostView_detail", kwargs={"pk": self.pk})

# stores comments and replies attached to posts
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
    
    # checks whether this comment is a reply to another comment
    def is_reply(self) -> bool:
        return self.parent_id is not None
    
    # validates that comments belong to a post and replies stay attached to the same post as their parent
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

# stores a like made by a user on a post or comment using a generic relation
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

# stores a hashtag that can be attached to posts
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

# links a post to a hashtag
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

# stores a user mention made inside a post or comment
   
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

# stores a notification sent to a user about an action triggered by another user
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


# stores that one user has blocked another user
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

# stores the overall interest profile used to personalise community content for a user
class UserInterestProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='interest_profile')
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Interest Profile"

# stores how interested a user is in a specific hashtag
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

# stores how interested a user is in content from a specific author
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

# stores the calculated interest score between a user and a specific post
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

    
