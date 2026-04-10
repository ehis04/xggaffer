from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from apps.predictions.ml.features.player_workload import (
    compute_workload_features,
    PARTIAL_REST_MINUTES_THRESHOLD,
)
from apps.predictions.ml.models.availability.config import (
    INJURY_CATEGORIES,
    INJURY_CATEGORY_OTHER,
    INJURY_SPELLS_PATH,
    LEAGUES,
    LINEUP_DIR,
    PLAYER_DOBS_PATH,
    PLAYER_ID_MAPPING_PATH,
    RISK_DATASET_PATH,
    SURVIVAL_DATASET_PATH,
)
from apps.predictions.ml.models.availability.runtime import ensure_workspace_venv

logger = logging.getLogger(__name__)

PEAK_SEASON_START_MONTH = 11
PEAK_SEASON_END_MONTH = 3
PRIOR_WORKLOAD_DAYS = 30
RISK_WEEK_DAYS = 7
RISK_LOOKAHEAD_DAYS = 7
SEASON_PHASE_EARLY_END_FRACTION = 0.33
SEASON_PHASE_LATE_START_FRACTION = 0.66
WEEK_OFFSET = pd.Timedelta(days=RISK_WEEK_DAYS)
LOOKAHEAD_OFFSET = pd.Timedelta(days=RISK_LOOKAHEAD_DAYS)
PRIOR_WORKLOAD_OFFSET = pd.Timedelta(days=PRIOR_WORKLOAD_DAYS)


def load_lineups(matched_player_ids: Optional[set[int]] = None) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in sorted(LINEUP_DIR.glob("*_lineups.csv")):
        df = pd.read_csv(path)
        frames.append(df)

    if not frames:
        raise FileNotFoundError(f"No lineup CSVs in {LINEUP_DIR}")

    lineups = pd.concat(frames, ignore_index=True)
    lineups["date"] = pd.to_datetime(lineups["date"], format="mixed", errors="coerce")

    if matched_player_ids is not None:
        lineups = lineups[lineups["player_id"].isin(matched_player_ids)].copy()

    return lineups


def load_injury_spells() -> pd.DataFrame:
    df = pd.read_csv(INJURY_SPELLS_PATH)
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
    df = df.dropna(subset=["start_date", "understat_player_id"]).copy()
    df["understat_player_id"] = df["understat_player_id"].astype(int)
    return df


def load_player_dobs() -> pd.DataFrame:
    df = pd.read_csv(PLAYER_DOBS_PATH)
    df["dob"] = pd.to_datetime(df["dob"], errors="coerce")
    df = df.dropna(subset=["understat_player_id", "dob"]).copy()
    df["understat_player_id"] = df["understat_player_id"].astype(int)
    return df[["understat_player_id", "dob"]].drop_duplicates(subset=["understat_player_id"])


def _compute_age_at(reference_date: pd.Series, dob: pd.Series) -> pd.Series:
    delta_days = (reference_date - dob).dt.days
    return delta_days / 365.25


def _is_peak_season(dates: pd.Series) -> pd.Series:
    months = dates.dt.month
    return ((months >= PEAK_SEASON_START_MONTH) | (months <= PEAK_SEASON_END_MONTH)).astype(int)


def _one_hot_injury_categories(df: pd.DataFrame, source_col: str = "injury_type_category") -> pd.DataFrame:
    for category in INJURY_CATEGORIES:
        if category == INJURY_CATEGORY_OTHER:
            continue
        col_name = f"injury_type_{category.lower()}"
        df[col_name] = (df[source_col] == category).astype(int)
    return df


def _count_team_matchdays_between(
    team_match_dates: pd.DataFrame,
    team_id: int,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> int:
    team_matches = team_match_dates[team_match_dates["team_id"] == team_id]
    mask = (team_matches["date"] > start_date) & (team_matches["date"] <= end_date)
    return int(mask.sum())


def _build_team_match_dates(lineups: pd.DataFrame) -> pd.DataFrame:
    return (
        lineups[["team_id", "match_id", "date"]]
        .drop_duplicates(subset=["team_id", "match_id"])
        .sort_values(["team_id", "date"])
        .reset_index(drop=True)
    )


def _player_team_lookup(lineups: pd.DataFrame) -> pd.DataFrame:
    return (
        lineups.sort_values(["player_id", "date"])
        .groupby("player_id")
        .agg(team_id=("team_id", "last"))
        .reset_index()
    )


def _assign_team_ids_for_spells(spells: pd.DataFrame, lineups: pd.DataFrame) -> pd.Series:
    lineup_history = (
        lineups[["player_id", "date", "team_id"]]
        .dropna(subset=["player_id", "date", "team_id"])
        .sort_values(["date", "player_id"])
        .drop_duplicates(subset=["player_id", "date"], keep="last")
    )

    spell_keys = (
        spells[["understat_player_id", "start_date"]]
        .reset_index()
        .rename(columns={"understat_player_id": "player_id"})
    )

    left_sorted = spell_keys.sort_values(["start_date", "player_id"])

    merged = pd.merge_asof(
        left_sorted,
        lineup_history,
        by="player_id",
        left_on="start_date",
        right_on="date",
        direction="backward",
        allow_exact_matches=True,
    )

    missing_mask = merged["team_id"].isna()
    if missing_mask.any():
        fallback = pd.merge_asof(
            merged.loc[missing_mask, ["index", "player_id", "start_date"]].sort_values(
                ["start_date", "player_id"]
            ),
            lineup_history,
            by="player_id",
            left_on="start_date",
            right_on="date",
            direction="forward",
            allow_exact_matches=True,
        )
        fallback_team_ids = fallback.set_index("index")["team_id"]
        merged.loc[missing_mask, "team_id"] = merged.loc[missing_mask, "index"].map(
            fallback_team_ids
        )

    return merged.set_index("index")["team_id"].reindex(spells.index)


def build_survival_dataset(
    lineups: Optional[pd.DataFrame] = None,
    output_path: Path = SURVIVAL_DATASET_PATH,
) -> pd.DataFrame:
    spells = load_injury_spells()
    dobs = load_player_dobs()

    mapping = pd.read_csv(PLAYER_ID_MAPPING_PATH)
    matched_player_ids = set(
        mapping[mapping["understat_player_id"].notna()]["understat_player_id"].astype(int)
    )

    if lineups is None:
        lineups = load_lineups(matched_player_ids=matched_player_ids)

    logger.info("Computing workload features for %d lineup rows", len(lineups))
    lineups_with_workload = compute_workload_features(lineups)

    team_match_dates = _build_team_match_dates(lineups)
    spells["team_id"] = _assign_team_ids_for_spells(spells, lineups)

    player_lineup_span = (
        lineups.groupby("player_id")["date"]
        .agg(lineup_min="min", lineup_max="max")
        .reset_index()
        .rename(columns={"player_id": "understat_player_id"})
    )
    spells = spells.merge(player_lineup_span, on="understat_player_id", how="left")
    spells = spells[
        spells["team_id"].notna()
        & spells["lineup_min"].notna()
        & (spells["start_date"] >= spells["lineup_min"])
        & (spells["start_date"] <= spells["lineup_max"])
    ].copy()

    spells = spells.merge(dobs, on="understat_player_id", how="left")
    spells["player_age"] = _compute_age_at(spells["start_date"], spells["dob"])

    spells = spells.sort_values(["understat_player_id", "start_date"]).reset_index(drop=True)
    spells["prior_end_date"] = spells.groupby("understat_player_id")["end_date"].shift(1)
    spells["days_since_last_injury"] = (spells["start_date"] - spells["prior_end_date"]).dt.days

    censor_date = spells["start_date"].max() + pd.Timedelta(days=1)

    durations: list[int] = []
    events: list[int] = []
    matches_30d: list[int] = []
    minutes_30d: list[int] = []

    workload_indexed = lineups_with_workload.set_index(["player_id", "date"]).sort_index()

    for spell in spells.itertuples(index=False):
        player_id = spell.understat_player_id
        start_date = spell.start_date
        end_date = spell.end_date
        team_id = spell.team_id
        observed_end = spell.lineup_max

        if (
            pd.notna(end_date)
            and not bool(spell.is_open_spell)
            and pd.notna(observed_end)
            and end_date <= observed_end
        ):
            duration = _count_team_matchdays_between(
                team_match_dates, team_id, start_date, end_date
            )
            event = 1
        else:
            duration = _count_team_matchdays_between(
                team_match_dates,
                team_id,
                start_date,
                min(censor_date, observed_end) if pd.notna(observed_end) else censor_date,
            )
            event = 0

        durations.append(max(duration, 1))
        events.append(event)

        prior_window_start = start_date - PRIOR_WORKLOAD_OFFSET
        try:
            player_history = workload_indexed.loc[player_id]
        except KeyError:
            matches_30d.append(0)
            minutes_30d.append(0)
            continue

        prior_mask = (player_history.index > prior_window_start) & (
            player_history.index < start_date
        )
        prior_rows = player_history[prior_mask]
        matches_30d.append(int(len(prior_rows)))
        minutes_30d.append(int(prior_rows["minutes_played"].sum()))

    spells["duration"] = durations
    spells["event"] = events
    spells["matches_in_prior_30d"] = matches_30d
    spells["minutes_in_prior_30d"] = minutes_30d
    spells["is_peak_season"] = _is_peak_season(spells["start_date"])

    spells = _one_hot_injury_categories(spells)

    spells["season"] = spells["start_date"].apply(_calendar_to_football_season)

    output_columns = [
        "understat_player_id",
        "player_name",
        "team_id",
        "season",
        "start_date",
        "end_date",
        "is_open_spell",
        "duration",
        "event",
        "injury_type_category",
        "player_age",
        "days_since_last_injury",
        "matches_in_prior_30d",
        "minutes_in_prior_30d",
        "is_peak_season",
    ]
    one_hot_cols = [
        f"injury_type_{cat.lower()}"
        for cat in INJURY_CATEGORIES
        if cat != INJURY_CATEGORY_OTHER
    ]
    output_columns.extend(one_hot_cols)

    output = spells[output_columns].copy()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False)
    logger.info("Saved survival dataset: %s (%d rows)", output_path, len(output))

    return output


def _calendar_to_football_season(date: pd.Timestamp) -> int:
    if pd.isna(date):
        return -1
    return date.year if date.month >= 7 else date.year - 1


def build_risk_dataset(
    lineups: Optional[pd.DataFrame] = None,
    output_path: Path = RISK_DATASET_PATH,
) -> pd.DataFrame:
    spells = load_injury_spells()
    dobs = load_player_dobs()

    mapping = pd.read_csv(PLAYER_ID_MAPPING_PATH)
    matched_player_ids = set(
        mapping[mapping["understat_player_id"].notna()]["understat_player_id"].astype(int)
    )

    if lineups is None:
        lineups = load_lineups(matched_player_ids=matched_player_ids)

    logger.info("Computing workload features for %d lineup rows", len(lineups))
    lineups_with_workload = compute_workload_features(lineups)

    spells_indexed = (
        spells[["understat_player_id", "start_date", "end_date", "is_open_spell"]]
        .sort_values(["understat_player_id", "start_date"])
    )
    spells_by_player: dict[int, pd.DataFrame] = {
        player_id: group.reset_index(drop=True)
        for player_id, group in spells_indexed.groupby("understat_player_id")
    }

    rows: list[dict] = []

    player_season_groups = lineups_with_workload.groupby(["player_id", "season", "league"])

    logger.info("Generating player-week rows for %d player-seasons", len(player_season_groups))

    for (player_id, season, league), group in player_season_groups:
        season_dates = group["date"]
        season_start = season_dates.min().normalize()
        season_end = season_dates.max().normalize()

        weeks = pd.date_range(start=season_start, end=season_end, freq="W-MON")
        if len(weeks) == 0:
            continue

        player_spells = spells_by_player.get(player_id)

        for week_start in weeks:
            lookahead_end = week_start + LOOKAHEAD_OFFSET

            if _player_injured_on_date(player_spells, week_start):
                continue

            workload_row = _latest_workload_before(group, week_start)
            if workload_row is None:
                continue

            injury_label = _injury_starts_in_window(
                player_spells, week_start, lookahead_end
            )

            row = {
                "understat_player_id": int(player_id),
                "league": league,
                "season": int(season),
                "week_start": week_start,
                "minutes_last_7d": workload_row.get("minutes_last_7d", 0),
                "minutes_last_14d": workload_row.get("minutes_last_14d", 0),
                "minutes_last_30d": workload_row.get("minutes_last_30d", 0),
                "matches_last_7d": workload_row.get("matches_last_7d", 0),
                "matches_last_14d": workload_row.get("matches_last_14d", 0),
                "matches_last_30d": workload_row.get("matches_last_30d", 0),
                "consecutive_starts": workload_row.get("consecutive_starts", 0),
                "days_since_last_rest": workload_row.get("days_since_last_rest", np.nan),
                "injury_next_7d": int(injury_label),
            }
            rows.append(row)

    risk_df = pd.DataFrame(rows)

    risk_df = risk_df.merge(dobs, on="understat_player_id", how="left")
    risk_df["age"] = _compute_age_at(risk_df["week_start"], risk_df["dob"])
    risk_df = risk_df.drop(columns=["dob"])

    risk_df = _add_prior_injury_features(risk_df, spells_by_player)
    risk_df = _add_season_phase(risk_df)
    risk_df = _add_engineered_risk_features(risk_df)

    output_columns = [
        "understat_player_id",
        "league",
        "season",
        "week_start",
        "minutes_last_7d",
        "minutes_last_14d",
        "minutes_last_30d",
        "matches_last_7d",
        "matches_last_14d",
        "matches_last_30d",
        "consecutive_starts",
        "days_since_last_rest",
        "age",
        "prior_injuries_count",
        "days_since_last_injury",
        "season_phase_mid",
        "season_phase_late",
        "acwr_7_28",
        "minutes_per_match_30d",
        "workload_zscore_30d",
        "recent_match_density",
        "cumulative_workload_per_week",
        "injury_next_7d",
    ]
    output = risk_df[output_columns].copy()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False)
    logger.info("Saved risk dataset: %s (%d rows)", output_path, len(output))

    return output


def _player_injured_on_date(
    player_spells: Optional[pd.DataFrame],
    date: pd.Timestamp,
) -> bool:
    if player_spells is None or player_spells.empty:
        return False

    starts = player_spells["start_date"]
    ends = player_spells["end_date"].fillna(date + pd.Timedelta(days=1))

    return bool(((starts <= date) & (ends >= date)).any())


def _injury_starts_in_window(
    player_spells: Optional[pd.DataFrame],
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
) -> bool:
    if player_spells is None or player_spells.empty:
        return False

    starts = player_spells["start_date"]
    mask = (starts > window_start) & (starts <= window_end)
    return bool(mask.any())


def _latest_workload_before(
    player_group: pd.DataFrame,
    cutoff: pd.Timestamp,
) -> Optional[pd.Series]:
    prior = player_group[player_group["date"] < cutoff]
    if prior.empty:
        return None
    return prior.iloc[-1]


def _add_prior_injury_features(
    risk_df: pd.DataFrame,
    spells_by_player: dict[int, pd.DataFrame],
) -> pd.DataFrame:
    prior_counts: list[int] = []
    days_since: list[float] = []

    for row in risk_df.itertuples(index=False):
        player_id = row.understat_player_id
        week_start = row.week_start

        player_spells = spells_by_player.get(player_id)
        if player_spells is None or player_spells.empty:
            prior_counts.append(0)
            days_since.append(np.nan)
            continue

        prior_mask = player_spells["start_date"] < week_start
        prior_spells = player_spells[prior_mask]
        prior_counts.append(int(len(prior_spells)))

        if prior_spells.empty:
            days_since.append(np.nan)
        else:
            last_end = prior_spells["end_date"].max()
            if pd.isna(last_end):
                days_since.append(np.nan)
            else:
                days_since.append(float((week_start - last_end).days))

    risk_df["prior_injuries_count"] = prior_counts
    risk_df["days_since_last_injury"] = days_since
    return risk_df


def _add_season_phase(risk_df: pd.DataFrame) -> pd.DataFrame:
    risk_df = risk_df.sort_values(["understat_player_id", "season", "week_start"]).copy()

    grouped = risk_df.groupby(["understat_player_id", "season"])
    season_min = grouped["week_start"].transform("min")
    season_max = grouped["week_start"].transform("max")
    season_span = (season_max - season_min).dt.days.replace(0, 1)
    progress = (risk_df["week_start"] - season_min).dt.days / season_span

    risk_df["season_phase_mid"] = (
        (progress >= SEASON_PHASE_EARLY_END_FRACTION)
        & (progress < SEASON_PHASE_LATE_START_FRACTION)
    ).astype(int)
    risk_df["season_phase_late"] = (progress >= SEASON_PHASE_LATE_START_FRACTION).astype(int)

    return risk_df


def _add_engineered_risk_features(risk_df: pd.DataFrame) -> pd.DataFrame:
    risk_df = risk_df.copy()

    chronic_weekly_baseline = risk_df["minutes_last_30d"].clip(lower=1) / 4.0
    risk_df["acwr_7_28"] = risk_df["minutes_last_7d"] / chronic_weekly_baseline

    risk_df["minutes_per_match_30d"] = np.where(
        risk_df["matches_last_30d"] > 0,
        risk_df["minutes_last_30d"] / risk_df["matches_last_30d"].clip(lower=1),
        0.0,
    )

    risk_df["recent_match_density"] = risk_df["matches_last_14d"] / 2.0

    risk_df = risk_df.sort_values(["understat_player_id", "week_start"])
    grouped = risk_df.groupby("understat_player_id")["minutes_last_7d"]
    rolling_mean = grouped.transform(lambda s: s.shift(1).rolling(4, min_periods=2).mean())
    rolling_std = grouped.transform(lambda s: s.shift(1).rolling(4, min_periods=2).std())
    risk_df["workload_zscore_30d"] = (
        (risk_df["minutes_last_7d"] - rolling_mean) / rolling_std.replace(0, np.nan)
    )

    risk_df = risk_df.sort_values(["understat_player_id", "season", "week_start"])
    season_grouped = risk_df.groupby(["understat_player_id", "season"])
    season_week_index = season_grouped.cumcount() + 1
    season_cumulative_minutes = season_grouped["minutes_last_7d"].cumsum()
    risk_df["cumulative_workload_per_week"] = season_cumulative_minutes / season_week_index

    return risk_df


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    mapping = pd.read_csv(PLAYER_ID_MAPPING_PATH)
    matched_player_ids = set(
        mapping[mapping["understat_player_id"].notna()]["understat_player_id"].astype(int)
    )

    logger.info("Loading lineups (filtered to %d matched players)", len(matched_player_ids))
    lineups = load_lineups(matched_player_ids=matched_player_ids)
    logger.info("Loaded %d lineup rows", len(lineups))

    survival_df = build_survival_dataset(lineups=lineups)
    print()
    print("=== SURVIVAL DATASET ===")
    print(f"Rows: {len(survival_df)}")
    print(f"Events (returned): {survival_df['event'].sum()}")
    print(f"Censored (open): {(survival_df['event'] == 0).sum()}")
    print(f"Mean duration (matchdays): {survival_df['duration'].mean():.1f}")
    print(f"Median duration: {survival_df['duration'].median():.1f}")
    print()
    print("Duration by category:")
    print(survival_df.groupby("injury_type_category")["duration"].agg(["count", "mean", "median"]).round(1).to_string())

    risk_df = build_risk_dataset(lineups=lineups)
    print()
    print("=== RISK DATASET ===")
    print(f"Rows: {len(risk_df)}")
    print(f"Injury rate: {risk_df['injury_next_7d'].mean():.3%}")
    print(f"Total positive labels: {risk_df['injury_next_7d'].sum()}")


if __name__ == "__main__":
    ensure_workspace_venv("apps.predictions.ml.models.availability.prepare_data")
    main()