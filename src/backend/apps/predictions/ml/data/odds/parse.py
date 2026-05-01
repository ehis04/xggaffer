from __future__ import annotations

from pathlib import Path

import pandas as pd

from apps.predictions.ml.data.odds.devig import devig_columns, validate_odds
from apps.predictions.ml.data.odds.download import RAW_ODDS_DIR, ALL_LEAGUES, ALL_SEASONS, build_output_path


ODDS_COLUMN_PRIORITY = [
    ("AvgCH", "AvgCD", "AvgCA"),
    ("AvgH", "AvgD", "AvgA"),
    ("B365CH", "B365CD", "B365CA"),
    ("B365H", "B365D", "B365A"),
    ("PSH", "PSD", "PSA"),
]

MATCH_COLUMNS = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]

DATE_FORMATS = ["%d/%m/%Y", "%d/%m/%y"]


def _select_odds_columns(df: pd.DataFrame) -> tuple[str, str, str] | None:
    for home_col, draw_col, away_col in ODDS_COLUMN_PRIORITY:
        if all(col in df.columns for col in (home_col, draw_col, away_col)):
            non_null = df[[home_col, draw_col, away_col]].notna().all(axis=1).sum()
            if non_null > 0:
                return home_col, draw_col, away_col
    return None


def _parse_date(date_series: pd.Series) -> pd.Series:
    for fmt in DATE_FORMATS:
        try:
            parsed = pd.to_datetime(date_series, format=fmt)
            if parsed.notna().sum() > len(date_series) * 0.9:
                return parsed.dt.normalize()
        except (ValueError, TypeError):
            continue

    return pd.to_datetime(date_series, format="mixed", dayfirst=True).dt.normalize()


def parse_single_csv(
    path: Path,
    league: str,
    season: str,
) -> pd.DataFrame | None:
    try:
        raw = pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")
    except UnicodeDecodeError:
        raw = pd.read_csv(path, encoding="latin-1", on_bad_lines="skip")

    if raw.empty:
        return None

    raw = raw.dropna(how="all")
    raw = raw[raw["HomeTeam"].notna() & raw["AwayTeam"].notna()]

    if len(raw) == 0:
        return None

    odds_cols = _select_odds_columns(raw)
    if odds_cols is None:
        print(f"  WARNING: No valid odds columns in {path.name}")
        return None

    home_col, draw_col, away_col = odds_cols

    keep_cols = MATCH_COLUMNS + [home_col, draw_col, away_col]
    available = [c for c in keep_cols if c in raw.columns]
    df = raw[available].copy()

    df["date"] = _parse_date(df["Date"])
    df = df.dropna(subset=["date"])

    for col in (home_col, draw_col, away_col):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    valid_mask = df.apply(
        lambda row: validate_odds(row[home_col], row[draw_col], row[away_col]),
        axis=1,
    )
    pre_filter = len(df)
    df = df[valid_mask]
    if len(df) < pre_filter:
        dropped = pre_filter - len(df)
        print(f"  {path.name}: {dropped} rows dropped (invalid odds)")

    devigged = devig_columns(df, home_col, draw_col, away_col)

    result = pd.DataFrame({
        "date": df["date"].values,
        "fdcouk_home_team": df["HomeTeam"].values,
        "fdcouk_away_team": df["AwayTeam"].values,
        "fdcouk_home_goals": pd.to_numeric(df.get("FTHG"), errors="coerce").values,
        "fdcouk_away_goals": pd.to_numeric(df.get("FTAG"), errors="coerce").values,
        "fdcouk_result": df.get("FTR", pd.Series(dtype=str)).values,
        "market_home_prob": devigged["market_home_prob"].values,
        "market_draw_prob": devigged["market_draw_prob"].values,
        "market_away_prob": devigged["market_away_prob"].values,
        "overround": devigged["overround"].values,
        "odds_source": f"{home_col}/{draw_col}/{away_col}",
        "league": league,
        "season": season,
    })

    return result.reset_index(drop=True)


def parse_all(
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
) -> pd.DataFrame:
    leagues = leagues or ALL_LEAGUES
    seasons = seasons or ALL_SEASONS

    frames: list[pd.DataFrame] = []

    for league in leagues:
        for season in seasons:
            path = build_output_path(league, season)
            if not path.exists():
                continue

            df = parse_single_csv(path, league, season)
            if df is not None and len(df) > 0:
                frames.append(df)

    if not frames:
        raise FileNotFoundError("No odds data parsed. Run download first.")

    combined = pd.concat(frames, ignore_index=True)

    prob_sum = (
        combined["market_home_prob"]
        + combined["market_draw_prob"]
        + combined["market_away_prob"]
    )
    tolerance = 1e-6
    assert (prob_sum - 1.0).abs().max() < tolerance, "De-vigged probabilities do not sum to 1.0"

    print(f"\nParsed {len(combined)} matches from {len(frames)} files")
    print(f"Overround range: {combined['overround'].min():.3f} — {combined['overround'].max():.3f}")
    print(f"Odds sources used: {combined['odds_source'].value_counts().to_dict()}")

    return combined


if __name__ == "__main__":
    df = parse_all()
    print(f"\nShape: {df.shape}")
    print(f"\nSample de-vigged probabilities:")
    print(df[["fdcouk_home_team", "fdcouk_away_team", "market_home_prob", "market_draw_prob", "market_away_prob"]].head(10).to_string(index=False))