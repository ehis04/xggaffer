from typing import Dict
import re
import math
from textstat import flesch_reading_ease

class QualityScorer:

    @staticmethod
    def calculate_readability_score(text: str) -> float:
        if not text or len(text) < 100:
            return 50.0

        try:
            score = flesch_reading_ease(text)

            return max(0, min(100, score))
        except:
            return 50.0

    @staticmethod
    def calculate_engagement_score(article) -> float:
        view_weight = 0.3
        rating_weight = 0.3
        like_weight = 0.2
        share_weight = 0.2
        view_score = min(100, math.log(article.view_count + 1) * 10)

        rating_score = (article.average_rating / 5.0) * 100 if article.total_ratings > 0 else 50
        
        total_feedback = article.total_likes + article.total_dislikes
        like_ratio = (article.total_likes / total_feedback * 100) if total_feedback > 0 else 50

        share_score = min(100, math.log(article.external_shares + 1) * 15)

        engagement = (
            view_score * view_weight +
            rating_score * rating_weight +
            like_ratio * like_weight +
            share_score * share_weight
        )

        return round(engagement, 2)

    @staticmethod
    def calculate_quality_score(article) -> float:
        site_score = article.site.reputation_score

        author_scores = [author.expertise_score for author in article.authors.all()]
        author_score = sum(author_scores) / len(author_scores) if author_scores else 50.0

        external_score = (article.external_rating / 5.0 * 100) if article.external_rating else None

        if external_score:
            quality = (site_score * 0.3 + author_score * 0.3 + external_score * 0.4)
        else:
            quality = (site_score * 0.5 + author_score * 0.5)

        return round(quality, 2)

    @classmethod
    def calculate_composite_quality_score(cls, article) -> float:
        readability = article.readability_score
        quality = article.quality_score
        engagement = article.engagement_score

        from django.utils import timezone
        from datetime import timedelta
        age_days = (timezone.now() - article.publication_date).days 
        recency_bonus = max(0, 10 - age_days) if age_days < 10 else 0

        final_quality = (
            readability * 0.2 +
            quality * 0.4 +
            engagement * 0.3 +
            recency_bonus * 0.1
        )

        return round(min(100, final_quality), 2)

    @classmethod
    def update_article_quality_scores(cls, article):
        if article.content:
            article.readability_score = cls.calculate_readability_score(article.content)

        article.quality_score = cls.calculate_quality_score(article)
        article.engagement_score = cls.calculate_engagement_score(article)
        composite = cls.calculate_composite_quality_score(article)

        article.save(update_fields=['readability_score', 'quality_score', 'engagement_score'])

        return article
