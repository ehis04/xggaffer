from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from ml.models.match_outcome.config import (
    ARTIFACT_REQUIRED_KEYS,
    DEFAULT_MODEL_TYPE,
    FRONTEND_CONTRACT_VERSION,
    MODELS_DIR,
    PREDICTION_LABEL_MAP,
    PROBABILITY_KEY_MAP,
    resolve_latest_model_path,
)


class MatchPredictor:
    def __init__(self, model_path: Path):
        artifact = joblib.load(model_path)
        missing_keys = [key for key in ARTIFACT_REQUIRED_KEYS if key not in artifact]
        if missing_keys:
            raise ValueError(f'Invalid model artifact — missing keys: {missing_keys}')

        self.model = artifact['model']
        self.feature_columns = artifact['feature_columns']
        self.model_type = artifact['model_type']
        self.metrics = artifact['metrics']
        self.training_info = artifact['training_info']
        self.version = artifact['version']
        self.model_path = model_path

    def _validate_features(self, features: pd.DataFrame) -> pd.DataFrame:
        missing = [column for column in self.feature_columns if column not in features.columns]
        if missing:
            raise ValueError(f'Missing feature columns: {missing}')
        return features[self.feature_columns]

    def predict(self, features: pd.DataFrame) -> dict:
        X = self._validate_features(features)

        prediction_code = self.model.predict(X)[0]
        probabilities = self.model.predict_proba(X)[0]
        classes = self.model.classes_

        probability_codes = {
            cls: round(float(prob), 4)
            for cls, prob in zip(classes, probabilities)
        }
        probability_labels = {
            PROBABILITY_KEY_MAP[cls]: probability_codes.get(cls, 0.0)
            for cls in ['H', 'D', 'A']
        }

        return {
            'prediction_code': prediction_code,
            'prediction': PREDICTION_LABEL_MAP[prediction_code],
            'probabilities_raw': probability_codes,
            'probabilities': probability_labels,
            'model_type': self.model_type,
            'metrics': {
                'accuracy': self.metrics.get('accuracy'),
                'brier_score': self.metrics.get('brier_score'),
            },
            'version': self.version,
            'contract_version': FRONTEND_CONTRACT_VERSION,
        }

    def predict_batch(self, features: pd.DataFrame) -> pd.DataFrame:
        X = self._validate_features(features)

        predictions = self.model.predict(X)
        probabilities = self.model.predict_proba(X)
        classes = self.model.classes_

        result = features.copy()
        result['prediction_code'] = predictions
        result['prediction'] = [PREDICTION_LABEL_MAP[label] for label in predictions]
        for index, cls in enumerate(classes):
            result[f'prob_{cls}'] = probabilities[:, index].round(4)
        return result

    def get_model_info(self) -> dict:
        return {
            'model_type': self.model_type,
            'version': self.version,
            'metrics': {
                'accuracy': self.metrics.get('accuracy'),
                'brier_score': self.metrics.get('brier_score'),
                'log_loss': self.metrics.get('log_loss'),
            },
            'feature_count': len(self.feature_columns),
            'training_info': self.training_info,
            'contract_version': FRONTEND_CONTRACT_VERSION,
        }


_predictor_cache: dict[str, MatchPredictor] = {}


def get_predictor(model_path: Path | None = None) -> MatchPredictor:
    if model_path is None:
        model_path = resolve_latest_model_path(DEFAULT_MODEL_TYPE)

    cache_key = str(model_path)
    if cache_key not in _predictor_cache:
        _predictor_cache[cache_key] = MatchPredictor(model_path)

    return _predictor_cache[cache_key]
