import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split

from ml.features.understat import build_match_features


DATA_DIR = Path(__file__).resolve().parents[5] / 'data'
PROCESSED_DIR = DATA_DIR / 'processed'


TEAM_STATS_FEATURES = [
    'home_npxgd',
    'home_ppda',
    'home_oppda',
    'home_deep',
    'away_npxgd',
    'away_ppda',
    'away_oppda',
    'away_deep',
]

SQUAD_FEATURES = [
    'home_squad_total_xg',
    'home_squad_total_xa',
    'home_squad_avg_xg90',
    'home_squad_top_xg90',
    'away_squad_total_xg',
    'away_squad_total_xa',
    'away_squad_avg_xg90',
    'away_squad_top_xg90',
]

SUMMARY_FEATURES = [
    'home_xgd',
    'home_xg_per_shot',
    'home_primary_formation_pct',
    'home_xg_per_min_winning',
    'home_xg_per_min_drawing',
    'home_xg_per_min_losing',
    'home_fast_attack_ratio',
    'away_xgd',
    'away_xg_per_shot',
    'away_primary_formation_pct',
    'away_xg_per_min_winning',
    'away_xg_per_min_drawing',
    'away_xg_per_min_losing',
    'away_fast_attack_ratio',
]

DERIVED_FEATURES = [
    'npxgd_diff',
    'ppda_diff',
    'deep_diff',
    'squad_xg_diff',
    'squad_xa_diff',
    'squad_avg_xg90_diff',
    'squad_top_xg90_diff',
    'xgd_diff',
    'xg_per_shot_diff',
    'xg_winning_diff',
    'xg_losing_diff',
    'fast_attack_diff',
]

FEATURE_COLUMNS = TEAM_STATS_FEATURES + SQUAD_FEATURES + SUMMARY_FEATURES + DERIVED_FEATURES

METADATA_COLUMNS = [
    'match_id',
    'date',
    'league',
    'season',
    'home_team',
    'away_team',
]

TARGET_COLUMN = 'result'


def create_target(df: pd.DataFrame) -> pd.DataFrame:
    def get_result(row):
        if row['home_goals'] > row['away_goals']:
            return 'H'
        elif row['home_goals'] < row['away_goals']:
            return 'A'
        return 'D'
    
    df = df.copy()
    df['result'] = df.apply(get_result, axis=1)
    return df


def prepare_dataset(
    leagues: list[str] = None,
    seasons: list[str] = None,
    save: bool = True,
) -> pd.DataFrame:
    leagues = leagues or ['EPL']
    seasons = seasons or ['2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024']
    
    df = build_match_features(leagues, seasons)
    df = create_target(df)
    
    available_features = [c for c in FEATURE_COLUMNS if c in df.columns]
    required_cols = METADATA_COLUMNS + available_features + [TARGET_COLUMN]
    available_cols = [c for c in required_cols if c in df.columns]
    df = df[available_cols]
    
    df = df.dropna(subset=available_features + [TARGET_COLUMN])
    
    print(f"Features available: {len(available_features)}/{len(FEATURE_COLUMNS)}")
    missing = set(FEATURE_COLUMNS) - set(available_features)
    if missing:
        print(f"Missing features: {missing}")
    
    if save:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        output_path = PROCESSED_DIR / 'match_outcome_features.csv'
        df.to_csv(output_path, index=False)
    
    return df


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in FEATURE_COLUMNS if c in df.columns]


def get_train_test_split(
    df: pd.DataFrame = None,
    test_size: float = 0.2,
    random_state: int = 42,
    stratify: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    if df is None:
        filepath = PROCESSED_DIR / 'match_outcome_features.csv'
        if not filepath.exists():
            df = prepare_dataset()
        else:
            df = pd.read_csv(filepath)
    
    feature_cols = get_feature_columns(df)
    X = df[feature_cols]
    y = df[TARGET_COLUMN]
    
    stratify_col = y if stratify else None
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify_col,
    )
    
    return X_train, X_test, y_train, y_test


def get_temporal_split(
    df: pd.DataFrame = None,
    test_seasons: list[str] = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    test_seasons = test_seasons or ['2024']
    
    if df is None:
        filepath = PROCESSED_DIR / 'match_outcome_features.csv'
        if not filepath.exists():
            df = prepare_dataset()
        else:
            df = pd.read_csv(filepath)
    
    train_df = df[~df['season'].astype(str).isin(test_seasons)]
    test_df = df[df['season'].astype(str).isin(test_seasons)]
    
    feature_cols = get_feature_columns(df)
    
    X_train = train_df[feature_cols]
    y_train = train_df[TARGET_COLUMN]
    X_test = test_df[feature_cols]
    y_test = test_df[TARGET_COLUMN]
    
    return X_train, X_test, y_train, y_test


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--leagues', nargs='+', default=['EPL'])
    parser.add_argument('--seasons', nargs='+', default=['2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024'])
    
    args = parser.parse_args()
    
    df = prepare_dataset(leagues=args.leagues, seasons=args.seasons)
    
    print(f"\nDataset shape: {df.shape}")
    print(f"\nTarget distribution:")
    print(df['result'].value_counts(normalize=True).round(3))
    print(f"\nFeature columns ({len(get_feature_columns(df))}):")
    for col in get_feature_columns(df):
        print(f"  {col}")