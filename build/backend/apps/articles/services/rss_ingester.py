from __future__ import annotations

import hashlib
import logging
from typing import Optional
from urllib.parse import urlparse

from django.utils import timezone
from django.utils.text import slugify

_logger = logging.getLogger(__name__)

# RSS feeds for the seeded sites — one feed URL per source.
RSS_FEEDS: list[dict] = [
    {
        'site_name': 'BBC Sport',
        'feed_url': 'https://feeds.bbci.co.uk/sport/football/rss.xml',
        'default_topics': ['Match Analysis', 'Team News'],
    },
    {
        'site_name': 'Sky Sports',
        'feed_url': 'https://www.skysports.com/rss/12040',
        'default_topics': ['Match Analysis', 'Team News'],
    },
    {
        'site_name': 'talkSPORT',
        'feed_url': 'https://talksport.com/feed/',
        'default_topics': ['Match Analysis'],
    },
    {
        'site_name': 'The Guardian',
        'feed_url': 'https://www.theguardian.com/football/rss',
        'default_topics': ['Match Analysis', 'Player Performance'],
    },
    {
        'site_name': 'ESPN',
        'feed_url': 'https://www.espn.com/espn/rss/soccer/news',
        'default_topics': ['Match Analysis', 'Player Performance'],
    },
    {
        'site_name': 'RTE',
        'feed_url': 'https://www.rte.ie/rss/sport/soccer.xml',
        'default_topics': ['Match Analysis', 'Team News'],
    },
]


def _unique_slug(title: str, url: str) -> str:
    base = slugify(title)[:200]
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{base}-{url_hash}"


def _get_or_create_site(name: str, domain: str):
    from apps.articles.models import Site
    site, _ = Site.objects.get_or_create(
        domain=domain,
        defaults={'name': name, 'reputation_score': 70.0, 'trust_score': 75.0},
    )
    return site


def _get_topics(topic_names: list[str]):
    from apps.articles.models import Topic
    topics = []
    for name in topic_names:
        topic, _ = Topic.objects.get_or_create(name=name, defaults={'slug': slugify(name)})
        topics.append(topic)
    return topics


def _parse_published(entry) -> Optional[object]:
    struct = getattr(entry, 'published_parsed', None) or getattr(entry, 'updated_parsed', None)
    if struct:
        import datetime
        published = datetime.datetime(*struct[:6])
        if timezone.is_naive(published):
            return timezone.make_aware(published, timezone.get_current_timezone())
        return published
    return timezone.now()


def ingest_rss_feeds() -> int:
    """
    Pull each configured RSS feed, upsert Article rows, and return the
    total number of new articles created.
    """
    try:
        import feedparser
    except ImportError:
        _logger.error('feedparser is not installed — run: pip install feedparser')
        return 0

    from apps.articles.models import Article

    total_created = 0

    for feed_cfg in RSS_FEEDS:
        site_name = feed_cfg['site_name']
        feed_url = feed_cfg['feed_url']
        default_topics = feed_cfg.get('default_topics', [])

        try:
            parsed = feedparser.parse(feed_url)
        except Exception as exc:
            _logger.warning('Failed to fetch feed %s: %s', feed_url, exc)
            continue

        if parsed.bozo and not parsed.entries:
            _logger.warning('Malformed or empty feed: %s', feed_url)
            continue

        parsed_domain = urlparse(feed_url).netloc or site_name.lower().replace(' ', '')
        site = _get_or_create_site(site_name, parsed_domain)
        topics = _get_topics(default_topics)

        for entry in parsed.entries:
            url = getattr(entry, 'link', None)
            title = getattr(entry, 'title', None)
            if not url or not title:
                continue

            title = title.strip()
            summary = getattr(entry, 'summary', '') or ''
            # Strip basic HTML tags from summary
            import re
            summary = re.sub(r'<[^>]+>', '', summary)[:2000]

            image_url = ''
            media = getattr(entry, 'media_content', None) or getattr(entry, 'media_thumbnail', None)
            if media and isinstance(media, list) and media:
                image_url = media[0].get('url', '')

            pub_date = _parse_published(entry)
            slug = _unique_slug(title, url)

            try:
                article, created = Article.objects.get_or_create(
                    url=url,
                    defaults={
                        'title': title,
                        'slug': slug,
                        'summary': summary,
                        'image_url': image_url,
                        'site': site,
                        'publication_date': pub_date,
                        'word_count': len(summary.split()),
                        'read_time_minutes': max(1, len(summary.split()) // 200),
                        'quality_score': site.reputation_score,
                    },
                )
                if created:
                    article.topics.set(topics)
                    total_created += 1
            except Exception as exc:
                _logger.warning('Failed to save article "%s": %s', title, exc)

        _logger.info('Feed %s: ingested, new=%d', site_name, total_created)

    _logger.info('RSS ingest complete. Total new articles: %d', total_created)
    return total_created
