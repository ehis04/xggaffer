from django.core.management.base import BaseCommand

from apps.livefootball.publication import run_livefootball_publication


class Command(BaseCommand):
    help = 'Create or refresh the active livefootball PublishedSnapshot.'

    def handle(self, *args, **options):
        run_livefootball_publication()
        self.stdout.write(self.style.SUCCESS('Livefootball snapshot published.'))
