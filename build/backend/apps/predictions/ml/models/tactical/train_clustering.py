from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import normalized_mutual_info_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from apps.predictions.ml.models.tactical.config import (
    CLUSTER_MODEL_PREFIX,
    KMEANS_CANDIDATE_K,
    KMEANS_DEFAULT_K,
    KMEANS_NMI_N_INIT,
    KMEANS_NMI_SEEDS,
    KMEANS_N_INIT,
    MODELS_DIR,
    MODEL_VERSION,
    NMI_STABILITY_TARGET,
    SILHOUETTE_SOFT_MINIMUM,
    SILHOUETTE_TARGET,
    TEAM_MATCH_CLUSTERS_PATH,
    TEAM_SEASON_PROFILES_PATH,
    ZONE_COUNT,
    ZONE_PROFILES_PATH,
)
from apps.predictions.ml.models.tactical.prepare_data import get_clustering_feature_columns


logger = logging.getLogger(__name__)

MIN_TEAM_MATCHES_FOR_STABILITY = 10
TEMPORAL_STABILITY_TARGET = 0.50
TOP_ZONES_PER_CLUSTER = 5


def load_team_season_profiles(path: Path = TEAM_SEASON_PROFILES_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def load_team_match_profiles(path: Path = ZONE_PROFILES_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def build_feature_matrix(profiles: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    feature_cols = get_clustering_feature_columns()
    X = profiles[feature_cols].values
    return X, feature_cols


def evaluate_k_candidates(
    X_scaled: np.ndarray,
    candidates: list[int],
) -> dict[int, float]:
    scores = {}
    for k in candidates:
        km = KMeans(n_clusters=k, random_state=42, n_init=KMEANS_N_INIT)
        labels = km.fit_predict(X_scaled)
        sil = silhouette_score(X_scaled, labels)
        scores[k] = sil
        logger.info("k=%d -> silhouette=%.4f", k, sil)
    return scores


def select_best_k(scores: dict[int, float]) -> int:
    best_k = max(scores, key=scores.get)
    if scores[best_k] < SILHOUETTE_SOFT_MINIMUM:
        logger.warning(
            "Best silhouette %.4f below soft minimum %.4f - falling back to k=%d",
            scores[best_k],
            SILHOUETTE_SOFT_MINIMUM,
            min(KMEANS_CANDIDATE_K),
        )
        return min(KMEANS_CANDIDATE_K)
    return best_k


def compute_nmi_stability(X_scaled: np.ndarray, k: int) -> tuple[float, list[float]]:
    label_runs = []
    for seed in range(KMEANS_NMI_SEEDS):
        km = KMeans(n_clusters=k, random_state=seed, n_init=KMEANS_NMI_N_INIT)
        label_runs.append(km.fit_predict(X_scaled))

    pairwise = []
    for i in range(len(label_runs)):
        for j in range(i + 1, len(label_runs)):
            pairwise.append(
                normalized_mutual_info_score(label_runs[i], label_runs[j])
            )
    return float(np.mean(pairwise)), pairwise


def fit_final_model(X_scaled: np.ndarray, k: int) -> KMeans:
    km = KMeans(n_clusters=k, random_state=42, n_init=KMEANS_N_INIT)
    km.fit(X_scaled)
    return km


def describe_centroids(
    km: KMeans,
    scaler: StandardScaler,
    feature_cols: list[str],
) -> pd.DataFrame:
    centroids_scaled = km.cluster_centers_
    centroids = scaler.inverse_transform(centroids_scaled)
    df = pd.DataFrame(centroids, columns=feature_cols)
    df.index.name = "cluster"
    return df


def top_zones_per_cluster(
    centroid_df: pd.DataFrame,
    n_top: int = TOP_ZONES_PER_CLUSTER,
) -> dict[int, dict]:
    result = {}
    for cluster_id in centroid_df.index:
        row = centroid_df.loc[cluster_id]
        success_part = row[[c for c in row.index if "success_rate" in c]]
        volume_part = row[[c for c in row.index if "pass_volume" in c]]
        top_success = [
            (int(col.split("_")[1]), float(val))
            for col, val in success_part.sort_values(ascending=False).head(n_top).items()
        ]
        top_volume = [
            (int(col.split("_")[1]), float(val))
            for col, val in volume_part.sort_values(ascending=False).head(n_top).items()
        ]
        result[cluster_id] = {"top_success": top_success, "top_volume": top_volume}
    return result


def cluster_size_distribution(labels: np.ndarray, k: int) -> pd.DataFrame:
    counts = pd.Series(labels).value_counts().sort_index()
    df = pd.DataFrame(
        {
            "cluster": counts.index,
            "n": counts.values,
            "fraction": counts.values / len(labels),
        }
    )
    return df


def temporal_consistency(
    match_clusters: pd.DataFrame,
    labels: np.ndarray,
) -> tuple[float, int]:
    df = match_clusters[["team_name"]].copy()
    df["cluster"] = labels

    team_stability = []
    for team, group in df.groupby("team_name"):
        if len(group) < MIN_TEAM_MATCHES_FOR_STABILITY:
            continue
        mode_count = group["cluster"].value_counts().iloc[0]
        team_stability.append(mode_count / len(group))

    if not team_stability:
        return 0.0, 0
    return float(np.mean(team_stability)), len(team_stability)
    
def assign_team_match_clusters(
    km: KMeans,
    scaler: StandardScaler,
    feature_cols: list[str],
    output_path: Path = TEAM_MATCH_CLUSTERS_PATH,
) -> pd.DataFrame:
    match_profiles = load_team_match_profiles()
    X_match = match_profiles[feature_cols].values
    X_match_scaled = scaler.transform(X_match)
    labels = km.predict(X_match_scaled)

    output = match_profiles[
        [
            "match_id",
            "team_id",
            "team_name",
            "competition_name",
            "season_id",
            "season_name",
        ]
    ].copy()
    output["cluster"] = labels
    output.to_csv(output_path, index=False)
    logger.info("Saved %d team-match cluster assignments to %s", len(output), output_path)
    return output

def save_model(
    km: KMeans,
    scaler: StandardScaler,
    feature_cols: list[str],
    metrics: dict,
) -> Path:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = MODELS_DIR / f"{CLUSTER_MODEL_PREFIX}_{MODEL_VERSION}_{timestamp}.joblib"

    artifact = {
        "model": km,
        "scaler": scaler,
        "feature_columns": feature_cols,
        "metrics": metrics,
        "trained_at": timestamp,
    }
    joblib.dump(artifact, output_path)
    return output_path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    profiles = load_team_season_profiles()
    logger.info("Loaded %d team-season profiles", len(profiles))

    X, feature_cols = build_feature_matrix(profiles)
    logger.info("Feature count: %d", len(feature_cols))

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print()
    print("=== K SELECTION (silhouette score) ===")
    scores = evaluate_k_candidates(X_scaled, KMEANS_CANDIDATE_K)
    for k, sil in scores.items():
        marker = " <-- best" if k == max(scores, key=scores.get) else ""
        print(f"k={k}: silhouette={sil:.4f}{marker}")
    best_k = select_best_k(scores)
    print(f"Selected k: {best_k}")
    print(f"Silhouette target: > {SILHOUETTE_TARGET}")

    print()
    print("=== NMI STABILITY ===")
    nmi_mean, nmi_pairs = compute_nmi_stability(X_scaled, best_k)
    print(f"Mean pairwise NMI across {KMEANS_NMI_SEEDS} seeds: {nmi_mean:.4f}")
    print(f"Min/max pairwise NMI: {min(nmi_pairs):.4f} / {max(nmi_pairs):.4f}")
    print(f"NMI target: > {NMI_STABILITY_TARGET}")

    final_km = fit_final_model(X_scaled, best_k)
    final_labels = final_km.labels_

    print()
    print("=== CLUSTER SIZE DISTRIBUTION (team-seasons) ===")
    size_df = cluster_size_distribution(final_labels, best_k)
    print(size_df.to_string(index=False))

    print()
    print("=== CLUSTER CENTROIDS ===")
    centroid_df = describe_centroids(final_km, scaler, feature_cols)
    top_data = top_zones_per_cluster(centroid_df)
    for cluster_id, parts in top_data.items():
        success_str = ", ".join(f"z{z}={r:.3f}" for z, r in parts["top_success"])
        volume_str = ", ".join(f"z{z}={r:.3f}" for z, r in parts["top_volume"])
        print(f"Cluster {cluster_id}:")
        print(f"  top success rates: {success_str}")
        print(f"  top pass volumes:  {volume_str}")

    print()
    print("=== EXAMPLE TEAM-SEASON ASSIGNMENTS ===")
    profiles_with_labels = profiles.copy()
    profiles_with_labels["cluster"] = final_labels
    for team in ["Barcelona", "Real Madrid", "Atlético Madrid"]:
        team_data = profiles_with_labels[profiles_with_labels["team_name"] == team]
        if not team_data.empty:
            for _, row in team_data.iterrows():
                print(f"  {team} {row['season_name']}: cluster {int(row['cluster'])}")

    print()
    print("=== ASSIGNING CLUSTERS TO ALL TEAM-MATCH PROFILES ===")
    match_clusters = assign_team_match_clusters(final_km, scaler, feature_cols)
    print(f"Team-match cluster assignments: {len(match_clusters)} rows")
    print()
    print("Team-match cluster size distribution:")
    match_dist = match_clusters["cluster"].value_counts().sort_index()
    for cluster_id, count in match_dist.items():
        print(f"  Cluster {int(cluster_id)}: {count} ({count / len(match_clusters):.1%})")

    print()
    print("=== ROLLING-MATCH TEMPORAL CONSISTENCY ===")
    stability, n_teams = temporal_consistency(match_clusters, match_clusters["cluster"].values)
    print(f"Mean fraction in mode cluster across team-matches: {stability:.4f} ({n_teams} teams)")

    metrics = {
        "best_k": int(best_k),
        "silhouette": float(scores[best_k]),
        "silhouette_all_k": {int(k): float(v) for k, v in scores.items()},
        "nmi_stability": nmi_mean,
        "team_match_temporal_stability": stability,
        "n_team_seasons": int(len(profiles)),
        "n_team_matches": int(len(match_clusters)),
    }

    output_path = save_model(final_km, scaler, feature_cols, metrics)
    print()
    print(f"Saved model: {output_path}")

if __name__ == "__main__":
    main()