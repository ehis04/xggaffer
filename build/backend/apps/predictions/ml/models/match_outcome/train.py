import joblib
import pandas as pd
from pathlib import Path
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from ml.models.match_outcome.prepare_data import (
    prepare_dataset,
    get_train_test_split,
    get_temporal_split,
    get_feature_columns,
)


DATA_DIR = Path(__file__).resolve().parents[5] / 'data'
MODELS_DIR = DATA_DIR / 'models'


MODELS = {
    'logistic_regression': Pipeline([
        ('scaler', StandardScaler()),
        ('clf', LogisticRegression(max_iter=1000, random_state=42)),
    ]),
    'random_forest': RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
    ),
    'gradient_boosting': GradientBoostingClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        min_samples_split=10,
        random_state=42,
    ),
}


def train_model(
    model_type: str = 'random_forest',
    use_temporal_split: bool = True,
    test_seasons: list[str] = None,
    leagues: list[str] = None,
    seasons: list[str] = None,
    save: bool = True,
) -> dict:
    leagues = leagues or ['EPL']
    seasons = seasons or ['2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024']
    test_seasons = test_seasons or ['2024']
    
    print(f"Preparing dataset...")
    df = prepare_dataset(leagues=leagues, seasons=seasons, save=False)
    print(f"  Total samples: {len(df)}")
    
    feature_cols = get_feature_columns(df)
    print(f"  Features: {len(feature_cols)}")
    
    if use_temporal_split:
        print(f"Using temporal split (test seasons: {test_seasons})")
        X_train, X_test, y_train, y_test = get_temporal_split(df, test_seasons)
    else:
        print(f"Using random split (80/20)")
        X_train, X_test, y_train, y_test = get_train_test_split(df)
    
    print(f"  Train samples: {len(X_train)}")
    print(f"  Test samples: {len(X_test)}")
    
    if model_type not in MODELS:
        raise ValueError(f"Unknown model type: {model_type}. Choose from: {list(MODELS.keys())}")
    
    model = MODELS[model_type]
    
    print(f"\nTraining {model_type}...")
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)
    conf_matrix = confusion_matrix(y_test, y_pred, labels=['H', 'D', 'A'])
    
    print(f"\n{'='*50}")
    print(f"Results: {model_type}")
    print(f"{'='*50}")
    print(f"Accuracy: {accuracy:.3f}")
    print(f"\nClassification Report:")
    print(classification_report(y_test, y_pred))
    print(f"Confusion Matrix (H/D/A):")
    print(conf_matrix)
    
    if hasattr(model, 'feature_importances_'):
        importances = pd.DataFrame({
            'feature': feature_cols,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        print(f"\nTop 10 Feature Importances:")
        print(importances.head(10).to_string(index=False))
    elif hasattr(model, 'named_steps') and hasattr(model.named_steps['clf'], 'coef_'):
        coefs = pd.DataFrame({
            'feature': feature_cols,
            'coef_H': model.named_steps['clf'].coef_[0],
            'coef_D': model.named_steps['clf'].coef_[1],
            'coef_A': model.named_steps['clf'].coef_[2],
        })
        coefs['abs_mean'] = coefs[['coef_H', 'coef_D', 'coef_A']].abs().mean(axis=1)
        coefs = coefs.sort_values('abs_mean', ascending=False)
        print(f"\nTop 10 Feature Coefficients:")
        print(coefs.head(10).to_string(index=False))
    
    results = {
        'model_type': model_type,
        'accuracy': accuracy,
        'report': report,
        'confusion_matrix': conf_matrix,
        'features': feature_cols,
        'feature_count': len(feature_cols),
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'leagues': leagues,
        'seasons': seasons,
        'test_seasons': test_seasons if use_temporal_split else None,
        'trained_at': datetime.now().isoformat(),
    }
    
    if save:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_filename = f"match_outcome_{model_type}_{timestamp}.joblib"
        model_path = MODELS_DIR / model_filename
        
        joblib.dump({
            'model': model,
            'metadata': results,
        }, model_path)
        
        print(f"\nModel saved to: {model_path}")
        results['model_path'] = str(model_path)
    
    return results


def compare_models(
    use_temporal_split: bool = True,
    test_seasons: list[str] = None,
    leagues: list[str] = None,
    seasons: list[str] = None,
) -> pd.DataFrame:
    results = []
    
    for model_type in MODELS.keys():
        print(f"\n{'='*60}")
        print(f"Training: {model_type}")
        print(f"{'='*60}")
        
        result = train_model(
            model_type=model_type,
            use_temporal_split=use_temporal_split,
            test_seasons=test_seasons,
            leagues=leagues,
            seasons=seasons,
            save=False,
        )
        
        results.append({
            'model': model_type,
            'accuracy': result['accuracy'],
            'features': result['feature_count'],
            'precision_H': result['report']['H']['precision'],
            'recall_H': result['report']['H']['recall'],
            'f1_H': result['report']['H']['f1-score'],
            'precision_D': result['report']['D']['precision'],
            'recall_D': result['report']['D']['recall'],
            'f1_D': result['report']['D']['f1-score'],
            'precision_A': result['report']['A']['precision'],
            'recall_A': result['report']['A']['recall'],
            'f1_A': result['report']['A']['f1-score'],
        })
    
    comparison = pd.DataFrame(results)
    comparison = comparison.sort_values('accuracy', ascending=False)
    
    print(f"\n{'='*60}")
    print("Model Comparison Summary")
    print(f"{'='*60}")
    print(comparison[['model', 'accuracy', 'features', 'f1_H', 'f1_D', 'f1_A']].to_string(index=False))
    
    return comparison


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='random_forest', choices=list(MODELS.keys()))
    parser.add_argument('--leagues', nargs='+', default=['EPL'])
    parser.add_argument('--seasons', nargs='+', default=['2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024'])
    parser.add_argument('--test-seasons', nargs='+', default=['2024'])
    parser.add_argument('--random-split', action='store_true')
    parser.add_argument('--compare', action='store_true')
    parser.add_argument('--no-save', action='store_true')
    
    args = parser.parse_args()
    
    if args.compare:
        compare_models(
            use_temporal_split=not args.random_split,
            test_seasons=args.test_seasons,
            leagues=args.leagues,
            seasons=args.seasons,
        )
    else:
        train_model(
            model_type=args.model,
            use_temporal_split=not args.random_split,
            test_seasons=args.test_seasons,
            leagues=args.leagues,
            seasons=args.seasons,
            save=not args.no_save,
        )