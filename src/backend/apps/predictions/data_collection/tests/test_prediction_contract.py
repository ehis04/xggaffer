from __future__ import annotations

import importlib
from pathlib import Path

import joblib
import pandas as pd
import pytest


serializers_module = pytest.importorskip('serializers')
predict_module = pytest.importorskip('ml.models.match_outcome.predict')

PredictionRequestSerializer = serializers_module.PredictionRequestSerializer
PredictionResponseSerializer = serializers_module.PredictionResponseSerializer
MatchPredictor = predict_module.MatchPredictor


class DummyModel:
    classes_ = ['H', 'D', 'A']

    def predict(self, X):
        return ['H']

    def predict_proba(self, X):
        return [[0.61, 0.23, 0.16]]


@pytest.fixture

def fake_artifact_path(tmp_path: Path) -> Path:
    artifact = {
        'model': DummyModel(),
        'feature_columns': ['feature_a', 'feature_b'],
        'model_type': 'logistic_regression',
        'metrics': {
            'accuracy': 0.555,
            'brier_score': 0.6123,
            'log_loss': 0.98,
        },
        'training_info': {
            'leagues': ['EPL'],
            'seasons': ['2024'],
            'test_seasons': ['2024'],
        },
        'version': 'v2',
    }
    path = tmp_path / 'match_outcome_logistic_regression_v2_20990101_000000.joblib'
    joblib.dump(artifact, path)
    return path


def test_request_serializer_rejects_same_teams():
    serializer = PredictionRequestSerializer(data={
        'home_team': 'Arsenal',
        'away_team': 'Arsenal',
        'league': 'EPL',
        'season': '2024',
    })

    assert not serializer.is_valid()
    assert 'non_field_errors' in serializer.errors



def test_response_serializer_accepts_frontend_contract_payload():
    serializer = PredictionResponseSerializer(data={
        'home_team': 'Arsenal',
        'away_team': 'Chelsea',
        'league': 'EPL',
        'season': '2024',
        'prediction': 'Home',
        'probabilities': {
            'home': 0.61,
            'draw': 0.23,
            'away': 0.16,
        },
        'top_factors': [
            {
                'feature': 'xgd_diff',
                'value': 0.72,
                'contribution': 0.34,
                'description': 'Home team has the edge in expected goal difference (+0.72)',
            }
        ],
        'metrics': {
            'accuracy': 0.555,
            'brier_score': 0.6123,
        },
        'model_type': 'logistic_regression',
        'version': 'v2',
        'contract_version': 'v1',
    })

    assert serializer.is_valid(), serializer.errors



def test_match_predictor_returns_frontend_contract(fake_artifact_path: Path):
    predictor = MatchPredictor(fake_artifact_path)
    features = pd.DataFrame([{'feature_a': 1.5, 'feature_b': -0.2}])

    result = predictor.predict(features)

    assert result['prediction_code'] == 'H'
    assert result['prediction'] == 'Home'
    assert result['probabilities'] == {
        'home': 0.61,
        'draw': 0.23,
        'away': 0.16,
    }
    assert result['probabilities_raw'] == {
        'H': 0.61,
        'D': 0.23,
        'A': 0.16,
    }
    assert result['metrics'] == {
        'accuracy': 0.555,
        'brier_score': 0.6123,
    }



def test_model_info_includes_frontend_metrics(fake_artifact_path: Path):
    predictor = MatchPredictor(fake_artifact_path)

    info = predictor.get_model_info()

    assert info['model_type'] == 'logistic_regression'
    assert info['metrics']['accuracy'] == 0.555
    assert info['metrics']['brier_score'] == 0.6123
    assert info['feature_count'] == 2
