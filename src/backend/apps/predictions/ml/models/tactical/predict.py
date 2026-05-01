from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from apps.predictions.ml.models.tactical.config import (
    CLUSTER_MODEL_PREFIX,
    MODELS_DIR,
    PASS_MODEL_PREFIX,
    ZONE_COUNT,
)
from apps.predictions.ml.models.tactical.feature_service import (
    get_team_season_profile,
    get_team_rolling_zone_profile,
)


logger = logging.getLogger(__name__)

DOMINANT_ZONE_COUNT = 5
SIMILARITY_MIRROR_THRESHOLD = 0.85
SIMILARITY_CONTRAST_THRESHOLD = 0.50

CLUSTER_LABELS = {
    0: "elite_final_third_possession",
    1: "league_average_buildup",
    2: "deep_central_control",
}

UNKNOWN_CLUSTER_LABEL = "unknown"


def _latest_artifact(prefix: str) -> Path:
    candidates = sorted(MODELS_DIR.glob(f"{prefix}_*.joblib"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(f"No model artifacts found for prefix {prefix}")
    return candidates[-1]


class TacticalAnalyser:

    def __init__(
        self,
        pass_model_path: Optional[Path] = None,
        cluster_model_path: Optional[Path] = None,
    ):
        self.pass_model_path = pass_model_path or _latest_artifact(PASS_MODEL_PREFIX)
        self.cluster_model_path = cluster_model_path or _latest_artifact(CLUSTER_MODEL_PREFIX)

        pass_artifact = joblib.load(self.pass_model_path)
        self.pass_model = pass_artifact["model"]
        self.pass_feature_columns = pass_artifact["feature_columns"]
        self.pass_is_calibrated = pass_artifact.get("is_calibrated", False)

        cluster_artifact = joblib.load(self.cluster_model_path)
        self.cluster_model = cluster_artifact["model"]
        self.cluster_scaler = cluster_artifact["scaler"]
        self.cluster_feature_columns = cluster_artifact["feature_columns"]

        logger.info("TacticalAnalyser loaded: pass=%s cluster=%s", self.pass_model_path.name, self.cluster_model_path.name)

    def predict_pass_success(self, pass_df: pd.DataFrame) -> np.ndarray:
        X = pass_df[self.pass_feature_columns]
        return self.pass_model.predict_proba(X)[:, 1]

    def _zone_dict(self, profile: pd.Series) -> dict:
        return {
            zone_id: float(profile[f"zone_{zone_id}_success_rate"])
            for zone_id in range(ZONE_COUNT)
        }

    def _dominant_zones(self, profile: pd.Series) -> list[int]:
        volume_cols = [f"zone_{i}_pass_volume" for i in range(ZONE_COUNT)]
        volumes = profile[volume_cols].astype(float)
        ranked = volumes.sort_values(ascending=False)
        return [int(col.split("_")[1]) for col in ranked.head(DOMINANT_ZONE_COUNT).index]

    def _cluster_label(self, cluster_id: int) -> str:
        return CLUSTER_LABELS.get(int(cluster_id), UNKNOWN_CLUSTER_LABEL)

    def _predict_cluster_for_profile(self, profile: pd.Series) -> int:
        X = profile[self.cluster_feature_columns].values.reshape(1, -1)
        X_scaled = self.cluster_scaler.transform(X)
        return int(self.cluster_model.predict(X_scaled)[0])

    def analyse_team(
        self,
        team_name: str,
        season_name: Optional[str] = None,
    ) -> Optional[dict]:
        profile = get_team_season_profile(team_name, season_name)
        if profile is None:
            return None

        cluster_id = self._predict_cluster_for_profile(profile)

        return {
            "team": team_name,
            "season_name": str(profile["season_name"]),
            "competition_name": str(profile["competition_name"]),
            "n_matches_in_profile": int(profile["n_matches"]),
            "style_cluster": cluster_id,
            "style_label": self._cluster_label(cluster_id),
            "zone_success_rates": self._zone_dict(profile),
            "overall_completion_rate": float(profile["overall_completion_rate"]),
            "overall_forward_ratio": float(profile["overall_forward_ratio"]),
            "overall_pass_length": float(profile["overall_pass_length"]),
            "dominant_zones": self._dominant_zones(profile),
        }

    def _scaled_style_vector(self, profile: pd.Series) -> np.ndarray:
        X = profile[self.cluster_feature_columns].values.reshape(1, -1)
        return self.cluster_scaler.transform(X)

    def compare_teams(
        self,
        team_a: str,
        team_b: str,
        season_name: Optional[str] = None,
    ) -> Optional[dict]:
        analysis_a = self.analyse_team(team_a, season_name)
        analysis_b = self.analyse_team(team_b, season_name)
        if analysis_a is None or analysis_b is None:
            return None

        profile_a = get_team_season_profile(team_a, season_name)
        profile_b = get_team_season_profile(team_b, season_name)

        vec_a = self._scaled_style_vector(profile_a)
        vec_b = self._scaled_style_vector(profile_b)

        raw_cosine = float(cosine_similarity(vec_a, vec_b)[0, 0])
        similarity = (raw_cosine + 1.0) / 2.0
        similarity = max(0.0, min(1.0, similarity))

        if similarity >= SIMILARITY_MIRROR_THRESHOLD:
            matchup_type = "mirror"
        elif similarity <= SIMILARITY_CONTRAST_THRESHOLD:
            matchup_type = "contrast"
        else:
            matchup_type = "neutral"

        return {
            "team_a": analysis_a,
            "team_b": analysis_b,
            "style_similarity": similarity,
            "matchup_type": matchup_type,
        }

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    analyser = TacticalAnalyser()
    print()
    print("=== ANALYSER LOAD CHECK ===")
    print(f"Pass model:    {analyser.pass_model_path.name}")
    print(f"Cluster model: {analyser.cluster_model_path.name}")
    print(f"Pass features: {len(analyser.pass_feature_columns)}")
    print(f"Cluster features: {len(analyser.cluster_feature_columns)}")
    print(f"Calibrated:    {analyser.pass_is_calibrated}")

    print()
    print("=== analyse_team(Barcelona, 2018/2019) ===")
    result = analyser.analyse_team("Barcelona", "2018/2019")
    if result:
        for k, v in result.items():
            if k != "zone_success_rates":
                print(f"  {k}: {v}")
        print(f"  zone_success_rates (first 4): {dict(list(result['zone_success_rates'].items())[:4])}")

    print()
    print("=== compare_teams(Barcelona, Atlético Madrid, 2015/2016) ===")
    matchup = analyser.compare_teams("Barcelona", "Atlético Madrid", "2015/2016")
    if matchup:
        print(f"  team_a cluster: {matchup['team_a']['style_label']}")
        print(f"  team_b cluster: {matchup['team_b']['style_label']}")
        print(f"  style_similarity: {matchup['style_similarity']:.4f}")
        print(f"  matchup_type:     {matchup['matchup_type']}")

    print()
    print("=== compare_teams(Barcelona, Real Madrid, 2015/2016) ===")
    matchup = analyser.compare_teams("Barcelona", "Real Madrid", "2015/2016")
    if matchup:
        print(f"  team_a cluster: {matchup['team_a']['style_label']}")
        print(f"  team_b cluster: {matchup['team_b']['style_label']}")
        print(f"  style_similarity: {matchup['style_similarity']:.4f}")
        print(f"  matchup_type:     {matchup['matchup_type']}")


if __name__ == "__main__":
    main()