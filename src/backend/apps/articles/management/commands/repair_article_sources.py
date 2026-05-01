"""
Repairs article source data after imports or source URL changes

Normalises site domains, merges duplicate sites, and fixes article URLs so stored source links stay valid
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.articles.models import Article, Author, Site, UserFeedback, UserProfile
from apps.articles.services.source_utils import normalize_site_domain, sanitize_external_url


# Command for repairing article source domains and URLs
class Command(BaseCommand):
    help = 'Repair invalid article source URLs and normalize site domains.'

    # Merge a duplicate site into the canonical site record
    @staticmethod
    def _merge_sites(source: Site, target: Site) -> None:
        if source.pk == target.pk:
            return

        Article.objects.filter(site=source).update(site=target)
        UserFeedback.objects.filter(site=source).update(site=target)

        for author in Author.objects.filter(sites=source).only('id'):
            author.sites.add(target)
            author.sites.remove(source)

        for profile in UserProfile.objects.filter(preferred_sites=source).only('id'):
            profile.preferred_sites.add(target)
            profile.preferred_sites.remove(source)

        for profile in UserProfile.objects.filter(disliked_sites=source).only('id'):
            profile.disliked_sites.add(target)
            profile.disliked_sites.remove(source)

        source.delete()

    # Run the source repair command
    def handle(self, *args, **options):
        site_domain_updates = 0
        site_merges = 0
        article_url_updates = 0

        with transaction.atomic():
            for site in Site.objects.order_by('id'):
                normalized_domain = normalize_site_domain(site.domain, site.name)
                if site.domain == normalized_domain:
                    continue

                collision = Site.objects.filter(domain=normalized_domain).exclude(pk=site.pk).order_by('id').first()
                if collision:
                    self._merge_sites(site, collision)
                    site_merges += 1
                    continue

                site.domain = normalized_domain
                site.save(update_fields=['domain'])
                site_domain_updates += 1

            typo = 'https://theatheletic.com'
            fixed = 'https://www.nytimes.com/athletic'
            for site in Site.objects.filter(domain__iexact=typo).order_by('id'):
                collision = Site.objects.filter(domain=fixed).exclude(pk=site.pk).order_by('id').first()
                if collision:
                    self._merge_sites(site, collision)
                    site_merges += 1
                    continue

                site.domain = fixed
                site.save(update_fields=['domain'])
                site_domain_updates += 1

            articles = Article.objects.select_related('site').all()
            for article in articles:
                cleaned_url = sanitize_external_url(
                    article.url,
                    site_domain=article.site.domain,
                    enforce_same_family=True,
                )
                if cleaned_url:
                    if cleaned_url != article.url:
                        article.url = cleaned_url
                        article.save(update_fields=['url'])
                        article_url_updates += 1
                    continue

                base = normalize_site_domain(article.site.domain, article.site.name)
                fallback_url = f"{base.rstrip('/')}/article/{article.slug}"
                if fallback_url != article.url:
                    article.url = fallback_url
                    article.save(update_fields=['url'])
                    article_url_updates += 1

        self.stdout.write(self.style.SUCCESS(
            f'Repaired source data: {site_domain_updates} site domain(s), {site_merges} site merge(s), {article_url_updates} article URL(s).'
        ))