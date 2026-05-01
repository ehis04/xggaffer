from django.core.management.base import BaseCommand

from apps.clubs.publication import run_clubs_publication


class Command(BaseCommand):
    help = 'Create or refresh the active clubs PublishedSnapshot.'

    def handle(self, *args, **options):
        run_clubs_publication()
        self.stdout.write(self.style.SUCCESS('Clubs snapshot published.'))
