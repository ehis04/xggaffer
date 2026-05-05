"""
Ingests football articles from configured Really Simple Syndication(RSS) feeds

Fetches RSS entries, normalises source URLs, creates missing sites and topics, and stores new articles for recommendations
"""

from __future__ import annotations

import datetime
import hashlib
import logging
import re
from typing import Optional

from django.utils import timezone
from django.utils.text import slugify

from apps.articles.services.source_utils import normalize_site_domain, sanitize_external_url

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# RSS feed configuration
# ---------------------------------------------------------------------------

# RSS feeds for seeded article sources
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


# ---------------------------------------------------------------------------
# RSS helper functions
# ---------------------------------------------------------------------------

# Build a stable unique slug from the article title and URL
def _unique_slug(title: str, url: str) -> str:
    base = slugify(title)[:200]
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{base}-{url_hash}"


# Get or create the source site for an RSS feed
def _get_or_create_site(name: str, domain: str):
    from apps.articles.models import Site

    normalized_domain = normalize_site_domain(domain, name)
    site, _ = Site.objects.get_or_create(
        domain=normalized_domain,
        defaults={'name': name, 'reputation_score': 70.0, 'trust_score': 75.0},
    )
    return site


# Get or create topics attached to ingested RSS articles
def _get_topics(topic_names: list[str]):
    from apps.articles.models import Topic

    topics = []
    for name in topic_names:
        topic, _ = Topic.objects.get_or_create(name=name, defaults={'slug': slugify(name)})
        topics.append(topic)
    return topics


def _extract_author_names(entry) -> list[str]:
    names: list[str] = []

    raw_authors = getattr(entry, 'authors', None)
    if isinstance(raw_authors, list):
        for author_obj in raw_authors:
            if isinstance(author_obj, dict):
                candidate = author_obj.get('name') or ''
            else:
                candidate = getattr(author_obj, 'name', '')
            candidate = (candidate or '').strip()
            if candidate:
                names.append(candidate)

    raw_author = (getattr(entry, 'author', None) or '').strip()
    if raw_author:
        names.extend(re.split(r',|;|\|| and ', raw_author))

    cleaned: list[str] = []
    seen = set()
    for name in names:
        normalized = re.sub(r'^by\s+', '', (name or '').strip(), flags=re.IGNORECASE)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        if len(normalized) < 2:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(normalized)
    return cleaned[:3]


def _get_authors(author_names: list[str]):
    from apps.articles.models import Author

    authors = []
    for name in author_names:
        safe_name = name[:100].strip()
        if len(safe_name) < 2:
            continue
        try:
            author, _ = Author.objects.get_or_create(
                name=safe_name,
                defaults={'expertise_score': 65.0, 'credibility_score': 70.0, 'is_verified': False},
            )
            authors.append(author)
        except Exception as exc:
            _logger.warning('Skipping invalid author value "%s": %s', safe_name, exc)
    return authors


# Parse a feed entry publication date into an aware datetime
def _parse_published(entry) -> Optional[object]:
    struct = getattr(entry, 'published_parsed', None) or getattr(entry, 'updated_parsed', None)
    if struct:
        published = datetime.datetime(*struct[:6])
        if timezone.is_naive(published):
            return timezone.make_aware(published, timezone.get_current_timezone())
        return published
    return timezone.now()


# ---------------------------------------------------------------------------
# RSS ingestion
# ---------------------------------------------------------------------------

# Pull configured RSS feeds and create new article records
def ingest_rss_feeds() -> int:
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
        created_for_feed = 0

        try:
            parsed = feedparser.parse(feed_url)
        except Exception as exc:
            _logger.warning('Failed to fetch feed %s: %s', feed_url, exc)
            continue

        if parsed.bozo and not parsed.entries:
            _logger.warning('Malformed or empty feed: %s', feed_url)
            continue

        site = _get_or_create_site(site_name, feed_url)
        topics = _get_topics(default_topics)

        for entry in parsed.entries:
            url = sanitize_external_url(
                getattr(entry, 'link', None),
                site_domain=site.domain,
                enforce_same_family=True,
            )
            title = getattr(entry, 'title', None)
            if not url or not title:
                continue

            title = title.strip()
            summary = getattr(entry, 'summary', '') or ''
            summary = re.sub(r'<[^>]+>', '', summary)[:2000]

            image_url = ''
            media = getattr(entry, 'media_content', None) or getattr(entry, 'media_thumbnail', None)
            if media and isinstance(media, list) and media:
                image_url = sanitize_external_url(media[0].get('url', '')) or ''

            pub_date = _parse_published(entry)
            slug = _unique_slug(title, url)
            authors = _get_authors(_extract_author_names(entry))

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
                    if authors:
                        article.authors.set(authors)
                    created_for_feed += 1
                    total_created += 1
                elif authors and not article.authors.exists():
                    article.authors.set(authors)
            except Exception as exc:
                _logger.warning('Failed to save article "%s": %s', title, exc)

        _logger.info('Feed %s: ingested, new=%d', site_name, created_for_feed)

    _logger.info('RSS ingest complete. Total new articles: %d', total_created)
    return total_created