from __future__ import annotations

import logging
import math
import warnings

import numpy as np
import pandas as pd
from statsbombpy import sb

from apps.predictions.ml.models.tactical.config import (
    INCOMPLETE_PASS_OUTCOMES,
    MAX_GOAL_DIFF_CLIP,
    PASS_EVENTS_PATH,
    PASS_EVENT_TYPE,
    PROCESSED_DIR,
    STATSBOMB_CHECKPOINT_DIR,
    STATSBOMB_COMPETITIONS,
    compute_zone_id,
)


warnings.filterwarnings("ignore", message="credentials were not supplied")

logger = logging.getLogger(__name__)

OUTPUT_COLUMNS = [
    "match_id",
    "competition_id",
    "competition_name",
    "season_id",
    "season_name",
    "team_id",
    "team_name",
    "player_id",
    "player_name",
    "minute",
    "second",
    "match_period",
    "start_x",
    "start_y",
    "end_x",
    "end_y",
    "zone_id",
    "zone_col",
    "zone_row",
    "end_zone_id",
    "pass_length",
    "pass_angle",
    "is_forward_pass",
    "under_pressure",
    "pass_height",
    "body_part",
    "pass_technique",
    "pass_completed",
    "home_team",
    "away_team",
    "team_side",
    "home_score_at_time",
    "away_score_at_time",
    "game_state_goal_diff",
]


def list_competition_seasons() -> list[dict]:
    comps = sb.competitions()
    selected_ids = {c["competition_id"] for c in STATSBOMB_COMPETITIONS}
    filtered = comps[comps["competition_id"].isin(selected_ids)].copy()
    filtered = filtered.sort_values(["competition_id", "season_id"])
    return filtered[
        ["competition_id", "competition_name", "season_id", "season_name"]
    ].to_dict("records")


def get_match_ids(competition_id: int, season_id: int) -> pd.DataFrame:
    matches = sb.matches(competition_id=competition_id, season_id=season_id)
    return matches[["match_id", "home_team", "away_team", "home_score", "away_score"]].copy()


def _safe_first(value, default=None):
    if isinstance(value, (list, tuple)) and len(value) > 0:
        return value[0]
    return default


def _safe_second(value, default=None):
    if isinstance(value, (list, tuple)) and len(value) > 1:
        return value[1]
    return default


def _compute_pass_angle(start_x: float, start_y: float, end_x: float, end_y: float) -> float:
    dx = end_x - start_x
    dy = end_y - start_y
    return math.atan2(dy, dx)


def _compute_pass_length(start_x: float, start_y: float, end_x: float, end_y: float) -> float:
    dx = end_x - start_x
    dy = end_y - start_y
    return math.sqrt(dx * dx + dy * dy)


def _build_running_score(events: pd.DataFrame, home_team: str, away_team: str) -> pd.DataFrame:
    sorted_events = events.sort_values(["period", "minute", "second"], kind="stable").copy()
    sorted_events["_row"] = np.arange(len(sorted_events))

    is_goal = (sorted_events["type"] == "Shot") & (
        sorted_events.get("shot_outcome") == "Goal"
    )
    sorted_events["_home_goal"] = (is_goal & (sorted_events["team"] == home_team)).astype(int)
    sorted_events["_away_goal"] = (is_goal & (sorted_events["team"] == away_team)).astype(int)
    sorted_events["home_score_at_time"] = sorted_events["_home_goal"].cumsum() - sorted_events["_home_goal"]
    sorted_events["away_score_at_time"] = sorted_events["_away_goal"].cumsum() - sorted_events["_away_goal"]

    sorted_events = sorted_events.drop(columns=["_home_goal", "_away_goal"])
    return sorted_events


def extract_pass_rows_for_match(
    match_id: int,
    competition_id: int,
    competition_name: str,
    season_id: int,
    season_name: str,
    home_team: str,
    away_team: str,
) -> pd.DataFrame:
    events = sb.events(match_id=match_id)
    if events is None or events.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    if "shot_outcome" not in events.columns:
        events["shot_outcome"] = np.nan

    events = _build_running_score(events, home_team, away_team)

    passes = events[events["type"] == PASS_EVENT_TYPE].copy()
    if passes.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    for col in [
        "location",
        "pass_end_location",
        "pass_outcome",
        "pass_height",
        "pass_body_part",
        "pass_technique",
        "under_pressure",
        "player",
        "player_id",
        "team",
        "team_id",
    ]:
        if col not in passes.columns:
            passes[col] = np.nan

    rows = []
    for _, ev in passes.iterrows():
        start = ev["location"]
        end = ev["pass_end_location"]
        start_x = _safe_first(start)
        start_y = _safe_second(start)
        end_x = _safe_first(end)
        end_y = _safe_second(end)
        if start_x is None or start_y is None or end_x is None or end_y is None:
            continue

        zone_id = compute_zone_id(start_x, start_y)
        end_zone_id = compute_zone_id(end_x, end_y)
        zone_col = zone_id // 4
        zone_row = zone_id % 4
        pass_length = _compute_pass_length(start_x, start_y, end_x, end_y)
        pass_angle = _compute_pass_angle(start_x, start_y, end_x, end_y)
        is_forward = end_x > start_x

        outcome = ev["pass_outcome"]
        if pd.isna(outcome):
            completed = 1
        elif outcome in INCOMPLETE_PASS_OUTCOMES:
            completed = 0
        else:
            completed = 0

        team_name = ev["team"]
        team_side = "home" if team_name == home_team else "away"

        home_score = int(ev.get("home_score_at_time", 0) or 0)
        away_score = int(ev.get("away_score_at_time", 0) or 0)
        if team_side == "home":
            goal_diff = home_score - away_score
        else:
            goal_diff = away_score - home_score
        if goal_diff > MAX_GOAL_DIFF_CLIP:
            goal_diff = MAX_GOAL_DIFF_CLIP
        elif goal_diff < -MAX_GOAL_DIFF_CLIP:
            goal_diff = -MAX_GOAL_DIFF_CLIP

        under_pressure = bool(ev["under_pressure"]) if pd.notna(ev["under_pressure"]) else False

        rows.append(
            {
                "match_id": match_id,
                "competition_id": competition_id,
                "competition_name": competition_name,
                "season_id": season_id,
                "season_name": season_name,
                "team_id": ev.get("team_id"),
                "team_name": team_name,
                "player_id": ev.get("player_id"),
                "player_name": ev.get("player"),
                "minute": ev.get("minute"),
                "second": ev.get("second"),
                "match_period": ev.get("period"),
                "start_x": start_x,
                "start_y": start_y,
                "end_x": end_x,
                "end_y": end_y,
                "zone_id": zone_id,
                "zone_col": zone_col,
                "zone_row": zone_row,
                "end_zone_id": end_zone_id,
                "pass_length": pass_length,
                "pass_angle": pass_angle,
                "is_forward_pass": is_forward,
                "under_pressure": under_pressure,
                "pass_height": ev.get("pass_height"),
                "body_part": ev.get("pass_body_part"),
                "pass_technique": ev.get("pass_technique"),
                "pass_completed": completed,
                "home_team": home_team,
                "away_team": away_team,
                "team_side": team_side,
                "home_score_at_time": home_score,
                "away_score_at_time": away_score,
                "game_state_goal_diff": goal_diff,
            }
        )

    if not rows:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def collect_match_with_checkpoint(
    match_id: int,
    competition_id: int,
    competition_name: str,
    season_id: int,
    season_name: str,
    home_team: str,
    away_team: str,
) -> pd.DataFrame:
    checkpoint_path = STATSBOMB_CHECKPOINT_DIR / f"match_{match_id}.csv"
    if checkpoint_path.exists():
        return pd.read_csv(checkpoint_path)

    df = extract_pass_rows_for_match(
        match_id=match_id,
        competition_id=competition_id,
        competition_name=competition_name,
        season_id=season_id,
        season_name=season_name,
        home_team=home_team,
        away_team=away_team,
    )
    df.to_csv(checkpoint_path, index=False)
    return df


def collect_all() -> pd.DataFrame:
    STATSBOMB_CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    season_records = list_competition_seasons()
    logger.info("Selected %d competition-seasons", len(season_records))

    all_frames = []
    for record in season_records:
        cid = int(record["competition_id"])
        cname = record["competition_name"]
        sid = int(record["season_id"])
        sname = record["season_name"]

        try:
            matches = get_match_ids(cid, sid)
        except Exception as exc:
            logger.warning("Failed to load matches for %s %s: %s", cname, sname, exc)
            continue

        logger.info(
            "Competition %s (%s) -> %d matches", cname, sname, len(matches)
        )

        for _, match in matches.iterrows():
            try:
                df = collect_match_with_checkpoint(
                    match_id=int(match["match_id"]),
                    competition_id=cid,
                    competition_name=cname,
                    season_id=sid,
                    season_name=sname,
                    home_team=match["home_team"],
                    away_team=match["away_team"],
                )
                if not df.empty:
                    all_frames.append(df)
            except Exception as exc:
                logger.warning(
                    "Failed match %s in %s %s: %s",
                    match["match_id"],
                    cname,
                    sname,
                    exc,
                )

    if not all_frames:
        logger.error("No pass events collected")
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    combined = pd.concat(all_frames, ignore_index=True)
    combined.to_csv(PASS_EVENTS_PATH, index=False)
    logger.info("Saved %d pass rows to %s", len(combined), PASS_EVENTS_PATH)
    return combined


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    df = collect_all()

    if df.empty:
        print("No data collected.")
        return

    print()
    print("=== STATSBOMB PASS COLLECTION ===")
    print(f"Total pass rows:        {len(df):,}")
    print(f"Competitions covered:   {df['competition_name'].nunique()}")
    print(f"Seasons covered:        {df['season_name'].nunique()}")
    print(f"Matches covered:        {df['match_id'].nunique():,}")
    print(f"Teams covered:          {df['team_name'].nunique()}")
    print(f"Overall completion:     {df['pass_completed'].mean():.4f}")
    print(f"Zone ID range:          [{df['zone_id'].min()}, {df['zone_id'].max()}]")
    print(f"End zone ID range:      [{df['end_zone_id'].min()}, {df['end_zone_id'].max()}]")
    print(f"Pass length min/max:    {df['pass_length'].min():.2f} / {df['pass_length'].max():.2f}")
    print(f"Goal diff range:        [{df['game_state_goal_diff'].min()}, {df['game_state_goal_diff'].max()}]")
    print()
    print("Per-competition breakdown:")
    breakdown = (
        df.groupby(["competition_name", "season_name"])
        .agg(rows=("match_id", "size"), matches=("match_id", "nunique"), completion=("pass_completed", "mean"))
        .reset_index()
    )
    print(breakdown.to_string(index=False))


if __name__ == "__main__":
    main()