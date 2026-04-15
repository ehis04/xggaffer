from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import statsmodels.api as sm

from apps.predictions.ml.models.scoreline.config import MODELS_DIR
from apps.predictions.ml.models.scoreline.train import derive_probabilities, scoreline_matrix


def resolve_latest_score_model() -> Path:
    candidates = sorted(
        MODELS_DIR.glob("score_poisson_dc_*.joblib"),
        key=lambda f: f.stat().st_mtime,
    )
    if not candidates:
        raise FileNotFoundError(
            f"No score model artifacts found in {MODELS_DIR}. Train first."
        )
    return candidates[-1]


class ScorePredictor:

    def __init__(self, artifact_path: Path | str | None = None):
        artifact_path = artifact_path or resolve_latest_score_model()
        artifact = joblib.load(artifact_path)

        self.model_home = artifact["model_home"]
        self.model_away = artifact["model_away"]
        self.rho = artifact["rho"]
        self.home_features = artifact["home_features"]
        self.away_features = artifact["away_features"]
        self.naive_home = artifact.get("naive_home")
        self.naive_away = artifact.get("naive_away")

    def predict_lambdas(self, features_df: pd.DataFrame) -> tuple[float, float]:
        X_home = sm.add_constant(
            features_df[self.home_features].astype(float),
            has_constant="add",
        )
        X_away = sm.add_constant(
            features_df[self.away_features].astype(float),
            has_constant="add",
        )

        lambda_home = float(self.model_home.predict(X_home).iloc[0])
        lambda_away = float(self.model_away.predict(X_away).iloc[0])

        return lambda_home, lambda_away

    def predict_lambdas_batch(
        self, features_df: pd.DataFrame,
    ) -> tuple[np.ndarray, np.ndarray]:
        X_home = sm.add_constant(
            features_df[self.home_features].astype(float),
            has_constant="add",
        )
        X_away = sm.add_constant(
            features_df[self.away_features].astype(float),
            has_constant="add",
        )

        return (
            self.model_home.predict(X_home).values,
            self.model_away.predict(X_away).values,
        )

    def predict_scoreline_matrix(
        self, features_df: pd.DataFrame,
    ) -> tuple[np.ndarray, float, float]:
        lh, la = self.predict_lambdas(features_df)
        matrix = scoreline_matrix(lh, la, self.rho)
        return matrix, lh, la

    def predict(self, features_df: pd.DataFrame) -> dict:
        matrix, lh, la = self.predict_scoreline_matrix(features_df)
        derived = derive_probabilities(matrix)

        return {
            "lambda_home": round(lh, 3),
            "lambda_away": round(la, 3),
            "rho": round(self.rho, 4),
            "scoreline_matrix": matrix.round(4).tolist(),
            **{
                k: round(v, 4) if isinstance(v, float) else v
                for k, v in derived.items()
            },
        }


if __name__ == "__main__":
    predictor = ScorePredictor()
    print(f"Loaded model with rho={predictor.rho:.4f}")
    print(f"Home features: {predictor.home_features}")
    print(f"Away features: {predictor.away_features}")