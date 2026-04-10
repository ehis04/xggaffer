import warnings

import pandas as pd
from sklearn.model_selection import train_test_split

from ml.features.rolling import (
    ALL_LEAGUES,
    ALL_SEASONS,
    DIFF_STATS,
    EWM_HALF_LIVES,
    ROLLING_STATS,
    ROLLING_WINDOWS,
    build_all_features,
)
from ml.models.match_outcome.config import (
    PROCESSED_DIR,
    DEFAULT_LEAGUES,
    DEFAULT_SEASONS,
    TEST_SEASONS,
    RANDOM_SEED,
)


ELO_RATINGS_PATH = PROCESSED_DIR / "elo_ratings.csv"

ROLLING_FEATURES = [
    f"{side}_rolling_{stat}_{window}"
    for side in ["home", "away"]
    for stat in ROLLING_STATS
    for window in ROLLING_WINDOWS
]

EWM_FEATURES = [
    f"{side}_ewm_xg_{halflife}"
    for side in ["home", "away"]
    for halflife in EWM_HALF_LIVES
]

FORM_FEATURES = [
    "home_rolling_wins_5",
    "away_rolling_wins_5",
    "home_xgd_slope",
    "away_xgd_slope",
]

SCHEDULE_FEATURES = [
    "home_days_rest",
    "away_days_rest",
    "home_matches_last_14d",
    "away_matches_last_14d",
    "home_matches_last_28d",
    "away_matches_last_28d",
]

DIFF_FEATURES = [
    f"{stat}_diff_{window}"
    for stat in DIFF_STATS
    for window in ROLLING_WINDOWS
]

INDICATOR_FEATURES = [
    "is_home",
]

ELO_FEATURES = [
    "elo_difference",
]

ODDS_FEATURES = [
    "market_home_prob",
    "market_draw_prob",
    "market_away_prob",
]

BASE_FEATURE_COLUMNS = (
    ROLLING_FEATURES
    + EWM_FEATURES
    + FORM_FEATURES
    + SCHEDULE_FEATURES
    + DIFF_FEATURES
    + INDICATOR_FEATURES
    + ELO_FEATURES
)

FEATURE_COLUMNS = BASE_FEATURE_COLUMNS

FEATURE_COLUMNS_WITH_ODDS = BASE_FEATURE_COLUMNS + ODDS_FEATURES

METADATA_COLUMNS = [
    "match_id",
    "date",
    "league",
    "season",
    "home_team",
    "away_team",
]

TARGET_COLUMN = "result"


def _merge_elo_features(df: pd.DataFrame) -> pd.DataFrame:
    if not ELO_RATINGS_PATH.exists():
        return df

    elo = pd.read_csv(ELO_RATINGS_PATH)

    elo_cols = elo[["match_id", "elo_difference"]]

    merged = df.merge(elo_cols, on="match_id", how="left")

    matched = merged["elo_difference"].notna().sum()
    total = len(merged)
    if matched < total:
        print(f"  Elo merge: {matched}/{total} matches matched ({total - matched} missing)")
    else:
        print(f"  Elo merge: {matched}/{total} matches matched")

    return merged


def _merge_odds_features(df: pd.DataFrame) -> pd.DataFrame:
    try:
        from ml.data.odds.merge import merge_odds_to_matches
    except ImportError as exc:
        print(f"  Odds merge skipped (import error): {exc}")
        return df

    leagues = df["league"].unique().tolist() if "league" in df.columns else None
    seasons = df["season"].astype(str).unique().tolist() if "season" in df.columns else None

    merged = merge_odds_to_matches(df, leagues=leagues, seasons=seasons)

    return merged


def create_target(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["result"] = "D"
    df.loc[df["home_goals"] > df["away_goals"], "result"] = "H"
    df.loc[df["home_goals"] < df["away_goals"], "result"] = "A"
    return df


def prepare_dataset(
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
    save: bool = True,
    include_odds: bool = False,
) -> pd.DataFrame:
    leagues = leagues or DEFAULT_LEAGUES
    seasons = seasons or DEFAULT_SEASONS

    df = build_all_features(leagues, seasons)
    df = create_target(df)
    df = _merge_elo_features(df)

    if include_odds:
        df = _merge_odds_features(df)

    feature_cols = FEATURE_COLUMNS_WITH_ODDS if include_odds else FEATURE_COLUMNS
    available_features = [c for c in feature_cols if c in df.columns]
    required_cols = METADATA_COLUMNS + available_features + [TARGET_COLUMN]
    available_cols = [c for c in required_cols if c in df.columns]
    df = df[available_cols]

    pre_drop = len(df)
    df = df.dropna(subset=available_features + [TARGET_COLUMN])
    dropped = pre_drop - len(df)

    print(f"Features available: {len(available_features)}/{len(feature_cols)}")
    missing = set(feature_cols) - set(available_features)
    if missing:
        print(f"Missing features: {sorted(missing)}")
    if dropped:
        print(f"Rows dropped (insufficient history or missing odds): {dropped}/{pre_drop}")

    if save:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        suffix = "_with_odds" if include_odds else ""
        output_path = PROCESSED_DIR / f"match_outcome_features{suffix}.csv"
        df.to_csv(output_path, index=False)
        print(f"Saved to {output_path}")

    return df


def get_feature_columns(df: pd.DataFrame, include_odds: bool = False) -> list[str]:
    feature_cols = FEATURE_COLUMNS_WITH_ODDS if include_odds else FEATURE_COLUMNS
    return [c for c in feature_cols if c in df.columns]


def get_train_test_split(
    df: pd.DataFrame | None = None,
    test_size: float = 0.2,
    random_state: int = RANDOM_SEED,
    stratify: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    warnings.warn(
        "get_train_test_split uses random splits which leak future data. "
        "Use get_temporal_split instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    if df is None:
        filepath = PROCESSED_DIR / "match_outcome_features.csv"
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
    df: pd.DataFrame | None = None,
    test_seasons: list[str] | None = None,
    include_odds: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    test_seasons = test_seasons or TEST_SEASONS

    if df is None:
        suffix = "_with_odds" if include_odds else ""
        filepath = PROCESSED_DIR / f"match_outcome_features{suffix}.csv"
        if not filepath.exists():
            df = prepare_dataset(include_odds=include_odds)
        else:
            df = pd.read_csv(filepath)

    train_df = df[~df["season"].astype(str).isin(test_seasons)]
    test_df = df[df["season"].astype(str).isin(test_seasons)]

    feature_cols = get_feature_columns(df, include_odds=include_odds)

    X_train = train_df[feature_cols]
    y_train = train_df[TARGET_COLUMN]
    X_test = test_df[feature_cols]
    y_test = test_df[TARGET_COLUMN]

    return X_train, X_test, y_train, y_test


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--leagues", nargs="+", default=DEFAULT_LEAGUES)
    parser.add_argument("--seasons", nargs="+", default=DEFAULT_SEASONS)
    parser.add_argument("--with-odds", action="store_true")

    args = parser.parse_args()

    df = prepare_dataset(
        leagues=args.leagues,
        seasons=args.seasons,
        include_odds=args.with_odds,
    )

    feature_cols = get_feature_columns(df, include_odds=args.with_odds)

    print(f"\nDataset shape: {df.shape}")
    print(f"\nTarget distribution:")
    print(df["result"].value_counts(normalize=True).round(3))
    print(f"\nFeature columns ({len(feature_cols)}):")
    for col in feature_cols:
        print(f"  {col}")