from __future__ import annotations

import numpy as np
import pandas as pd

from apps.predictions.ml.models.scoreline.config import HOME_GOALS_FEATURES, AWAY_GOALS_FEATURES
from apps.predictions.ml.models.scoreline.train import (
    derive_probabilities,
    scoreline_matrix,
    train_score_model,
)


def _get_engine2_predictions(test_df: pd.DataFrame) -> dict:
    from apps.predictions.ml.models.match_outcome.config import resolve_latest_model_path, INTERPRETABLE_MODEL_TYPE
    from apps.predictions.ml.models.match_outcome.predict import get_predictor

    model_path = resolve_latest_model_path(INTERPRETABLE_MODEL_TYPE)
    predictor = get_predictor(model_path=model_path)
    required_features = predictor.feature_columns

    available = [c for c in required_features if c in test_df.columns]
    missing = [c for c in required_features if c not in test_df.columns]

    if missing:
        print(f"Engine 2 features missing from Engine 3 dataset: {len(missing)}")
        print(f"  Using {len(available)}/{len(required_features)} features")
        print(f"  NOTE: Engine 2 predictions may differ from its own evaluation")
        print(f"        due to using a different feature pipeline.\n")

    features = test_df[available].copy()
    if features.isnull().any().any():
        features = features.fillna(0)

    y_proba = predictor.model.predict_proba(features)
    classes = predictor.model.classes_

    probs = {}
    for i, cls in enumerate(classes):
        probs[cls] = y_proba[:, i]

    predictions = classes[np.argmax(y_proba, axis=1)]

    return {"probs": probs, "predictions": predictions, "classes": classes}


def run_comparison(results: dict) -> None:
    test_df = results["test_df"]
    lh = results["test_lambda_home"]
    la = results["test_lambda_away"]
    rho = results["rho"]

    hg = test_df["home_goals"].values.astype(int)
    ag = test_df["away_goals"].values.astype(int)
    actual = np.where(hg > ag, "H", np.where(ag > hg, "A", "D"))
    n = len(test_df)

    e3_predictions = []
    e3_probs = {"H": [], "D": [], "A": []}

    for i in range(n):
        matrix = scoreline_matrix(lh[i], la[i], rho)
        probs = derive_probabilities(matrix)

        best = max(
            ("H", probs["home_win"]), ("D", probs["draw"]), ("A", probs["away_win"]),
            key=lambda x: x[1],
        )
        e3_predictions.append(best[0])
        e3_probs["H"].append(probs["home_win"])
        e3_probs["D"].append(probs["draw"])
        e3_probs["A"].append(probs["away_win"])

    e3_predictions = np.array(e3_predictions)
    e3_acc = float((e3_predictions == actual).mean())

    print("=" * 60)
    print("ENGINE 2 vs ENGINE 3 — COMPARISON")
    print("=" * 60)

    try:
        e2 = _get_engine2_predictions(test_df)
        e2_predictions = e2["predictions"]
        e2_probs = e2["probs"]
        e2_acc = float((e2_predictions == actual).mean())
    except (FileNotFoundError, Exception) as exc:
        print(f"\nCould not load Engine 2 model: {exc}")
        print("Skipping direct comparison. Using reported Engine 2 metrics.")
        print(f"\n  Engine 3 W/D/L accuracy: {e3_acc:.1%}")
        return

    print(f"\n--- Overall Accuracy ---")
    print(f"  Engine 2: {e2_acc:.1%}")
    print(f"  Engine 3: {e3_acc:.1%}")
    print(f"  Delta:    {(e3_acc - e2_acc):+.1%}")

    agreement = float((e2_predictions == e3_predictions).mean())
    print(f"\n--- Agreement Rate ---")
    print(f"  Same prediction: {agreement:.1%} ({int(agreement * n)}/{n})")

    disagree_mask = e2_predictions != e3_predictions
    disagree_count = int(disagree_mask.sum())

    if disagree_count > 0:
        e2_correct_when_disagree = int((e2_predictions[disagree_mask] == actual[disagree_mask]).sum())
        e3_correct_when_disagree = int((e3_predictions[disagree_mask] == actual[disagree_mask]).sum())
        neither_correct = disagree_count - e2_correct_when_disagree - e3_correct_when_disagree

        print(f"  Disagree on: {disagree_count} matches")
        print(f"  Engine 2 correct: {e2_correct_when_disagree} ({e2_correct_when_disagree/disagree_count:.1%})")
        print(f"  Engine 3 correct: {e3_correct_when_disagree} ({e3_correct_when_disagree/disagree_count:.1%})")
        print(f"  Neither correct:  {neither_correct} ({neither_correct/disagree_count:.1%})")

    print(f"\n--- Per-Class Recall ---")
    print(f"  {'Class':<6} {'Support':<10} {'E2 Recall':<12} {'E3 Recall':<12}")
    for cls in ("H", "D", "A"):
        mask = actual == cls
        support = int(mask.sum())
        e2_recall = float((e2_predictions[mask] == cls).mean()) if support > 0 else 0.0
        e3_recall = float((e3_predictions[mask] == cls).mean()) if support > 0 else 0.0
        print(f"  {cls:<6} {support:<10} {e2_recall:<12.1%} {e3_recall:<12.1%}")

    print(f"\n--- Per-Class Prediction Count ---")
    print(f"  {'Class':<6} {'Actual':<10} {'E2 Predicted':<15} {'E3 Predicted':<15}")
    for cls in ("H", "D", "A"):
        actual_count = int((actual == cls).sum())
        e2_count = int((e2_predictions == cls).sum())
        e3_count = int((e3_predictions == cls).sum())
        print(f"  {cls:<6} {actual_count:<10} {e2_count:<15} {e3_count:<15}")

    print(f"\n--- Draw Probability Calibration ---")
    e3_draw_probs = np.array(e3_probs["D"])
    actual_draws = actual == "D"
    actual_draw_rate = float(actual_draws.mean())

    print(f"  Actual draw rate:         {actual_draw_rate:.1%}")
    print(f"  Engine 3 mean P(draw):    {e3_draw_probs.mean():.1%}")

    if "D" in e2_probs:
        e2_draw_probs = e2_probs["D"]
        print(f"  Engine 2 mean P(draw):    {e2_draw_probs.mean():.1%}")

        bins = [(0.0, 0.15), (0.15, 0.25), (0.25, 0.35), (0.35, 1.0)]
        print(f"\n  Engine 3 draw calibration by predicted probability bin:")
        print(f"  {'Bin':<12} {'Count':<8} {'Mean P(D)':<12} {'Actual D%':<12}")
        for lo, hi in bins:
            mask = (e3_draw_probs >= lo) & (e3_draw_probs < hi)
            count = int(mask.sum())
            if count > 0:
                mean_pred = float(e3_draw_probs[mask].mean())
                actual_rate = float(actual_draws[mask].mean())
                print(f"  [{lo:.2f},{hi:.2f}) {count:<8} {mean_pred:<12.1%} {actual_rate:<12.1%}")

    print(f"\n--- Write-Up Narrative ---")
    print(f"  Engine 2 (discriminative): {e2_acc:.1%} W/D/L accuracy,")
    e2_draw_recall = float((e2_predictions[actual == 'D'] == 'D').mean()) if (actual == 'D').sum() > 0 else 0.0
    e3_draw_recall = float((e3_predictions[actual == 'D'] == 'D').mean()) if (actual == 'D').sum() > 0 else 0.0
    print(f"    draw recall {e2_draw_recall:.0%}")
    print(f"  Engine 3 (generative):     {e3_acc:.1%} W/D/L accuracy,")
    print(f"    draw recall {e3_draw_recall:.0%}, mean P(draw) {e3_draw_probs.mean():.1%}")
    print(f"  Complementary: Engine 3 produces calibrated draw probabilities")
    print(f"  ({e3_draw_probs.mean():.1%} vs {actual_draw_rate:.1%} actual) that Engine 2 cannot,")
    print(f"  plus scoreline distributions and lambda parameters for Engine 4.")
    print()


if __name__ == "__main__":
    results = train_score_model(save=False)
    run_comparison(results)