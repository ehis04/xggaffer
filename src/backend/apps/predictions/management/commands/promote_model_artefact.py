from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.predictions.publication import promote_model_artefact


class Command(BaseCommand):
    help = 'Register a trained model artefact as the active version for an algorithm.'

    def add_arguments(self, parser):
        parser.add_argument('algorithm', type=str, help='Algorithm name (e.g. match_outcome)')
        parser.add_argument('path', type=str, help='Absolute path to the .joblib artefact')
        parser.add_argument(
            '--trained-at',
            dest='trained_at',
            default=None,
            help='ISO datetime when model was trained (defaults to now)',
        )

    def handle(self, *args, **options):
        from pathlib import Path

        path = options['path']
        if not Path(path).exists():
            raise CommandError(f'Model file does not exist: {path}')

        trained_at = timezone.now()
        if options['trained_at']:
            from django.utils.dateparse import parse_datetime
            parsed = parse_datetime(options['trained_at'])
            if not parsed:
                raise CommandError(f"Could not parse --trained-at: {options['trained_at']}")
            trained_at = parsed

        record = promote_model_artefact(
            algorithm=options['algorithm'],
            path=path,
            trained_at=trained_at,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Promoted {record.algorithm} artefact: {record.path}'
        ))