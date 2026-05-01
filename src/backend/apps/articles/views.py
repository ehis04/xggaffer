"""
API views for article feeds, interactions, and user article preferences

Handles personalised feeds, favourites, article details, ratings, feedback, read history, lookup lists, and preference profile updates
"""

from __future__ import annotations

import logging

from django.db import transaction
from django.db.models import Avg, Case, Count, IntegerField, Q, When
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.counters import decrement_count, increment_count
from common.pagination import StandardPageNumberPagination
from .models import (
    Article, Author, Site, Topic,
    ArticleRating, UserFeedback, ReadingHistory, UserProfile,
    UserRecommendation,
    ArticleFavorite,
)
from .serializers import (
    ArticleDetailSerializer,
    ArticleListSerializer,
    ArticleRatingSerializer,
    ArticleFeedbackSerializer,
    MarkReadSerializer,
    TopicSerializer,
    SiteSerializer,
    AuthorSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
)

_logger = logging.getLogger(__name__)
MAX_FILTER_OPTIONS = 12


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

# Build the shared filter for valid external article sources
def _valid_source_filter() -> Q:
    return (
        Q(url__startswith='http')
        & ~Q(url__icontains='.local')
        & ~Q(url__icontains='zclkvisitor')
        & ~Q(url__icontains='campaignid=')
        & ~Q(url__icontains='clickid=')
        & ~Q(url__icontains='theatheletic.com')
    )


def _feed_base_queryset_for_user(user):
    today = timezone.now().date()
    recs = UserRecommendation.objects.filter(user=user, batch_date=today)
    if recs.exists():
        article_ids = list(recs.values_list('article_id', flat=True))
        return Article.objects.filter(id__in=article_ids, is_active=True).filter(_valid_source_filter())
    return Article.objects.filter(is_active=True).filter(_valid_source_filter())


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

# Pagination settings for article feed responses
class ArticlePagination(StandardPageNumberPagination):
    max_page_size = 50


# ---------------------------------------------------------------------------
# Article feed and detail views
# ---------------------------------------------------------------------------

# Returns the personalised article feed for the authenticated user
class ArticleFeedView(ListAPIView):
    serializer_class = ArticleListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ArticlePagination

    # Build the article feed queryset from recommendations, filters, search, and sorting
    def get_queryset(self):
        user = self.request.user
        topic_param = self.request.query_params.get('topic')
        site_param = self.request.query_params.get('site')
        author_param = self.request.query_params.get('author')
        sort_param = (self.request.query_params.get('sort') or 'relevance').strip().lower()
        q_param = (self.request.query_params.get('q') or '').strip()

        from django.utils import timezone
        today = timezone.now().date()
        recs = (
            UserRecommendation.objects
            .filter(user=user, batch_date=today)
            .select_related('article__site')
            .prefetch_related('article__authors', 'article__topics')
            .order_by('-score')
        )
        has_recs = recs.exists()

        if has_recs:
            article_ids = list(recs.values_list('article_id', flat=True))
            qs = Article.objects.filter(
                id__in=article_ids,
                is_active=True,
            ).filter(_valid_source_filter())

            if sort_param == 'relevance':
                order_by_case = Case(
                    *[When(id=article_id, then=position) for position, article_id in enumerate(article_ids)],
                    output_field=IntegerField(),
                )
                qs = qs.order_by(order_by_case)
        else:
            qs = Article.objects.filter(is_active=True).filter(_valid_source_filter()).order_by('-publication_date')

        qs = qs.select_related('site').prefetch_related('authors', 'topics')

        if topic_param:
            if topic_param.isdigit():
                qs = qs.filter(topics__id=int(topic_param))
            else:
                qs = qs.filter(topics__slug=topic_param)

        if site_param and site_param.isdigit():
            qs = qs.filter(site_id=int(site_param))

        if author_param and author_param.isdigit():
            qs = qs.filter(authors__id=int(author_param))

        if q_param:
            qs = qs.filter(
                Q(title__icontains=q_param)
                | Q(summary__icontains=q_param)
                | Q(content__icontains=q_param)
                | Q(site__name__icontains=q_param)
                | Q(authors__name__icontains=q_param)
                | Q(topics__name__icontains=q_param)
            )

        if sort_param == 'recent':
            qs = qs.order_by('-publication_date')
        elif sort_param == 'popularity':
            qs = qs.order_by('-total_likes', '-view_count', '-publication_date')
        elif sort_param == 'relevance' and not has_recs:
            qs = qs.order_by('-quality_score', '-publication_date')
        elif sort_param not in ('recent', 'popularity', 'relevance'):
            qs = qs.order_by('-publication_date')

        return qs.distinct()


# Returns the authenticated user's favourited articles as a feed
class FavoriteArticleFeedView(ArticleFeedView):

    # Limit the base feed queryset to the user's favourited article IDs
    def get_queryset(self):
        base_qs = super().get_queryset()
        favorite_ids = ArticleFavorite.objects.filter(user=self.request.user).values_list('article_id', flat=True)
        return base_qs.filter(id__in=favorite_ids).distinct()


# Returns one article and increments its view count
class ArticleDetailView(RetrieveAPIView):
    queryset = (
        Article.objects.filter(is_active=True)
        .filter(_valid_source_filter())
        .select_related('site')
        .prefetch_related('authors', 'topics')
    )
    serializer_class = ArticleDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    lookup_url_kwarg = 'article_id'

    # Increment the article view count before returning detail data
    def retrieve(self, request, *args, **kwargs):
        article = self.get_object()
        article.view_count += 1
        article.save(update_fields=['view_count'])
        return super().retrieve(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Article interaction views
# ---------------------------------------------------------------------------

# Creates, updates, or deletes the authenticated user's article rating
class ArticleRateView(APIView):
    permission_classes = [IsAuthenticated]

    # Create or update a rating for an article
    @transaction.atomic
    def post(self, request, article_id: int):
        article = get_object_or_404(Article, pk=article_id, is_active=True)
        serializer = ArticleRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rating_obj, _ = ArticleRating.objects.update_or_create(
            article=article,
            user=request.user,
            defaults={
                'rating': serializer.validated_data['rating'],
                'review': serializer.validated_data.get('review', ''),
            },
        )

        agg = ArticleRating.objects.filter(article=article).aggregate(
            count=Count('id'), avg=Avg('rating')
        )
        article.total_ratings = agg['count']
        article.average_rating = agg['avg'] or 0.0
        article.save(update_fields=['total_ratings', 'average_rating'])

        return Response(ArticleRatingSerializer(rating_obj).data, status=status.HTTP_200_OK)

    # Delete the authenticated user's rating for an article
    def delete(self, request, article_id: int):
        article = get_object_or_404(Article, pk=article_id, is_active=True)
        ArticleRating.objects.filter(article=article, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Handles like and dislike feedback for articles, authors, and sites
class ArticleFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    # Create, update, or remove feedback for a selected target
    @transaction.atomic
    def post(self, request):
        serializer = ArticleFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_type = serializer.validated_data['target_type']
        feedback_type = serializer.validated_data['feedback_type']
        target_id = serializer.validated_data['target_id']

        article = author = site = None
        if target_type == 'article':
            article = get_object_or_404(Article, pk=target_id)
        elif target_type == 'author':
            author = get_object_or_404(Author, pk=target_id)
        elif target_type == 'site':
            site = get_object_or_404(Site, pk=target_id)

        existing = UserFeedback.objects.filter(
            user=request.user,
            target_type=target_type,
            article=article,
            author=author,
            site=site,
        ).first()

        if existing:
            if existing.feedback_type == feedback_type:
                self._decrement_counts(existing)
                existing.delete()
                return Response({'status': 'removed'}, status=status.HTTP_200_OK)
            else:
                self._decrement_counts(existing)
                existing.feedback_type = feedback_type
                existing.save(update_fields=['feedback_type'])
                self._increment_counts(existing)
                return Response({'status': 'updated', 'feedback_type': feedback_type})

        feedback = UserFeedback.objects.create(
            user=request.user,
            feedback_type=feedback_type,
            target_type=target_type,
            article=article,
            author=author,
            site=site,
        )
        self._increment_counts(feedback)
        return Response({'status': 'created', 'feedback_type': feedback_type}, status=status.HTTP_201_CREATED)

    # Increment the matching feedback counter for a feedback target
    def _increment_counts(self, feedback: UserFeedback):
        target = feedback.article or feedback.author or feedback.site
        if not target:
            return
        field = 'total_likes' if feedback.feedback_type == 'like' else 'total_dislikes'
        increment_count(type(target), target.pk, field)

    # Decrement the matching feedback counter for a feedback target
    def _decrement_counts(self, feedback: UserFeedback):
        target = feedback.article or feedback.author or feedback.site
        if not target:
            return
        field = 'total_likes' if feedback.feedback_type == 'like' else 'total_dislikes'
        decrement_count(type(target), target.pk, field)


# Toggles an article favourite for the authenticated user
class ArticleFavoriteToggleView(APIView):
    permission_classes = [IsAuthenticated]

    # Create or remove an article favourite
    @transaction.atomic
    def post(self, request, article_id: int):
        article = get_object_or_404(Article, pk=article_id, is_active=True)
        favorite = ArticleFavorite.objects.filter(user=request.user, article=article).first()

        if favorite:
            favorite.delete()
            return Response({'status': 'removed', 'is_favorited': False}, status=status.HTTP_200_OK)

        ArticleFavorite.objects.create(user=request.user, article=article)
        return Response({'status': 'created', 'is_favorited': True}, status=status.HTTP_201_CREATED)


# Records that the authenticated user has read an article
class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    # Create or update a reading history record
    @transaction.atomic
    def post(self, request, article_id: int):
        article = get_object_or_404(Article, pk=article_id, is_active=True)
        serializer = MarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        history, created = ReadingHistory.objects.update_or_create(
            user=request.user,
            article=article,
            defaults={
                'completed': serializer.validated_data['completed'],
                'time_spent_seconds': serializer.validated_data['read_duration_seconds'],
            },
        )

        if created:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile.articles_read += 1
            profile.save(update_fields=['articles_read'])

        return Response({'status': 'recorded', 'completed': history.completed})


# ---------------------------------------------------------------------------
# Lookup list views
# ---------------------------------------------------------------------------

# Returns all article topics
class TopicListView(ListAPIView):
    serializer_class = TopicSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        base_articles = _feed_base_queryset_for_user(self.request.user)
        return (
            Topic.objects
            .filter(articles__in=base_articles)
            .annotate(article_count=Count('articles', filter=Q(articles__in=base_articles), distinct=True))
            .filter(article_count__gt=0)
            .order_by('-article_count', 'name')[:MAX_FILTER_OPTIONS]
        )


# Returns all active article source sites
class SiteListView(ListAPIView):
    serializer_class = SiteSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        base_articles = _feed_base_queryset_for_user(self.request.user)
        return (
            Site.objects
            .filter(is_active=True, article__in=base_articles)
            .annotate(article_count=Count('article', filter=Q(article__in=base_articles), distinct=True))
            .filter(article_count__gt=0)
            .order_by('-article_count', 'name')[:MAX_FILTER_OPTIONS]
        )


# Returns all article authors
class AuthorListView(ListAPIView):
    serializer_class = AuthorSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        base_articles = _feed_base_queryset_for_user(self.request.user)
        return (
            Author.objects
            .filter(articles__in=base_articles)
            .annotate(article_count=Count('articles', filter=Q(articles__in=base_articles), distinct=True))
            .filter(article_count__gt=0)
            .order_by('-article_count', 'name')[:MAX_FILTER_OPTIONS]
        )


# ---------------------------------------------------------------------------
# User article profile view
# ---------------------------------------------------------------------------

# Returns and updates the authenticated user's article preference profile
class UserArticleProfileView(APIView):
    permission_classes = [IsAuthenticated]

    # Build the profile payload with explicit and inferred preferences
    def _serialize_profile(self, user, profile):
        liked_article_feedback = UserFeedback.objects.filter(
            user=user,
            target_type='article',
            feedback_type='like',
            article__isnull=False,
        ).select_related('article')

        disliked_article_feedback = UserFeedback.objects.filter(
            user=user,
            target_type='article',
            feedback_type='dislike',
            article__isnull=False,
        ).select_related('article')

        liked_ids = liked_article_feedback.values_list('article_id', flat=True)
        disliked_ids = disliked_article_feedback.values_list('article_id', flat=True)

        liked_topic_ids = Topic.objects.filter(
            articles__id__in=liked_ids
        ).annotate(popularity=Count('id')).order_by('-popularity', 'name').values_list('id', flat=True)

        disliked_topic_ids = Topic.objects.filter(
            articles__id__in=disliked_ids
        ).annotate(popularity=Count('id')).order_by('-popularity', 'name').values_list('id', flat=True)

        liked_site_ids = Site.objects.filter(
            article__id__in=liked_ids
        ).annotate(popularity=Count('id')).order_by('-popularity', 'name').values_list('id', flat=True)

        disliked_site_ids = Site.objects.filter(
            article__id__in=disliked_ids
        ).annotate(popularity=Count('id')).order_by('-popularity', 'name').values_list('id', flat=True)

        liked_author_ids = Author.objects.filter(
            articles__id__in=liked_ids
        ).annotate(popularity=Count('id')).order_by('-popularity', 'name').values_list('id', flat=True)

        disliked_author_ids = Author.objects.filter(
            articles__id__in=disliked_ids
        ).annotate(popularity=Count('id')).order_by('-popularity', 'name').values_list('id', flat=True)

        payload = UserProfileSerializer(profile).data
        payload['articles_liked'] = liked_article_feedback.count()
        payload['articles_disliked'] = disliked_article_feedback.count()
        payload['articles_favorited'] = ArticleFavorite.objects.filter(user=user).count()
        payload['liked_topics'] = TopicSerializer(Topic.objects.filter(id__in=liked_topic_ids), many=True).data
        payload['inferred_disliked_topics'] = TopicSerializer(Topic.objects.filter(id__in=disliked_topic_ids), many=True).data
        payload['liked_sites'] = SiteSerializer(Site.objects.filter(id__in=liked_site_ids), many=True).data
        payload['inferred_disliked_sites'] = SiteSerializer(Site.objects.filter(id__in=disliked_site_ids), many=True).data
        payload['liked_authors'] = AuthorSerializer(Author.objects.filter(id__in=liked_author_ids), many=True).data
        payload['inferred_disliked_authors'] = AuthorSerializer(Author.objects.filter(id__in=disliked_author_ids), many=True).data
        return payload

    # Return the authenticated user's article profile
    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(self._serialize_profile(request.user, profile))

    # Update the authenticated user's article profile preferences
    @transaction.atomic
    def patch(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        scalar_fields = [
            'preferred_quality_threshold',
            'min_read_time',
            'max_read_time',
            'daily_recommendation_count',
            'enable_auto_refresh',
        ]
        for field in scalar_fields:
            if field in data:
                setattr(profile, field, data[field])
        profile.save()

        if 'preferred_topic_ids' in data:
            profile.preferred_topics.set(Topic.objects.filter(id__in=data['preferred_topic_ids']))
        if 'disliked_topic_ids' in data:
            profile.disliked_topics.set(Topic.objects.filter(id__in=data['disliked_topic_ids']))
        if 'preferred_author_ids' in data:
            profile.preferred_authors.set(Author.objects.filter(id__in=data['preferred_author_ids']))
        if 'disliked_author_ids' in data:
            profile.disliked_authors.set(Author.objects.filter(id__in=data['disliked_author_ids']))
        if 'preferred_site_ids' in data:
            profile.preferred_sites.set(Site.objects.filter(id__in=data['preferred_site_ids']))
        if 'disliked_site_ids' in data:
            profile.disliked_sites.set(Site.objects.filter(id__in=data['disliked_site_ids']))

        return Response(self._serialize_profile(request.user, profile))