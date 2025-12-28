import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
from django.db.models import Q, Avg, Count
from django.utils import timezone
from datetime import timedelta
from typing import List, Dict, Tuple
import logging

from apps.articles.models import (
    Article, UserProfile, UserRecommendation,
    ArticleRating, UserFeedback, ReadingHistory
)

logger = logging.getLogger(__name__)


class RecommendationEngine:

    def __init__(self, user):
        self.user = user
        try:
            self.user_profile = user.article_profile
        except:
            from apps.articles.models import UserProfile
            self.user_profile = UserProfile.objects.create(user=user)
    
    def generate_recommendations(self, count: int = 50) -> List[Article]:
        logger.info(f"Generating {count} recommendations for {self.user.username}")
        
        candidates = self._get_candidate_articles()
        
        if candidates.count() < count:
            logger.warning(f"Only {candidates.count()} candidate articles available")
            return list(candidates[:count])
        article_scores = []
        
        for article in candidates:
            score = self._calculate_article_score(article)
            article_scores.append((article, score))
        
        article_scores.sort(key=lambda x: x[1], reverse=True)
        recommended_articles = [article for article, score in article_scores[:count]]
        
        logger.info(f"Generated {len(recommended_articles)} recommendations")
        return recommended_articles
    
    def _get_candidate_articles(self) -> 'QuerySet':
        read_article_ids = ReadingHistory.objects.filter(
            user=self.user
        ).values_list('article_id', flat=True)
        
        disliked_author_ids = self.user_profile.disliked_authors.values_list('id', flat=True)
        disliked_site_ids = self.user_profile.disliked_sites.values_list('id', flat=True)
        cutoff_date = timezone.now() - timedelta(days=90)  # Last 3 months
        
        candidates = Article.objects.filter(
            is_active=True,
            published_date__gte=cutoff_date,
            quality_score__gte=self.user_profile.preferred_quality_threshold,
            read_time_minutes__gte=self.user_profile.min_read_time,
            read_time_minutes__lte=self.user_profile.max_read_time,
        ).exclude(
            id__in=read_article_ids
        ).exclude(
            authors__id__in=disliked_author_ids
        ).exclude(
            site__id__in=disliked_site_ids
        ).select_related('site').prefetch_related('authors', 'topics')
        
        return candidates
    
    def _calculate_article_score(self, article: Article) -> float:
        content_score = self._calculate_content_score(article)
        collaborative_score = self._calculate_collaborative_score(article)
        quality_score = article.quality_score / 100.0
        popularity_score = self._calculate_popularity_score(article)
        recency_score = self._calculate_recency_score(article)
        preference_boost = self._calculate_preference_boost(article)
        final_score = (
            content_score * 0.25 +
            collaborative_score * 0.20 +
            quality_score * 0.20 +
            popularity_score * 0.15 +
            recency_score * 0.10 +
            preference_boost * 0.10
        )
        
        return final_score
    
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
        except:
            return 0.5
    
    def _calculate_collaborative_score(self, article: Article) -> float:
        user_high_ratings = ArticleRating.objects.filter(
            user=self.user,
            rating__gte=4
        ).values_list('article_id', flat=True)
        
        if not user_high_ratings:
            return 0.5
        similar_users = ArticleRating.objects.filter(
            article_id__in=user_high_ratings,
            rating__gte=4
        ).exclude(
            user=self.user
        ).values_list('user_id', flat=True).distinct()
        
        if not similar_users:
            return 0.5
        similar_user_ratings = ArticleRating.objects.filter(
            article=article,
            user_id__in=similar_users
        ).aggregate(avg_rating=Avg('rating'), count=Count('id'))
        
        if similar_user_ratings['count'] == 0:
            return 0.5
        avg_rating = similar_user_ratings['avg_rating']
        return (avg_rating - 1) / 4.0
    
    def _calculate_popularity_score(self, article: Article) -> float:
        view_score = min(1.0, article.view_count / 10000)
        rating_score = article.average_rating / 5.0 if article.total_ratings > 0 else 0.5
        
        total_feedback = article.total_likes + article.total_dislikes
        like_ratio = article.total_likes / total_feedback if total_feedback > 0 else 0.5
        popularity = (view_score * 0.3 + rating_score * 0.4 + like_ratio * 0.3)
        return popularity
    
    def _calculate_recency_score(self, article: Article) -> float:
        age_days = (timezone.now() - article.published_date).days
        
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
    
    def save_recommendations(self, articles: List[Article], batch_date=None):
        if batch_date is None:
            batch_date = timezone.now().date()
        UserRecommendation.objects.filter(
            user=self.user,
            batch_date=batch_date
        ).delete()
        recommendations = []
        for position, article in enumerate(articles, start=1):
            score = self._calculate_article_score(article)
            reason = self._generate_recommendation_reason(article)
            
            rec = UserRecommendation(
                user=self.user,
                article=article,
                score=score,
                reason=reason,
                position=position,
                batch_date=batch_date
            )
            recommendations.append(rec)
        
        UserRecommendation.objects.bulk_create(recommendations)
        self.user_profile.last_recommendation_refresh = timezone.now()
        self.user_profile.save(update_fields=['last_recommendation_refresh'])
        
        logger.info(f"Saved {len(recommendations)} recommendations for {self.user.username}")
    
    def _generate_recommendation_reason(self, article: Article) -> str:
        reasons = []
        article_topics = set(article.topics.values_list('name', flat=True))
        preferred_topics = set(self.user_profile.preferred_topics.values_list('name', flat=True))
        
        matching_topics = article_topics.intersection(preferred_topics)
        if matching_topics:
            reasons.append(f"Matches your interest in {', '.join(list(matching_topics)[:2])}")
        article_author_names = [a.name for a in article.authors.all()]
        preferred_author_names = list(self.user_profile.preferred_authors.values_list('name', flat=True))
        
        for author_name in article_author_names:
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


def generate_recommendations_for_user(user, count=50):
    engine = RecommendationEngine(user)
    articles = engine.generate_recommendations(count)
    engine.save_recommendations(articles)
    return articles