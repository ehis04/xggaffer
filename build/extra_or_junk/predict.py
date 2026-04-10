import joblib
import pandas as pd
from pathlib import Path


MODELS_DIR = Path(__file__).resolve().parents[4] / 'data' / 'models'


class MatchPredictor:

    def __init__(self, model_name: str):
        model_path = MODELS_DIR / f"{model_name}.joblib"
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        metadata = joblib.load(model_path)
        
        self.model = metadata['model']
        self.feature_columns = metadata['feature_columns']
        self.feature_set = metadata['feature_set']
        self.metrics = metadata['metrics']
    
    def _engineer_features(self, team_xg: float, opponent_xg: float, is_home: bool) -> pd.DataFrame:
        features = {
            'team_xg': team_xg,
            'opponent_xg': opponent_xg,
            'is_home': int(is_home),
            'xg_diff': team_xg - opponent_xg,
            'xg_ratio': team_xg / max(opponent_xg, 0.1),
        }
        
        return pd.DataFrame([features])[self.feature_columns]
    
    def predict(self, team_xg: float, opponent_xg: float, is_home: bool) -> dict:
        features = self._engineer_features(team_xg, opponent_xg, is_home)
        
        prediction = self.model.predict(features)[0]
        probabilities = self.model.predict_proba(features)[0]
        
        raw_win_prob = float(probabilities[1]) if len(probabilities) > 1 else float(probabilities[0])
        raw_confidence = float(max(probabilities))
        
        smoothed_win_prob = 0.5 + (raw_win_prob - 0.5) * 0.7
        smoothed_confidence = 0.5 + (raw_confidence - 0.5) * 0.7
        
        return {
            'prediction': 'W' if prediction == 1 else 'L',
            'confidence': round(smoothed_confidence, 3),
            'win_probability': round(smoothed_win_prob, 3),
        }


_predictors = {}


def get_predictor(model_name: str = 'match_predictor_v1') -> MatchPredictor:
    if model_name not in _predictors:
        _predictors[model_name] = MatchPredictor(model_name)
    return _predictors[model_name]