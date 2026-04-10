"""
xgGaffer ML Test Suite

Run all tests:
    pytest test_ml.py -v

Run by category:
    pytest test_ml.py -v -k unit
    pytest test_ml.py -v -k integration
    pytest test_ml.py -v -k ml_behaviour
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from unittest.mock import patch



class TestCreateTarget:
    """Test the target labelling function."""

    def _get_fn(self):
        from ml.models.match_outcome.prepare_data import create_target
        return create_target

    def test_unit_home_win(self):
        df = pd.DataFrame([{'home_goals': 2, 'away_goals': 1}])
        result = self._get_fn()(df)
        assert result['result'].iloc[0] == 'H'

    def test_unit_away_win(self):
        df = pd.DataFrame([{'home_goals': 1, 'away_goals': 3}])
        result = self._get_fn()(df)
        assert result['result'].iloc[0] == 'A'

    def test_unit_draw(self):
        df = pd.DataFrame([{'home_goals': 0, 'away_goals': 0}])
        result = self._get_fn()(df)
        assert result['result'].iloc[0] == 'D'

    def test_unit_high_scoring_draw(self):
        df = pd.DataFrame([{'home_goals': 4, 'away_goals': 4}])
        result = self._get_fn()(df)
        assert result['result'].iloc[0] == 'D'

    def test_unit_does_not_modify_original(self):
        df = pd.DataFrame([{'home_goals': 2, 'away_goals': 1}])
        self._get_fn()(df)
        assert 'result' not in df.columns

    def test_unit_multiple_matches(self):
        df = pd.DataFrame([
            {'home_goals': 3, 'away_goals': 0},
            {'home_goals': 1, 'away_goals': 1},
            {'home_goals': 0, 'away_goals': 2},
        ])
        result = self._get_fn()(df)
        assert list(result['result']) == ['H', 'D', 'A']


class TestDerivedFeatures:
    """Test the derived feature computation."""

    def _get_fn(self):
        from ml.features.understat import add_derived_features
        return add_derived_features

    def test_unit_npxgd_diff(self):
        df = pd.DataFrame([{'home_npxgd': 10.0, 'away_npxgd': -5.0}])
        result = self._get_fn()(df)
        assert result['npxgd_diff'].iloc[0] == 15.0

    def test_unit_ppda_diff(self):
        df = pd.DataFrame([{'home_ppda': 8.0, 'away_ppda': 12.0}])
        result = self._get_fn()(df)
        assert result['ppda_diff'].iloc[0] == -4.0

    def test_unit_squad_xg_diff(self):
        df = pd.DataFrame([{
            'home_squad_total_xg': 50.0, 'away_squad_total_xg': 30.0,
            'home_squad_total_xa': 40.0, 'away_squad_total_xa': 25.0,
            'home_squad_avg_xg90': 0.5, 'away_squad_avg_xg90': 0.3,
            'home_squad_top_xg90': 0.8, 'away_squad_top_xg90': 0.6,
        }])
        result = self._get_fn()(df)
        assert result['squad_xg_diff'].iloc[0] == 20.0
        assert result['squad_xa_diff'].iloc[0] == 15.0

    def test_unit_does_not_modify_original(self):
        df = pd.DataFrame([{'home_npxgd': 10.0, 'away_npxgd': -5.0}])
        self._get_fn()(df)
        assert 'npxgd_diff' not in df.columns

    def test_unit_missing_columns_handled(self):
        df = pd.DataFrame([{'some_other_col': 1.0}])
        result = self._get_fn()(df)
        assert 'npxgd_diff' not in result.columns


class TestFeatureColumns:
    """Test feature column definitions are consistent."""

    def test_unit_feature_count(self):
        from ml.models.match_outcome.prepare_data import FEATURE_COLUMNS
        assert len(FEATURE_COLUMNS) == 83

    def test_unit_no_duplicate_features(self):
        from ml.models.match_outcome.prepare_data import FEATURE_COLUMNS
        assert len(FEATURE_COLUMNS) == len(set(FEATURE_COLUMNS))

    def test_unit_all_features_have_home_or_away_or_diff(self):
        from ml.models.match_outcome.prepare_data import FEATURE_COLUMNS
        for col in FEATURE_COLUMNS:
            assert any(prefix in col for prefix in ['home_', 'away_', '_diff', 'is_']), \
                f"Feature '{col}' doesn't follow naming convention"


class TestConfig:
    """Test configuration values are sensible."""

    def test_unit_paths_are_path_objects(self):
        from ml.models.match_outcome.config import DATA_DIR, RAW_DIR, PROCESSED_DIR, MODELS_DIR
        assert isinstance(DATA_DIR, Path)
        assert isinstance(RAW_DIR, Path)
        assert isinstance(PROCESSED_DIR, Path)
        assert isinstance(MODELS_DIR, Path)

    def test_unit_seasons_are_strings(self):
        from ml.models.match_outcome.config import DEFAULT_SEASONS, TEST_SEASONS
        for s in DEFAULT_SEASONS:
            assert isinstance(s, str)
            assert s.isdigit()
        for s in TEST_SEASONS:
            assert isinstance(s, str)

    def test_unit_test_seasons_subset_of_default(self):
        from ml.models.match_outcome.config import DEFAULT_SEASONS, TEST_SEASONS
        for s in TEST_SEASONS:
            assert s in DEFAULT_SEASONS

    def test_unit_artifact_keys_defined(self):
        from ml.models.match_outcome.config import ARTIFACT_REQUIRED_KEYS
        assert 'model' in ARTIFACT_REQUIRED_KEYS
        assert 'feature_columns' in ARTIFACT_REQUIRED_KEYS
        assert 'version' in ARTIFACT_REQUIRED_KEYS


class TestArtifactValidation:
    """Test that the predictor validates artifact format."""

    def test_unit_missing_keys_raises(self, tmp_path):
        import joblib
        bad_artifact = {'model': None}
        path = tmp_path / 'bad.joblib'
        joblib.dump(bad_artifact, path)

        from ml.models.match_outcome.predict import MatchPredictor
        with pytest.raises(ValueError, match="missing keys"):
            MatchPredictor(path)



class TestPredictionSerializers:
    """Test request/response serializer constraints for the frontend demo contract."""

    def test_unit_same_team_request_rejected(self):
        from apps.predictions.serializers import PredictionRequestSerializer
        serializer = PredictionRequestSerializer(data={
            'home_team': 'Arsenal',
            'away_team': 'Arsenal',
            'league': 'EPL',
            'season': '2024',
        })
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors

    def test_unit_response_contract_valid(self):
        from apps.predictions.serializers import PredictionResponseSerializer
        serializer = PredictionResponseSerializer(data={
            'home_team': 'Arsenal',
            'away_team': 'Chelsea',
            'league': 'EPL',
            'season': '2024',
            'prediction': 'Home',
            'probabilities': {'home': 0.55, 'draw': 0.24, 'away': 0.21},
            'top_factors': [{
                'feature': 'npxgd_diff',
                'value': 0.88,
                'contribution': 0.12,
                'description': 'Home team has stronger non-penalty expected goal difference (+0.88)',
            }],
            'metrics': {'accuracy': 0.56, 'brier_score': 0.61},
            'model_type': 'logistic_regression',
            'version': 'v2',
        })
        assert serializer.is_valid(), serializer.errors



class TestPipelineIntegration:
    """Test the full pipeline from data loading through prediction."""

    @pytest.fixture(autouse=True)
    def _check_data_available(self):
        from ml.models.match_outcome.config import RAW_DIR
        matches_dir = RAW_DIR / 'matches'
        if not matches_dir.exists() or not list(matches_dir.glob('*.csv')):
            pytest.skip("Raw data files not available — run scraper first")

    def test_integration_prepare_dataset(self):
        from ml.models.match_outcome.prepare_data import prepare_dataset, FEATURE_COLUMNS
        df = prepare_dataset(leagues=['EPL'], seasons=['2024'], save=False)
        assert len(df) > 100
        available = [c for c in FEATURE_COLUMNS if c in df.columns]
        assert len(available) == 42
        assert 'result' in df.columns
        assert set(df['result'].unique()).issubset({'H', 'D', 'A'})

    def test_integration_feature_service(self):
        from ml.models.match_outcome.feature_service import FeatureService
        from ml.models.match_outcome.prepare_data import FEATURE_COLUMNS
        service = FeatureService(leagues=['EPL'], seasons=['2024'])
        features = service.build_prediction_features('Arsenal', 'Chelsea', 'EPL', '2024')
        assert list(features.columns) == FEATURE_COLUMNS
        assert len(features) == 1
        assert not features.isnull().any().any()

    def test_integration_feature_service_invalid_team(self):
        from ml.models.match_outcome.feature_service import FeatureService
        service = FeatureService(leagues=['EPL'], seasons=['2024'])
        with pytest.raises(ValueError, match="No data found"):
            service.build_prediction_features('Fake FC', 'Chelsea', 'EPL', '2024')

    def test_integration_available_teams(self):
        from ml.models.match_outcome.feature_service import FeatureService
        service = FeatureService(leagues=['EPL'], seasons=['2024'])
        teams = service.get_available_teams(league='EPL', season='2024')
        assert len(teams) == 20
        assert 'Arsenal' in teams


class TestPredictorIntegration:
    """Test the predictor with a real saved model."""

    @pytest.fixture(autouse=True)
    def _check_model_available(self):
        from ml.models.match_outcome.config import MODELS_DIR
        models = list(MODELS_DIR.glob('match_outcome_logistic_regression_*.joblib'))
        if not models:
            pytest.skip("No trained logistic regression model available — run train.py --model logistic_regression first")

    def test_integration_load_predictor(self):
        from ml.models.match_outcome.predict import get_predictor
        from ml.models.match_outcome.prepare_data import FEATURE_COLUMNS
        predictor = get_predictor()
        assert predictor.model is not None
        assert predictor.model_type == 'logistic_regression'
        assert len(predictor.feature_columns) == len(FEATURE_COLUMNS)

    def test_integration_predict_returns_valid_format(self):
        from ml.models.match_outcome.predict import get_predictor
        from ml.models.match_outcome.feature_service import FeatureService
        predictor = get_predictor()
        service = FeatureService(leagues=['EPL'], seasons=['2024'])
        features = service.build_prediction_features('Arsenal', 'Chelsea', 'EPL', '2024')
        result = predictor.predict(features)

        assert result['prediction'] in ['Home', 'Draw', 'Away']
        assert set(result['probabilities'].keys()) == {'home', 'draw', 'away'}
        assert abs(sum(result['probabilities'].values()) - 1.0) < 0.01
        assert result['model_type'] == 'logistic_regression'
        assert 'metrics' in result
        assert 'version' in result

    def test_integration_model_info(self):
        from ml.models.match_outcome.predict import get_predictor
        predictor = get_predictor()
        info = predictor.get_model_info()
        assert 'metrics' in info
        assert info['metrics']['accuracy'] > 0.3
        assert 'brier_score' in info['metrics']
        from ml.models.match_outcome.prepare_data import FEATURE_COLUMNS
        assert info['feature_count'] == len(FEATURE_COLUMNS)


class TestInterpretIntegration:
    """Test the interpretation pipeline end-to-end."""

    @pytest.fixture(autouse=True)
    def _check_available(self):
        from ml.models.match_outcome.config import MODELS_DIR, RAW_DIR
        models = list(MODELS_DIR.glob('match_outcome_logistic_regression_*.joblib'))
        matches = list((RAW_DIR / 'matches').glob('*.csv')) if (RAW_DIR / 'matches').exists() else []
        if not models or not matches:
            pytest.skip("Model or data not available")

    def test_integration_explain_match(self):
        from ml.models.match_outcome.interpret import explain_match
        result = explain_match('Arsenal', 'Chelsea', 'EPL', '2024', top_n=3)
        assert result['prediction'] in ['H', 'D', 'A']
        assert len(result['top_factors']) == 3
        for factor in result['top_factors']:
            assert 'feature' in factor
            assert 'contribution' in factor
            assert 'description' in factor

    def test_integration_coefficients(self):
        from ml.models.match_outcome.interpret import get_coefficients
        coefs = get_coefficients()
        assert len(coefs) == 42
        assert 'coef_H' in coefs.columns
        assert 'coef_D' in coefs.columns
        assert 'coef_A' in coefs.columns



class TestModelBehaviour:
    """Test that the model produces sensible predictions."""

    @pytest.fixture(autouse=True)
    def _check_available(self):
        from ml.models.match_outcome.config import MODELS_DIR, RAW_DIR
        models = list(MODELS_DIR.glob('match_outcome_logistic_regression_*.joblib'))
        matches = list((RAW_DIR / 'matches').glob('*.csv')) if (RAW_DIR / 'matches').exists() else []
        if not models or not matches:
            pytest.skip("Model or data not available")

    def test_ml_behaviour_probabilities_sum_to_one(self):
        from ml.models.match_outcome.predict import get_predictor
        from ml.models.match_outcome.feature_service import FeatureService
        predictor = get_predictor()
        service = FeatureService(leagues=['EPL'], seasons=['2024'])

        matchups = [
            ('Arsenal', 'Everton'),
            ('Chelsea', 'Liverpool'),
            ('Bournemouth', 'Brentford'),
        ]
        for home, away in matchups:
            features = service.build_prediction_features(home, away, 'EPL', '2024')
            result = predictor.predict(features)
            total = sum(result['probabilities'].values())
            assert abs(total - 1.0) < 0.01, f"{home} vs {away}: probs sum to {total}"

    def test_ml_behaviour_no_negative_probabilities(self):
        from ml.models.match_outcome.predict import get_predictor
        from ml.models.match_outcome.feature_service import FeatureService
        predictor = get_predictor()
        service = FeatureService(leagues=['EPL'], seasons=['2024'])

        features = service.build_prediction_features('Arsenal', 'Everton', 'EPL', '2024')
        result = predictor.predict(features)
        for cls, prob in result['probabilities'].items():
            assert prob >= 0.0, f"Negative probability for {cls}: {prob}"
            assert prob <= 1.0, f"Probability > 1.0 for {cls}: {prob}"

    def test_ml_behaviour_strong_vs_weak_favours_strong(self):
        from ml.models.match_outcome.feature_service import predict_match
        result = predict_match('Arsenal', 'Everton', 'EPL', '2024')
        assert result['probabilities']['H'] > result['probabilities']['A'], \
            "Arsenal at home should be favoured over Everton"

    def test_ml_behaviour_home_advantage(self):
        from ml.models.match_outcome.feature_service import predict_match
        home_result = predict_match('Arsenal', 'Chelsea', 'EPL', '2024')
        away_result = predict_match('Chelsea', 'Arsenal', 'EPL', '2024')
        assert home_result['probabilities']['H'] != away_result['probabilities']['H'], \
            "Swapping home/away should change probabilities"

    def test_ml_behaviour_accuracy_above_baseline(self):
        from ml.models.match_outcome.predict import get_predictor
        predictor = get_predictor()
        accuracy = predictor.metrics['accuracy']
        assert accuracy > 0.42, \
            f"Model accuracy {accuracy} is below the home-always baseline of 0.42"

    def test_ml_behaviour_feature_count_matches_model(self):
        from ml.models.match_outcome.predict import get_predictor
        from ml.models.match_outcome.prepare_data import FEATURE_COLUMNS
        predictor = get_predictor()
        assert predictor.feature_columns == FEATURE_COLUMNS, \
            "Predictor feature columns don't match FEATURE_COLUMNS definition"

    def test_ml_behaviour_reproducible_predictions(self):
        from ml.models.match_outcome.predict import get_predictor
        from ml.models.match_outcome.feature_service import FeatureService
        predictor = get_predictor()
        service = FeatureService(leagues=['EPL'], seasons=['2024'])

        features = service.build_prediction_features('Arsenal', 'Chelsea', 'EPL', '2024')
        result1 = predictor.predict(features)
        result2 = predictor.predict(features)
        assert result1['prediction'] == result2['prediction']
        assert result1['probabilities'] == result2['probabilities']



class TestAPIEndpoints:
    """Test the DRF prediction endpoints."""

    @pytest.fixture(autouse=True)
    def _check_available(self):
        try:
            import django
            django.setup()
        except Exception:
            pytest.skip("Django not configured")

        from ml.models.match_outcome.config import MODELS_DIR, RAW_DIR
        models = list(MODELS_DIR.glob('match_outcome_logistic_regression_*.joblib'))
        matches = list((RAW_DIR / 'matches').glob('*.csv')) if (RAW_DIR / 'matches').exists() else []
        if not models or not matches:
            pytest.skip("Model or data not available")

    def test_api_predict_success(self):
        from django.test import RequestFactory
        from apps.predictions.views import PredictMatchView

        factory = RequestFactory()
        request = factory.post(
            '/api/predictions/predict/',
            data={'home_team': 'Arsenal', 'away_team': 'Chelsea', 'league': 'EPL', 'season': '2024'},
            content_type='application/json',
        )
        response = PredictMatchView.as_view()(request)
        assert response.status_code == 200
        assert response.data['prediction'] in ['Home', 'Draw', 'Away']
        assert set(response.data['probabilities'].keys()) == {'home', 'draw', 'away'}
        assert 'top_factors' in response.data
        assert 'metrics' in response.data

    def test_api_predict_invalid_team(self):
        from django.test import RequestFactory
        from apps.predictions.views import PredictMatchView

        factory = RequestFactory()
        request = factory.post(
            '/api/predictions/predict/',
            data={'home_team': 'Fake FC', 'away_team': 'Chelsea', 'league': 'EPL', 'season': '2024'},
            content_type='application/json',
        )
        response = PredictMatchView.as_view()(request)
        assert response.status_code == 400
        assert 'error' in response.data

    def test_api_predict_missing_field(self):
        from django.test import RequestFactory
        from apps.predictions.views import PredictMatchView

        factory = RequestFactory()
        request = factory.post(
            '/api/predictions/predict/',
            data={'home_team': 'Arsenal'},
            content_type='application/json',
        )
        response = PredictMatchView.as_view()(request)
        assert response.status_code == 400

    def test_api_teams(self):
        from django.test import RequestFactory
        from apps.predictions.views import AvailableTeamsView

        factory = RequestFactory()
        request = factory.get('/api/predictions/teams/', {'league': 'EPL', 'season': '2024'})
        response = AvailableTeamsView.as_view()(request)
        assert response.status_code == 200
        assert response.data['count'] == 20
        assert 'Arsenal' in response.data['teams']

    def test_api_model_info(self):
        from django.test import RequestFactory
        from apps.predictions.views import ModelInfoView

        factory = RequestFactory()
        request = factory.get('/api/predictions/model-info/')
        response = ModelInfoView.as_view()(request)
        assert response.status_code == 200
        assert response.data['model_type'] == 'logistic_regression'
        assert 'metrics' in response.data
        assert 'accuracy' in response.data['metrics']
        assert 'version' in response.data