from __future__ import annotations

from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.articles.models import Article, Site


class Command(BaseCommand):
    help = 'Repair invalid article source URLs and normalize site domains.'

    _BLOCKED_URL_TOKENS = (
        'zclkvisitor',
        'campaignid=',
        'clickid=',
        'utm_',
    )

    @staticmethod
    def _host(value: str | None) -> str:
        if not value:
            return ''
        parsed = urlparse(value)
        return (parsed.netloc or '').lower()

    @classmethod
    def _same_source_family(cls, article_url: str, site_domain: str) -> bool:
        article_host = cls._host(article_url)
        site_host = cls._host(site_domain)
        if not article_host or not site_host:
            return False
        return article_host.endswith(site_host) or site_host.endswith(article_host)

    @classmethod
    def _is_valid_http_url(cls, value: str | None, site_domain: str | None) -> bool:
        if not value:
            return False
        try:
            parsed = urlparse(value)
        except Exception:
            return False

        if not (parsed.scheme in {'http', 'https'} and bool(parsed.netloc) and '.local' not in parsed.netloc):
            return False

        lowered = value.lower()
        if any(token in lowered for token in cls._BLOCKED_URL_TOKENS):
            return False

        if site_domain and not cls._same_source_family(value, site_domain):
            return False

        return True

    @staticmethod
    def _normalize_domain(site: Site) -> str:
        domain = (site.domain or '').strip()
        if domain:
            parsed = urlparse(domain)
            if parsed.scheme in {'http', 'https'} and parsed.netloc and '.local' not in parsed.netloc:
                return domain.rstrip('/')

            if parsed.netloc:
                host = parsed.netloc
            else:
                host = domain.replace('http://', '').replace('https://', '').strip('/')

            if host and '.local' not in host:
                return f'https://{host}'

        return f'https://www.{slugify(site.name)}.com'

    def handle(self, *args, **options):
        site_domain_updates = 0
        article_url_updates = 0

        with transaction.atomic():
            for site in Site.objects.all():
                normalized_domain = self._normalize_domain(site)
                if site.domain != normalized_domain:
                    site.domain = normalized_domain
                    site.save(update_fields=['domain'])
                    site_domain_updates += 1

            # Known typo cleanup if it exists in historical data.
            typo = 'https://theatheletic.com'
            fixed = 'https://www.nytimes.com/athletic'
            typo_sites = Site.objects.filter(domain__iexact=typo)
            site_domain_updates += typo_sites.update(domain=fixed)

            articles = Article.objects.select_related('site').all()
            for article in articles:
                if self._is_valid_http_url(article.url, article.site.domain):
                    continue

                base = self._normalize_domain(article.site)
                article.url = f"{base}/article/{article.slug}"
                article.save(update_fields=['url'])
                article_url_updates += 1

        self.stdout.write(self.style.SUCCESS(
            f'Repaired source data: {site_domain_updates} site domain(s), {article_url_updates} article URL(s).'
        ))
