from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import (
    brier_score_loss,
    log_loss,
    normalized_mutual_info_score,
    roc_auc_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler

from apps.predictions.ml.models.tactical.config import (
    CLUSTER_MODEL_PREFIX,
    KMEANS_NMI_N_INIT,
    KMEANS_NMI_SEEDS,
    MODELS_DIR,
    PASS_MODEL_PREFIX,
    TARGET,
    TEAM_MATCH_CLUSTERS_PATH,
    TEAM_SEASON_PROFILES_PATH,
    ZONE_COUNT,
    ZONE_PROFILES_PATH,
    ZONE_STATS_PATH,
)
from apps.predictions.ml.models.tactical.prepare_data import (
    build_pass_dataset,
    get_clustering_feature_columns,
)


logger = logging.getLogger(__name__)

DECILE_COUNT = 10
TOP_FEATURE_COUNT = 10
MIN_TEAM_MATCHES_FOR_STABILITY = 10


def _latest_artifact(prefix: str) -> Path:
    candidates = sorted(MODELS_DIR.glob(f"{prefix}_*.joblib"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(f"No model artifacts found for prefix {prefix}")
    return candidates[-1]


def evaluate_pass_model() -> dict:
    artifact = joblib.load(_latest_artifact(PASS_MODEL_PREFIX))
    model = artifact["model"]
    feature_cols = artifact["feature_columns"]

    _, test_df, _ = build_pass_dataset()
    X_test = test_df[feature_cols]
    y_test = test_df[TARGET].values.astype(int)

    y_proba = model.predict_proba(X_test)[:, 1]

    auc = roc_auc_score(y_test, y_proba)
    brier = brier_score_loss(y_test, y_proba)
    ll = log_loss(y_test, y_proba)

    print()
    print("=== MODEL 6A: PASS SUCCESS CLASSIFIER ===")
    print(f"Test rows:       {len(y_test):,}")
    print(f"Test AUC-ROC:    {auc:.4f}")
    print(f"Test Brier:      {brier:.4f}")
    print(f"Test Log loss:   {ll:.4f}")
    print(f"Test mean P:     {y_proba.mean():.4f}")
    print(f"Test actual:     {y_test.mean():.4f}")
    print(f"Baseline AUC:    0.5000 (always-predict-complete)")

    print()
    print("Calibration table (deciles of predicted probability):")
    cal_df = pd.DataFrame({"proba": y_proba, "y": y_test})
    cal_df["decile"] = pd.qcut(cal_df["proba"], q=DECILE_COUNT, labels=False, duplicates="drop")
    cal_summary = (
        cal_df.groupby("decile")
        .agg(n=("y", "size"), mean_proba=("proba", "mean"), actual_rate=("y", "mean"))
        .reset_index()
    )
    cal_summary["abs_deviation"] = (cal_summary["mean_proba"] - cal_summary["actual_rate"]).abs()
    print(cal_summary.to_string(index=False))
    print(f"Max abs deviation: {cal_summary['abs_deviation'].max():.4f}")

    print()
    print("Top 10 features by importance:")
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    else:
        importances = np.mean(
            [cc.estimator.feature_importances_ for cc in model.calibrated_classifiers_],
            axis=0,
        )
    importance_df = pd.DataFrame({"feature": feature_cols, "importance": importances}).sort_values(
        "importance", ascending=False
    )
    print(importance_df.head(TOP_FEATURE_COUNT).to_string(index=False))

    print()
    print("AUC-ROC by start zone:")
    test_with_proba = test_df[["zone_id", TARGET]].copy()
    test_with_proba["proba"] = y_proba
    zone_aucs = []
    for zone_id in range(ZONE_COUNT):
        sub = test_with_proba[test_with_proba["zone_id"] == zone_id]
        if len(sub) >= 50 and sub[TARGET].nunique() == 2:
            zone_auc = roc_auc_score(sub[TARGET].values, sub["proba"].values)
            zone_aucs.append({"zone_id": zone_id, "n": len(sub), "auc": zone_auc, "actual": sub[TARGET].mean()})
    zone_auc_df = pd.DataFrame(zone_aucs)
    print(zone_auc_df.to_string(index=False))

    return {
        "auc_roc": auc,
        "brier": brier,
        "log_loss": ll,
        "max_calibration_deviation": float(cal_summary["abs_deviation"].max()),
        "test_size": int(len(y_test)),
    }


def generate_zone_heatmap_data() -> pd.DataFrame:
    artifact = joblib.load(_latest_artifact(PASS_MODEL_PREFIX))
    model = artifact["model"]
    feature_cols = artifact["feature_columns"]

    _, test_df, _ = build_pass_dataset()
    test_df = test_df.copy()
    test_df["proba"] = model.predict_proba(test_df[feature_cols])[:, 1]

    rows = []
    for zone_id in range(ZONE_COUNT):
        sub = test_df[test_df["zone_id"] == zone_id]
        if sub.empty:
            continue
        rows.append(
            {
                "zone_id": zone_id,
                "zone_col": zone_id // 4,
                "zone_row": zone_id % 4,
                "n_passes": len(sub),
                "actual_completion_rate": float(sub[TARGET].mean()),
                "predicted_completion_rate": float(sub["proba"].mean()),
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(ZONE_STATS_PATH, index=False)
    print()
    print(f"Saved zone heatmap data to {ZONE_STATS_PATH}")
    print(df.to_string(index=False))
    return df


def evaluate_clustering_model() -> dict:
    artifact = joblib.load(_latest_artifact(CLUSTER_MODEL_PREFIX))
    km: KMeans = artifact["model"]
    scaler: StandardScaler = artifact["scaler"]
    feature_cols = artifact["feature_columns"]

    season_profiles = pd.read_csv(TEAM_SEASON_PROFILES_PATH)
    X = season_profiles[feature_cols].values
    X_scaled = scaler.transform(X)

    labels = km.predict(X_scaled)
    sil = silhouette_score(X_scaled, labels)

    nmi_pairs = []
    label_runs = []
    for seed in range(KMEANS_NMI_SEEDS):
        km_seed = KMeans(n_clusters=km.n_clusters, random_state=seed, n_init=KMEANS_NMI_N_INIT)
        label_runs.append(km_seed.fit_predict(X_scaled))
    for i in range(len(label_runs)):
        for j in range(i + 1, len(label_runs)):
            nmi_pairs.append(normalized_mutual_info_score(label_runs[i], label_runs[j]))
    nmi_mean = float(np.mean(nmi_pairs))

    print()
    print("=== MODEL 6B: TEAM STYLE CLUSTERING ===")
    print(f"Team-seasons:    {len(season_profiles)}")
    print(f"Feature count:   {len(feature_cols)}")
    print(f"k:               {km.n_clusters}")
    print(f"Silhouette:      {sil:.4f}  (target > 0.35, soft floor 0.25)")
    print(f"NMI stability:   {nmi_mean:.4f}  (target > 0.5)")

    print()
    print("Cluster size distribution (team-seasons):")
    sizes = pd.Series(labels).value_counts().sort_index()
    for cluster_id, count in sizes.items():
        print(f"  Cluster {int(cluster_id)}: {count} ({count / len(labels):.1%})")

    print()
    print("Match-level stability (team-match clusters):")
    match_clusters = pd.read_csv(TEAM_MATCH_CLUSTERS_PATH)
    team_stability = []
    for team, group in match_clusters.groupby("team_name"):
        if len(group) < MIN_TEAM_MATCHES_FOR_STABILITY:
            continue
        mode_count = group["cluster"].value_counts().iloc[0]
        team_stability.append(mode_count / len(group))
    mean_stability = float(np.mean(team_stability)) if team_stability else 0.0
    print(f"  Mean fraction in mode cluster: {mean_stability:.4f}")
    print(f"  Teams with >= {MIN_TEAM_MATCHES_FOR_STABILITY} matches: {len(team_stability)}")

    print()
    print("Match-level cluster distribution:")
    match_sizes = match_clusters["cluster"].value_counts().sort_index()
    for cluster_id, count in match_sizes.items():
        print(f"  Cluster {int(cluster_id)}: {count} ({count / len(match_clusters):.1%})")

    return {
        "best_k": int(km.n_clusters),
        "silhouette": float(sil),
        "nmi_stability": nmi_mean,
        "n_team_seasons": int(len(season_profiles)),
        "n_team_matches": int(len(match_clusters)),
        "match_level_temporal_stability": mean_stability,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    print()
    print("########################################")
    print("#  ENGINE 6 EVALUATION REPORT          #")
    print("########################################")

    pass_metrics = evaluate_pass_model()
    generate_zone_heatmap_data()
    cluster_metrics = evaluate_clustering_model()

    print()
    print("########################################")
    print("#  SUMMARY                             #")
    print("########################################")
    print()
    print("Model 6A (Pass Success Classifier):")
    print(f"  AUC-ROC:    {pass_metrics['auc_roc']:.4f}")
    print(f"  Brier:      {pass_metrics['brier']:.4f}")
    print(f"  Log loss:   {pass_metrics['log_loss']:.4f}")
    print(f"  Max cal dev:{pass_metrics['max_calibration_deviation']:.4f}")
    print(f"  Test rows:  {pass_metrics['test_size']:,}")
    print()
    print("Model 6B (Team Style Clustering):")
    print(f"  k:                  {cluster_metrics['best_k']}")
    print(f"  Silhouette:         {cluster_metrics['silhouette']:.4f}")
    print(f"  NMI stability:      {cluster_metrics['nmi_stability']:.4f}")
    print(f"  Team-seasons:       {cluster_metrics['n_team_seasons']}")
    print(f"  Team-matches:       {cluster_metrics['n_team_matches']}")
    print(f"  Match stability:    {cluster_metrics['match_level_temporal_stability']:.4f}")


if __name__ == "__main__":
    main()