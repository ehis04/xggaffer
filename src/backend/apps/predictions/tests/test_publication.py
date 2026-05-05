import pytest
from django.utils import timezone

from apps.predictions.models import InferenceSnapshotRecord, ModelArtefactRecord
from apps.predictions.publication import (
    promote_model_artefact,
    publish_inference_snapshot,
    run_predictions_publication,
    validate_predictions_snapshot,
)
from apps.predictions.selectors import get_active_inference_snapshot, get_prediction_freshness
from apps.sync_pipeline.models import PublishedSnapshot


@pytest.mark.django_db
class TestPromoteModelArtefact:
    def test_creates_active_record(self, tmp_path):
        fake = tmp_path / 'match_outcome_v1.joblib'
        fake.touch()
        record = promote_model_artefact('match_outcome', str(fake), timezone.now())
        assert record.is_active is True

    def test_replaces_previous_active(self, tmp_path):
        fake1 = tmp_path / 'v1.joblib'
        fake2 = tmp_path / 'v2.joblib'
        fake1.touch()
        fake2.touch()
        r1 = promote_model_artefact('match_outcome', str(fake1), timezone.now())
        r2 = promote_model_artefact('match_outcome', str(fake2), timezone.now())
        r1.refresh_from_db()
        assert r1.is_active is False
        assert r2.is_active is True

    def test_only_one_active_per_algorithm(self, tmp_path):
        for i in range(3):
            f = tmp_path / f'v{i}.joblib'
            f.touch()
            promote_model_artefact('match_outcome', str(f), timezone.now())
        assert ModelArtefactRecord.objects.filter(
            algorithm='match_outcome', is_active=True
        ).count() == 1


@pytest.mark.django_db
class TestPublishInferenceSnapshot:
    def test_creates_active_snapshot(self):
        record = publish_inference_snapshot('match_outcome')
        assert record.is_active is True
        assert record.snapshot_published_at is not None

    def test_replaces_previous_active(self):
        s1 = publish_inference_snapshot('match_outcome')
        s2 = publish_inference_snapshot('match_outcome')
        s1.refresh_from_db()
        assert s1.is_active is False
        assert s2.is_active is True


@pytest.mark.django_db
class TestValidatePredictionsSnapshot:
    def test_fails_with_no_artefacts(self):
        valid, warnings = validate_predictions_snapshot()
        assert valid is False
        assert warnings

    def test_passes_with_active_artefact(self, tmp_path):
        fake = tmp_path / 'model.joblib'
        fake.touch()
        promote_model_artefact('match_outcome', str(fake), timezone.now())
        valid, warnings = validate_predictions_snapshot()
        assert valid is True


@pytest.mark.django_db
class TestRunPredictionsPublication:
    def test_no_publication_when_no_artefacts(self):
        run_predictions_publication()
        assert PublishedSnapshot.objects.filter(surface='predictions').count() == 0

    def test_publishes_when_artefact_exists(self, tmp_path):
        fake = tmp_path / 'model.joblib'
        fake.touch()
        promote_model_artefact('match_outcome', str(fake), timezone.now())
        run_predictions_publication()
        snap = PublishedSnapshot.objects.filter(surface='predictions', is_active=True).first()
        assert snap is not None

    def test_freshness_not_stale_after_publication(self, tmp_path):
        fake = tmp_path / 'model.joblib'
        fake.touch()
        promote_model_artefact('match_outcome', str(fake), timezone.now())
        run_predictions_publication()
        fp = get_prediction_freshness()
        assert fp.is_stale is False


@pytest.mark.django_db
class TestGetActiveInferenceSnapshot:
    def test_returns_none_before_publish(self):
        assert get_active_inference_snapshot('match_outcome') is None

    def test_returns_record_after_publish(self):
        publish_inference_snapshot('match_outcome')
        snap = get_active_inference_snapshot('match_outcome')
        assert snap is not None