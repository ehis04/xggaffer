from __future__ import annotations

import numpy as np
import pandas as pd

from apps.predictions.ml.models.match_outcome.config import INTERPRETABLE_MODEL_TYPE, resolve_latest_model_path
from apps.predictions.ml.models.match_outcome.predict import get_predictor


STAT_LABELS = {
    'xg': 'xG',
    'xga': 'xG conceded',
    'xa': 'xA',
    'shots': 'shots',
    'shots_conceded': 'shots conceded',
    'key_passes': 'key passes',
    'points': 'points per match',
    'xpts': 'expected points',
}

DIFF_LABELS = {
    'xg': 'expected goals',
    'xga': 'xG conceded',
    'xa': 'expected assists',
    'shots': 'shots',
    'points': 'points per match',
    'xpts': 'expected points',
}

FEATURE_DESCRIPTIONS: dict[str, tuple[str, str]] = {"market_home_prob": ("Market home prob", "de-vigged bookmaker implied probability of home win"),
    "market_draw_prob": ("Market draw prob", "de-vigged bookmaker implied probability of draw"),
    "market_away_prob": ("Market away prob", "de-vigged bookmaker implied probability of away win"),}

for _side in ('home', 'away'):
    _side_label = _side.title()
    for _stat, _label in STAT_LABELS.items():
        for _w in (5, 10, 20):
            _key = f'{_side}_rolling_{_stat}_{_w}'
            FEATURE_DESCRIPTIONS[_key] = (
                f'{_side_label} {_label} ({_w})',
                f'{_side} team average {_label} over last {_w} matches',
            )

    for _h in (5, 10, 20):
        _key = f'{_side}_ewm_xg_{_h}'
        FEATURE_DESCRIPTIONS[_key] = (
            f'{_side_label} xG trend ({_h})',
            f'{_side} team exponentially weighted xG with half-life {_h}',
        )

    FEATURE_DESCRIPTIONS[f'{_side}_rolling_wins_5'] = (
        f'{_side_label} wins (5)',
        f'{_side} team wins in last 5 matches',
    )
    FEATURE_DESCRIPTIONS[f'{_side}_xgd_slope'] = (
        f'{_side_label} form trend',
        f'{_side} team xG difference trend over recent matches',
    )
    FEATURE_DESCRIPTIONS[f'{_side}_days_rest'] = (
        f'{_side_label} rest days',
        f'days since {_side} team last played',
    )
    for _d in (14, 28):
        FEATURE_DESCRIPTIONS[f'{_side}_matches_last_{_d}d'] = (
            f'{_side_label} congestion ({_d}d)',
            f'{_side} team matches in last {_d} days',
        )

for _stat, _label in DIFF_LABELS.items():
    for _w in (5, 10, 20):
        _key = f'{_stat}_diff_{_w}'
        FEATURE_DESCRIPTIONS[_key] = (
            f'{_label} advantage ({_w})',
            f'{_label} over last {_w} matches',
        )

FEATURE_DESCRIPTIONS['is_home'] = ('Home advantage', 'playing at home')
FEATURE_DESCRIPTIONS['home_elo'] = ('Home Elo rating', 'home team Elo strength rating')
FEATURE_DESCRIPTIONS['away_elo'] = ('Away Elo rating', 'away team Elo strength rating')
FEATURE_DESCRIPTIONS['elo_difference'] = ('Elo advantage', 'home Elo minus away Elo')


def _get_interpretable_predictor(predictor=None):
    if predictor is not None:
        return predictor

    model_path = resolve_latest_model_path(INTERPRETABLE_MODEL_TYPE)
    return get_predictor(model_path=model_path)


def _extract_linear_components(predictor):
    model = predictor.model

    if hasattr(model, 'calibrated_classifiers_'):
        base = model.calibrated_classifiers_[0].estimator
    else:
        base = model

    if hasattr(base, 'named_steps'):
        clf = base.named_steps['clf']
        scaler = base.named_steps.get('scaler')
    else:
        clf = base
        scaler = None

    if not hasattr(clf, 'coef_'):
        raise TypeError(
            f'Deterministic interpretation requires coefficient-based models. '
            f'Loaded model type {type(clf).__name__} is not supported.'
        )

    return clf, scaler


def get_coefficients(predictor=None) -> pd.DataFrame:
    predictor = _get_interpretable_predictor(predictor)
    clf, _ = _extract_linear_components(predictor)

    rows = []
    for feat_idx, feat_name in enumerate(predictor.feature_columns):
        row = {'feature': feat_name}
        for cls_idx, cls in enumerate(clf.classes_):
            row[f'coef_{cls}'] = float(clf.coef_[cls_idx][feat_idx])
        row['abs_mean'] = np.mean([abs(clf.coef_[c][feat_idx]) for c in range(len(clf.classes_))])
        rows.append(row)

    return pd.DataFrame(rows).sort_values('abs_mean', ascending=False)


def _describe_feature(feature: str, value: float) -> str:
    label, description = FEATURE_DESCRIPTIONS.get(feature, (feature, feature))

    is_diff = '_diff_' in feature or feature == 'elo_difference'

    if is_diff:
        if value > 0:
            advantage = 'Home team has the edge in'
        elif value < 0:
            advantage = 'Away team has the edge in'
        else:
            advantage = 'Teams are level in'
        return f'{advantage} {description} ({value:+.2f})'

    if feature.startswith('home_'):
        return f'{label}: {value:.2f}'
    if feature.startswith('away_'):
        return f'{label}: {value:.2f}'
    return f'{label}: {value:.2f}'


def explain_prediction(
    features: pd.DataFrame,
    predictor=None,
    top_n: int = 5,
) -> dict:
    predictor = _get_interpretable_predictor(predictor)
    clf, scaler = _extract_linear_components(predictor)

    feature_names = predictor.feature_columns
    feature_values = features[feature_names].iloc[0]
    scaled_values = (
        scaler.transform(features[feature_names]).flatten()
        if scaler is not None
        else feature_values.values
    )

    contributions = {}
    for cls_idx, cls in enumerate(clf.classes_):
        cls_contribs = scaled_values * clf.coef_[cls_idx]
        contributions[cls] = dict(zip(feature_names, cls_contribs))

    prediction = predictor.predict(features)
    predicted_class = prediction['prediction_code']

    sorted_features = sorted(
        feature_names,
        key=lambda feature: abs(contributions[predicted_class][feature]),
        reverse=True,
    )

    top_factors = []
    for feature in sorted_features[:top_n]:
        contribution = float(contributions[predicted_class][feature])
        value = float(feature_values[feature])
        top_factors.append({
            'feature': feature,
            'value': round(value, 3),
            'contribution': round(contribution, 4),
            'description': _describe_feature(feature, value),
        })

    return {
        **prediction,
        'top_factors': top_factors,
        'all_contributions': {
            cls: {feature: round(float(value), 4) for feature, value in cls_values.items()}
            for cls, cls_values in contributions.items()
        },
    }


def explain_match(
    home_team: str,
    away_team: str,
    league: str,
    season: str,
    top_n: int = 5,
) -> dict:
    from apps.predictions.ml.models.match_outcome.feature_service import get_feature_service

    service = get_feature_service(leagues=[league], seasons=[season])
    features = service.build_prediction_features(home_team, away_team, league, season)
    result = explain_prediction(features, top_n=top_n)
    result.update({
        'home_team': home_team,
        'away_team': away_team,
        'league': str(league),
        'season': str(season),
    })
    return result


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--home', required=True)
    parser.add_argument('--away', required=True)
    parser.add_argument('--league', default='EPL')
    parser.add_argument('--season', default='2024')
    parser.add_argument('--top', type=int, default=5)
    parser.add_argument('--coefficients', action='store_true')
    args = parser.parse_args()

    if args.coefficients:
        print(get_coefficients().head(20).to_string(index=False))
    else:
        result = explain_match(args.home, args.away, args.league, args.season, top_n=args.top)
        print(f"\n{args.home} vs {args.away} ({args.league} {args.season})")
        print(f"Prediction: {result['prediction']} ({result['probabilities']})")
        print(f"\nTop {args.top} factors:")
        for factor in result['top_factors']:
            symbol = '+' if factor['contribution'] > 0 else '-'
            print(f"  [{symbol}] {factor['description']}")
            print(f"      Contribution: {factor['contribution']:+.4f}")