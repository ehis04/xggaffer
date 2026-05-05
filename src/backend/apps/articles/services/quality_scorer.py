"""
Scores article quality for recommendation and ranking

Calculates readability, engagement, source quality, and composite article scores used by the article recommendation system
"""

from __future__ import annotations

import math
from datetime import timedelta

from django.utils import timezone
from textstat import flesch_reading_ease


# Service for calculating article quality and ranking scores
class QualityScorer:

    # Calculate a readability score from article text
    @staticmethod
    def calculate_readability_score(text: str) -> float:
        if not text or len(text) < 100:
            return 50.0
        try:
            return max(0.0, min(100.0, flesch_reading_ease(text)))
        except Exception:
            return 50.0

    # Calculate an engagement score from views, ratings, likes, and shares
    @staticmethod
    def calculate_engagement_score(article) -> float:
        view_score = min(100, math.log(article.view_count + 1) * 10)
        rating_score = (article.average_rating / 5.0) * 100 if article.total_ratings > 0 else 50.0
        total_feedback = article.total_likes + article.total_dislikes
        like_ratio = (article.total_likes / total_feedback * 100) if total_feedback > 0 else 50.0
        share_score = min(100, math.log(article.external_shares + 1) * 15)

        return round(
            view_score * 0.3 + rating_score * 0.3 + like_ratio * 0.2 + share_score * 0.2,
            2,
        )

    # Calculate source and author based quality score for an article
    @staticmethod
    def calculate_quality_score(article) -> float:
        site_score = article.site.reputation_score
        author_scores = [author.expertise_score for author in article.authors.all()]
        author_score = sum(author_scores) / len(author_scores) if author_scores else 50.0
        external_score = (article.external_rating / 5.0 * 100) if article.external_rating else None

        if external_score:
            quality = site_score * 0.3 + author_score * 0.3 + external_score * 0.4
        else:
            quality = site_score * 0.5 + author_score * 0.5

        return round(quality, 2)

    # Calculate the final composite quality score for recommendation ranking
    @classmethod
    def calculate_composite_quality_score(cls, article) -> float:
        age_days = (timezone.now() - article.publication_date).days
        recency_bonus = max(0, 10 - age_days) if age_days < 10 else 0

        return round(
            min(
                100,
                article.readability_score * 0.2
                + article.quality_score * 0.4
                + article.engagement_score * 0.3
                + recency_bonus * 0.1,
            ),
            2,
        )

    # Recalculate and save all quality scores for one article
    @classmethod
    def update_article_quality_scores(cls, article):
        if article.content:
            article.readability_score = cls.calculate_readability_score(article.content)
        article.quality_score = cls.calculate_quality_score(article)
        article.engagement_score = cls.calculate_engagement_score(article)
        article.quality_score = cls.calculate_composite_quality_score(article)
        article.save(update_fields=['readability_score', 'quality_score', 'engagement_score'])
        return article