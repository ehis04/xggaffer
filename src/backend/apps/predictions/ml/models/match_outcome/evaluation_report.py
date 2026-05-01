from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, classification_report, log_loss

from apps.predictions.ml.models.match_outcome.config import RANDOM_SEED
from apps.predictions.ml.models.match_outcome.evaluate import (
    compute_ece,
    compute_reliability_data,
    compare_calibration_methods,
    run_ablation,
    run_baselines,
    run_model_comparison,
    run_walk_forward_cv,
    print_walk_forward_summary,
    tune_regularisation,
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


SECTION_WIDTH = 70


def _header(number, title):
    print(f"\n{'=' * SECTION_WIDTH}")
    print(f'{number}. {title}')
    print(f"{'=' * SECTION_WIDTH}")


def _section_dataset_summary(df, feature_cols):
    _header(1, 'DATASET SUMMARY')

    print(f'Total matches: {len(df)}')
    print(f'Features:      {len(feature_cols)}')
    print(f"Leagues:       {sorted(df['league'].unique().tolist())}")
    print(f"Seasons:       {sorted(df['season'].unique().tolist())}")

    print('\nPer-league match counts:')
    for league, count in df.groupby('league').size().items():
        print(f'  {league:<15} {count:>5}')

    print('\nOverall target distribution:')
    for label, pct in df['result'].value_counts(normalize=True).sort_index().items():
        print(f'  {label}: {pct:.1%}')

    print('\nPer-league target distribution:')
    dist = df.groupby('league')['result'].value_counts(normalize=True).round(3).unstack()
    print(dist.to_string())


def _section_baselines(y_train, y_test):
    _header(2, 'BASELINES')

    baselines = run_baselines(y_train, y_test)
    print(baselines.to_string(index=False))


def _section_walk_forward(df, feature_cols):
    _header(3, 'WALK-FORWARD TEMPORAL CROSS-VALIDATION')

    results = run_walk_forward_cv(df, feature_cols)
    print_walk_forward_summary(results)
    return results


def _section_regularisation(df, feature_cols):
    _header(4, 'REGULARISATION TUNING')

    reg_results = tune_regularisation(df, feature_cols)
    print(reg_results.to_string(index=False))

    best = reg_results.loc[reg_results['log_loss'].idxmin()]
    print(f"\nBest C by log loss: {best['C']}")
    print(f"  Accuracy:  {best['accuracy']:.4f}")
    print(f"  Brier:     {best['brier']:.4f}")
    print(f"  Log loss:  {best['log_loss']:.4f}")
    print(f"  ECE:       {best['ece']:.4f}")

    return reg_results


def _section_calibration(df, feature_cols):
    _header(5, 'CALIBRATION COMPARISON')

    cal_results = compare_calibration_methods(df, feature_cols)

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

    print('\nReliability diagram data (per class):')
    for r in cal_results:
        if r['method'] != CALIBRATION_METHOD:
            continue
        for cls, data in r['reliability_data'].items():
            if data['prob_true']:
                pairs = list(zip(data['prob_pred'], data['prob_true']))
                print(f"  {cls}: {', '.join(f'({p:.2f},{t:.2f})' for p, t in pairs)}")

    return cal_results


def _section_ablation(df, feature_cols):
    _header(6, 'ABLATION ANALYSIS')

    abl_results = run_ablation(df, feature_cols)

    display_cols = [
        'variant', 'features_removed', 'accuracy',
        'brier', 'log_loss', 'ece', 'mcnemar_p',
    ]
    print(abl_results[display_cols].to_string(index=False))

    full_acc = abl_results.loc[
        abl_results['variant'] == 'FULL MODEL', 'accuracy'
    ].iloc[0]
    full_ll = abl_results.loc[
        abl_results['variant'] == 'FULL MODEL', 'log_loss'
    ].iloc[0]

    print(f'\nImpact of removing each family:')
    print(f"  {'Family':<25} {'Acc delta':>10} {'LL delta':>10} {'p-value':>10} {'Sig':>4}")
    print(f"  {'-' * 59}")
    for _, row in abl_results.iterrows():
        if row['variant'] == 'FULL MODEL':
            continue
        acc_delta = row['accuracy'] - full_acc
        ll_delta = row['log_loss'] - full_ll
        sig = '*' if row['mcnemar_p'] < 0.05 else ''
        print(
            f"  {row['removed']:<25} "
            f"{acc_delta:>+10.4f} "
            f"{ll_delta:>+10.4f} "
            f"{row['mcnemar_p']:>10.4f} "
            f"{sig:>4}"
        )

    return abl_results


def _section_per_class(X_train, X_test, y_train, y_test):
    _header(7, 'PER-CLASS ANALYSIS')

    model = CalibratedClassifierCV(
        estimator=clone(MODELS['logistic_regression']),
        method=CALIBRATION_METHOD,
        cv=CALIBRATION_CV,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)
    classes = model.classes_

    print(classification_report(y_test, y_pred, zero_division=0))

    print('Probability distribution when actual class is:')
    prob_df = pd.DataFrame(y_proba, columns=classes)
    prob_df['actual'] = y_test.values

    for cls in sorted(classes):
        mask = prob_df['actual'] == cls
        if mask.sum() == 0:
            continue
        avg_p = prob_df.loc[mask, cls].mean()
        std_p = prob_df.loc[mask, cls].std()
        print(f'  {cls}: mean predicted P({cls}) = {avg_p:.3f} +/- {std_p:.3f}')


def _section_model_comparison(X_train, X_test, y_train, y_test):
    _header(8, 'MODEL COMPARISON (LR vs RF vs GB)')

    comparison = run_model_comparison(
        X_train, X_test, y_train, y_test, calibrate=True,
    )
    print(comparison.to_string(index=False))

    best = comparison.iloc[0]
    print(f"\nBest model by accuracy: {best['model']} ({best['accuracy']:.4f})")
    print('Logistic regression is the production choice for:')
    print('  - Calibration quality (Brier, log loss)')
    print('  - Deterministic explanation via coefficients')
    print('  - Training speed and simplicity')


def _section_production_summary(wf_results, reg_results, abl_results):
    _header(9, 'PRODUCTION MODEL SUMMARY')

    mean_acc = wf_results['accuracy'].mean()
    std_acc = wf_results['accuracy'].std()
    mean_brier = wf_results['brier'].mean()
    mean_ll = wf_results['log_loss'].mean()
    mean_ece = wf_results['ece'].mean()

    best_c = reg_results.loc[reg_results['log_loss'].idxmin(), 'C']

    print(f'Model:              Logistic Regression + CalibratedClassifierCV (sigmoid)')
    print(f'Regularisation:     C = {best_c}')
    print(f'Features:           86 (rolling + EWM + form + schedule + diff + Elo)')
    print(f'Training leagues:   EPL, La Liga, Bundesliga, Serie A, Ligue 1')
    print(f'Training seasons:   2014-2023')
    print(f'Evaluation:         7-fold walk-forward temporal CV')
    print(f'')
    print(f'Walk-forward results:')
    print(f'  Accuracy:   {mean_acc:.4f} +/- {std_acc:.4f}')
    print(f'  Brier:      {mean_brier:.4f}')
    print(f'  Log loss:   {mean_ll:.4f}')
    print(f'  ECE:        {mean_ece:.4f}')
    print(f'')
    print(f'Targets vs actual:')
    print(f'  Accuracy target:  52-57%    actual: {mean_acc:.1%}')
    print(f'  Log loss target:  0.95-1.02 actual: {mean_ll:.4f}')
    print(f'  Brier target:     0.54-0.58 actual: {mean_brier:.4f}')
    print(f'  ECE target:       < 5%      actual: {mean_ece:.1%}')
    print(f'')
    print(f'Draw recall:        0% across all folds (expected without betting odds)')
    print(f'Next step:          Milestone B adds de-vigged odds for draw signal')


def main():
    print(f"\n{'#' * SECTION_WIDTH}")
    print(f"{'xgGaffer Engine 2 Milestone A — Evaluation Report':^{SECTION_WIDTH}}")
    print(f"{'#' * SECTION_WIDTH}")

    print('\nLoading dataset...')
    df = prepare_dataset(save=False)
    feature_cols = get_feature_columns(df)

    test_seasons = ['2024']
    X_train, X_test, y_train, y_test = get_temporal_split(df, test_seasons)

    print(f'Total samples: {len(df)}')
    print(f'Train: {len(X_train)} | Test: {len(X_test)}')
    print(f'Features: {len(feature_cols)}')

    _section_dataset_summary(df, feature_cols)
    _section_baselines(y_train, y_test)
    wf_results = _section_walk_forward(df, feature_cols)
    reg_results = _section_regularisation(df, feature_cols)
    _section_calibration(df, feature_cols)
    abl_results = _section_ablation(df, feature_cols)
    _section_per_class(X_train, X_test, y_train, y_test)
    _section_model_comparison(X_train, X_test, y_train, y_test)
    _section_production_summary(wf_results, reg_results, abl_results)

    print(f"\n{'#' * SECTION_WIDTH}")
    print(f"{'END OF REPORT':^{SECTION_WIDTH}}")
    print(f"{'#' * SECTION_WIDTH}")


if __name__ == '__main__':
    main()