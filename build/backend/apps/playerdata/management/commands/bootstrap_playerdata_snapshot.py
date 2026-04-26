from django.core.management.base import BaseCommand

from apps.playerdata.publication import run_playerdata_publication


class Command(BaseCommand):
    help = 'Create or refresh the active playerdata PublishedSnapshot.'

    def handle(self, *args, **options):
        run_playerdata_publication()
        self.stdout.write(self.style.SUCCESS('Playerdata snapshot published.'))
