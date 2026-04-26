import html
import re

from rest_framework import serializers

from .models import Article, Author, Site, Topic, ArticleRating, UserFeedback, ReadingHistory, UserProfile


_BLOCK_BREAK_RE = re.compile(r'</?(p|div|br|li|ul|ol|h[1-6]|blockquote)[^>]*>', re.IGNORECASE)
_TAG_RE = re.compile(r'<[^>]+>')
_WHITESPACE_RE = re.compile(r'[ \t\f\v]+')
_PROMO_LINE_RE = re.compile(
    r'(?i)(live scores|table|top scorers|follow us on\s+\w+|continue reading\.{0,3})'
)


def _strip_source_artifacts(text: str) -> str:
    normalized = text
    normalized = normalized.replace('⚽', '\n\n')
    normalized = normalized.replace('|', '\n')
    normalized = re.sub(r'\.(\s*)\[', '.\n\n[', normalized)
    normalized = re.sub(r'(?<!\n)\s*(\[[^\]]+\])', '\n\n\\1', normalized)
    normalized = re.sub(r'(?<=[a-z])(?=[A-Z][a-z]+\s[A-Z])', '\n\n', normalized)
    normalized = re.sub(r'(?i)\bcontinue reading\.{0,3}\b', '', normalized)

    lines = [line.strip() for line in normalized.split('\n')]
    kept_lines = [line for line in lines if line and not _PROMO_LINE_RE.fullmatch(line)]
    return '\n'.join(kept_lines)


def _clean_text(value: str | None) -> str:
    if not value:
        return ''

    text = html.unescape(value)
    text = text.replace('\xa0', ' ')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = _BLOCK_BREAK_RE.sub('\n\n', text)
    text = _TAG_RE.sub(' ', text)
    text = _strip_source_artifacts(text)
    text = _WHITESPACE_RE.sub(' ', text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text.strip()


def _normalize_for_compare(value: str) -> str:
    lowered = value.casefold()
    lowered = re.sub(r'\s+', ' ', lowered)
    return lowered.strip(' .,!?:;"\'()[]{}')


def _dedupe_paragraphs(value: str) -> str:
    paragraphs = [segment.strip() for segment in re.split(r'\n{2,}', value) if segment.strip()]
    if len(paragraphs) <= 1 and '\n' in value:
        paragraphs = [segment.strip() for segment in value.split('\n') if segment.strip()]
    deduped: list[str] = []
    seen: set[str] = set()

    for paragraph in paragraphs:
        key = _normalize_for_compare(paragraph)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(paragraph)

    return '\n\n'.join(deduped)


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ['id', 'name', 'slug', 'description']


class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ['id', 'name', 'domain', 'logo_url', 'reputation_score', 'trust_score', 'user_sentiment_score']


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


class ArticleListSerializer(serializers.ModelSerializer):
    summary = serializers.SerializerMethodField()
    site = SiteSerializer(read_only=True)
    authors = AuthorSerializer(many=True, read_only=True)
    topics = TopicSerializer(many=True, read_only=True)
    user_rating = serializers.SerializerMethodField()
    user_feedback = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'url', 'summary', 'image_url',
            'site', 'authors', 'topics',
            'publication_date', 'read_time_minutes', 'word_count',
            'quality_score', 'view_count', 'average_rating', 'total_ratings',
            'total_likes', 'total_dislikes', 'is_featured', 'is_recent',
            'user_rating', 'user_feedback', 'is_read',
        ]

    def get_user_rating(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        rating = ArticleRating.objects.filter(article=obj, user=request.user).first()
        return rating.rating if rating else None

    def get_summary(self, obj):
        summary = _dedupe_paragraphs(_clean_text(obj.summary))
        if summary:
            return summary

        content = _dedupe_paragraphs(_clean_text(obj.content))
        if content:
            return content[:280]

        return f"Preview unavailable. Open source: {obj.title}"

    def get_user_feedback(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        feedback = UserFeedback.objects.filter(
            article=obj, user=request.user, target_type='article'
        ).first()
        return feedback.feedback_type if feedback else None

    def get_is_read(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return ReadingHistory.objects.filter(user=request.user, article=obj).exists()


class ArticleDetailSerializer(ArticleListSerializer):
    content = serializers.SerializerMethodField()

    class Meta(ArticleListSerializer.Meta):
        fields = ArticleListSerializer.Meta.fields + ['content', 'scraped_date', 'external_shares']

    def get_content(self, obj):
        summary = _clean_text(obj.summary)
        content = _dedupe_paragraphs(_clean_text(obj.content))

        if not content:
            return ''

        normalized_summary = _normalize_for_compare(summary)
        normalized_content = _normalize_for_compare(content)
        if normalized_summary and normalized_summary == normalized_content:
            return ''

        if normalized_summary:
            paragraphs = [segment.strip() for segment in content.split('\n\n') if segment.strip()]
            filtered = [
                paragraph
                for paragraph in paragraphs
                if _normalize_for_compare(paragraph) != normalized_summary
            ]
            if filtered:
                return '\n\n'.join(filtered)

        return content


class ArticleRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleRating
        fields = ['id', 'rating', 'review', 'created_at']
        read_only_fields = ['id', 'created_at']


class ArticleFeedbackSerializer(serializers.Serializer):
    feedback_type = serializers.ChoiceField(choices=['like', 'dislike'])
    target_type = serializers.ChoiceField(choices=['article', 'author', 'site'])
    target_id = serializers.IntegerField()


class MarkReadSerializer(serializers.Serializer):
    completed = serializers.BooleanField(default=False)
    read_duration_seconds = serializers.IntegerField(default=0, min_value=0)


class UserProfileSerializer(serializers.ModelSerializer):
    preferred_topics = TopicSerializer(many=True, read_only=True)
    preferred_authors = AuthorSerializer(many=True, read_only=True)
    preferred_sites = SiteSerializer(many=True, read_only=True)
    disliked_authors = AuthorSerializer(many=True, read_only=True)
    disliked_sites = SiteSerializer(many=True, read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'preferred_topics', 'preferred_authors', 'preferred_sites',
            'disliked_authors', 'disliked_sites',
            'preferred_quality_threshold', 'min_read_time', 'max_read_time',
            'daily_recommendation_count', 'enable_auto_refresh',
        ]
