from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .config import (
    FORMATION_SLOTS,
    MODELS_DIR,
    POSITION_CATEGORY_MAP,
)

logger = logging.getLogger(__name__)


def resolve_latest_lineup_model() -> Path:
    pattern = 'lineup_xgboost_*.joblib'
    model_files = sorted(MODELS_DIR.glob(pattern), key=lambda f: f.stat().st_mtime)

    if not model_files:
        raise FileNotFoundError(
            f'No lineup model artifacts found in {MODELS_DIR}'
        )

    return model_files[-1]


class LineupPredictor:

    def __init__(self, artifact_path: Path | str | None = None) -> None:
        path = Path(artifact_path) if artifact_path else resolve_latest_lineup_model()
        artifact = joblib.load(path)

        self.model = artifact['model']
        self.feature_columns = artifact['feature_columns']
        self.metrics = artifact.get('metrics', {})

    def predict_start_probabilities(
        self,
        player_features_df: pd.DataFrame,
    ) -> pd.DataFrame:
        X = player_features_df[self.feature_columns]
        probs = self.model.predict_proba(X)[:, 1]

        result = player_features_df[
            ['player_id', 'player_name', 'team_id', 'position']
        ].copy()
        result['p_start'] = probs

        return result

    def predict_starting_xi(
        self,
        player_features_df: pd.DataFrame,
        formation: str | None = None,
    ) -> pd.DataFrame:
        probs_df = self.predict_start_probabilities(player_features_df)

        if formation is None:
            formation = infer_formation(player_features_df)

        xi = assemble_xi(probs_df, formation)
        return xi


def infer_formation(
    df: pd.DataFrame,
    n_recent: int = 5,
) -> str:
    if 'date' not in df.columns or 'team_id' not in df.columns:
        return '4-3-3'

    team_id = df['team_id'].iloc[0]

    starters = df[df.get('started', df.get('p_start', pd.Series(dtype=float))) == True]
    if starters.empty:
        return '4-3-3'

    recent_matches = (
        df[['match_id', 'date']].drop_duplicates()
        .sort_values('date', ascending=False)
        .head(n_recent)
    )
    recent_match_ids = set(recent_matches['match_id'])

    recent_starters = df[
        (df['match_id'].isin(recent_match_ids)) &
        (df['started'] == True) &
        (df['team_id'] == team_id)
    ]

    if recent_starters.empty:
        return '4-3-3'

    formations_per_match = []
    for match_id, group in recent_starters.groupby('match_id'):
        categories = group['position'].map(POSITION_CATEGORY_MAP).fillna('MID')
        n_def = (categories == 'DEF').sum()
        n_mid = (categories == 'MID').sum()
        n_fwd = (categories == 'FWD').sum()
        formation_str = f'{n_def}-{n_mid}-{n_fwd}'
        formations_per_match.append(formation_str)

    if not formations_per_match:
        return '4-3-3'

    mode = pd.Series(formations_per_match).mode()
    inferred = mode.iloc[0] if len(mode) > 0 else '4-3-3'

    if inferred not in FORMATION_SLOTS:
        return '4-3-3'

    return inferred


def assemble_xi(
    probs_df: pd.DataFrame,
    formation: str,
) -> pd.DataFrame:
    slots = FORMATION_SLOTS.get(formation, FORMATION_SLOTS['4-3-3'])

    df = probs_df.copy()
    df['category'] = df['position'].map(POSITION_CATEGORY_MAP).fillna('MID')

    df.loc[df['category'] == 'SUB', 'category'] = _guess_category_from_history(
        df[df['category'] == 'SUB']
    )

    selected: list[dict] = []
    used_player_ids: set = set()

    for category in ['GK', 'DEF', 'MID', 'FWD']:
        n_needed = slots.get(category, 0)

        eligible = df[
            (df['category'] == category) &
            (~df['player_id'].isin(used_player_ids))
        ].sort_values('p_start', ascending=False)

        for _, row in eligible.head(n_needed).iterrows():
            selected.append(row.to_dict())
            used_player_ids.add(row['player_id'])

    total_selected = len(selected)
    if total_selected < 11:
        remaining = df[
            ~df['player_id'].isin(used_player_ids)
        ].sort_values('p_start', ascending=False)

        for _, row in remaining.head(11 - total_selected).iterrows():
            selected.append(row.to_dict())
            used_player_ids.add(row['player_id'])

    return pd.DataFrame(selected)


def _guess_category_from_history(sub_df: pd.DataFrame) -> pd.Series:
    return pd.Series('MID', index=sub_df.index)


_predictor_cache: LineupPredictor | None = None


def predict_match_lineups(
    player_features_df: pd.DataFrame,
    predictor: LineupPredictor | None = None,
    formation: str | None = None,
) -> dict[str, pd.DataFrame]:
    global _predictor_cache
    if predictor is None:
        if _predictor_cache is None:
            _predictor_cache = LineupPredictor()
        predictor = _predictor_cache

    results = {}

    for team_id, team_group in player_features_df.groupby('team_id'):
        probs = predictor.predict_start_probabilities(team_group)

        team_formation = formation or infer_formation(team_group)

        xi = assemble_xi(probs, team_formation)

        team_name = team_group['team_name'].iloc[0] if 'team_name' in team_group.columns else str(team_id)

        results[team_name] = {
            'formation': team_formation,
            'predicted_xi': xi,
            'all_probabilities': probs.sort_values('p_start', ascending=False),
        }

    return results