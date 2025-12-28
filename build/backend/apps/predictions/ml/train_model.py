import argparse
import joblib
from pathlib import Path
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

from .prepare_data import prepare_pipeline
from .evaluate import evaluate_model, print_metrics 
from .features import get_feature_set, TARGET_COLUMN_BINARY

MODEL_TYPES = {
    'decision_tree': lambda: DecisionTreeClassifier(max_depth=5, random_state=42),
    'random_forest': lambda: RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42),
}

def train_model(
    data_file: str,
    model_name: str,
    model_type: str = 'random_forest',
    feature_set: str = 'xg_only',
    test_size: float = 0.2,
) -> tuple:
    
    feature_columns = get_feature_set(feature_set)
    
    data = prepare_pipeline(data_file, test_size, feature_columns)
    
    X_train = data['X_train']
    y_train = data['y_train']
    X_test = data['X_test']
    y_test = data['y_test']
    
    if model_type not in MODEL_TYPES:
        raise ValueError(f"Unknown model type: {model_type}")
    
    model = MODEL_TYPES[model_type]()
    model.fit(X_train, y_train)
    
    metrics = evaluate_model(model, X_test, y_test)
    
    model_path = Path(f"models/{model_name}.joblib")
    model_path.parent.mkdir(parents=True, exist_ok=True)
    
    metadata = {
        'model': model,
        'feature_columns': feature_columns,
        'feature_set': feature_set,
        'model_type': model_type,
        'data_file': data_file,
        'metrics': metrics,
    }
    
    joblib.dump(metadata, model_path)
    
    return model, metrics


def save_model(model, filepath: str = 'models/match_predictor_v1.joblib') -> None:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load_model(filepath: str = 'models/match_predictor_v1.joblib'):
    return joblib.load(filepath)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True, help='Path to CSV file')
    parser.add_argument('--name', required=True, help='Model name for saving')
    parser.add_argument('--type', default='random_forest', choices=MODEL_TYPES.keys())
    parser.add_argument('--features', default='xg_only', help='Feature set name')
    parser.add_argument('--test-size', type=float, default=0.2)
    
    args = parser.parse_args()
    
    model, metrics = train_model(
        data_file=args.data,
        model_name=args.name,
        model_type=args.type,
        feature_set=args.features,
        test_size=args.test_size,
    )
    
    print(f"Model saved: models/{args.name}.joblib")
    print_metrics(metrics)