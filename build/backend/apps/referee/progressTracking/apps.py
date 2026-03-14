from django.apps import AppConfig


class ProgressConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.referee.progressTracking'
    label = "referee_progressTracking"

    def ready(self):
        import apps.referee.progressTracking.signals  # noqa: F401