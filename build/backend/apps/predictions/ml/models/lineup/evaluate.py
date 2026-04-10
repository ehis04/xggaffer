from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score

from .config import (
    DATA_DIR,
    DEFAULT_LEAGUES,
    DEFAULT_SEASONS,
    FORMATION_SLOTS,
    POSITION_CATEGORY_MAP,
    TARGET,
    TEST_SEASONS,
)
from .predict import resolve_latest_lineup_model
from .prepare_data import build_lineup_dataset

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 0.50
ROTATION_THRESHOLD = 0.60
DEFAULT_FORMATION = '4-3-3'


def _compute_persistence_baseline(test_df: pd.DataFrame) -> float:
    mask = test_df['started_last_match'].notna()
    subset = test_df[mask]

    if subset.empty:
        return 0.0

    correct = (subset[TARGET] == subset['started_last_match'].astype(bool)).sum()
    return float(correct / len(subset))


def _compute_dropped_player_metrics(
    test_df: pd.DataFrame,
    y_pred: np.ndarray,
) -> dict:
    test_df = test_df.copy()
    test_df['predicted'] = y_pred

    mask = test_df['started_last_match'].notna()
    valid = test_df[mask]

    dropped_actual = valid[
        (valid['started_last_match'].astype(bool) == True) &
        (valid[TARGET] == False)
    ]
    dropped_predicted = valid[valid['predicted'] == False]

    if dropped_actual.empty:
        return {
            'recall': 0.0, 'precision': 0.0,
            'dropped_count': 0, 'correctly_identified': 0,
            'total_predicted_drops': int(len(dropped_predicted)),
        }

    correctly_identified = (dropped_actual['predicted'] == False).sum()
    recall = float(correctly_identified / len(dropped_actual))

    precision = (
        float(correctly_identified / len(dropped_predicted))
        if len(dropped_predicted) > 0 else 0.0
    )

    return {
        'recall': recall,
        'precision': precision,
        'dropped_count': int(len(dropped_actual)),
        'correctly_identified': int(correctly_identified),
        'total_predicted_drops': int(len(dropped_predicted)),
    }


def _predict_xi_for_team_match(
    team_match_df: pd.DataFrame,
    probs: np.ndarray,
    formation: str = DEFAULT_FORMATION,
) -> set:
    df = team_match_df.copy()
    df['p_start'] = probs
    df['category'] = df['position'].map(POSITION_CATEGORY_MAP).fillna('MID')

    slots = FORMATION_SLOTS.get(formation, FORMATION_SLOTS[DEFAULT_FORMATION])

    selected_ids: set = set()

    for category in ['GK', 'DEF', 'MID', 'FWD']:
        n_needed = slots.get(category, 0)
        eligible = df[
            (df['category'] == category) &
            (~df['player_id'].isin(selected_ids))
        ].sort_values('p_start', ascending=False)

        for _, row in eligible.head(n_needed).iterrows():
            selected_ids.add(row['player_id'])

    if len(selected_ids) < 11:
        remaining = df[~df['player_id'].isin(selected_ids)].sort_values(
            'p_start', ascending=False,
        )
        for _, row in remaining.head(11 - len(selected_ids)).iterrows():
            selected_ids.add(row['player_id'])

    return selected_ids


def _compute_xi_metrics(
    test_df: pd.DataFrame,
    y_proba: np.ndarray,
) -> dict:
    test_df = test_df.copy()
    test_df['p_start'] = y_proba

    exact_correct = 0
    total_team_matches = 0
    jaccard_scores = []

    for (match_id, team_id), group in test_df.groupby(['match_id', 'team_id']):
        actual_xi = set(group[group[TARGET]]['player_id'])
        predicted_xi = _predict_xi_for_team_match(
            group, group['p_start'].values,
            formation=DEFAULT_FORMATION,
        )

        total_team_matches += 1
        if actual_xi == predicted_xi:
            exact_correct += 1

        intersection = len(actual_xi & predicted_xi)
        union = len(actual_xi | predicted_xi)
        jaccard = intersection / union if union > 0 else 0
        jaccard_scores.append(jaccard)

    return {
        'exact_xi_accuracy': float(exact_correct / total_team_matches) if total_team_matches > 0 else 0.0,
        'mean_jaccard': float(np.mean(jaccard_scores)) if jaccard_scores else 0.0,
        'total_team_matches': total_team_matches,
    }


def _compute_position_accuracy(
    test_df: pd.DataFrame,
    y_pred: np.ndarray,
) -> dict:
    test_df = test_df.copy()
    test_df['predicted'] = y_pred
    test_df['category'] = test_df['position'].map(POSITION_CATEGORY_MAP).fillna('MID')

    result = {}
    for category in ['GK', 'DEF', 'MID', 'FWD', 'SUB']:
        subset = test_df[test_df['category'] == category]
        if subset.empty:
            continue
        acc = (subset[TARGET] == subset['predicted']).mean()
        result[category] = {
            'accuracy': float(acc),
            'count': int(len(subset)),
        }
    return result


def _metrics_at_threshold(
    test_df: pd.DataFrame,
    y_proba: np.ndarray,
    threshold: float,
) -> dict:
    y_pred = (y_proba >= threshold).astype(bool)
    accuracy = accuracy_score(test_df[TARGET].values, y_pred)
    dropped = _compute_dropped_player_metrics(test_df, y_pred)
    position_acc = _compute_position_accuracy(test_df, y_pred)

    return {
        'threshold': threshold,
        'accuracy': float(accuracy),
        'dropped_recall': dropped['recall'],
        'dropped_precision': dropped['precision'],
        'dropped_count': dropped['dropped_count'],
        'dropped_correctly_identified': dropped['correctly_identified'],
        'total_predicted_drops': dropped['total_predicted_drops'],
        'position_accuracy': position_acc,
    }


def evaluate_lineup_model(
    artifact_path: Path | str | None = None,
    df: pd.DataFrame | None = None,
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
    test_seasons: list[str] | None = None,
) -> dict:
    path = Path(artifact_path) if artifact_path else resolve_latest_lineup_model()
    artifact = joblib.load(path)
    model = artifact['model']
    feature_cols = artifact['feature_columns']

    test_seasons = test_seasons or TEST_SEASONS
    test_season_ints = [int(s) for s in test_seasons]

    if df is None:
        df = build_lineup_dataset(
            leagues=leagues or DEFAULT_LEAGUES,
            seasons=seasons or DEFAULT_SEASONS,
            save=False,
        )

    test_df = df[df['season'].isin(test_season_ints)].copy()
    logger.info('Evaluating on %d test rows', len(test_df))

    X_test = test_df[feature_cols]
    y_proba = model.predict_proba(X_test)[:, 1]

    persistence = _compute_persistence_baseline(test_df)
    xi_metrics = _compute_xi_metrics(test_df, y_proba)

    default_metrics = _metrics_at_threshold(test_df, y_proba, DEFAULT_THRESHOLD)
    rotation_metrics = _metrics_at_threshold(test_df, y_proba, ROTATION_THRESHOLD)

    return {
        'persistence_baseline': persistence,
        'exact_xi_accuracy': xi_metrics['exact_xi_accuracy'],
        'mean_jaccard': xi_metrics['mean_jaccard'],
        'total_team_matches': xi_metrics['total_team_matches'],
        'default_threshold': default_metrics,
        'rotation_threshold': rotation_metrics,
        'accuracy_gain': default_metrics['accuracy'] - persistence,
    }


def print_evaluation(metrics: dict) -> None:
    default = metrics['default_threshold']
    rotation = metrics['rotation_threshold']

    print()
    print('=' * 70)
    print('ENGINE 7 — LINEUP PREDICTION EVALUATION')
    print('=' * 70)
    print()
    print(f'Test team-matches: {metrics["total_team_matches"]}')
    print(f'Persistence baseline (accuracy): {metrics["persistence_baseline"]:.4f}')
    print()
    print('-' * 70)
    print(f'OPERATING POINT 1 — th={default["threshold"]:.2f} (accuracy-optimised)')
    print('-' * 70)
    print(f'  Per-player accuracy:        {default["accuracy"]:.4f}')
    print(f'  Accuracy gain over baseline: {default["accuracy"] - metrics["persistence_baseline"]:+.4f}')
    print(f'  Dropped-player recall:      {default["dropped_recall"]:.4f}')
    print(f'  Dropped-player precision:   {default["dropped_precision"]:.4f}')
    print(f'  Drops identified:           {default["dropped_correctly_identified"]}/{default["dropped_count"]}')
    print()
    print('-' * 70)
    print(f'OPERATING POINT 2 — th={rotation["threshold"]:.2f} (rotation-detection-optimised)')
    print('-' * 70)
    print(f'  Per-player accuracy:        {rotation["accuracy"]:.4f}')
    print(f'  Accuracy gain over baseline: {rotation["accuracy"] - metrics["persistence_baseline"]:+.4f}')
    print(f'  Dropped-player recall:      {rotation["dropped_recall"]:.4f}')
    print(f'  Dropped-player precision:   {rotation["dropped_precision"]:.4f}')
    print(f'  Drops identified:           {rotation["dropped_correctly_identified"]}/{rotation["dropped_count"]}')
    print()
    print('-' * 70)
    print('FULL-XI METRICS (threshold-independent, fixed 4-3-3 formation)')
    print('-' * 70)
    print(f'  Exact XI accuracy:          {metrics["exact_xi_accuracy"]:.4f}')
    print(f'  Mean Jaccard:               {metrics["mean_jaccard"]:.4f}')
    print()
    print('-' * 70)
    print(f'PER-POSITION ACCURACY (th={default["threshold"]:.2f})')
    print('-' * 70)
    for category, stats in default['position_accuracy'].items():
        print(f'  {category:5} {stats["accuracy"]:.4f}  ({stats["count"]} rows)')
    print('=' * 70)


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

    metrics = evaluate_lineup_model()
    print_evaluation(metrics)