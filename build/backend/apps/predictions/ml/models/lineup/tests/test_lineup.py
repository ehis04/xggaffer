"""
xgGaffer Engine 7 — Lineup Prediction Test Suite

Run all tests:
    pytest apps/predictions/ml/models/lineup/tests/test_lineup.py -v

Run by category:
    pytest apps/predictions/ml/models/lineup/tests/test_lineup.py -v -k unit
    pytest apps/predictions/ml/models/lineup/tests/test_lineup.py -v -k integration
    pytest apps/predictions/ml/models/lineup/tests/test_lineup.py -v -k ml_behaviour
    pytest apps/predictions/ml/models/lineup/tests/test_lineup.py -v -k api
"""

import pytest
import numpy as np
import pandas as pd


class TestPositionCategoryMapping:

    def _get_map(self):
        from apps.predictions.ml.models.lineup.config import POSITION_CATEGORY_MAP
        return POSITION_CATEGORY_MAP

    def test_unit_goalkeeper_mapped_to_gk(self):
        assert self._get_map()['GK'] == 'GK'

    def test_unit_defenders_mapped_to_def(self):
        m = self._get_map()
        assert m['DC'] == 'DEF'
        assert m['DR'] == 'DEF'
        assert m['DL'] == 'DEF'

    def test_unit_midfielders_mapped_to_mid(self):
        m = self._get_map()
        assert m['DMC'] == 'MID'
        assert m['MC'] == 'MID'
        assert m['AMC'] == 'MID'

    def test_unit_forwards_mapped_to_fwd(self):
        m = self._get_map()
        assert m['FW'] == 'FWD'

    def test_unit_sub_mapped_to_sub(self):
        assert self._get_map()['Sub'] == 'SUB'


class TestFormationSlots:

    def _get_slots(self):
        from apps.predictions.ml.models.lineup.config import FORMATION_SLOTS
        return FORMATION_SLOTS

    def test_unit_4_3_3_slots_sum_to_11(self):
        slots = self._get_slots()['4-3-3']
        assert sum(slots.values()) == 11

    def test_unit_all_formations_sum_to_11(self):
        for formation, slots in self._get_slots().items():
            assert sum(slots.values()) == 11, f'{formation} does not sum to 11'

    def test_unit_all_formations_have_one_gk(self):
        for formation, slots in self._get_slots().items():
            assert slots['GK'] == 1, f'{formation} does not have exactly 1 GK'


class TestAssembleXI:

    def _make_probs_df(self):
        from apps.predictions.ml.models.lineup.config import POSITION_CATEGORY_MAP
        rows = []
        rows.append({'player_id': 'gk1', 'player_name': 'Keeper', 'team_id': '1', 'position': 'GK', 'p_start': 0.99})
        for i, pos in enumerate(['DC', 'DC', 'DR', 'DL', 'DC', 'DR']):
            rows.append({
                'player_id': f'def{i}', 'player_name': f'Defender{i}', 'team_id': '1',
                'position': pos, 'p_start': 0.95 - i * 0.05,
            })
        for i, pos in enumerate(['MC', 'DMC', 'AMC', 'MC', 'AMC']):
            rows.append({
                'player_id': f'mid{i}', 'player_name': f'Mid{i}', 'team_id': '1',
                'position': pos, 'p_start': 0.90 - i * 0.05,
            })
        for i, pos in enumerate(['FW', 'FWL', 'FWR', 'FW']):
            rows.append({
                'player_id': f'fwd{i}', 'player_name': f'Fwd{i}', 'team_id': '1',
                'position': pos, 'p_start': 0.85 - i * 0.05,
            })
        return pd.DataFrame(rows)

    def test_unit_xi_produces_11_players(self):
        from apps.predictions.ml.models.lineup.predict import assemble_xi
        probs = self._make_probs_df()
        xi = assemble_xi(probs, '4-3-3')
        assert len(xi) == 11

    def test_unit_xi_respects_4_3_3_formation(self):
        from apps.predictions.ml.models.lineup.predict import assemble_xi
        from apps.predictions.ml.models.lineup.config import POSITION_CATEGORY_MAP
        probs = self._make_probs_df()
        xi = assemble_xi(probs, '4-3-3')
        xi['category'] = xi['position'].map(POSITION_CATEGORY_MAP).fillna('MID')
        assert (xi['category'] == 'GK').sum() == 1
        assert (xi['category'] == 'DEF').sum() == 4
        assert (xi['category'] == 'MID').sum() == 3
        assert (xi['category'] == 'FWD').sum() == 3

    def test_unit_xi_has_exactly_one_gk(self):
        from apps.predictions.ml.models.lineup.predict import assemble_xi
        from apps.predictions.ml.models.lineup.config import POSITION_CATEGORY_MAP
        probs = self._make_probs_df()
        xi = assemble_xi(probs, '4-2-3-1')
        xi['category'] = xi['position'].map(POSITION_CATEGORY_MAP).fillna('MID')
        assert (xi['category'] == 'GK').sum() == 1

    def test_unit_xi_selects_highest_probability(self):
        from apps.predictions.ml.models.lineup.predict import assemble_xi
        probs = self._make_probs_df()
        xi = assemble_xi(probs, '4-3-3')
        assert 'gk1' in xi['player_id'].values

    def test_unit_xi_no_duplicate_players(self):
        from apps.predictions.ml.models.lineup.predict import assemble_xi
        probs = self._make_probs_df()
        xi = assemble_xi(probs, '4-3-3')
        assert xi['player_id'].nunique() == 11


class TestFeatureMatrix:

    @pytest.fixture(autouse=True)
    def _check_available(self):
        from apps.predictions.ml.models.lineup.config import LINEUP_DIR
        if not any(LINEUP_DIR.glob('*_lineups.csv')):
            pytest.skip('No lineup CSVs available')

    def test_integration_feature_matrix_shape(self):
        from apps.predictions.ml.models.lineup.prepare_data import (
            build_lineup_dataset, get_feature_columns,
        )
        df = build_lineup_dataset(leagues=['EPL'], seasons=['2024'], save=False)
        assert len(df) > 5000
        features = get_feature_columns(df)
        assert len(features) == 20

    def test_integration_starter_rate_reasonable(self):
        from apps.predictions.ml.models.lineup.prepare_data import build_lineup_dataset
        df = build_lineup_dataset(leagues=['EPL'], seasons=['2024'], save=False)
        starter_rate = df['started'].mean()
        assert 0.60 < starter_rate < 0.80

    def test_integration_all_features_present(self):
        from apps.predictions.ml.models.lineup.prepare_data import (
            build_lineup_dataset, get_feature_columns,
        )
        df = build_lineup_dataset(leagues=['EPL'], seasons=['2024'], save=False)
        features = get_feature_columns(df)
        for feature in features:
            assert feature in df.columns

    def test_integration_temporal_contract_workload(self):
        from apps.predictions.ml.models.lineup.prepare_data import build_lineup_dataset
        df = build_lineup_dataset(leagues=['EPL'], seasons=['2024'], save=False)
        df_sorted = df.sort_values(['player_id', 'date'])
        first_match_per_player = df_sorted.groupby('player_id').head(1)
        assert first_match_per_player['minutes_last_match'].isna().all()


class TestModelBehaviour:

    @pytest.fixture(autouse=True)
    def _check_available(self):
        from apps.predictions.ml.models.lineup.config import MODELS_DIR
        models = list(MODELS_DIR.glob('lineup_xgboost_*.joblib'))
        if not models:
            pytest.skip('No lineup model available')

    def test_ml_behaviour_probabilities_between_0_and_1(self):
        from apps.predictions.ml.models.lineup.predict import LineupPredictor
        from apps.predictions.ml.models.lineup.feature_service import get_latest_team_features
        predictor = LineupPredictor()
        features = get_latest_team_features('Arsenal', 'EPL', '2024')
        probs = predictor.predict_start_probabilities(features)
        assert (probs['p_start'] >= 0).all()
        assert (probs['p_start'] <= 1).all()

    def test_ml_behaviour_model_beats_persistence(self):
        from apps.predictions.ml.models.lineup.predict import LineupPredictor
        predictor = LineupPredictor()
        accuracy = predictor.metrics.get('accuracy', 0)
        baseline = predictor.metrics.get('persistence_baseline', 0)
        assert accuracy > baseline, \
            f'Model accuracy {accuracy} does not beat persistence baseline {baseline}'

    def test_ml_behaviour_accuracy_above_baseline(self):
        from apps.predictions.ml.models.lineup.predict import LineupPredictor
        predictor = LineupPredictor()
        accuracy = predictor.metrics.get('accuracy', 0)
        assert accuracy > 0.80, f'Accuracy {accuracy} below 0.80'

    def test_ml_behaviour_feature_importance_sensible(self):
        from apps.predictions.ml.models.lineup.predict import LineupPredictor
        predictor = LineupPredictor()
        importance = predictor.metrics.get('feature_importance', {})
        if importance:
            top_5 = list(importance.keys())[:5]
            position_features = ['is_gk', 'is_def', 'is_mid', 'is_fwd']
            workload_features = [
                'minutes_last_match', 'minutes_last_3_matches', 'minutes_last_5_matches',
                'started_last_match', 'consecutive_starts', 'squad_role',
            ]
            relevant = any(f in top_5 for f in position_features + workload_features)
            assert relevant, f'Top 5 features {top_5} contain no expected signals'

    def test_ml_behaviour_xi_valid_formation(self):
        from apps.predictions.ml.models.lineup.predict import LineupPredictor, assemble_xi, infer_formation
        from apps.predictions.ml.models.lineup.feature_service import get_latest_team_features
        from apps.predictions.ml.models.lineup.config import POSITION_CATEGORY_MAP
        predictor = LineupPredictor()
        features = get_latest_team_features('Arsenal', 'EPL', '2024')
        probs = predictor.predict_start_probabilities(features)
        formation = infer_formation(features)
        xi = assemble_xi(probs, formation)
        assert len(xi) == 11
        xi['category'] = xi['position'].map(POSITION_CATEGORY_MAP).fillna('MID')
        assert (xi['category'] == 'GK').sum() == 1

    def test_ml_behaviour_reproducible_predictions(self):
        from apps.predictions.ml.models.lineup.predict import LineupPredictor
        from apps.predictions.ml.models.lineup.feature_service import get_latest_team_features
        predictor = LineupPredictor()
        features = get_latest_team_features('Arsenal', 'EPL', '2024')
        probs1 = predictor.predict_start_probabilities(features)
        probs2 = predictor.predict_start_probabilities(features)
        pd.testing.assert_series_equal(probs1['p_start'], probs2['p_start'])


@pytest.mark.django_db
class TestAPIEndpoints:

    @pytest.fixture(autouse=True)
    def _check_available(self):
        try:
            import django
            django.setup()
        except Exception:
            pytest.skip('Django not configured')

        from apps.predictions.ml.models.lineup.config import MODELS_DIR
        from apps.predictions.ml.models.lineup.feature_service import FEATURES_CSV
        models = list(MODELS_DIR.glob('lineup_xgboost_*.joblib'))
        if not models or not FEATURES_CSV.exists():
            pytest.skip('Model or feature cache not available')

    def test_api_lineup_success(self):
        from django.test import RequestFactory
        from apps.predictions.views import PredictLineupView
        factory = RequestFactory()
        request = factory.get(
            '/api/predictions/lineup/',
            {'team': 'Arsenal', 'league': 'EPL', 'season': '2024'},
        )
        response = PredictLineupView.as_view()(request)
        assert response.status_code == 200
        assert response.data['data']['team'] == 'Arsenal'
        assert len(response.data['data']['predicted_xi']) == 11
        assert 'formation' in response.data['data']
        assert 'rotation_risks' in response.data['data']

    def test_api_lineup_invalid_team(self):
        from django.test import RequestFactory
        from apps.predictions.views import PredictLineupView
        factory = RequestFactory()
        request = factory.get(
            '/api/predictions/lineup/',
            {'team': 'Fake FC XYZ', 'league': 'EPL', 'season': '2024'},
        )
        response = PredictLineupView.as_view()(request)
        assert response.status_code == 400

    def test_api_lineup_missing_field(self):
        from django.test import RequestFactory
        from apps.predictions.views import PredictLineupView
        factory = RequestFactory()
        request = factory.get('/api/predictions/lineup/', {'team': 'Arsenal'})
        response = PredictLineupView.as_view()(request)
        assert response.status_code == 400

    def test_api_lineup_probabilities_valid(self):
        from django.test import RequestFactory
        from apps.predictions.views import PredictLineupView
        factory = RequestFactory()
        request = factory.get(
            '/api/predictions/lineup/',
            {'team': 'Arsenal', 'league': 'EPL', 'season': '2024'},
        )
        response = PredictLineupView.as_view()(request)
        for player in response.data['predicted_xi']:
            assert 0.0 <= player['p_start'] <= 1.0

    def test_api_lineup_teams_success(self):
        from django.test import RequestFactory
        from apps.predictions.views import AvailableLineupTeamsView
        factory = RequestFactory()
        request = factory.get(
            '/api/predictions/lineup/teams/',
            {'league': 'EPL', 'season': '2024'},
        )
        response = AvailableLineupTeamsView.as_view()(request)
        assert response.status_code == 200
        assert response.data['count'] == 20
        assert 'Arsenal' in response.data['teams']