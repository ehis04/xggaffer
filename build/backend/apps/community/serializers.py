from rest_framework import serializers
from .models import Post, Comment, HashTag, PostTag, Notification, Mention, Block, Like, PostView
from apps.users.models import User, UserProfile

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['author', 'text_body', 'attachments_count', 'created_at', 'no_of_likes', 'no_of_comments', 'visibility']
        read_only_fields = ['author', 'moderation_status', 'no_of_likes', 'attachments_count', 'created_at', 'no_of_comments']

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = "__all__"
        read_only_fields = ['author']


class HashTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = HashTag
        fields = ['id', 'body', 'usage_count']

class PostTagSerializer(serializers.ModelSerializer):
    hashtag = HashTagSerializer(read_only=True)
    
    class Meta:
        model = PostTag
        fields = ['hashtag']
        
class CommentSummarySerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()
    
    class Meta:
        model = Comment
        fields = ['id', 'author', 'text_body', 'created_at', 'no_of_likes']
        
class CommentListSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source='author.username', read_only=True)
    children = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = ['id', 'author', 'text_body', 'created_at', 'no_of_likes', 'no_of_replies', 'post', 'parent', 'moderation_status', 'children', 'is_liked']
        
    def get_children(self, obj):
        qs = obj.children.select_related("author").filter(moderation_status="OK")
        return CommentListSerializer(qs, many=True, context=self.context).data

    def get_is_liked(self, obj):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            from django.contrib.contenttypes.models import ContentType
            content_type = ContentType.objects.get_for_model(Comment)
            return Like.objects.filter(
                user=request.user,
                content_type=content_type,
                object_id=obj.id
            ).exists()
        return False

class PostAuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class ExplorePostSerializer(serializers.ModelSerializer):
    author = PostAuthorSerializer(read_only=True)
    post_tags = PostTagSerializer(read_only=True)
    recent_comments = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    hashtags = serializers.SerializerMethodField()
    time_since_posted = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    ranked_score = serializers.FloatField(read_only=True, required=False)
    popularity = serializers.FloatField(read_only=True, required=False)
    recency_scaled = serializers.FloatField(read_only=True, required=False)
    
    class Meta:
        model = Post
        fields = ['id', 'author', 'text_body', 'created_at', 'no_of_likes', 'no_of_comments', 'visibility', 'post_tags', 'recent_comments', 'is_liked', 'hashtags', 'time_since_posted', 'type', 'ranked_score', 'popularity', 'recency_scaled']
        read_only_fields = ['id', 'author', 'created_at', 'no_of_likes', 'no_of_comments', 'attachments_count', 'type']
        
    def get_type(self, obj):
        return "post"

    def get_recent_comments(self, obj):
        recent_comments = obj.comments.filter(
            moderation_status='OK'
        ).select_related('author')[:2]
        return CommentSummarySerializer(recent_comments, many=True).data
    
    def get_is_liked(self, obj):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            from django.contrib.contenttypes.models import ContentType
            content_type = ContentType.objects.get_for_model(Post)
            return Like.objects.filter(user=request.user, content_type=content_type, object_id=obj.id).exists()
        return False

    def get_hashtags(self, obj):
        return [tag.hashtag.body for tag in obj.post_tags.all()]

    def get_time_since_posted(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 0:
            return f"{diff.days}d"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m"
        else:
            return "now"
        
class CommentResponseSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source='author.username', read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'author', 'text_body', 'created_at', 'no_of_likes', 'no_of_replies', 'post', 'parent', 'moderation_status']
        