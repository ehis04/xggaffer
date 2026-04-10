from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report

from .config import (
    DEFAULT_LEAGUES,
    DEFAULT_SEASONS,
    MODELS_DIR,
    RANDOM_SEED,
    TARGET,
    TEST_SEASONS,
    XGBOOST_PARAMS,
)
from .prepare_data import build_lineup_dataset, get_feature_columns

logger = logging.getLogger(__name__)


def _compute_persistence_baseline(test_df: pd.DataFrame) -> float:
    mask = test_df['started_last_match'].notna()
    subset = test_df[mask]

    if subset.empty:
        return 0.0

    correct = (subset[TARGET] == subset['started_last_match'].astype(bool)).sum()
    return float(correct / len(subset))


def train_lineup_model(
    df: pd.DataFrame | None = None,
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
    test_seasons: list[str] | None = None,
    save: bool = True,
) -> dict:
    test_seasons = test_seasons or TEST_SEASONS
    test_season_ints = [int(s) for s in test_seasons]

    if df is None:
        df = build_lineup_dataset(
            leagues=leagues or DEFAULT_LEAGUES,
            seasons=seasons or DEFAULT_SEASONS,
            save=False,
        )

    feature_cols = get_feature_columns(df)

    train_df = df[~df['season'].isin(test_season_ints)].copy()
    test_df = df[df['season'].isin(test_season_ints)].copy()

    logger.info(
        'Train: %d rows (%d matches) | Test: %d rows (%d matches)',
        len(train_df), train_df['match_id'].nunique(),
        len(test_df), test_df['match_id'].nunique(),
    )

    X_train = train_df[feature_cols]
    y_train = train_df[TARGET]
    X_test = test_df[feature_cols]
    y_test = test_df[TARGET]

    model = xgb.XGBClassifier(**XGBOOST_PARAMS)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    persistence = _compute_persistence_baseline(test_df)
    gain = accuracy - persistence

    logger.info('Per-player accuracy: %.4f', accuracy)
    logger.info('Persistence baseline: %.4f', persistence)
    logger.info('Accuracy gain: %+.4f', gain)

    report = classification_report(y_test, y_pred, output_dict=True)

    importance = dict(zip(
        feature_cols,
        model.feature_importances_,
    ))
    sorted_importance = dict(sorted(
        importance.items(),
        key=lambda x: x[1],
        reverse=True,
    ))
    logger.info('Top 5 features:')
    for feat, imp in list(sorted_importance.items())[:5]:
        logger.info('  %s: %.4f', feat, imp)

    metrics = {
        'accuracy': accuracy,
        'persistence_baseline': persistence,
        'accuracy_gain': gain,
        'classification_report': report,
        'feature_importance': sorted_importance,
    }

    artifact = {
        'model': model,
        'feature_columns': feature_cols,
        'params': XGBOOST_PARAMS,
        'metrics': metrics,
        'training_info': {
            'train_rows': len(train_df),
            'test_rows': len(test_df),
            'train_matches': int(train_df['match_id'].nunique()),
            'test_matches': int(test_df['match_id'].nunique()),
            'train_seasons': sorted(train_df['season'].unique().tolist()),
            'test_seasons': sorted(test_df['season'].unique().tolist()),
            'leagues': sorted(df['league'].unique().tolist()),
        },
        'version': 'v1',
    }

    if save:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = MODELS_DIR / f'lineup_xgboost_v1_{timestamp}.joblib'
        joblib.dump(artifact, path)
        logger.info('Model saved to %s', path)

    return {
        'model': model,
        'artifact': artifact,
        'test_df': test_df,
        'feature_columns': feature_cols,
        **metrics,
    }


if __name__ == '__main__':
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

    import django
    django.setup()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s  %(levelname)-8s  %(message)s',
        datefmt='%H:%M:%S',
    )

    train_lineup_model(save=True)