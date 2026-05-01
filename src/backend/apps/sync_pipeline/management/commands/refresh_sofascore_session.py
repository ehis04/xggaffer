from django.core.management.base import BaseCommand

from apps.sync_pipeline.models import SourceHealth
from common.constants import ProviderName
from common.utils import utcnow


class Command(BaseCommand):
    help = 'Mark the SofaScore session as valid after manual cookie renewal.'

    def handle(self, *args, **options):
        now = utcnow()
        health, _ = SourceHealth.objects.get_or_create(
            provider=ProviderName.SOFASCORE,
            defaults={'window_started_at': now},
        )
        health.session_valid = True
        health.save(update_fields=['session_valid'])
        self.stdout.write(self.style.SUCCESS(
            'SofaScore session marked valid. Next cycle will proceed.'
        ))