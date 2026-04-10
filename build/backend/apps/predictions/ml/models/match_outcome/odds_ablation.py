from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    log_loss,
    precision_recall_fscore_support,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, label_binarize

from ml.models.match_outcome.config import (
    MODELS_DIR,
    RANDOM_SEED,
)
from ml.models.match_outcome.prepare_data import (
    BASE_FEATURE_COLUMNS,
    FEATURE_COLUMNS_WITH_ODDS,
    ODDS_FEATURES,
    prepare_dataset,
)


LR_MAX_ITER = 1000
LR_C = 0.001
CALIBRATION_METHOD = "sigmoid"
CALIBRATION_CV = 5
WALK_FORWARD_START = 2018
WALK_FORWARD_END = 2025
ALL_LEAGUES = ["EPL", "La_Liga", "Bundesliga", "Serie_A", "Ligue_1"]
ALL_SEASONS = [str(y) for y in range(2014, 2026)]
CLASS_ORDER = ["H", "D", "A"]


def _make_pipeline() -> Pipeline:
    return Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(
            C=LR_C,
            max_iter=LR_MAX_ITER,
            random_state=RANDOM_SEED,
            multi_class="multinomial",
            solver="lbfgs",
        )),
    ])


def _calibrated_pipeline() -> CalibratedClassifierCV:
    return CalibratedClassifierCV(
        estimator=_make_pipeline(),
        method=CALIBRATION_METHOD,
        cv=CALIBRATION_CV,
    )


def compute_multiclass_brier(y_true, y_proba, classes) -> float:
    y_bin = label_binarize(y_true, classes=classes)
    return float(np.mean(np.sum((y_bin - y_proba) ** 2, axis=1)))


def compute_ece(y_true, y_proba, classes, n_bins: int = 10) -> float:
    y_bin = label_binarize(y_true, classes=classes)
    total_samples = len(y_true)
    ece = 0.0
    for cls_idx in range(len(classes)):
        probs = y_proba[:, cls_idx]
        actuals = y_bin[:, cls_idx]
        bin_edges = np.linspace(0, 1, n_bins + 1)
        for i in range(n_bins):
            mask = (probs >= bin_edges[i]) & (probs < bin_edges[i + 1])
            if mask.sum() == 0:
                continue
            bin_conf = probs[mask].mean()
            bin_acc = actuals[mask].mean()
            ece += mask.sum() / total_samples * abs(bin_conf - bin_acc)
    return ece / len(classes)


def mcnemar_test(y_true, y_pred_a, y_pred_b) -> dict:
    correct_a = (y_pred_a == y_true)
    correct_b = (y_pred_b == y_true)

    b_only = int((~correct_a & correct_b).sum())
    a_only = int((correct_a & ~correct_b).sum())

    n = b_only + a_only
    if n == 0:
        return {"b_only": b_only, "a_only": a_only, "n": n, "p_value": 1.0, "significant": False}

    result = binomtest(b_only, n, 0.5, alternative="two-sided")

    return {
        "b_only": b_only,
        "a_only": a_only,
        "n": n,
        "p_value": float(result.pvalue),
        "significant": result.pvalue < 0.05,
    }


def run_walk_forward_cv(
    df: pd.DataFrame,
    feature_cols: list[str],
    start_year: int = WALK_FORWARD_START,
    end_year: int = WALK_FORWARD_END,
) -> pd.DataFrame:
    rows = []

    for test_year in range(start_year, end_year):
        test_season = str(test_year)
        train_mask = df["season"].astype(str).astype(int) < test_year
        test_mask = df["season"].astype(str) == test_season

        train_df = df[train_mask]
        test_df = df[test_mask]

        if len(train_df) < 500 or len(test_df) < 100:
            continue

        available = [c for c in feature_cols if c in df.columns]
        X_train = train_df[available]
        y_train = train_df["result"]
        X_test = test_df[available]
        y_test = test_df["result"]

        model = _calibrated_pipeline()
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)
        classes = model.classes_

        acc = accuracy_score(y_test, y_pred)
        ll = log_loss(y_test, y_proba, labels=classes)
        brier = compute_multiclass_brier(y_test, y_proba, classes)
        ece = compute_ece(y_test, y_proba, classes)

        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

        rows.append({
            "test_season": test_season,
            "train_matches": len(train_df),
            "test_matches": len(test_df),
            "accuracy": acc,
            "log_loss": ll,
            "brier": brier,
            "ece": ece,
            "recall_H": report.get("H", {}).get("recall", 0),
            "recall_D": report.get("D", {}).get("recall", 0),
            "recall_A": report.get("A", {}).get("recall", 0),
            "precision_D": report.get("D", {}).get("precision", 0),
            "f1_D": report.get("D", {}).get("f1-score", 0),
        })

    return pd.DataFrame(rows)


def run_ablation(df_with_odds: pd.DataFrame) -> None:
    print("=" * 70)
    print("xgGaffer — Engine 2 Milestone B: Odds Ablation Analysis")
    print("=" * 70)

    base_features = [c for c in BASE_FEATURE_COLUMNS if c in df_with_odds.columns]
    odds_features = [c for c in FEATURE_COLUMNS_WITH_ODDS if c in df_with_odds.columns]

    print(f"\nDataset: {len(df_with_odds)} matches (all have odds)")
    print(f"Base features: {len(base_features)}")
    print(f"With-odds features: {len(odds_features)}")
    print(f"Leagues: {sorted(df_with_odds['league'].unique())}")
    print(f"Seasons: {sorted(df_with_odds['season'].astype(str).unique())}")

    target_dist = df_with_odds["result"].value_counts(normalize=True).round(3)
    print(f"\nTarget distribution: H={target_dist.get('H', 0):.1%}  D={target_dist.get('D', 0):.1%}  A={target_dist.get('A', 0):.1%}")

    print(f"\n{'=' * 70}")
    print("1. WALK-FORWARD CV — WITHOUT ODDS")
    print(f"{'=' * 70}")
    cv_base = run_walk_forward_cv(df_with_odds, base_features)
    print(cv_base[["test_season", "test_matches", "accuracy", "log_loss", "brier", "recall_D"]].to_string(index=False))
    print(f"\nMean: accuracy={cv_base['accuracy'].mean():.3f} ± {cv_base['accuracy'].std():.3f}")
    print(f"      log_loss={cv_base['log_loss'].mean():.4f}  brier={cv_base['brier'].mean():.4f}  ece={cv_base['ece'].mean():.3f}")
    print(f"      draw_recall={cv_base['recall_D'].mean():.3f}")

    print(f"\n{'=' * 70}")
    print("2. WALK-FORWARD CV — WITH ODDS")
    print(f"{'=' * 70}")
    cv_odds = run_walk_forward_cv(df_with_odds, odds_features)
    print(cv_odds[["test_season", "test_matches", "accuracy", "log_loss", "brier", "recall_D"]].to_string(index=False))
    print(f"\nMean: accuracy={cv_odds['accuracy'].mean():.3f} ± {cv_odds['accuracy'].std():.3f}")
    print(f"      log_loss={cv_odds['log_loss'].mean():.4f}  brier={cv_odds['brier'].mean():.4f}  ece={cv_odds['ece'].mean():.3f}")
    print(f"      draw_recall={cv_odds['recall_D'].mean():.3f}")

    print(f"\n{'=' * 70}")
    print("3. ABLATION COMPARISON")
    print(f"{'=' * 70}")
    acc_delta = cv_odds["accuracy"].mean() - cv_base["accuracy"].mean()
    ll_delta = cv_odds["log_loss"].mean() - cv_base["log_loss"].mean()
    brier_delta = cv_odds["brier"].mean() - cv_base["brier"].mean()
    draw_delta = cv_odds["recall_D"].mean() - cv_base["recall_D"].mean()

    print(f"  Accuracy:    {cv_base['accuracy'].mean():.3f} → {cv_odds['accuracy'].mean():.3f}  (Δ = {acc_delta:+.3f})")
    print(f"  Log loss:    {cv_base['log_loss'].mean():.4f} → {cv_odds['log_loss'].mean():.4f}  (Δ = {ll_delta:+.4f})")
    print(f"  Brier:       {cv_base['brier'].mean():.4f} → {cv_odds['brier'].mean():.4f}  (Δ = {brier_delta:+.4f})")
    print(f"  Draw recall: {cv_base['recall_D'].mean():.3f} → {cv_odds['recall_D'].mean():.3f}  (Δ = {draw_delta:+.3f})")

    print(f"\n{'=' * 70}")
    print("4. McNEMAR TEST (per fold)")
    print(f"{'=' * 70}")

    for test_year in range(WALK_FORWARD_START, WALK_FORWARD_END):
        test_season = str(test_year)
        train_mask = df_with_odds["season"].astype(str).astype(int) < test_year
        test_mask = df_with_odds["season"].astype(str) == test_season

        train_df = df_with_odds[train_mask]
        test_df = df_with_odds[test_mask]

        if len(train_df) < 500 or len(test_df) < 100:
            continue

        available_base = [c for c in base_features if c in df_with_odds.columns]
        available_odds = [c for c in odds_features if c in df_with_odds.columns]

        model_base = _calibrated_pipeline()
        model_base.fit(train_df[available_base], train_df["result"])
        pred_base = model_base.predict(test_df[available_base])

        model_odds = _calibrated_pipeline()
        model_odds.fit(train_df[available_odds], train_df["result"])
        pred_odds = model_odds.predict(test_df[available_odds])

        y_true = test_df["result"].values
        mcnemar = mcnemar_test(y_true, pred_base, pred_odds)

        sig_marker = "*" if mcnemar["significant"] else " "
        print(f"  {test_season}: odds_only_correct={mcnemar['b_only']}  base_only_correct={mcnemar['a_only']}  p={mcnemar['p_value']:.4f} {sig_marker}")

    print(f"\n{'=' * 70}")
    print("5. DRAW RECALL DEEP DIVE")
    print(f"{'=' * 70}")

    print("\n  Per-fold draw metrics (WITHOUT odds):")
    print(f"  {'Season':<8} {'Recall':<10} {'Precision':<10} {'F1':<10}")
    for _, row in cv_base.iterrows():
        print(f"  {row['test_season']:<8} {row['recall_D']:<10.3f} {row['precision_D']:<10.3f} {row['f1_D']:<10.3f}")

    print(f"\n  Per-fold draw metrics (WITH odds):")
    print(f"  {'Season':<8} {'Recall':<10} {'Precision':<10} {'F1':<10}")
    for _, row in cv_odds.iterrows():
        print(f"  {row['test_season']:<8} {row['recall_D']:<10.3f} {row['precision_D']:<10.3f} {row['f1_D']:<10.3f}")

    print(f"\n  Summary:")
    print(f"    Without odds — mean draw recall: {cv_base['recall_D'].mean():.3f}")
    print(f"    With odds    — mean draw recall: {cv_odds['recall_D'].mean():.3f}")

    print(f"\n{'=' * 70}")
    print("6. PRODUCTION MODEL TRAINING")
    print(f"{'=' * 70}")

    test_season = "2024"
    train_mask = df_with_odds["season"].astype(str).astype(int) < int(test_season)
    test_mask = df_with_odds["season"].astype(str) == test_season

    train_df = df_with_odds[train_mask]
    test_df = df_with_odds[test_mask]

    available_odds = [c for c in odds_features if c in df_with_odds.columns]
    available_base = [c for c in base_features if c in df_with_odds.columns]

    print(f"\n  Training on seasons < {test_season}, testing on {test_season}")
    print(f"  Train: {len(train_df)} matches, Test: {len(test_df)} matches")

    model_prod = _calibrated_pipeline()
    model_prod.fit(train_df[available_odds], train_df["result"])

    y_pred_prod = model_prod.predict(test_df[available_odds])
    y_proba_prod = model_prod.predict_proba(test_df[available_odds])
    classes_prod = model_prod.classes_

    prod_acc = accuracy_score(test_df["result"], y_pred_prod)
    prod_ll = log_loss(test_df["result"], y_proba_prod, labels=classes_prod)
    prod_brier = compute_multiclass_brier(test_df["result"], y_proba_prod, classes_prod)

    print(f"\n  With-odds production model (test={test_season}):")
    print(f"    Accuracy:  {prod_acc:.3f}")
    print(f"    Log loss:  {prod_ll:.4f}")
    print(f"    Brier:     {prod_brier:.4f}")
    print(f"\n  Classification report:")
    print(classification_report(test_df["result"], y_pred_prod, zero_division=0))
    print(f"  Confusion matrix (H/D/A):")
    print(confusion_matrix(test_df["result"], y_pred_prod, labels=CLASS_ORDER))

    model_base_prod = _calibrated_pipeline()
    model_base_prod.fit(train_df[available_base], train_df["result"])
    y_pred_base_prod = model_base_prod.predict(test_df[available_base])

    base_acc = accuracy_score(test_df["result"], y_pred_base_prod)
    print(f"\n  Without-odds production model (test={test_season}):")
    print(f"    Accuracy:  {base_acc:.3f}")
    print(f"    Accuracy lift from odds: {prod_acc - base_acc:+.3f}")

    mcnemar_prod = mcnemar_test(test_df["result"].values, y_pred_base_prod, y_pred_prod)
    print(f"    McNemar p-value: {mcnemar_prod['p_value']:.4f} {'(significant)' if mcnemar_prod['significant'] else '(not significant)'}")

    print(f"\n{'=' * 70}")
    print("7. ODDS FEATURE COEFFICIENT ANALYSIS")
    print(f"{'=' * 70}")

    base_pipeline = model_prod.calibrated_classifiers_[0].estimator
    clf = base_pipeline.named_steps["clf"]
    scaler = base_pipeline.named_steps["scaler"]

    print(f"\n  Logistic regression coefficients for odds features:")
    print(f"  {'Feature':<22} {'coef_H':>10} {'coef_D':>10} {'coef_A':>10}")
    for feat in ODDS_FEATURES:
        if feat in available_odds:
            feat_idx = available_odds.index(feat)
            coefs = {cls: clf.coef_[cls_idx][feat_idx] for cls_idx, cls in enumerate(clf.classes_)}
            print(f"  {feat:<22} {coefs.get('H', 0):>10.4f} {coefs.get('D', 0):>10.4f} {coefs.get('A', 0):>10.4f}")

    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Walk-forward accuracy (base):  {cv_base['accuracy'].mean():.3f} ± {cv_base['accuracy'].std():.3f}")
    print(f"  Walk-forward accuracy (odds):  {cv_odds['accuracy'].mean():.3f} ± {cv_odds['accuracy'].std():.3f}")
    print(f"  Accuracy lift:                 {acc_delta:+.3f}")
    print(f"  Log loss improvement:          {ll_delta:+.4f}")
    print(f"  Brier improvement:             {brier_delta:+.4f}")
    print(f"  Draw recall change:            {cv_base['recall_D'].mean():.3f} → {cv_odds['recall_D'].mean():.3f}")
    print(f"  Production accuracy (2024):    {prod_acc:.3f} (base: {base_acc:.3f})")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Engine 2 Milestone B — Odds Ablation")
    parser.add_argument("--leagues", nargs="+", default=ALL_LEAGUES)
    parser.add_argument("--seasons", nargs="+", default=ALL_SEASONS)

    args = parser.parse_args()

    print("Preparing dataset with odds (all 5 leagues)...")
    print("This will take a few minutes for the full dataset.\n")

    df = prepare_dataset(
        leagues=args.leagues,
        seasons=args.seasons,
        save=True,
        include_odds=True,
    )

    run_ablation(df)