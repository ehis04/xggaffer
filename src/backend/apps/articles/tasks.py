"""
Celery tasks for article ingestion and recommendations

Runs scheduled RSS ingestion and article recommendation generation without blocking API requests
"""

from __future__ import annotations

import logging

from celery import shared_task

_logger = logging.getLogger(__name__)


# Pull configured RSS feeds and persist new articles
@shared_task(name='apps.articles.tasks.ingest_rss_feeds_task', bind=True, max_retries=2)
def ingest_rss_feeds_task(self):
    try:
        from apps.articles.services.rss_ingester import ingest_rss_feeds
        new_count = ingest_rss_feeds()
        _logger.info('RSS ingest task complete: %d new articles', new_count)
        return f'created={new_count}'
    except Exception as exc:
        _logger.exception('RSS ingest task failed: %s', exc)
        raise self.retry(exc=exc, countdown=300)


# Regenerate article recommendations for active users who have none for today
@shared_task(name='apps.articles.tasks.generate_recommendations_task', bind=True, max_retries=1)
def generate_recommendations_task(self):
    try:
        from django.contrib.auth import get_user_model
        from django.utils import timezone

        from apps.articles.services.recommendation_engine import generate_recommendations_for_user
        from apps.articles.models import UserRecommendation

        User = get_user_model()
        today = timezone.now().date()

        users_with_recs_today = (
            UserRecommendation.objects
            .filter(batch_date=today)
            .values_list('user_id', flat=True)
            .distinct()
        )

        pending_users = User.objects.filter(is_active=True).exclude(id__in=users_with_recs_today)
        count = 0
        for user in pending_users:
            try:
                generate_recommendations_for_user(user)
                count += 1
            except Exception as exc:
                _logger.warning('Recommendation generation failed for user %s: %s', user.pk, exc)

        _logger.info('Recommendation task complete: %d users processed', count)
        return f'users_processed={count}'
    except Exception as exc:
        _logger.exception('Recommendation task failed: %s', exc)
        raise self.retry(exc=exc, countdown=600)