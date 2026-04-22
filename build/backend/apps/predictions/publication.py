from __future__ import annotations

import logging

from django.db import transaction

from apps.predictions.models import InferenceSnapshotRecord, ModelArtefactRecord
from apps.sync_pipeline.services import publish_snapshot
from common.constants import ProviderName
from common.utils import utcnow

_logger = logging.getLogger(__name__)

PREDICTIONS_SURFACE = 'predictions'
PREDICTIONS_PROVIDERS = [ProviderName.UNDERSTAT]
KNOWN_ALGORITHMS = ['match_outcome', 'score', 'availability', 'simulation']


def promote_model_artefact(algorithm: str, path: str, trained_at) -> ModelArtefactRecord:
    now = utcnow()
    with transaction.atomic():
        ModelArtefactRecord.objects.select_for_update().filter(
            algorithm=algorithm, is_active=True
        ).update(is_active=False)

        record = ModelArtefactRecord.objects.create(
            algorithm=algorithm,
            path=path,
            trained_at=trained_at,
            promoted_at=now,
            is_active=True,
        )

    _logger.info('ModelArtefactRecord promoted: algorithm=%s path=%s', algorithm, path)
    return record


def publish_inference_snapshot(algorithm: str) -> InferenceSnapshotRecord:
    now = utcnow()
    version = now.strftime('%Y%m%dT%H%M%SZ')

    with transaction.atomic():
        InferenceSnapshotRecord.objects.select_for_update().filter(
            algorithm=algorithm, is_active=True
        ).update(is_active=False)

        record = InferenceSnapshotRecord.objects.create(
            algorithm=algorithm,
            feature_set_version=version,
            snapshot_published_at=now,
            is_active=True,
        )

    return record


def validate_predictions_snapshot() -> tuple[bool, list[str]]:
    warnings = []
    if ModelArtefactRecord.objects.filter(is_active=True).count() == 0:
        warnings.append('No active ModelArtefactRecord found for any algorithm.')
    return True, warnings


def run_predictions_publication() -> None:
    valid, warnings = validate_predictions_snapshot()
    if not valid:
        _logger.warning('Predictions publication validation failed: %s', warnings)
        return

    for algorithm in KNOWN_ALGORITHMS:
        publish_inference_snapshot(algorithm)

    snapshot = publish_snapshot(
        surface=PREDICTIONS_SURFACE,
        source_provider_set=PREDICTIONS_PROVIDERS,
        source_max_fetched_at=utcnow(),
        metadata={'algorithms': KNOWN_ALGORITHMS, 'warnings': warnings},
    )
    _logger.info('Predictions publication promoted: version=%s warnings=%s', snapshot.version, warnings)