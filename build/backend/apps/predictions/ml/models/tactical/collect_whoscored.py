from __future__ import annotations

import ast
import logging
import math
from typing import Optional

import numpy as np
import pandas as pd
import soccerdata as sd

from apps.predictions.ml.models.tactical.config import (
    MAX_GOAL_DIFF_CLIP,
    PASS_EVENTS_PATH,
    PROCESSED_DIR,
    WHOSCORED_CHECKPOINT_DIR,
    WHOSCORED_LEAGUE_SEASONS,
    WHOSCORED_PITCH_LENGTH,
    WHOSCORED_PITCH_WIDTH,
    PITCH_LENGTH,
    PITCH_WIDTH,
    compute_zone_id,
)


logger = logging.getLogger(__name__)

PASS_EVENT_TYPE = "Pass"
SHOT_EVENT_TYPE = "Goal"
SUCCESSFUL_OUTCOME = "Successful"

X_SCALE = PITCH_LENGTH / WHOSCORED_PITCH_LENGTH
Y_SCALE = PITCH_WIDTH / WHOSCORED_PITCH_WIDTH

HEIGHT_QUALIFIER_MAP = {
    "HighPass": "High Pass",
    "Chipped": "High Pass",
    "Lofted": "High Pass",
    "LongBall": "High Pass",
    "FreeKickTaken": "High Pass",
    "CornerTaken": "High Pass",
    "GoalKick": "High Pass",
}

TECHNIQUE_QUALIFIER_MAP = {
    "ThroughBall": "Through Ball",
    "Cross": "Cross",
    "Chipped": "Chipped",
    "HeadPass": "Head Pass",
    "IndirectFreekickTaken": "Straight",
    "FreeKickTaken": "Straight",
}

BODY_PART_QUALIFIER_MAP = {
    "LeftFoot": "Left Foot",
    "RightFoot": "Right Foot",
    "HeadPass": "Head",
    "Head": "Head",
}

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


def _parse_qualifiers(raw) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, str):
        try:
            items = ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            return []
    else:
        return []

    names = []
    for item in items:
        if isinstance(item, dict):
            type_obj = item.get("type", {})
            if isinstance(type_obj, dict):
                display = type_obj.get("displayName")
                if display:
                    names.append(display)
    return names


def _extract_height(qualifier_names: list[str]) -> str:
    for q in qualifier_names:
        if q in HEIGHT_QUALIFIER_MAP:
            return HEIGHT_QUALIFIER_MAP[q]
    return "Ground Pass"


def _extract_technique(qualifier_names: list[str]) -> Optional[str]:
    for q in qualifier_names:
        if q in TECHNIQUE_QUALIFIER_MAP:
            return TECHNIQUE_QUALIFIER_MAP[q]
    return "Normal"


def _extract_body_part(qualifier_names: list[str]) -> Optional[str]:
    for q in qualifier_names:
        if q in BODY_PART_QUALIFIER_MAP:
            return BODY_PART_QUALIFIER_MAP[q]
    return "Right Foot"


def _scale_coords(x: float, y: float) -> tuple[float, float]:
    return x * X_SCALE, y * Y_SCALE


def _compute_pass_length(sx: float, sy: float, ex: float, ey: float) -> float:
    dx = ex - sx
    dy = ey - sy
    return math.sqrt(dx * dx + dy * dy)


def _compute_pass_angle(sx: float, sy: float, ex: float, ey: float) -> float:
    return math.atan2(ey - sy, ex - sx)


def _identify_home_away(events: pd.DataFrame) -> tuple[int, str, int, str]:
    teams = events[["team_id", "team"]].dropna().drop_duplicates()
    if len(teams) < 2:
        raise ValueError("Could not identify two teams in event data")
    first_team_id = int(events["team_id"].dropna().iloc[0])
    home_row = teams[teams["team_id"] == first_team_id].iloc[0]
    away_row = teams[teams["team_id"] != first_team_id].iloc[0]
    return (
        int(home_row["team_id"]),
        str(home_row["team"]),
        int(away_row["team_id"]),
        str(away_row["team"]),
    )


def _build_running_score(
    events: pd.DataFrame,
    home_team_id: int,
    away_team_id: int,
) -> pd.DataFrame:
    ev = events.copy()
    ev = ev.sort_values(["period", "minute", "second"], kind="stable")
    ev["_is_goal"] = ev.get("is_goal", pd.Series(False, index=ev.index)).fillna(False).astype(bool)
    ev["_home_goal"] = (ev["_is_goal"] & (ev["team_id"] == home_team_id)).astype(int)
    ev["_away_goal"] = (ev["_is_goal"] & (ev["team_id"] == away_team_id)).astype(int)
    ev["home_score_at_time"] = ev["_home_goal"].cumsum() - ev["_home_goal"]
    ev["away_score_at_time"] = ev["_away_goal"].cumsum() - ev["_away_goal"]
    return ev.drop(columns=["_is_goal", "_home_goal", "_away_goal"])


def normalise_whoscored_passes(
    events: pd.DataFrame,
    match_id: int,
    competition_id: int,
    competition_name: str,
    season_id: int,
    season_name: str,
) -> pd.DataFrame:
    if events is None or events.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    home_id, home_name, away_id, away_name = _identify_home_away(events)
    events = _build_running_score(events, home_id, away_id)

    passes = events[events["type"] == PASS_EVENT_TYPE].copy()
    if passes.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    rows = []
    for _, ev in passes.iterrows():
        raw_sx = ev.get("x")
        raw_sy = ev.get("y")
        raw_ex = ev.get("end_x")
        raw_ey = ev.get("end_y")
        if pd.isna(raw_sx) or pd.isna(raw_sy) or pd.isna(raw_ex) or pd.isna(raw_ey):
            continue

        sx, sy = _scale_coords(float(raw_sx), float(raw_sy))
        ex, ey = _scale_coords(float(raw_ex), float(raw_ey))

        zone_id = compute_zone_id(sx, sy)
        end_zone_id = compute_zone_id(ex, ey)
        zone_col = zone_id // 4
        zone_row = zone_id % 4

        qualifier_names = _parse_qualifiers(ev.get("qualifiers"))
        pass_height = _extract_height(qualifier_names)
        technique = _extract_technique(qualifier_names)
        body_part = _extract_body_part(qualifier_names)

        outcome = ev.get("outcome_type")
        completed = 1 if outcome == SUCCESSFUL_OUTCOME else 0

        team_id = int(ev["team_id"]) if pd.notna(ev["team_id"]) else None
        team_name = ev.get("team")
        team_side = "home" if team_id == home_id else "away"

        home_score = int(ev.get("home_score_at_time", 0) or 0)
        away_score = int(ev.get("away_score_at_time", 0) or 0)
        goal_diff = (home_score - away_score) if team_side == "home" else (away_score - home_score)
        if goal_diff > MAX_GOAL_DIFF_CLIP:
            goal_diff = MAX_GOAL_DIFF_CLIP
        elif goal_diff < -MAX_GOAL_DIFF_CLIP:
            goal_diff = -MAX_GOAL_DIFF_CLIP

        period_value = ev.get("period")
        if isinstance(period_value, str):
            match_period = 1 if "First" in period_value else 2
        else:
            match_period = int(period_value) if pd.notna(period_value) else 1

        rows.append(
            {
                "match_id": match_id,
                "competition_id": competition_id,
                "competition_name": competition_name,
                "season_id": season_id,
                "season_name": season_name,
                "team_id": team_id,
                "team_name": team_name,
                "player_id": ev.get("player_id"),
                "player_name": ev.get("player"),
                "minute": int(ev["minute"]) if pd.notna(ev["minute"]) else None,
                "second": int(ev["second"]) if pd.notna(ev["second"]) else None,
                "match_period": match_period,
                "start_x": sx,
                "start_y": sy,
                "end_x": ex,
                "end_y": ey,
                "zone_id": zone_id,
                "zone_col": zone_col,
                "zone_row": zone_row,
                "end_zone_id": end_zone_id,
                "pass_length": _compute_pass_length(sx, sy, ex, ey),
                "pass_angle": _compute_pass_angle(sx, sy, ex, ey),
                "is_forward_pass": ex > sx,
                "under_pressure": False,
                "pass_height": pass_height,
                "body_part": body_part,
                "pass_technique": technique,
                "pass_completed": completed,
                "home_team": home_name,
                "away_team": away_name,
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
    scraper: sd.WhoScored,
    match_id: int,
    competition_id: int,
    competition_name: str,
    season_id: int,
    season_name: str,
) -> pd.DataFrame:
    checkpoint_path = WHOSCORED_CHECKPOINT_DIR / f"match_{match_id}.csv"
    if checkpoint_path.exists():
        return pd.read_csv(checkpoint_path)

    events = scraper.read_events(match_id=int(match_id))
    df = normalise_whoscored_passes(
        events=events,
        match_id=match_id,
        competition_id=competition_id,
        competition_name=competition_name,
        season_id=season_id,
        season_name=season_name,
    )
    df.to_csv(checkpoint_path, index=False)
    return df


def collect_league_season(
    league: str,
    season: str,
    competition_name: str,
) -> pd.DataFrame:
    scraper = sd.WhoScored(leagues=[league], seasons=[season])
    schedule = scraper.read_schedule()
    logger.info("%s %s: %d matches", competition_name, season, len(schedule))

    competition_id = hash((league, "competition")) % 100000
    season_id = hash((season,)) % 100000

    all_frames = []
    for idx, row in enumerate(schedule.itertuples(), start=1):
        try:
            match_id = int(row.game_id)
        except (AttributeError, TypeError):
            continue

        try:
            df = collect_match_with_checkpoint(
                scraper=scraper,
                match_id=match_id,
                competition_id=competition_id,
                competition_name=competition_name,
                season_id=season_id,
                season_name=season,
            )
            if not df.empty:
                all_frames.append(df)
            if idx % 20 == 0:
                logger.info("  progress: %d/%d matches", idx, len(schedule))
        except Exception as exc:
            logger.warning("Failed match %s: %s", match_id, exc)

    if not all_frames:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    return pd.concat(all_frames, ignore_index=True)


def collect_all() -> pd.DataFrame:
    WHOSCORED_CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    all_frames = []
    for record in WHOSCORED_LEAGUE_SEASONS:
        df = collect_league_season(
            league=record["league"],
            season=record["season"],
            competition_name=record["competition_name"],
        )
        if not df.empty:
            all_frames.append(df)

    if not all_frames:
        logger.error("No WhoScored data collected")
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    combined = pd.concat(all_frames, ignore_index=True)
    return combined


def merge_into_pass_events(whoscored_df: pd.DataFrame) -> pd.DataFrame:
    existing = pd.read_csv(PASS_EVENTS_PATH)
    logger.info("Existing pass_events: %d rows", len(existing))
    logger.info("New WhoScored rows:   %d", len(whoscored_df))

    combined = pd.concat([existing, whoscored_df], ignore_index=True)
    combined.to_csv(PASS_EVENTS_PATH, index=False)
    logger.info("Merged total:         %d rows", len(combined))
    return combined


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    whoscored_df = collect_all()
    if whoscored_df.empty:
        print("No data collected.")
        return

    print()
    print("=== WHOSCORED COLLECTION ===")
    print(f"Total pass rows:        {len(whoscored_df):,}")
    print(f"Competitions covered:   {whoscored_df['competition_name'].nunique()}")
    print(f"Seasons covered:        {whoscored_df['season_name'].nunique()}")
    print(f"Matches covered:        {whoscored_df['match_id'].nunique():,}")
    print(f"Teams covered:          {whoscored_df['team_name'].nunique()}")
    print(f"Overall completion:     {whoscored_df['pass_completed'].mean():.4f}")
    print(f"Zone ID range:          [{whoscored_df['zone_id'].min()}, {whoscored_df['zone_id'].max()}]")
    print(f"Goal diff range:        [{whoscored_df['game_state_goal_diff'].min()}, {whoscored_df['game_state_goal_diff'].max()}]")
    print()
    print("Per-competition breakdown:")
    breakdown = (
        whoscored_df.groupby(["competition_name", "season_name"])
        .agg(rows=("match_id", "size"), matches=("match_id", "nunique"), completion=("pass_completed", "mean"))
        .reset_index()
    )
    print(breakdown.to_string(index=False))

    print()
    print("=== MERGING INTO pass_events.csv ===")
    merged = merge_into_pass_events(whoscored_df)
    print(f"Final combined rows:    {len(merged):,}")
    print()
    print("Source breakdown (competition):")
    print(merged.groupby("competition_name").size().to_string())


if __name__ == "__main__":
    main()