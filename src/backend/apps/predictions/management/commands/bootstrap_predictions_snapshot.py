from django.core.management.base import BaseCommand

from apps.predictions.publication import run_predictions_publication


class Command(BaseCommand):
    help = 'Create or refresh the active predictions PublishedSnapshot.'

    def handle(self, *args, **options):
        run_predictions_publication()
        self.stdout.write(self.style.SUCCESS('Predictions snapshot published.'))
