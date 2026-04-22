from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings

from apps.predictions.models import InferenceSnapshotRecord, ModelArtefactRecord
from apps.sync_pipeline.selectors import compute_surface_freshness
from common.freshness import FreshnessPayload

_logger = logging.getLogger(__name__)

PREDICTIONS_SURFACE = 'predictions'


def get_active_model_path(algorithm: str) -> str | None:
    record = ModelArtefactRecord.objects.filter(
        algorithm=algorithm, is_active=True
    ).first()

    if record and Path(record.path).exists():
        return record.path

    if record:
        _logger.warning('ModelArtefactRecord path does not exist on disk: %s', record.path)

    return _glob_fallback(algorithm)


def get_active_inference_snapshot(algorithm: str) -> InferenceSnapshotRecord | None:
    return InferenceSnapshotRecord.objects.filter(
        algorithm=algorithm, is_active=True
    ).first()


def get_prediction_freshness() -> FreshnessPayload:
    sla = settings.FRESHNESS_SLA_SECONDS.get(PREDICTIONS_SURFACE, 21600)
    return compute_surface_freshness(PREDICTIONS_SURFACE, sla_seconds=sla)


def _glob_fallback(algorithm: str) -> str | None:
    try:
        from apps.predictions.ml.models.match_outcome.config import MODELS_DIR
        import glob
        import os

        pattern = str(MODELS_DIR / f'*{algorithm}*.joblib')
        candidates = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        if candidates:
            _logger.info('glob fallback found model for %s: %s', algorithm, candidates[0])
            return candidates[0]
    except Exception as exc:
        _logger.warning('glob fallback failed for %s: %s', algorithm, exc)
    return None