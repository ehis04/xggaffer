from __future__ import annotations

import pandas as pd

from data_collection.config.team_name_mappings import to_canonical
from apps.predictions.ml.data.odds.parse import parse_all


FDCOUK_SOURCE = "football_data_co_uk"

ODDS_OUTPUT_COLUMNS = [
    "match_id",
    "market_home_prob",
    "market_draw_prob",
    "market_away_prob",
]


def _canonicalize_odds(odds_df: pd.DataFrame) -> pd.DataFrame:
    df = odds_df.copy()

    canonical_home = []
    canonical_away = []
    failed_teams: set[str] = set()

    for _, row in df.iterrows():
        try:
            ch = to_canonical(row["fdcouk_home_team"], FDCOUK_SOURCE)
        except KeyError:
            ch = None
            failed_teams.add(row["fdcouk_home_team"])

        try:
            ca = to_canonical(row["fdcouk_away_team"], FDCOUK_SOURCE)
        except KeyError:
            ca = None
            failed_teams.add(row["fdcouk_away_team"])

        canonical_home.append(ch)
        canonical_away.append(ca)

    df["canonical_home"] = canonical_home
    df["canonical_away"] = canonical_away

    if failed_teams:
        print(f"  WARNING: {len(failed_teams)} unmapped FDCOUK teams: {sorted(failed_teams)}")

    pre_drop = len(df)
    df = df.dropna(subset=["canonical_home", "canonical_away"])
    if len(df) < pre_drop:
        print(f"  Dropped {pre_drop - len(df)} rows with unmapped teams")

    return df


def merge_odds_to_matches(
    matches_df: pd.DataFrame,
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
) -> pd.DataFrame:
    print("Loading and parsing odds data...")
    odds_raw = parse_all(leagues=leagues, seasons=seasons)

    print("\nCanonicalising FDCOUK team names...")
    odds = _canonicalize_odds(odds_raw)

    odds["date"] = pd.to_datetime(odds["date"]).dt.normalize()

    matches = matches_df.copy()
    matches["_merge_date"] = pd.to_datetime(matches["date"]).dt.normalize()

    merged = matches.merge(
        odds[["canonical_home", "canonical_away", "date", "market_home_prob", "market_draw_prob", "market_away_prob"]],
        left_on=["home_team", "away_team", "_merge_date"],
        right_on=["canonical_home", "canonical_away", "date"],
        how="left",
        suffixes=("", "_odds"),
    )

    matched = merged["market_home_prob"].notna().sum()
    total = len(merged)
    match_rate = matched / total * 100

    print(f"\nMerge results:")
    print(f"  Understat matches:  {total}")
    print(f"  Odds matched:       {matched} ({match_rate:.1f}%)")
    print(f"  Odds missing:       {total - matched} ({100 - match_rate:.1f}%)")

    if match_rate < 90:
        unmatched = merged[merged["market_home_prob"].isna()]
        unmatched_teams = set(unmatched["home_team"].unique()) | set(unmatched["away_team"].unique())
        matched_teams = set(merged[merged["market_home_prob"].notna()]["home_team"].unique())
        never_matched = unmatched_teams - matched_teams
        if never_matched:
            print(f"  Teams NEVER matched: {sorted(never_matched)}")

    drop_cols = [c for c in ["canonical_home", "canonical_away", "date_odds", "_merge_date"] if c in merged.columns]
    merged = merged.drop(columns=drop_cols, errors="ignore")

    return merged


def load_merged_odds(
    matches_df: pd.DataFrame,
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
) -> pd.DataFrame:
    return merge_odds_to_matches(matches_df, leagues=leagues, seasons=seasons)


if __name__ == "__main__":
    from apps.predictions.ml.features.rolling import load_match_history

    print("Loading Understat match history...")
    matches = load_match_history()
    print(f"Loaded {len(matches)} matches\n")

    merged = merge_odds_to_matches(matches)

    print(f"\nPer-league match rates:")
    for league in sorted(merged["league"].unique()):
        league_df = merged[merged["league"] == league]
        league_matched = league_df["market_home_prob"].notna().sum()
        print(f"  {league}: {league_matched}/{len(league_df)} ({league_matched / len(league_df) * 100:.1f}%)")

    print(f"\nPer-season match rates:")
    for season in sorted(merged["season"].astype(str).unique()):
        season_df = merged[merged["season"].astype(str) == season]
        season_matched = season_df["market_home_prob"].notna().sum()
        print(f"  {season}: {season_matched}/{len(season_df)} ({season_matched / len(season_df) * 100:.1f}%)")