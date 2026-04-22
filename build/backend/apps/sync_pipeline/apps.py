from django.apps import AppConfig


class SyncPipelineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sync_pipeline'
    verbose_name = 'Sync Pipeline'