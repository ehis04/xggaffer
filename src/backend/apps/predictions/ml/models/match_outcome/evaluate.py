from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, log_loss
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from apps.predictions.ml.models.match_outcome.config import (
    DEFAULT_LEAGUES,
    DEFAULT_MODEL_TYPE,
    DEFAULT_SEASONS,
    INTERPRETABLE_MODEL_TYPE,
    RANDOM_SEED,
    TEST_SEASONS,
    resolve_latest_model_path,
)
from apps.predictions.ml.models.match_outcome.prepare_data import (
    get_feature_columns,
    get_temporal_split,
    prepare_dataset,
)
from apps.predictions.ml.models.match_outcome.train import (
    CALIBRATION_CV,
    CALIBRATION_METHOD,
    MODELS,
    compute_multiclass_brier,
)

WALK_FORWARD_TEST_SEASONS = [
    '2018', '2019', '2020', '2021', '2022', '2023', '2024',
]

ECE_N_BINS = 10

MIN_TRAIN_MATCHES = 500
MIN_TEST_MATCHES = 100

def run_baselines(y_train: pd.Series, y_test: pd.Series) -> pd.DataFrame:
    results = []

    always_home = np.full(len(y_test), 'H')
    results.append({
        'baseline': 'Always Home',
        'accuracy': accuracy_score(y_test, always_home),
    })

    most_common = y_train.value_counts().index[0]
    always_majority = np.full(len(y_test), most_common)
    results.append({
        'baseline': f'Always Majority ({most_common})',
        'accuracy': accuracy_score(y_test, always_majority),
    })

    np.random.seed(RANDOM_SEED)
    train_dist = y_train.value_counts(normalize=True)
    random_weighted = np.random.choice(
        train_dist.index,
        size=len(y_test),
        p=train_dist.values,
    )
    results.append({
        'baseline': 'Random Weighted',
        'accuracy': accuracy_score(y_test, random_weighted),
    })

    return pd.DataFrame(results).sort_values('accuracy', ascending=False)


def run_cross_validation(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    model_types: list[str] | None = None,
    n_folds: int = 5,
) -> pd.DataFrame:
    model_types = model_types or [INTERPRETABLE_MODEL_TYPE, 'random_forest', 'gradient_boosting']
    cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=RANDOM_SEED)
    results = []

    for model_type in model_types:
        print(f'  Cross-validating {model_type}...')
        estimator = clone(MODELS[model_type])
        scores = cross_val_score(estimator, X_train, y_train, cv=cv, scoring='accuracy', n_jobs=-1)
        results.append({
            'model': model_type,
            'mean_accuracy': float(scores.mean()),
            'std_accuracy': float(scores.std()),
            'min': float(scores.min()),
            'max': float(scores.max()),
            'folds': str([round(score, 3) for score in scores]),
        })

    return pd.DataFrame(results).sort_values('mean_accuracy', ascending=False)


def run_xg_only_baseline(df: pd.DataFrame, test_seasons: list[str]) -> dict:
    xg_features = ['home_xgd', 'away_xgd']
    available = [column for column in xg_features if column in df.columns]
    if len(available) < 2:
        return {'accuracy': None, 'note': 'xgd columns not available'}

    train_df = df[~df['season'].astype(str).isin(test_seasons)]
    test_df = df[df['season'].astype(str).isin(test_seasons)]

    model = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', LogisticRegression(max_iter=1000, random_state=RANDOM_SEED)),
    ])
    model.fit(train_df[available], train_df['result'])
    y_pred = model.predict(test_df[available])

    return {
        'accuracy': accuracy_score(test_df['result'], y_pred),
        'report': classification_report(test_df['result'], y_pred, output_dict=True),
    }


def run_model_comparison(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    model_types: list[str] | None = None,
    calibrate: bool = True,
) -> pd.DataFrame:
    model_types = model_types or [INTERPRETABLE_MODEL_TYPE, 'random_forest', 'gradient_boosting']
    rows = []

    for model_type in model_types:
        print(f'  Training {model_type}...')
        base_model = clone(MODELS[model_type])
        base_model.fit(X_train, y_train)

        if calibrate:
            estimator = CalibratedClassifierCV(
                estimator=clone(MODELS[model_type]),
                method=CALIBRATION_METHOD,
                cv=CALIBRATION_CV,
            )
            estimator.fit(X_train, y_train)
            model = estimator
        else:
            model = base_model

        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)
        model_classes = model.classes_
        report = classification_report(y_test, y_pred, output_dict=True)

        rows.append({
            'model': model_type,
            'accuracy': accuracy_score(y_test, y_pred),
            'brier_score': compute_multiclass_brier(y_test, y_proba, model_classes),
            'log_loss': log_loss(y_test, y_proba, labels=model_classes),
            'f1_H': report['H']['f1-score'],
            'f1_D': report['D']['f1-score'],
            'f1_A': report['A']['f1-score'],
            'recall_H': report['H']['recall'],
            'recall_D': report['D']['recall'],
            'recall_A': report['A']['recall'],
        })

    return pd.DataFrame(rows).sort_values(['accuracy', 'brier_score'], ascending=[False, True])


def run_temporal_stability(
    df: pd.DataFrame,
    feature_cols: list[str],
    *,
    model_type: str = DEFAULT_MODEL_TYPE,
    test_year_range: range | None = None,
) -> pd.DataFrame:
    test_year_range = test_year_range or range(2018, 2026)
    rows = []

    for year in test_year_range:
        season = str(year)
        train_df = df[df['season'].astype(str).astype(int) < year]
        test_df = df[df['season'].astype(str) == season]

        if len(train_df) < 500 or len(test_df) < 100:
            continue

        estimator = clone(MODELS[model_type])
        estimator.fit(train_df[feature_cols], train_df['result'])
        y_pred = estimator.predict(test_df[feature_cols])

        rows.append({
            'test_season': season,
            'train_matches': len(train_df),
            'test_matches': len(test_df),
            'model': model_type,
            'accuracy': accuracy_score(test_df['result'], y_pred),
            'home_win_rate': float((test_df['result'] == 'H').mean()),
        })

    return pd.DataFrame(rows)

def compute_ece(y_true, y_proba, classes, n_bins=ECE_N_BINS):
    ece_per_class = []

    for idx, cls in enumerate(classes):
        y_binary = (y_true == cls).astype(int)
        prob_cls = y_proba[:, idx]

        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
        bin_indices = np.digitize(prob_cls, bin_edges[1:-1])

        total = len(y_binary)
        ece = 0.0

        for b in range(n_bins):
            mask = bin_indices == b
            count = mask.sum()
            if count == 0:
                continue
            bin_accuracy = y_binary[mask].mean()
            bin_confidence = prob_cls[mask].mean()
            ece += (count / total) * abs(bin_accuracy - bin_confidence)

        ece_per_class.append(ece)

    return float(np.mean(ece_per_class))


def compute_reliability_data(y_true, y_proba, classes, n_bins=ECE_N_BINS):
    data = {}

    for idx, cls in enumerate(classes):
        y_binary = (y_true == cls).astype(int)
        prob_cls = y_proba[:, idx]

        try:
            prob_true, prob_pred = calibration_curve(
                y_binary, prob_cls, n_bins=n_bins, strategy='uniform',
            )
            data[cls] = {
                'prob_true': prob_true.tolist(),
                'prob_pred': prob_pred.tolist(),
            }
        except ValueError:
            data[cls] = {'prob_true': [], 'prob_pred': []}

    return data


def run_walk_forward_cv(
    df,
    feature_cols,
    model_type='logistic_regression',
    calibrate=True,
    test_seasons=None,
):
    test_seasons = test_seasons or WALK_FORWARD_TEST_SEASONS

    season_int = df['season'].astype(str).astype(int)

    results = []

    for test_season in test_seasons:
        test_year = int(test_season)

        train_mask = season_int < test_year
        test_mask = df['season'].astype(str) == test_season

        train_df = df[train_mask]
        test_df = df[test_mask]

        if len(train_df) < MIN_TRAIN_MATCHES or len(test_df) < MIN_TEST_MATCHES:
            continue

        X_train = train_df[feature_cols]
        y_train = train_df['result']
        X_test = test_df[feature_cols]
        y_test = test_df['result']

        base = clone(MODELS[model_type])

        if calibrate:
            model = CalibratedClassifierCV(
                estimator=base,
                method=CALIBRATION_METHOD,
                cv=CALIBRATION_CV,
            )
        else:
            model = base

        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)
        classes = model.classes_

        report = classification_report(
            y_test, y_pred, output_dict=True, zero_division=0,
        )

        results.append({
            'test_season': test_season,
            'train_matches': len(train_df),
            'test_matches': len(test_df),
            'accuracy': accuracy_score(y_test, y_pred),
            'brier': compute_multiclass_brier(y_test, y_proba, classes),
            'log_loss': log_loss(y_test, y_proba, labels=classes),
            'ece': compute_ece(y_test, y_proba, classes),
            'draw_recall': report.get('D', {}).get('recall', 0.0),
            'home_recall': report.get('H', {}).get('recall', 0.0),
            'away_recall': report.get('A', {}).get('recall', 0.0),
        })

    return pd.DataFrame(results)


def print_walk_forward_summary(results_df):
    metrics = ['accuracy', 'brier', 'log_loss', 'ece']

    print(f"\n{'Walk-Forward Temporal Cross-Validation':=^70}")
    print(f"{'Season':<10} {'Train':>7} {'Test':>6} {'Acc':>7} "
          f"{'Brier':>7} {'LogLoss':>8} {'ECE':>6} {'D_Rec':>6}")
    print('-' * 70)

    for _, row in results_df.iterrows():
        print(
            f"{row['test_season']:<10} "
            f"{int(row['train_matches']):>7} "
            f"{int(row['test_matches']):>6} "
            f"{row['accuracy']:>7.3f} "
            f"{row['brier']:>7.4f} "
            f"{row['log_loss']:>8.4f} "
            f"{row['ece']:>6.3f} "
            f"{row['draw_recall']:>6.2f}"
        )

    print('-' * 70)

    for metric in metrics:
        mean = results_df[metric].mean()
        std = results_df[metric].std()
        print(f"  {metric:<12} mean: {mean:.4f}  std: {std:.4f}")

    print('=' * 70)

def tune_regularisation(
    df,
    feature_cols,
    c_values=None,
    validation_season='2023',
    calibrate=True,
):
    c_values = c_values or [0.001, 0.01, 0.1, 1.0, 10.0]

    season_int = df['season'].astype(str).astype(int)
    val_year = int(validation_season)

    train_df = df[season_int < val_year]
    val_df = df[df['season'].astype(str) == validation_season]

    X_train = train_df[feature_cols]
    y_train = train_df['result']
    X_val = val_df[feature_cols]
    y_val = val_df['result']

    results = []

    for c in c_values:
        base = Pipeline([
            ('scaler', StandardScaler()),
            ('clf', LogisticRegression(
                C=c, max_iter=1000, random_state=RANDOM_SEED,
            )),
        ])

        if calibrate:
            model = CalibratedClassifierCV(
                estimator=base, method=CALIBRATION_METHOD, cv=CALIBRATION_CV,
            )
        else:
            model = base

        model.fit(X_train, y_train)

        y_pred = model.predict(X_val)
        y_proba = model.predict_proba(X_val)
        classes = model.classes_

        results.append({
            'C': c,
            'accuracy': accuracy_score(y_val, y_pred),
            'brier': compute_multiclass_brier(y_val, y_proba, classes),
            'log_loss': log_loss(y_val, y_proba, labels=classes),
            'ece': compute_ece(y_val, y_proba, classes),
        })

    return pd.DataFrame(results)

def compare_calibration_methods(
    df,
    feature_cols,
    test_season='2024',
    model_type='logistic_regression',
):
    season_int = df['season'].astype(str).astype(int)
    test_year = int(test_season)

    train_df = df[season_int < test_year]
    test_df = df[df['season'].astype(str) == test_season]

    X_train = train_df[feature_cols]
    y_train = train_df['result']
    X_test = test_df[feature_cols]
    y_test = test_df['result']

    methods = ['uncalibrated', 'sigmoid', 'isotonic']
    results = []

    for method in methods:
        base = clone(MODELS[model_type])

        if method == 'uncalibrated':
            model = base
        else:
            model = CalibratedClassifierCV(
                estimator=base, method=method, cv=CALIBRATION_CV,
            )

        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)
        classes = model.classes_

        reliability = compute_reliability_data(y_test, y_proba, classes)

        results.append({
            'method': method,
            'accuracy': accuracy_score(y_test, y_pred),
            'brier': compute_multiclass_brier(y_test, y_proba, classes),
            'log_loss': log_loss(y_test, y_proba, labels=classes),
            'ece': compute_ece(y_test, y_proba, classes),
            'reliability_data': reliability,
        })

    return results


def _mcnemar_test(y_true, preds_a, preds_b):
    a_right_b_wrong = sum(
        (pa == yt) and (pb != yt)
        for yt, pa, pb in zip(y_true, preds_a, preds_b)
    )
    a_wrong_b_right = sum(
        (pa != yt) and (pb == yt)
        for yt, pa, pb in zip(y_true, preds_a, preds_b)
    )

    n = a_right_b_wrong + a_wrong_b_right
    if n == 0:
        return 1.0

    from scipy.stats import binomtest
    return binomtest(a_right_b_wrong, n, 0.5).pvalue


def _build_feature_families(feature_cols):
    families = {
        'rolling_attack': [
            c for c in feature_cols
            if any(
                f'rolling_{stat}_' in c
                for stat in ('xg', 'xa', 'shots', 'key_passes')
            )
            and 'xga' not in c
            and 'shots_conceded' not in c
            and 'xpts' not in c
            and 'wins' not in c
            and 'points' not in c
        ],
        'rolling_defence': [
            c for c in feature_cols
            if 'rolling_xga_' in c or 'rolling_shots_conceded_' in c
        ],
        'rolling_general': [
            c for c in feature_cols
            if 'rolling_points_' in c or 'rolling_xpts_' in c
        ],
        'ewm': [c for c in feature_cols if 'ewm_' in c],
        'form': [
            c for c in feature_cols
            if 'rolling_wins_' in c or 'xgd_slope' in c
        ],
        'schedule': [
            c for c in feature_cols
            if 'days_rest' in c or 'matches_last_' in c
        ],
        'diff': [c for c in feature_cols if '_diff_' in c],
        'elo': [
            c for c in feature_cols
            if c in ('home_elo', 'away_elo', 'elo_difference')
        ],
    }
    return families


def _train_and_evaluate(X_train, y_train, X_test, y_test, model_type, calibrate):
    base = clone(MODELS[model_type])

    if calibrate:
        model = CalibratedClassifierCV(
            estimator=base, method=CALIBRATION_METHOD, cv=CALIBRATION_CV,
        )
    else:
        model = base

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)
    classes = model.classes_

    return {
        'accuracy': accuracy_score(y_test, y_pred),
        'brier': compute_multiclass_brier(y_test, y_proba, classes),
        'log_loss': log_loss(y_test, y_proba, labels=classes),
        'ece': compute_ece(y_test, y_proba, classes),
        'predictions': y_pred,
    }


def run_ablation(
    df,
    feature_cols,
    test_season='2024',
    model_type='logistic_regression',
    calibrate=True,
):
    season_int = df['season'].astype(str).astype(int)
    test_year = int(test_season)

    train_df = df[season_int < test_year]
    test_df = df[df['season'].astype(str) == test_season]

    y_train = train_df['result']
    y_test = test_df['result']

    print('  Training full model...')
    full_result = _train_and_evaluate(
        train_df[feature_cols], y_train,
        test_df[feature_cols], y_test,
        model_type, calibrate,
    )
    full_result['variant'] = 'FULL MODEL'
    full_result['removed'] = 'none'
    full_result['features_removed'] = 0
    full_result['mcnemar_p'] = float('nan')

    full_preds = full_result['predictions']

    families = _build_feature_families(feature_cols)
    results = [full_result]

    for family_name, family_cols in families.items():
        cols_present = [c for c in family_cols if c in feature_cols]
        if not cols_present:
            continue

        reduced_cols = [c for c in feature_cols if c not in cols_present]
        if not reduced_cols:
            continue

        print(f'  Training without {family_name} ({len(cols_present)} features)...')
        result = _train_and_evaluate(
            train_df[reduced_cols], y_train,
            test_df[reduced_cols], y_test,
            model_type, calibrate,
        )
        result['variant'] = f'WITHOUT {family_name}'
        result['removed'] = family_name
        result['features_removed'] = len(cols_present)
        result['mcnemar_p'] = _mcnemar_test(
            y_test.values, full_preds, result['predictions'],
        )

        results.append(result)

    return pd.DataFrame(results)
    
def tune_draw_threshold(
    df,
    feature_cols,
    test_season='2024',
    model_type='logistic_regression',
    calibrate=True,
    thresholds=None,
    min_draw_recall=0.15,
) -> pd.DataFrame:
    """Sweep draw probability thresholds and find the best accuracy with draw recall >= min_draw_recall.

    For each threshold t: predict 'D' when P(D) >= t, otherwise take argmax of H/A.
    """
    thresholds = thresholds or [round(t, 2) for t in np.arange(0.10, 0.45, 0.01)]

    season_int = df['season'].astype(str).astype(int)
    test_year = int(test_season)

    train_df = df[season_int < test_year]
    test_df = df[df['season'].astype(str) == test_season]

    X_train = train_df[feature_cols]
    y_train = train_df['result']
    X_test = test_df[feature_cols]
    y_test = test_df['result']

    base = clone(MODELS[model_type])

    if calibrate:
        model = CalibratedClassifierCV(
            estimator=base, method=CALIBRATION_METHOD, cv=CALIBRATION_CV,
        )
    else:
        model = base

    model.fit(X_train, y_train)
    y_proba = model.predict_proba(X_test)
    classes = list(model.classes_)

    h_idx = classes.index('H')
    d_idx = classes.index('D')
    a_idx = classes.index('A')

    y_true = y_test.values
    rows = []

    for thresh in thresholds:
        preds = []
        for probs in y_proba:
            if probs[d_idx] >= thresh:
                preds.append('D')
            else:
                ha_probs = [probs[h_idx], probs[a_idx]]
                preds.append('H' if ha_probs[0] >= ha_probs[1] else 'A')

        preds = np.array(preds)
        report = classification_report(y_true, preds, labels=['H', 'D', 'A'], output_dict=True, zero_division=0)

        rows.append({
            'threshold': thresh,
            'accuracy': accuracy_score(y_true, preds),
            'draw_recall': report.get('D', {}).get('recall', 0.0),
            'draw_precision': report.get('D', {}).get('precision', 0.0),
            'draw_f1': report.get('D', {}).get('f1-score', 0.0),
            'home_recall': report.get('H', {}).get('recall', 0.0),
            'away_recall': report.get('A', {}).get('recall', 0.0),
            'n_predicted_draw': int((preds == 'D').sum()),
        })

    return pd.DataFrame(rows)


def evaluate_saved_model_artifact(model_path=None) -> dict:
    model_path = model_path or resolve_latest_model_path(INTERPRETABLE_MODEL_TYPE)
    artifact = joblib.load(model_path)

    return {
        'model_path': str(model_path),
        'model_type': artifact['model_type'],
        'version': artifact['version'],
        'accuracy': artifact['metrics'].get('accuracy'),
        'brier_score': artifact['metrics'].get('brier_score'),
        'log_loss': artifact['metrics'].get('log_loss'),
        'feature_count': len(artifact['feature_columns']),
        'training_info': artifact.get('training_info', {}),
    }


def run_full_evaluation(
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
    test_seasons: list[str] | None = None,
    demo_model_type: str = INTERPRETABLE_MODEL_TYPE,
):
    leagues = leagues or DEFAULT_LEAGUES
    seasons = seasons or DEFAULT_SEASONS
    test_seasons = test_seasons or TEST_SEASONS

    print('=' * 60)
    print('xgGaffer Model Evaluation Report')
    print('=' * 60)
    print(f'Frontend demo model: {demo_model_type}')

    print('\nPreparing dataset...')
    df = prepare_dataset(leagues=leagues, seasons=seasons, save=False)
    feature_cols = get_feature_columns(df)
    X_train, X_test, y_train, y_test = get_temporal_split(df, test_seasons)

    print(f'Dataset: {len(df)} matches, {len(feature_cols)} features')
    print(f'Train: {len(X_train)} | Test: {len(X_test)} (seasons {test_seasons})')
    print(f'Leagues: {leagues}')

    print('\nTarget distribution (train):')
    for label, pct in y_train.value_counts(normalize=True).round(3).items():
        print(f'  {label}: {pct:.1%}')

    print(f"\n{'=' * 60}")
    print('1. BASELINE COMPARISONS')
    print(f"{'=' * 60}")
    baselines = run_baselines(y_train, y_test)
    print(baselines.to_string(index=False))

    xg_result = run_xg_only_baseline(df, test_seasons)
    if xg_result['accuracy']:
        print(f"\nxG-only model (2 features): {xg_result['accuracy']:.3f}")

    print(f"\n{'=' * 60}")
    print('2. CROSS-VALIDATION (5-fold on training set)')
    print(f"{'=' * 60}")
    cv_results = run_cross_validation(X_train, y_train)
    print(cv_results[['model', 'mean_accuracy', 'std_accuracy', 'min', 'max']].to_string(index=False))

    print(f"\n{'=' * 60}")
    print('3. MODEL COMPARISON (calibrated, on test set)')
    print(f"{'=' * 60}")
    comparison = run_model_comparison(X_train, X_test, y_train, y_test, calibrate=True)
    print(comparison.to_string(index=False))

    print(f"\n{'=' * 60}")
    print('4. PER-CLASS ANALYSIS (frontend demo model)')
    print(f"{'=' * 60}")
    demo_model = CalibratedClassifierCV(
        estimator=clone(MODELS[demo_model_type]),
        method=CALIBRATION_METHOD,
        cv=CALIBRATION_CV,
    )
    demo_model.fit(X_train, y_train)
    y_pred = demo_model.predict(X_test)
    y_proba = demo_model.predict_proba(X_test)

    print(f'\nDemo model: {demo_model_type}')
    print(classification_report(y_test, y_pred))

    prob_df = pd.DataFrame(y_proba, columns=demo_model.classes_)
    prob_df['actual'] = y_test.values
    prob_df['predicted'] = y_pred

    for cls in ['H', 'D', 'A']:
        mask = prob_df['actual'] == cls
        avg_prob = prob_df.loc[mask, cls].mean()
        max_prob = prob_df.loc[mask, cls].max()
        min_prob = prob_df.loc[mask, cls].min()
        print(
            f'  When actual={cls}: avg predicted prob for {cls} = '
            f'{avg_prob:.3f} (range {min_prob:.3f}-{max_prob:.3f})'
        )

    print(f"\n{'=' * 60}")
    print(f'5. TEMPORAL STABILITY ({demo_model_type} per season)')
    print(f"{'=' * 60}")
    stability = run_temporal_stability(df, feature_cols, model_type=demo_model_type)
    print(stability.to_string(index=False))
    print(f"\nMean accuracy across seasons: {stability['accuracy'].mean():.3f} ± {stability['accuracy'].std():.3f}")

    print(f"\n{'=' * 60}")
    print('6. SAVED DEMO ARTIFACT')
    print(f"{'=' * 60}")
    try:
        artifact_summary = evaluate_saved_model_artifact(resolve_latest_model_path(demo_model_type))
        for key, value in artifact_summary.items():
            print(f'{key}: {value}')
    except FileNotFoundError as exc:
        print(exc)

    print(f"\n{'=' * 60}")
    print('SUMMARY')
    print(f"{'=' * 60}")
    best_row = comparison.iloc[0]
    home_baseline = baselines.loc[baselines['baseline'] == 'Always Home', 'accuracy'].iloc[0]
    xg_accuracy = xg_result['accuracy'] or 0.0

    print(f"Best model overall: {best_row['model']}")
    print(f"Best accuracy: {best_row['accuracy']:.3f}")
    print(f"Demo model ({demo_model_type}) accuracy: {comparison.loc[comparison['model'] == demo_model_type, 'accuracy'].iloc[0]:.3f}")
    print(f'Home-always baseline: {home_baseline:.3f}')
    if xg_accuracy:
        print(f'xG-only baseline: {xg_accuracy:.3f}')


if __name__ == '__main__':
    import sys

    df = prepare_dataset(save=False)
    feature_cols = get_feature_columns(df)
    print(f'Samples: {len(df)}, Features: {len(feature_cols)}')

    if '--full' in sys.argv:
        run_full_evaluation()
    elif '--tune-c' in sys.argv:
        print('\nTuning regularisation (C)...')
        reg_results = tune_regularisation(df, feature_cols)
        print(f"\n{'Regularisation Tuning (validation=2023)':=^60}")
        print(reg_results.to_string(index=False))
        best = reg_results.loc[reg_results['log_loss'].idxmin()]
        print(f"\nBest C by log loss: {best['C']}")
        print(f"  Accuracy: {best['accuracy']:.4f}")
        print(f"  Brier:    {best['brier']:.4f}")
        print(f"  Log loss: {best['log_loss']:.4f}")
        print(f"  ECE:      {best['ece']:.4f}")
    elif '--calibration' in sys.argv:
        print('\nComparing calibration methods...')
        cal_results = compare_calibration_methods(df, feature_cols)
        print(f"\n{'Calibration Method Comparison (test=2024)':=^60}")
        print(f"{'Method':<15} {'Acc':>7} {'Brier':>7} {'LogLoss':>8} {'ECE':>6}")
        print('-' * 50)
        for r in cal_results:
            print(
                f"{r['method']:<15} "
                f"{r['accuracy']:>7.4f} "
                f"{r['brier']:>7.4f} "
                f"{r['log_loss']:>8.4f} "
                f"{r['ece']:>6.4f}"
            )
        best = min(cal_results, key=lambda r: r['log_loss'])
        print(f"\nBest method by log loss: {best['method']}")
    elif '--ablation' in sys.argv:
        print('\nRunning ablation analysis...')
        abl_results = run_ablation(df, feature_cols)
        display_cols = [
            'variant', 'features_removed', 'accuracy',
            'brier', 'log_loss', 'ece', 'mcnemar_p',
        ]
        print(f"\n{'Ablation Analysis (test=2024)':=^70}")
        print(abl_results[display_cols].to_string(index=False))

        full_acc = abl_results.loc[
            abl_results['variant'] == 'FULL MODEL', 'accuracy'
        ].iloc[0]
        print(f'\nFull model accuracy: {full_acc:.4f}')
        print('\nAccuracy delta from removing each family:')
        for _, row in abl_results.iterrows():
            if row['variant'] == 'FULL MODEL':
                continue
            delta = row['accuracy'] - full_acc
            sig = '*' if row['mcnemar_p'] < 0.05 else ''
            print(
                f"  {row['variant']:<25} "
                f"{delta:+.4f}  p={row['mcnemar_p']:.4f} {sig}"
            )
    elif '--tune-draw' in sys.argv:
        print('\nSweeping draw threshold (target: draw recall >= 15%)...')
        sweep = tune_draw_threshold(df, feature_cols)
        feasible = sweep[sweep['draw_recall'] >= 0.15]

        print(f"\n{'Draw Threshold Sweep (test=2024)':=^75}")
        print(f"{'Thresh':>7} {'Accuracy':>9} {'D_Recall':>9} {'D_Prec':>8} {'D_F1':>7} {'H_Rec':>7} {'A_Rec':>7} {'N_D':>5}")
        print('-' * 75)
        for _, row in sweep.iterrows():
            flag = ' *' if row['draw_recall'] >= 0.15 else '  '
            print(
                f"{row['threshold']:>7.2f}"
                f"{row['accuracy']:>9.4f}"
                f"{row['draw_recall']:>9.4f}"
                f"{row['draw_precision']:>8.4f}"
                f"{row['draw_f1']:>7.4f}"
                f"{row['home_recall']:>7.4f}"
                f"{row['away_recall']:>7.4f}"
                f"{int(row['n_predicted_draw']):>5}"
                f"{flag}"
            )

        print('-' * 75)
        print('* = draw recall >= 15%')

        if not feasible.empty:
            best = feasible.loc[feasible['accuracy'].idxmax()]
            print(f"\nBest threshold with draw recall >= 15%:")
            print(f"  threshold:      {best['threshold']:.2f}")
            print(f"  accuracy:       {best['accuracy']:.4f}")
            print(f"  draw_recall:    {best['draw_recall']:.4f}")
            print(f"  draw_precision: {best['draw_precision']:.4f}")
            print(f"  draw_f1:        {best['draw_f1']:.4f}")
            print(f"  n_predicted_D:  {int(best['n_predicted_draw'])}")
        else:
            print('\nNo threshold achieved draw recall >= 15%.')
    else:
        print('\nRunning walk-forward CV...')
        results = run_walk_forward_cv(df, feature_cols)
        print_walk_forward_summary(results)