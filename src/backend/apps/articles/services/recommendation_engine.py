"""
Builds personalised article recommendations for users

Combines content similarity, collaborative filtering, quality, popularity, recency, and user preferences to rank article suggestions
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import List, Tuple

import numpy as np
from django.db.models import Avg, Count, Q
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from apps.articles.models import (
    Article, ArticleRating, ReadingHistory, UserProfile, UserRecommendation,
)

logger = logging.getLogger(__name__)


# Service for generating and saving article recommendations for one user
class RecommendationEngine:

    # Set up the recommendation engine and ensure the user has an article profile
    def __init__(self, user):
        self.user = user
        try:
            self.user_profile = user.article_profile
        except UserProfile.DoesNotExist:
            self.user_profile = UserProfile.objects.create(user=user)

    # Generate ranked article recommendations for the user
    def generate_recommendations(self, count: int = 50) -> List[Tuple[Article, float]]:
        logger.info('Generating %d recommendations for %s', count, self.user.email)

        candidates = self._get_candidate_articles()
        candidate_count = candidates.count()

        if candidate_count < count:
            logger.warning('Only %d candidate articles available', candidate_count)

        article_scores = [
            (article, self._calculate_article_score(article))
            for article in candidates
        ]
        article_scores.sort(key=lambda x: x[1], reverse=True)

        logger.info('Generated %d recommendations', min(count, len(article_scores)))
        return article_scores[:count]

    # Get eligible unread articles based on profile filters and exclusions
    def _get_candidate_articles(self):
        read_article_ids = ReadingHistory.objects.filter(
            user=self.user
        ).values_list('article_id', flat=True)

        disliked_author_ids = self.user_profile.disliked_authors.values_list('id', flat=True)
        disliked_site_ids = self.user_profile.disliked_sites.values_list('id', flat=True)
        disliked_topic_ids = self.user_profile.disliked_topics.values_list('id', flat=True)
        cutoff_date = timezone.now() - timedelta(days=90)

        return (
            Article.objects.filter(
                is_active=True,
                publication_date__gte=cutoff_date,
                quality_score__gte=self.user_profile.preferred_quality_threshold,
                read_time_minutes__gte=self.user_profile.min_read_time,
                read_time_minutes__lte=self.user_profile.max_read_time,
            )
            .exclude(id__in=read_article_ids)
            .exclude(authors__id__in=disliked_author_ids)
            .exclude(site__id__in=disliked_site_ids)
            .exclude(topics__id__in=disliked_topic_ids)
            .select_related('site')
            .prefetch_related('authors', 'topics')
        )

    # Calculate the final weighted recommendation score for an article
    def _calculate_article_score(self, article: Article) -> float:
        return (
            self._calculate_content_score(article) * 0.25
            + self._calculate_collaborative_score(article) * 0.20
            + (article.quality_score / 100.0) * 0.20
            + self._calculate_popularity_score(article) * 0.15
            + self._calculate_recency_score(article) * 0.10
            + self._calculate_preference_boost(article) * 0.10
        )

    # Calculate how closely an article matches the user's reading history
    def _calculate_content_score(self, article: Article) -> float:
        read_articles = ReadingHistory.objects.filter(
            user=self.user,
            completed=True
        ).select_related('article')[:50]

        if not read_articles:
            article_topics = set(article.topics.values_list('id', flat=True))
            preferred_topics = set(self.user_profile.preferred_topics.values_list('id', flat=True))
            if not preferred_topics:
                return 0.5
            overlap = len(article_topics.intersection(preferred_topics))
            return min(1.0, overlap / len(preferred_topics))

        # Build simple text features from article title, topics, and authors
        def get_article_features(art):
            topics = ' '.join([t.name for t in art.topics.all()])
            authors = ' '.join([a.name for a in art.authors.all()])
            return f"{art.title} {topics} {authors}"

        read_features = [get_article_features(ra.article) for ra in read_articles]
        candidate_features = get_article_features(article)
        vectorizer = TfidfVectorizer(max_features=100)

        try:
            all_features = read_features + [candidate_features]
            tfidf_matrix = vectorizer.fit_transform(all_features)
            candidate_vector = tfidf_matrix[-1]
            read_vectors = tfidf_matrix[:-1]
            similarities = cosine_similarity(candidate_vector, read_vectors)[0]
            return float(np.mean(similarities))
        except Exception:
            return 0.5

    # Calculate how similar users have rated the article
    def _calculate_collaborative_score(self, article: Article) -> float:
        user_high_ratings = ArticleRating.objects.filter(
            user=self.user,
            rating__gte=4
        ).values_list('article_id', flat=True)

        if not user_high_ratings:
            return 0.5

        similar_users = (
            ArticleRating.objects
            .filter(article_id__in=user_high_ratings, rating__gte=4)
            .exclude(user=self.user)
            .values_list('user_id', flat=True)
            .distinct()
        )

        if not similar_users:
            return 0.5

        agg = ArticleRating.objects.filter(
            article=article,
            user_id__in=similar_users
        ).aggregate(avg_rating=Avg('rating'), count=Count('id'))

        if agg['count'] == 0:
            return 0.5

        return (agg['avg_rating'] - 1) / 4.0

    # Calculate popularity from views and average rating
    def _calculate_popularity_score(self, article: Article) -> float:
        view_score = min(1.0, article.view_count / 10000)
        rating_score = article.average_rating / 5.0 if article.total_ratings > 0 else 0.5
        return view_score * 0.5 + rating_score * 0.5

    # Calculate a recency score from publication age
    def _calculate_recency_score(self, article: Article) -> float:
        age_days = (timezone.now() - article.publication_date).days
        if age_days <= 1:
            return 1.0
        elif age_days <= 7:
            return 0.8
        elif age_days <= 30:
            return 0.6
        elif age_days <= 60:
            return 0.4
        else:
            return 0.2

    # Calculate boost from explicit preferred topics, authors, and sites
    def _calculate_preference_boost(self, article: Article) -> float:
        boost = 0.0
        article_topics = set(article.topics.values_list('id', flat=True))
        preferred_topics = set(self.user_profile.preferred_topics.values_list('id', flat=True))
        if preferred_topics and article_topics.intersection(preferred_topics):
            boost += 0.4

        article_authors = set(article.authors.values_list('id', flat=True))
        preferred_authors = set(self.user_profile.preferred_authors.values_list('id', flat=True))
        if preferred_authors and article_authors.intersection(preferred_authors):
            boost += 0.3

        if self.user_profile.preferred_sites.filter(id=article.site.id).exists():
            boost += 0.3

        return min(1.0, boost)

    # Save a recommendation batch for the user
    def save_recommendations(self, article_scores: List[Tuple[Article, float]], batch_date=None):
        if batch_date is None:
            batch_date = timezone.now().date()

        UserRecommendation.objects.filter(user=self.user, batch_date=batch_date).delete()

        recommendations = [
            UserRecommendation(
                user=self.user,
                article=article,
                score=score,
                reason=self._generate_recommendation_reason(article),
                position=position,
                batch_date=batch_date,
            )
            for position, (article, score) in enumerate(article_scores, start=1)
        ]

        UserRecommendation.objects.bulk_create(recommendations)
        self.user_profile.last_recommendation_refresh = timezone.now()
        self.user_profile.save(update_fields=['last_recommendation_refresh'])

        logger.info('Saved %d recommendations for %s', len(recommendations), self.user.email)

    # Build a short explanation for why an article was recommended
    def _generate_recommendation_reason(self, article: Article) -> str:
        reasons = []
        article_topics = set(article.topics.values_list('name', flat=True))
        preferred_topics = set(self.user_profile.preferred_topics.values_list('name', flat=True))
        matching_topics = article_topics.intersection(preferred_topics)
        if matching_topics:
            reasons.append(f"Matches your interest in {', '.join(list(matching_topics)[:2])}")

        preferred_author_names = set(self.user_profile.preferred_authors.values_list('name', flat=True))
        for author_name in [a.name for a in article.authors.all()]:
            if author_name in preferred_author_names:
                reasons.append(f"By {author_name}")
                break

        if article.quality_score >= 85:
            reasons.append("High quality content")
        if article.is_recent:
            reasons.append("Recently published")
        if not reasons:
            reasons.append("Based on your reading history")

        return " • ".join(reasons[:3])


# Generate and save recommendations for one user
def generate_recommendations_for_user(user, count=50):
    engine = RecommendationEngine(user)
    article_scores = engine.generate_recommendations(count)
    engine.save_recommendations(article_scores)
    return [article for article, _ in article_scores]