import logging

from django.apps import AppConfig

_logger = logging.getLogger(__name__)


class PredictionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.predictions'
    verbose_name = "Predictions"

    def ready(self):
        from django.conf import settings
        if getattr(settings, "PREDICTIONS_DISABLE_PREWARM", False):
            return

        import threading

        def _warm_caches():
            try:
                _logger.info("Pre-warming lineup features cache...")
                from apps.predictions.ml.models.lineup.feature_service import _load_features
                _load_features()
                _logger.info("Lineup features cache ready.")
            except Exception as exc:
                _logger.warning("Could not pre-warm lineup features: %s", exc)

            try:
                _logger.info("Pre-warming injury index...")
                from apps.predictions.services.availability_handler import _load_open_injury_index
                _load_open_injury_index()
                _logger.info("Injury index ready.")
            except Exception as exc:
                _logger.warning("Could not pre-warm injury index: %s", exc)

            try:
                _logger.info("Pre-warming availability ML models...")
                from apps.predictions.ml.models.availability.predict import get_shared_predictor
                get_shared_predictor()
                _logger.info("Availability models ready.")
            except Exception as exc:
                _logger.warning("Could not pre-warm availability models: %s", exc)

        # Run in a daemon thread so startup isn't blocked if the files are slow to load
        t = threading.Thread(target=_warm_caches, name="predictions-cache-warmup", daemon=True)
        t.start()
