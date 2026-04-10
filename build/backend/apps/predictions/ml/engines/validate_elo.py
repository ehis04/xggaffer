from __future__ import annotations

import argparse
from datetime import datetime

import numpy as np
import pandas as pd

from ml.engines.elo import load_elo_history
from ml.models.match_outcome.config import PROCESSED_DIR


ELO_RATINGS_PATH = PROCESSED_DIR / "elo_ratings.csv"

SAMPLE_DATES_PER_SEASON = [
    "{year}-09-15",
    "{year}-12-15",
    "{next_year}-03-15",
]

CANONICAL_TO_CLUBELO = {
    "RasenBallsport Leipzig": "RB Leipzig",
    "Paris Saint Germain": "Paris Saint-Germain",
    "Wolverhampton Wanderers": "Wolverhampton",
    "Borussia Monchengladbach": "Mönchengladbach",
    "FC Cologne": "Köln",
    "Atletico Madrid": "Atlético Madrid",
    "Athletic Club": "Athletic Bilbao",
    "Deportivo Alaves": "Alavés",
    "Cadiz": "Cádiz",
    "Almeria": "Almería",
    "Real Betis": "Betis",
    "Rayo Vallecano": "Vallecano",
    "Celta Vigo": "Celta",
    "Real Sociedad": "Sociedad",
    "Real Valladolid": "Valladolid",
    "Greuther Furth": "Greuther Fürth",
    "FC Heidenheim": "Heidenheim",
    "Darmstadt 98": "Darmstadt",
    "Hellas Verona": "Verona",
    "AC Milan": "Milan",
}

MIN_DATA_POINTS = 5
CORRELATION_TARGET = 0.85


def _build_sample_dates(seasons: list[str]) -> list[str]:
    dates = []
    for season_str in seasons:
        year = int(season_str)
        next_year = year + 1
        for template in SAMPLE_DATES_PER_SEASON:
            dates.append(template.format(year=year, next_year=next_year))
    return sorted(set(dates))


def _fetch_clubelo_snapshots(sample_dates: list[str]) -> pd.DataFrame:
    import soccerdata as sd

    elo_reader = sd.ClubElo()
    frames = []

    for date_str in sample_dates:
        try:
            df = elo_reader.read_by_date(date_str)
            df = df.reset_index()
            df["snapshot_date"] = pd.Timestamp(date_str)
            frames.append(df[["team", "elo", "snapshot_date"]])
        except Exception as exc:
            print(f"  Warning: could not fetch ClubElo for {date_str}: {exc}")

    if not frames:
        raise RuntimeError("Could not fetch any ClubElo data.")

    return pd.concat(frames, ignore_index=True)


def _build_name_mapping(
    our_teams: set[str],
    clubelo_teams: set[str],
) -> dict[str, str]:
    mapping: dict[str, str] = {}

    for our_name in our_teams:
        if our_name in clubelo_teams:
            mapping[our_name] = our_name
            continue

        if our_name in CANONICAL_TO_CLUBELO:
            ce_name = CANONICAL_TO_CLUBELO[our_name]
            if ce_name in clubelo_teams:
                mapping[our_name] = ce_name
                continue

        our_lower = our_name.lower().replace(" ", "")
        for ce_name in clubelo_teams:
            ce_lower = ce_name.lower().replace(" ", "")
            if our_lower == ce_lower:
                mapping[our_name] = ce_name
                break
            if our_lower in ce_lower or ce_lower in our_lower:
                mapping[our_name] = ce_name
                break

    return mapping


def _build_our_snapshots(
    our_history: pd.DataFrame,
    sample_dates: list[str],
) -> pd.DataFrame:
    our_history = our_history.copy()
    our_history["date"] = pd.to_datetime(our_history["date"])

    rows = []
    teams = set(our_history["home_team"].unique()) | set(our_history["away_team"].unique())

    team_series: dict[str, pd.DataFrame] = {}
    for _, row in our_history.iterrows():
        for side in ["home", "away"]:
            team = row[f"{side}_team"]
            if team not in team_series:
                team_series[team] = []
            team_series[team].append({
                "date": row["date"],
                "elo": row[f"{side}_elo_after"],
            })

    for team, entries in team_series.items():
        tdf = pd.DataFrame(entries).sort_values("date")
        for date_str in sample_dates:
            snap_date = pd.Timestamp(date_str)
            prior = tdf[tdf["date"] <= snap_date]
            if prior.empty:
                continue
            rows.append({
                "team": team,
                "snapshot_date": snap_date,
                "elo": prior.iloc[-1]["elo"],
            })

    return pd.DataFrame(rows)


def validate(
    seasons: list[str] | None = None,
    elo_path: str | None = None,
) -> dict:
    elo_path = elo_path or str(ELO_RATINGS_PATH)
    our_history = load_elo_history(elo_path)
    available_seasons = sorted(our_history["season"].astype(str).unique())
    seasons = seasons or [s for s in available_seasons if int(s) >= 2015]
    season_mask = our_history["season"].astype(str).isin(seasons)
    leagues_considered = sorted(our_history.loc[season_mask, "league"].dropna().astype(str).unique().tolist())

    print(f"Seasons for validation: {seasons}")
    print(f"Our history: {len(our_history)} match rows")

    sample_dates = _build_sample_dates(seasons)
    print(f"Sampling {len(sample_dates)} dates for comparison")

    print("\nFetching ClubElo data...")
    clubelo_df = _fetch_clubelo_snapshots(sample_dates)
    print(f"  Got {len(clubelo_df)} team-date observations from ClubElo")

    print("\nBuilding our snapshots at same dates...")
    our_snapshots = _build_our_snapshots(our_history, sample_dates)
    print(f"  Got {len(our_snapshots)} team-date observations from our system")

    our_teams = set(our_snapshots["team"].unique())
    clubelo_teams = set(clubelo_df["team"].unique())
    name_mapping = _build_name_mapping(our_teams, clubelo_teams)
    print(f"\nMatched {len(name_mapping)}/{len(our_teams)} teams")

    unmatched = our_teams - set(name_mapping.keys())
    if unmatched:
        print(f"  Unmatched teams: {sorted(unmatched)[:20]}")

    our_snapshots = our_snapshots[our_snapshots["team"].isin(name_mapping.keys())].copy()
    our_snapshots["clubelo_name"] = our_snapshots["team"].map(name_mapping)

    merged = our_snapshots.merge(
        clubelo_df,
        left_on=["clubelo_name", "snapshot_date"],
        right_on=["team", "snapshot_date"],
        suffixes=("_ours", "_clubelo"),
    )

    correlations = {}
    for team in merged["team_ours"].unique():
        team_data = merged[merged["team_ours"] == team]
        if len(team_data) < MIN_DATA_POINTS:
            continue

        corr = np.corrcoef(team_data["elo_ours"], team_data["elo_clubelo"])[0, 1]
        mad = np.mean(np.abs(team_data["elo_ours"] - team_data["elo_clubelo"]))

        correlations[team] = {
            "correlation": corr,
            "mean_abs_diff": mad,
            "n_points": len(team_data),
        }

    if not correlations:
        print("\nNo teams had enough overlapping data points for correlation.")
        return {
            "mean_correlation": float("nan"),
            "teams_evaluated": 0,
            "seasons_used": seasons,
            "leagues_considered": leagues_considered,
            "league_count": len(leagues_considered),
        }

    corr_df = pd.DataFrame(correlations).T.sort_values("correlation", ascending=False)

    mean_corr = corr_df["correlation"].mean()
    median_corr = corr_df["correlation"].median()
    mean_mad = corr_df["mean_abs_diff"].mean()

    print(f"\n{'=' * 60}")
    print("VALIDATION RESULTS")
    print(f"{'=' * 60}")
    print(f"Teams evaluated:       {len(corr_df)}")
    print(f"Mean correlation:      {mean_corr:.4f}  (target: > {CORRELATION_TARGET})")
    print(f"Median correlation:    {median_corr:.4f}")
    print(f"Mean absolute diff:    {mean_mad:.1f} Elo points")
    print(f"Teams above target:    {(corr_df['correlation'] >= CORRELATION_TARGET).sum()}/{len(corr_df)}")

    print(f"\nTop 10 (highest correlation):")
    for team, row in corr_df.head(10).iterrows():
        print(f"  {team:30s}  r={row['correlation']:.3f}  MAD={row['mean_abs_diff']:.1f}  n={row['n_points']:.0f}")

    print(f"\nBottom 10 (lowest correlation):")
    for team, row in corr_df.tail(10).iterrows():
        print(f"  {team:30s}  r={row['correlation']:.3f}  MAD={row['mean_abs_diff']:.1f}  n={row['n_points']:.0f}")

    passed = "PASS" if mean_corr >= CORRELATION_TARGET else "BELOW TARGET"
    print(f"\nOverall: {passed} (mean r = {mean_corr:.4f})")

    return {
        "mean_correlation": mean_corr,
        "median_correlation": median_corr,
        "mean_abs_diff": mean_mad,
        "teams_evaluated": len(corr_df),
        "teams_above_target": int((corr_df["correlation"] >= CORRELATION_TARGET).sum()),
        "seasons_used": seasons,
        "leagues_considered": leagues_considered,
        "league_count": len(leagues_considered),
        "details": corr_df,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="xgGaffer Engine 1 — Validate Elo ratings against ClubElo.com",
    )
    parser.add_argument("--elo-path", type=str, default=None)
    parser.add_argument("--seasons", nargs="+", default=None)

    args = parser.parse_args()

    validate(seasons=args.seasons, elo_path=args.elo_path)