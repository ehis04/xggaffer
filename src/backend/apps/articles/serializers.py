"""
Serializers for article recommendation models

Converts article, topic, site, author, rating, feedback, reading history, favourites, and user preference data between model instances and API payloads
"""

from rest_framework import serializers

from common.text_processing import clean_html_text, dedupe_paragraphs, normalize_for_compare
from .models import (
    Article,
    Author,
    Site,
    Topic,
    ArticleRating,
    UserFeedback,
    ReadingHistory,
    UserProfile,
    ArticleFavorite,
)


# ---------------------------------------------------------------------------
# Base content serializers
# ---------------------------------------------------------------------------

# Serializes article topic data
class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ['id', 'name', 'slug', 'description']


# Serializes article source site data
class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ['id', 'name', 'domain', 'logo_url', 'reputation_score', 'trust_score', 'user_sentiment_score']


# Serializes article author data
class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = [
            'id',
            'name',
            'bio',
            'profile_url',
            'avatar_url',
            'expertise_score',
            'credibility_score',
            'is_verified',
        ]


# ---------------------------------------------------------------------------
# Article serializers
# ---------------------------------------------------------------------------

# Serializes article cards and list results
class ArticleListSerializer(serializers.ModelSerializer):
    summary = serializers.SerializerMethodField()
    site = SiteSerializer(read_only=True)
    authors = AuthorSerializer(many=True, read_only=True)
    topics = TopicSerializer(many=True, read_only=True)
    user_rating = serializers.SerializerMethodField()
    user_feedback = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'url', 'summary', 'image_url',
            'site', 'authors', 'topics',
            'publication_date', 'read_time_minutes', 'word_count',
            'quality_score', 'view_count', 'average_rating', 'total_ratings',
            'total_likes', 'total_dislikes', 'is_featured', 'is_recent',
            'user_rating', 'user_feedback', 'is_read', 'is_favorited',
        ]

    # Return the current user's rating for the article
    def get_user_rating(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        rating = ArticleRating.objects.filter(article=obj, user=request.user).first()
        return rating.rating if rating else None

    # Return a cleaned article summary or fallback preview
    def get_summary(self, obj):
        summary = dedupe_paragraphs(clean_html_text(obj.summary))
        if summary:
            return summary

        content = dedupe_paragraphs(clean_html_text(obj.content))
        if content:
            return content[:280]

        return f"Preview unavailable. Open source: {obj.title}"

    # Return the current user's like or dislike feedback for the article
    def get_user_feedback(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        feedback = UserFeedback.objects.filter(
            article=obj, user=request.user, target_type='article'
        ).first()
        return feedback.feedback_type if feedback else None

    # Return whether the current user has read the article
    def get_is_read(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return ReadingHistory.objects.filter(user=request.user, article=obj).exists()

    # Return whether the current user has favourited the article
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return ArticleFavorite.objects.filter(user=request.user, article=obj).exists()


# Serializes full article detail including cleaned body content
class ArticleDetailSerializer(ArticleListSerializer):
    content = serializers.SerializerMethodField()

    class Meta(ArticleListSerializer.Meta):
        fields = ArticleListSerializer.Meta.fields + ['content', 'scraped_date', 'external_shares']

    # Return cleaned article content without duplicating the summary
    def get_content(self, obj):
        summary = clean_html_text(obj.summary)
        content = dedupe_paragraphs(clean_html_text(obj.content))

        if not content:
            return ''

        normalized_summary = normalize_for_compare(summary)
        normalized_content = normalize_for_compare(content)
        if normalized_summary and normalized_summary == normalized_content:
            return ''

        if normalized_summary:
            paragraphs = [segment.strip() for segment in content.split('\n\n') if segment.strip()]
            filtered = [
                paragraph
                for paragraph in paragraphs
                if normalize_for_compare(paragraph) != normalized_summary
            ]
            if filtered:
                return '\n\n'.join(filtered)

        return content


# ---------------------------------------------------------------------------
# Interaction serializers
# ---------------------------------------------------------------------------

# Serializes user article rating records
class ArticleRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleRating
        fields = ['id', 'rating', 'review', 'created_at']
        read_only_fields = ['id', 'created_at']


# Validates article, author, or site feedback requests
class ArticleFeedbackSerializer(serializers.Serializer):
    feedback_type = serializers.ChoiceField(choices=['like', 'dislike'])
    target_type = serializers.ChoiceField(choices=['article', 'author', 'site'])
    target_id = serializers.IntegerField()


# Validates mark-as-read requests
class MarkReadSerializer(serializers.Serializer):
    completed = serializers.BooleanField(default=False)
    read_duration_seconds = serializers.IntegerField(default=0, min_value=0)


# ---------------------------------------------------------------------------
# User profile serializers
# ---------------------------------------------------------------------------

# Serializes article recommendation preferences and inferred user interests
class UserProfileSerializer(serializers.ModelSerializer):
    preferred_topics = TopicSerializer(many=True, read_only=True)
    disliked_topics = TopicSerializer(many=True, read_only=True)
    preferred_authors = AuthorSerializer(many=True, read_only=True)
    preferred_sites = SiteSerializer(many=True, read_only=True)
    disliked_authors = AuthorSerializer(many=True, read_only=True)
    disliked_sites = SiteSerializer(many=True, read_only=True)
    liked_topics = TopicSerializer(many=True, read_only=True)
    inferred_disliked_topics = TopicSerializer(many=True, read_only=True)
    liked_sites = SiteSerializer(many=True, read_only=True)
    inferred_disliked_sites = SiteSerializer(many=True, read_only=True)
    liked_authors = AuthorSerializer(many=True, read_only=True)
    inferred_disliked_authors = AuthorSerializer(many=True, read_only=True)
    articles_liked = serializers.IntegerField(read_only=True)
    articles_disliked = serializers.IntegerField(read_only=True)
    articles_favorited = serializers.IntegerField(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'preferred_topics', 'preferred_authors', 'preferred_sites',
            'disliked_topics', 'disliked_authors', 'disliked_sites',
            'liked_topics', 'inferred_disliked_topics',
            'liked_authors', 'inferred_disliked_authors',
            'liked_sites', 'inferred_disliked_sites',
            'articles_liked', 'articles_disliked', 'articles_favorited',
            'preferred_quality_threshold', 'min_read_time', 'max_read_time',
            'daily_recommendation_count', 'enable_auto_refresh',
        ]


# Validates updates to article recommendation preferences
class UserProfileUpdateSerializer(serializers.Serializer):
    preferred_topic_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
    )
    disliked_topic_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
    )
    preferred_author_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
    )
    disliked_author_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
    )
    preferred_site_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
    )
    disliked_site_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
    )
    preferred_quality_threshold = serializers.FloatField(required=False, min_value=0, max_value=100)
    min_read_time = serializers.IntegerField(required=False, min_value=0)
    max_read_time = serializers.IntegerField(required=False, min_value=0)
    daily_recommendation_count = serializers.IntegerField(required=False, min_value=1, max_value=200)
    enable_auto_refresh = serializers.BooleanField(required=False)

    # Validate preference conflicts and read-time bounds
    def validate(self, attrs):
        preferred_topics = set(attrs.get('preferred_topic_ids', []))
        disliked_topics = set(attrs.get('disliked_topic_ids', []))
        overlap = preferred_topics.intersection(disliked_topics)
        if overlap:
            raise serializers.ValidationError(
                'The same topic cannot be both preferred and disliked.'
            )

        min_read = attrs.get('min_read_time')
        max_read = attrs.get('max_read_time')
        if min_read is not None and max_read is not None and max_read and max_read < min_read:
            raise serializers.ValidationError('max_read_time must be greater than or equal to min_read_time.')

        return attrs