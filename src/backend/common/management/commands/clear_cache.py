from __future__ import annotations

from django.core.management.base import BaseCommand

from common.cache_keys import KNOWN_CACHE_SURFACES, clear_surface_cache


class Command(BaseCommand):
    help = 'Clear xgGaffer Redis cache for one or all surfaces'

    def add_arguments(self, parser):
        parser.add_argument(
            'surface',
            nargs='?',
            default='all',
            choices=[*KNOWN_CACHE_SURFACES, 'all'],
        )

    def handle(self, *args, **options):
        surface = options['surface']

        if surface == 'all':
            total = sum(clear_surface_cache(s) for s in KNOWN_CACHE_SURFACES)
            self.stdout.write(f'Cleared all caches: {total} keys deleted total')
        else:
            deleted = clear_surface_cache(surface)
            self.stdout.write(f'Cleared {surface} cache: {deleted} keys deleted')