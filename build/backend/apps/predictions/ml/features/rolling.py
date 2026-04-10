from __future__ import annotations

import numpy as np
import pandas as pd

from ml.models.match_outcome.config import DATA_DIR

PROCESSED_MATCHES_DIR = DATA_DIR / "processed" / "matches"
LEGACY_MATCHES_DIR = DATA_DIR / "raw" / "understat" / "matches"
MERGED_MATCHES_FILE = DATA_DIR / "processed" / "matches" / "merged" / "all_leagues_all_seasons_matches_merged.csv"
LEGACY_MERGED_MATCHES_FILE = DATA_DIR / "raw" / "understat" / "merged" / "all_leagues_all_seasons_matches.csv"

SOURCE_PREFERENCE = ["understat", "sofascore"]

ROLLING_WINDOWS = [5, 10, 20]
EWM_HALF_LIVES = [5, 10, 20]
SLOPE_WINDOW = 10
MIN_SLOPE_PERIODS = 2
SCHEDULE_WINDOWS_DAYS = [14, 28]

ROLLING_STATS = [
    "xg", "xga", "xa", "shots", "shots_conceded",
    "key_passes", "points", "xpts",
]

DIFF_STATS = ["xg", "xga", "xa", "shots", "points", "xpts"]

ALL_LEAGUES = ["EPL", "La_Liga", "Bundesliga", "Serie_A", "Ligue_1"]
ALL_SEASONS = [str(y) for y in range(2014, 2026)]

MATCH_LOAD_COLUMNS = [
    "match_id", "date", "home_team", "away_team",
    "home_goals", "away_goals", "home_xg", "away_xg",
    "home_xa", "away_xa", "home_shots", "away_shots",
    "home_key_passes", "away_key_passes", "home_xpts", "away_xpts",
    "league", "season",
]


def _normalize_season(s: str) -> str:
    """Convert sofascore XXYY codes (e.g. '2425') to start-year format (e.g. '2024')."""
    try:
        v = int(s)
        if v > 2025:
            return str(2000 + int(str(v)[:2]))
    except (ValueError, IndexError):
        pass
    return s


def _source_priority(path) -> int:
    name = path.stem
    for i, src in enumerate(SOURCE_PREFERENCE):
        if f"_{src}_" in name:
            return i
    return len(SOURCE_PREFERENCE)


def _row_source_priority(series: pd.Series) -> pd.Series:
    source_order = {source: index for index, source in enumerate(SOURCE_PREFERENCE)}
    return series.map(lambda value: source_order.get(str(value), len(SOURCE_PREFERENCE)))


try:
    from data_collection.config.team_name_mappings import to_canonical as _raw_to_canonical

    def _canonicalize_team(name: str) -> str:
        try:
            return _raw_to_canonical(name, "understat")
        except KeyError:
            return name
except ImportError:
    def _canonicalize_team(name: str) -> str:
        return name



def load_match_history(
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
) -> pd.DataFrame:
    leagues = leagues or ALL_LEAGUES
    seasons = [str(s) for s in (seasons or ALL_SEASONS)]

    dfs: list[pd.DataFrame] = []

    loaded_combos: set[tuple[str, str]] = set()

    # Prefer season-scoped canonical files first since they are refreshed more often
    # than the historical merged export.
    for league in leagues:
        for season in seasons:
            season_dir = PROCESSED_MATCHES_DIR / season
            found = False

            if season_dir.exists():
                candidates = sorted(
                    season_dir.glob(f"matches_*_{league}_{season}_canonical.csv"),
                    key=_source_priority,
                )
                if candidates:
                    chosen = candidates[0]
                    df = pd.read_csv(chosen)
                    if "source_match_id" in df.columns and "match_id" not in df.columns:
                        df = df.rename(columns={"source_match_id": "match_id"})
                    dfs.append(df)
                    loaded_combos.add((league, season))
                    found = True

            if not found:
                legacy_path = LEGACY_MATCHES_DIR / f"{league.lower()}_{season}_matches.csv"
                if legacy_path.exists():
                    dfs.append(pd.read_csv(legacy_path))
                    loaded_combos.add((league, season))

    # Use merged data only as a backfill for league/season pairs with no
    # season-level files.
    if MERGED_MATCHES_FILE.exists() or LEGACY_MERGED_MATCHES_FILE.exists():
        merged_path = MERGED_MATCHES_FILE if MERGED_MATCHES_FILE.exists() else LEGACY_MERGED_MATCHES_FILE
        merged = pd.read_csv(merged_path, low_memory=False)
        if "source_match_id" in merged.columns and "match_id" not in merged.columns:
            merged = merged.rename(columns={"source_match_id": "match_id"})
        merged["season"] = merged["season"].astype(str)
        if "source" in merged.columns:
            merged = merged.assign(_source_priority=_row_source_priority(merged["source"]))
            dedupe_columns = [
                column
                for column in ["league", "season", "date", "home_team", "away_team"]
                if column in merged.columns
            ]
            if dedupe_columns:
                merged = (
                    merged
                    .sort_values(["_source_priority", *dedupe_columns], kind="stable")
                    .drop_duplicates(subset=dedupe_columns, keep="first")
                    .drop(columns=["_source_priority"])
                )

        missing_combos = [
            (league, season)
            for league in leagues
            for season in seasons
            if (league, season) not in loaded_combos
        ]

        for league, season in missing_combos:
            subset = merged[
                (merged["league"] == league)
                & (merged["season"] == season)
            ]
            if not subset.empty:
                dfs.append(subset)
                loaded_combos.add((league, season))

    if not dfs:
        raise FileNotFoundError(
            f"No match files found. Checked: {MERGED_MATCHES_FILE}, {LEGACY_MERGED_MATCHES_FILE}, "
            f"{PROCESSED_MATCHES_DIR}, {LEGACY_MATCHES_DIR}"
        )

    matches = pd.concat(dfs, ignore_index=True)
    matches["date"] = pd.to_datetime(matches["date"], format="mixed", dayfirst=False).dt.normalize()
    matches["season"] = matches["season"].astype(str).map(_normalize_season)
    matches["home_team"] = matches["home_team"].map(_canonicalize_team)
    matches["away_team"] = matches["away_team"].map(_canonicalize_team)

    available = [c for c in MATCH_LOAD_COLUMNS if c in matches.columns]
    matches = matches[available]

    return matches.sort_values("date").reset_index(drop=True)



def to_team_match_rows(matches_df: pd.DataFrame) -> pd.DataFrame:
    home = pd.DataFrame({
        "team": matches_df["home_team"],
        "opponent": matches_df["away_team"],
        "date": matches_df["date"],
        "match_id": matches_df["match_id"],
        "is_home": True,
        "xg": matches_df["home_xg"],
        "xga": matches_df["away_xg"],
        "xa": matches_df["home_xa"],
        "shots": matches_df["home_shots"],
        "shots_conceded": matches_df["away_shots"],
        "key_passes": matches_df["home_key_passes"],
        "goals_for": matches_df["home_goals"],
        "goals_against": matches_df["away_goals"],
        "xpts": matches_df["home_xpts"],
        "league": matches_df["league"],
        "season": matches_df["season"],
    })

    away = pd.DataFrame({
        "team": matches_df["away_team"],
        "opponent": matches_df["home_team"],
        "date": matches_df["date"],
        "match_id": matches_df["match_id"],
        "is_home": False,
        "xg": matches_df["away_xg"],
        "xga": matches_df["home_xg"],
        "xa": matches_df["away_xa"],
        "shots": matches_df["away_shots"],
        "shots_conceded": matches_df["home_shots"],
        "key_passes": matches_df["away_key_passes"],
        "goals_for": matches_df["away_goals"],
        "goals_against": matches_df["home_goals"],
        "xpts": matches_df["away_xpts"],
        "league": matches_df["league"],
        "season": matches_df["season"],
    })

    combined = pd.concat([home, away], ignore_index=True)

    combined["points"] = np.where(
        combined["goals_for"] > combined["goals_against"], 3,
        np.where(combined["goals_for"] == combined["goals_against"], 1, 0),
    )
    combined["xgd"] = combined["xg"] - combined["xga"]

    return combined.sort_values(["team", "date"]).reset_index(drop=True)



def _xgd_slope(values: np.ndarray) -> float:
    n = len(values)
    if n < MIN_SLOPE_PERIODS:
        return 0.0
    x = np.arange(n, dtype=float)
    x_mean = x.mean()
    y_mean = values.mean()
    denom = np.sum((x - x_mean) ** 2)
    if denom == 0:
        return 0.0
    return float(np.sum((x - x_mean) * (values - y_mean)) / denom)



def compute_team_rolling_features(
    team_matches: pd.DataFrame,
    as_of: pd.Timestamp,
    windows: list[int] | None = None,
) -> dict:
    windows = windows or ROLLING_WINDOWS

    prior = team_matches[team_matches["date"] < as_of].sort_values("date")

    if prior.empty:
        return {}

    features: dict[str, float] = {}

    for w in windows:
        tail = prior.tail(w)
        for stat in ROLLING_STATS:
            if stat in tail.columns:
                features[f"rolling_{stat}_{w}"] = float(tail[stat].mean())

    for h in EWM_HALF_LIVES:
        if "xg" in prior.columns and len(prior) >= 1:
            ewm_series = prior["xg"].ewm(halflife=h, min_periods=1).mean()
            features[f"ewm_xg_{h}"] = float(ewm_series.iloc[-1])

    if "points" in prior.columns:
        wins_tail = prior.tail(5)
        features["rolling_wins_5"] = int((wins_tail["points"] == 3).sum())

    if "xgd" in prior.columns and len(prior) >= MIN_SLOPE_PERIODS:
        slope_data = prior["xgd"].tail(SLOPE_WINDOW).values
        features["xgd_slope"] = _xgd_slope(slope_data)
    else:
        features["xgd_slope"] = 0.0

    if len(prior) >= 1:
        last_date = prior["date"].iloc[-1]
        features["days_rest"] = (as_of - last_date).total_seconds() / 86400.0
    else:
        features["days_rest"] = np.nan

    for days in SCHEDULE_WINDOWS_DAYS:
        cutoff = as_of - pd.Timedelta(days=days)
        features[f"matches_last_{days}d"] = int((prior["date"] >= cutoff).sum())

    return features


def build_features(
    match_id: int,
    home_team: str,
    away_team: str,
    kickoff: pd.Timestamp,
    all_matches: pd.DataFrame,
    all_team_matches: pd.DataFrame,
) -> dict:
    home_history = all_team_matches[all_team_matches["team"] == home_team]
    away_history = all_team_matches[all_team_matches["team"] == away_team]

    home_feats = compute_team_rolling_features(home_history, kickoff)
    away_feats = compute_team_rolling_features(away_history, kickoff)

    row: dict[str, object] = {"match_id": match_id, "is_home": 1}

    for key, value in home_feats.items():
        row[f"home_{key}"] = value
    for key, value in away_feats.items():
        row[f"away_{key}"] = value

    for stat in DIFF_STATS:
        for w in ROLLING_WINDOWS:
            home_key = f"home_rolling_{stat}_{w}"
            away_key = f"away_rolling_{stat}_{w}"
            if home_key in row and away_key in row:
                row[f"{stat}_diff_{w}"] = row[home_key] - row[away_key]

    return row



def _compute_rolling_batch(team_rows: pd.DataFrame) -> pd.DataFrame:
    grouped = team_rows.groupby("team", sort=False)

    feature_frames: list[pd.Series] = []

    for stat in ROLLING_STATS:
        if stat not in team_rows.columns:
            continue
        for w in ROLLING_WINDOWS:
            col_name = f"rolling_{stat}_{w}"
            rolled = grouped[stat].transform(
                lambda s: s.rolling(w, min_periods=1).mean().shift(1)
            )
            feature_frames.append(rolled.rename(col_name))

    for h in EWM_HALF_LIVES:
        if "xg" not in team_rows.columns:
            continue
        col_name = f"ewm_xg_{h}"
        ewm_vals = grouped["xg"].transform(
            lambda s: s.ewm(halflife=h, min_periods=1).mean().shift(1)
        )
        feature_frames.append(ewm_vals.rename(col_name))

    if "points" in team_rows.columns:
        wins_col = grouped["points"].transform(
            lambda s: (s == 3).astype(float).rolling(5, min_periods=1).sum().shift(1)
        )
        feature_frames.append(wins_col.rename("rolling_wins_5"))

    if "xgd" in team_rows.columns:
        slope_col = grouped["xgd"].transform(
            lambda s: s.rolling(SLOPE_WINDOW, min_periods=MIN_SLOPE_PERIODS)
            .apply(_xgd_slope, raw=True)
            .shift(1)
        )
        feature_frames.append(slope_col.rename("xgd_slope"))

    return pd.concat(feature_frames, axis=1)


def _compute_schedule_batch(team_rows: pd.DataFrame) -> pd.DataFrame:
    date_values = team_rows["date"].values
    team_values = team_rows["team"].values

    days_rest = np.full(len(team_rows), np.nan)
    schedule_arrays = {
        d: np.zeros(len(team_rows), dtype=int) for d in SCHEDULE_WINDOWS_DAYS
    }

    grouped = team_rows.groupby("team", sort=False)

    for _, group_index in grouped.groups.items():
        idx = group_index.values if hasattr(group_index, "values") else np.array(group_index)
        team_dates = date_values[idx]

        for pos in range(len(idx)):
            if pos > 0:
                delta = (team_dates[pos] - team_dates[pos - 1]) / np.timedelta64(1, "D")
                days_rest[idx[pos]] = float(delta)

            for d in SCHEDULE_WINDOWS_DAYS:
                cutoff = team_dates[pos] - np.timedelta64(d, "D")
                schedule_arrays[d][idx[pos]] = int(np.sum(team_dates[:pos] >= cutoff))

    result = pd.DataFrame({"days_rest": days_rest}, index=team_rows.index)
    for d in SCHEDULE_WINDOWS_DAYS:
        result[f"matches_last_{d}d"] = schedule_arrays[d]

    return result


def build_all_features(
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
) -> pd.DataFrame:
    matches = load_match_history(leagues, seasons)
    team_rows = to_team_match_rows(matches)

    rolling_feats = _compute_rolling_batch(team_rows)
    schedule_feats = _compute_schedule_batch(team_rows)

    team_features = pd.concat(
        [team_rows[["match_id", "is_home"]], rolling_feats, schedule_feats],
        axis=1,
    )

    feat_cols = [
        c for c in team_features.columns if c not in ("match_id", "is_home")
    ]

    home_feats = (
        team_features[team_features["is_home"] == True]
        .set_index("match_id")[feat_cols]
        .add_prefix("home_")
    )
    away_feats = (
        team_features[team_features["is_home"] == False]
        .set_index("match_id")[feat_cols]
        .add_prefix("away_")
    )

    result = matches.set_index("match_id").join(home_feats).join(away_feats)

    diff_cols: dict[str, pd.Series] = {}
    for stat in DIFF_STATS:
        for w in ROLLING_WINDOWS:
            home_col = f"home_rolling_{stat}_{w}"
            away_col = f"away_rolling_{stat}_{w}"
            if home_col in result.columns and away_col in result.columns:
                diff_cols[f"{stat}_diff_{w}"] = result[home_col] - result[away_col]

    if diff_cols:
        result = pd.concat([result, pd.DataFrame(diff_cols, index=result.index)], axis=1)

    result["is_home"] = 1

    return result.reset_index()