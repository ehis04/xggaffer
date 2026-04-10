from __future__ import annotations

from copy import deepcopy
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    log_loss,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, label_binarize

from ml.models.match_outcome.config import (
    DEFAULT_LEAGUES,
    DEFAULT_MODEL_TYPE,
    DEFAULT_SEASONS,
    FRONTEND_CONTRACT_VERSION,
    INTERPRETABLE_MODEL_TYPE,
    MODEL_VERSION,
    MODELS_DIR,
    RANDOM_SEED,
    TEST_SEASONS,
)
from ml.models.match_outcome.prepare_data import (
    get_feature_columns,
    get_temporal_split,
    get_train_test_split,
    prepare_dataset,
)


RF_N_ESTIMATORS = 200
RF_MAX_DEPTH = 12
RF_MIN_SAMPLES_SPLIT = 10
RF_MIN_SAMPLES_LEAF = 5

GB_N_ESTIMATORS = 200
GB_MAX_DEPTH = 6
GB_LEARNING_RATE = 0.1
GB_MIN_SAMPLES_SPLIT = 10

LR_MAX_ITER = 1000
LR_REGULARISATION_C = 0.05
LR_CLASS_WEIGHT = 'balanced'

CALIBRATION_METHOD = 'sigmoid'
CALIBRATION_CV = 5


MODELS = {
    'logistic_regression': Pipeline([
        ('scaler', StandardScaler()),
        ('clf', LogisticRegression(
            C=LR_REGULARISATION_C,
            class_weight=LR_CLASS_WEIGHT,
            max_iter=LR_MAX_ITER,
            random_state=RANDOM_SEED,
        )),
    ]),
    'random_forest': RandomForestClassifier(
        n_estimators=RF_N_ESTIMATORS,
        max_depth=RF_MAX_DEPTH,
        min_samples_split=RF_MIN_SAMPLES_SPLIT,
        min_samples_leaf=RF_MIN_SAMPLES_LEAF,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    ),
    'gradient_boosting': GradientBoostingClassifier(
        n_estimators=GB_N_ESTIMATORS,
        max_depth=GB_MAX_DEPTH,
        learning_rate=GB_LEARNING_RATE,
        min_samples_split=GB_MIN_SAMPLES_SPLIT,
        random_state=RANDOM_SEED,
    ),
}



def compute_multiclass_brier(y_true, y_proba, classes) -> float:
    y_bin = label_binarize(y_true, classes=classes)
    return float(np.mean(np.sum((y_bin - y_proba) ** 2, axis=1)))


def _get_fresh_model(model_type: str):
    if model_type not in MODELS:
        raise ValueError(f"Unknown model type: {model_type}. Choose from: {list(MODELS.keys())}")
    return deepcopy(MODELS[model_type])


def _build_artifact(
    *,
    model,
    model_type: str,
    feature_cols: list[str],
    accuracy: float,
    brier: float,
    logloss: float,
    report: dict,
    conf_matrix,
    calibrate: bool,
    raw_accuracy: float,
    raw_brier: float,
    raw_logloss: float,
    leagues: list[str],
    seasons: list[str],
    test_seasons: list[str] | None,
    train_samples: int,
    test_samples: int,
) -> dict:
    trained_at = datetime.now().isoformat()
    return {
        'model': model,
        'feature_columns': feature_cols,
        'model_type': model_type,
        'metrics': {
            'accuracy': accuracy,
            'brier_score': brier,
            'log_loss': logloss,
            'report': report,
            'confusion_matrix': conf_matrix,
            'calibrated': calibrate,
            'calibration_method': CALIBRATION_METHOD if calibrate else None,
            'raw_accuracy': raw_accuracy,
            'raw_brier_score': raw_brier,
            'raw_log_loss': raw_logloss,
        },
        'training_info': {
            'leagues': leagues,
            'seasons': seasons,
            'test_seasons': test_seasons,
            'train_samples': train_samples,
            'test_samples': test_samples,
            'trained_at': trained_at,
            'frontend_contract_version': FRONTEND_CONTRACT_VERSION,
            'deterministic_explanation_model': model_type == INTERPRETABLE_MODEL_TYPE,
        },
        'version': MODEL_VERSION,
    }



def train_model(
    model_type: str = DEFAULT_MODEL_TYPE,
    use_temporal_split: bool = True,
    test_seasons: list[str] | None = None,
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
    calibrate: bool = True,
    save: bool = True,
) -> dict:
    leagues = leagues or DEFAULT_LEAGUES
    seasons = seasons or DEFAULT_SEASONS
    test_seasons = test_seasons or TEST_SEASONS

    print('Preparing dataset...')
    df = prepare_dataset(leagues=leagues, seasons=seasons, save=False)
    print(f'  Total samples: {len(df)}')

    feature_cols = get_feature_columns(df)
    print(f'  Features: {len(feature_cols)}')

    if use_temporal_split:
        print(f'Using temporal split (test seasons: {test_seasons})')
        X_train, X_test, y_train, y_test = get_temporal_split(df, test_seasons)
    else:
        print('Using random split (80/20)')
        X_train, X_test, y_train, y_test = get_train_test_split(df)

    print(f'  Train samples: {len(X_train)}')
    print(f'  Test samples: {len(X_test)}')

    base_model = _get_fresh_model(model_type)

    print(f'\nTraining {model_type}...')
    base_model.fit(X_train, y_train)

    y_pred_raw = base_model.predict(X_test)
    y_proba_raw = base_model.predict_proba(X_test)
    classes = base_model.classes_

    raw_accuracy = accuracy_score(y_test, y_pred_raw)
    raw_brier = compute_multiclass_brier(y_test, y_proba_raw, classes)
    raw_logloss = log_loss(y_test, y_proba_raw, labels=classes)

    if calibrate:
        print(f'Calibrating with {CALIBRATION_METHOD} (cv={CALIBRATION_CV})...')
        calibrated_model = CalibratedClassifierCV(
            estimator=_get_fresh_model(model_type),
            method=CALIBRATION_METHOD,
            cv=CALIBRATION_CV,
        )
        calibrated_model.fit(X_train, y_train)
        model = calibrated_model
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)
        classes = model.classes_
    else:
        model = base_model
        y_pred = y_pred_raw
        y_proba = y_proba_raw

    accuracy = accuracy_score(y_test, y_pred)
    brier = compute_multiclass_brier(y_test, y_proba, classes)
    logloss = log_loss(y_test, y_proba, labels=classes)

    report = classification_report(y_test, y_pred, output_dict=True)
    conf_matrix = confusion_matrix(y_test, y_pred, labels=['H', 'D', 'A'])

    print(f"\n{'=' * 60}")
    print(f'{model_type} results')
    print(f"{'=' * 60}")
    print(f'Accuracy:     {accuracy:.3f}')
    print(f'Brier score:  {brier:.4f}')
    print(f'Log loss:     {logloss:.4f}')
    print('\nClassification Report:')
    print(classification_report(y_test, y_pred))
    print('Confusion Matrix (H/D/A):')
    print(conf_matrix)

    artifact = _build_artifact(
        model=model,
        model_type=model_type,
        feature_cols=feature_cols,
        accuracy=accuracy,
        brier=brier,
        logloss=logloss,
        report=report,
        conf_matrix=conf_matrix,
        calibrate=calibrate,
        raw_accuracy=raw_accuracy,
        raw_brier=raw_brier,
        raw_logloss=raw_logloss,
        leagues=leagues,
        seasons=seasons,
        test_seasons=test_seasons if use_temporal_split else None,
        train_samples=len(X_train),
        test_samples=len(X_test),
    )

    results = {
        'model_type': model_type,
        'accuracy': accuracy,
        'brier_score': brier,
        'log_loss': logloss,
        'calibrated': calibrate,
        'report': report,
        'confusion_matrix': conf_matrix,
        'features': feature_cols,
        'feature_count': len(feature_cols),
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'leagues': leagues,
        'seasons': seasons,
        'test_seasons': test_seasons if use_temporal_split else None,
        'trained_at': artifact['training_info']['trained_at'],
        'artifact': artifact,
    }

    if save:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_filename = f'match_outcome_{model_type}_{MODEL_VERSION}_{timestamp}.joblib'
        model_path = MODELS_DIR / model_filename
        joblib.dump(artifact, model_path)
        results['model_path'] = str(model_path)
        print(f'\nModel saved to: {model_path}')

    return results


def train_demo_model(
    *,
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
    test_seasons: list[str] | None = None,
    calibrate: bool = True,
    save: bool = True,
) -> dict:
    """Train the locked logistic-regression demo model used by the frontend prototype."""
    return train_model(
        model_type=INTERPRETABLE_MODEL_TYPE,
        use_temporal_split=True,
        test_seasons=test_seasons,
        leagues=leagues,
        seasons=seasons,
        calibrate=calibrate,
        save=save,
    )


def compare_models(
    use_temporal_split: bool = True,
    test_seasons: list[str] | None = None,
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
    calibrate: bool = True,
) -> pd.DataFrame:
    rows: list[dict] = []
    for model_type in MODELS.keys():
        print(f"\n{'=' * 60}")
        print(f'Training: {model_type}')
        print(f"{'=' * 60}")
        result = train_model(
            model_type=model_type,
            use_temporal_split=use_temporal_split,
            test_seasons=test_seasons,
            leagues=leagues,
            seasons=seasons,
            calibrate=calibrate,
            save=False,
        )
        rows.append({
            'model': model_type,
            'accuracy': result['accuracy'],
            'brier_score': result['brier_score'],
            'log_loss': result['log_loss'],
            'feature_count': result['feature_count'],
        })

    return pd.DataFrame(rows).sort_values(['accuracy', 'brier_score'], ascending=[False, True])


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Train xgGaffer match outcome models.')
    parser.add_argument(
        '--model',
        default=DEFAULT_MODEL_TYPE,
        choices=list(MODELS.keys()) + ['demo'],
        help='Model type to train. Use demo for the locked logistic-regression demo artifact.',
    )
    parser.add_argument('--no-calibration', action='store_true')
    parser.add_argument('--random-split', action='store_true')
    parser.add_argument('--compare', action='store_true')
    parser.add_argument('--leagues', nargs='+', default=None)
    parser.add_argument('--seasons', nargs='+', default=None)

    args = parser.parse_args()

    if args.compare:
        df = compare_models(
            use_temporal_split=not args.random_split,
            calibrate=not args.no_calibration,
        )
        print('\nComparison summary:')
        print(df.to_string(index=False))
    elif args.model == 'demo':
        train_demo_model(calibrate=not args.no_calibration, save=True)
    else:
        train_model(
            model_type=args.model,
            use_temporal_split=not args.random_split,
            calibrate=not args.no_calibration,
            leagues=args.leagues,
            seasons=args.seasons,
            save=True,
        )
