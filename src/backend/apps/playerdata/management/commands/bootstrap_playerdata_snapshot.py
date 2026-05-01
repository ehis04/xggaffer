"""
Management command for publishing the active player data snapshot

Runs the player data publication workflow so fresh enrichment data is exposed through the published snapshot layer
"""

from django.core.management.base import BaseCommand

from apps.playerdata.publication import run_playerdata_publication


class Command(BaseCommand):
    help = 'Create or refresh the active playerdata PublishedSnapshot.'

    # Run the player data publication workflow
    def handle(self, *args, **options):
        run_playerdata_publication()
        self.stdout.write(self.style.SUCCESS('Playerdata snapshot published.'))