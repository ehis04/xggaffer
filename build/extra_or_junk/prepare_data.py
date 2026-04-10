import pandas as pd
from pathlib import Path
from .features import FEATURE_COLUMNS, TARGET_COLUMN_BINARY


def load_raw_data(filepath: str = '/mnt/c/Users/ehiso/OneDrive/Code/yr4/2026-csc-1097-adenire-2-oghinae-2/build/backend/data/raw/epl_2024_matches.csv') -> pd.DataFrame:
    return pd.read_csv(filepath)
OUTPUT_DIR = Path("/mnt/c/Users/ehiso/OneDrive/Code/yr4/2026-csc-1097-adenire-2-oghinae-2/build/backend/data/raw")


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    df['xg_diff'] = df['team_xg'] - df['opponent_xg']
    df['xg_ratio'] = df['team_xg'] / df['opponent_xg'].replace(0, 0.1)
    
    df['win'] = (df['result'] == 'W').astype(int)
    
    return df


def split_data(df: pd.DataFrame, test_size: float = 0.2) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.sort_values('date').reset_index(drop=True)
    
    split_idx = int(len(df) * (1 - test_size))
    
    train = df.iloc[:split_idx]
    test = df.iloc[split_idx:]
    
    return train, test


def get_feature_target_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN_BINARY]
    
    return X, y


def prepare_pipeline(filepath: str = '/mnt/c/Users/ehiso/OneDrive/Code/yr4/2026-csc-1097-adenire-2-oghinae-2/build/backend/data/raw/epl_2024_matches.csv', test_size: float = 0.2) -> dict:
    df = load_raw_data(filepath)
    df = engineer_features(df)
    
    train, test = split_data(df, test_size)
    
    X_train, y_train = get_feature_target_split(train)
    X_test, y_test = get_feature_target_split(test)
    
    return {
        'X_train': X_train,
        'y_train': y_train,
        'X_test': X_test,
        'y_test': y_test,
        'train_df': train,
        'test_df': test,
    }