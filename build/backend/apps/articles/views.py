from __future__ import annotations

import logging

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Article, Author, Site, Topic,
    ArticleRating, UserFeedback, ReadingHistory, UserProfile,
    UserRecommendation,
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
)

_logger = logging.getLogger(__name__)


class ArticlePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 50


class ArticleFeedView(ListAPIView):
    """
    Personalised article feed.  Returns recommended articles for the
    authenticated user.  Falls back to recency-sorted active articles
    when no recommendations exist yet.
    """
    serializer_class = ArticleListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ArticlePagination

    @staticmethod
    def _valid_source_filter() -> Q:
        return (
            Q(url__startswith='http')
            & ~Q(url__icontains='.local')
            & ~Q(url__icontains='zclkvisitor')
            & ~Q(url__icontains='campaignid=')
            & ~Q(url__icontains='clickid=')
            & ~Q(url__icontains='theatheletic.com')
        )

    def get_queryset(self):
        user = self.request.user
        topic_param = self.request.query_params.get('topic')
        site_param = self.request.query_params.get('site')
        author_param = self.request.query_params.get('author')
        q_param = (self.request.query_params.get('q') or '').strip()

        # Try to serve from pre-computed recommendations first
        from django.utils import timezone
        today = timezone.now().date()
        recs = (
            UserRecommendation.objects
            .filter(user=user, batch_date=today)
            .select_related('article__site')
            .prefetch_related('article__authors', 'article__topics')
            .order_by('-score')
        )

        if recs.exists():
            article_ids = list(recs.values_list('article_id', flat=True))
            qs = Article.objects.filter(
                id__in=article_ids,
                is_active=True,
            ).filter(self._valid_source_filter())
        else:
            qs = Article.objects.filter(is_active=True).filter(self._valid_source_filter()).order_by('-publication_date')

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

        return qs.distinct()


class ArticleDetailView(RetrieveAPIView):
    queryset = (
        Article.objects.filter(is_active=True)
        .exclude(url__icontains='.local')
        .exclude(url__icontains='zclkvisitor')
        .exclude(url__icontains='campaignid=')
        .exclude(url__icontains='clickid=')
        .exclude(url__icontains='theatheletic.com')
        .filter(url__startswith='http')
        .select_related('site')
        .prefetch_related('authors', 'topics')
    )
    serializer_class = ArticleDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    lookup_url_kwarg = 'article_id'

    def retrieve(self, request, *args, **kwargs):
        article = self.get_object()
        article.view_count += 1
        article.save(update_fields=['view_count'])
        return super().retrieve(request, *args, **kwargs)


class ArticleRateView(APIView):
    """Create or update the authenticated user's star rating for an article."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, article_id: int):
        article = get_object_or_404(Article, pk=article_id, is_active=True)
        serializer = ArticleRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rating_obj, created = ArticleRating.objects.update_or_create(
            article=article,
            user=request.user,
            defaults={
                'rating': serializer.validated_data['rating'],
                'review': serializer.validated_data.get('review', ''),
            },
        )

        # Recalculate article aggregate
        all_ratings = ArticleRating.objects.filter(article=article)
        article.total_ratings = all_ratings.count()
        article.average_rating = (
            sum(r.rating for r in all_ratings) / article.total_ratings
        )
        article.save(update_fields=['total_ratings', 'average_rating'])

        return Response(ArticleRatingSerializer(rating_obj).data, status=status.HTTP_200_OK)

    def delete(self, request, article_id: int):
        article = get_object_or_404(Article, pk=article_id, is_active=True)
        ArticleRating.objects.filter(article=article, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ArticleFeedbackView(APIView):
    """Like / dislike an article, author, or site, toggling off on repeat."""
    permission_classes = [IsAuthenticated]

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
                # Toggle off
                self._decrement_counts(existing)
                existing.delete()
                return Response({'status': 'removed'}, status=status.HTTP_200_OK)
            else:
                # Switch direction
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

    def _increment_counts(self, feedback: UserFeedback):
        target = feedback.article or feedback.author or feedback.site
        if not target:
            return
        field = 'total_likes' if feedback.feedback_type == 'like' else 'total_dislikes'
        type(target).objects.filter(pk=target.pk).update(**{field: getattr(target, field) + 1})

    def _decrement_counts(self, feedback: UserFeedback):
        target = feedback.article or feedback.author or feedback.site
        if not target:
            return
        field = 'total_likes' if feedback.feedback_type == 'like' else 'total_dislikes'
        current = getattr(target, field)
        type(target).objects.filter(pk=target.pk).update(**{field: max(0, current - 1)})


class MarkReadView(APIView):
    """Record that the user has read an article."""
    permission_classes = [IsAuthenticated]

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


class TopicListView(ListAPIView):
    queryset = Topic.objects.all().order_by('name')
    serializer_class = TopicSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


class SiteListView(ListAPIView):
    queryset = Site.objects.filter(is_active=True).order_by('name')
    serializer_class = SiteSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


class AuthorListView(ListAPIView):
    queryset = Author.objects.all().order_by('name')
    serializer_class = AuthorSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


class UserArticleProfileView(APIView):
    """Return the current user's article preference profile."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(UserProfileSerializer(profile).data)
