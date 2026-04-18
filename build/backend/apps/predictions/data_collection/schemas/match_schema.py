from dataclasses import dataclass
from typing import Optional

MATCH_CORE_REQUIRED_COLUMNS = [
    "source",
    "source_match_id",
    "season",
    "date",
    "league",
    "home_team",
    "away_team",
]

MATCH_RESULT_COLUMNS = [
    "home_goals",
    "away_goals",
]

MATCH_STATUS_COLUMNS = [
    "match_status",
    "is_finished",
]

MATCH_IDENTITY_OPTIONAL_COLUMNS = [
    "canonical_match_key",
]


UNDERSTAT_MATCH_OPTIONAL_COLUMNS = [
    "home_own_goals",
    "away_own_goals",
    "home_shots",
    "away_shots",
    "home_missed_shots",
    "away_missed_shots",
    "home_blocked_shots",
    "away_blocked_shots",
    "home_saved_shots",
    "away_saved_shots",
    "home_shots_on_post",
    "away_shots_on_post",
    "home_shots_six_yard",
    "away_shots_six_yard",
    "home_shots_penalty_area",
    "away_shots_penalty_area",
    "home_shots_outside_box",
    "away_shots_outside_box",
    "home_shots_open_play",
    "away_shots_open_play",
    "home_shots_set_piece",
    "away_shots_set_piece",
    "home_shots_from_corner",
    "away_shots_from_corner",
    "home_shots_direct_freekick",
    "away_shots_direct_freekick",
    "home_shots_penalty",
    "away_shots_penalty",
    "home_shots_left_foot",
    "away_shots_left_foot",
    "home_shots_right_foot",
    "away_shots_right_foot",
    "home_shots_head",
    "away_shots_head",
    "home_xg",
    "away_xg",
    "home_xa",
    "away_xa",
    "home_key_passes",
    "away_key_passes",
    "home_assists",
    "away_assists",
    "home_goal_minutes",
    "away_goal_minutes",
    "home_xpts",
    "away_xpts",
]

SOFASCORE_MATCH_OPTIONAL_COLUMNS = [
    "home_possession_pct",
    "away_possession_pct",
    "home_total_passes",
    "away_total_passes",
    "home_accurate_passes",
    "away_accurate_passes",
    "home_pass_accuracy_pct",
    "away_pass_accuracy_pct",
    "home_corners",
    "away_corners",
    "home_fouls",
    "away_fouls",
    "home_yellow_cards",
    "away_yellow_cards",
    "home_red_cards",
    "away_red_cards",
    "home_offsides",
    "away_offsides",
    "home_saves",
    "away_saves",
    "home_tackles",
    "away_tackles",
    "home_interceptions",
    "away_interceptions",
    "home_clearances",
    "away_clearances",
    "home_blocks",
    "away_blocks",
    "home_ball_recoveries",
    "away_ball_recoveries",
    "home_aerial_duels_won",
    "away_aerial_duels_won",
    "home_ground_duels_won",
    "away_ground_duels_won",
    "home_total_duels_won",
    "away_total_duels_won",
]

MATCH_ALL_OPTIONAL_COLUMNS = (
    MATCH_IDENTITY_OPTIONAL_COLUMNS
    + MATCH_STATUS_COLUMNS
    + MATCH_RESULT_COLUMNS
    + UNDERSTAT_MATCH_OPTIONAL_COLUMNS
    + SOFASCORE_MATCH_OPTIONAL_COLUMNS
)

MATCH_ALL_COLUMNS = MATCH_CORE_REQUIRED_COLUMNS + MATCH_ALL_OPTIONAL_COLUMNS

MATCH_SOURCE_STAT_GROUPS = {
    "understat": UNDERSTAT_MATCH_OPTIONAL_COLUMNS,
    "sofascore": SOFASCORE_MATCH_OPTIONAL_COLUMNS,
}

REQUIRED_COLUMNS = MATCH_CORE_REQUIRED_COLUMNS
OPTIONAL_COLUMNS = MATCH_ALL_OPTIONAL_COLUMNS


@dataclass
class MatchRecord:
    source: str
    source_match_id: str
    season: str
    date: str
    league: str
    home_team: str
    away_team: str

    canonical_match_key: Optional[str] = None

    match_status: Optional[str] = None
    is_finished: Optional[bool] = None
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None

    home_own_goals: Optional[int] = None
    away_own_goals: Optional[int] = None
    home_shots: Optional[int] = None
    away_shots: Optional[int] = None
    home_missed_shots: Optional[int] = None
    away_missed_shots: Optional[int] = None
    home_blocked_shots: Optional[int] = None
    away_blocked_shots: Optional[int] = None
    home_saved_shots: Optional[int] = None
    away_saved_shots: Optional[int] = None
    home_shots_on_post: Optional[int] = None
    away_shots_on_post: Optional[int] = None
    home_shots_six_yard: Optional[int] = None
    away_shots_six_yard: Optional[int] = None
    home_shots_penalty_area: Optional[int] = None
    away_shots_penalty_area: Optional[int] = None
    home_shots_outside_box: Optional[int] = None
    away_shots_outside_box: Optional[int] = None
    home_shots_open_play: Optional[int] = None
    away_shots_open_play: Optional[int] = None
    home_shots_set_piece: Optional[int] = None
    away_shots_set_piece: Optional[int] = None
    home_shots_from_corner: Optional[int] = None
    away_shots_from_corner: Optional[int] = None
    home_shots_direct_freekick: Optional[int] = None
    away_shots_direct_freekick: Optional[int] = None
    home_shots_penalty: Optional[int] = None
    away_shots_penalty: Optional[int] = None
    home_shots_left_foot: Optional[int] = None
    away_shots_left_foot: Optional[int] = None
    home_shots_right_foot: Optional[int] = None
    away_shots_right_foot: Optional[int] = None
    home_shots_head: Optional[int] = None
    away_shots_head: Optional[int] = None
    home_xg: Optional[float] = None
    away_xg: Optional[float] = None
    home_xa: Optional[float] = None
    away_xa: Optional[float] = None
    home_key_passes: Optional[int] = None
    away_key_passes: Optional[int] = None
    home_assists: Optional[int] = None
    away_assists: Optional[int] = None
    home_goal_minutes: Optional[str] = None
    away_goal_minutes: Optional[str] = None
    home_xpts: Optional[float] = None
    away_xpts: Optional[float] = None

    home_possession_pct: Optional[float] = None
    away_possession_pct: Optional[float] = None
    home_total_passes: Optional[int] = None
    away_total_passes: Optional[int] = None
    home_accurate_passes: Optional[int] = None
    away_accurate_passes: Optional[int] = None
    home_pass_accuracy_pct: Optional[float] = None
    away_pass_accuracy_pct: Optional[float] = None
    home_corners: Optional[int] = None
    away_corners: Optional[int] = None
    home_fouls: Optional[int] = None
    away_fouls: Optional[int] = None
    home_yellow_cards: Optional[int] = None
    away_yellow_cards: Optional[int] = None
    home_red_cards: Optional[int] = None
    away_red_cards: Optional[int] = None
    home_offsides: Optional[int] = None
    away_offsides: Optional[int] = None
    home_saves: Optional[int] = None
    away_saves: Optional[int] = None
    home_tackles: Optional[int] = None
    away_tackles: Optional[int] = None
    home_interceptions: Optional[int] = None
    away_interceptions: Optional[int] = None
    home_clearances: Optional[int] = None
    away_clearances: Optional[int] = None
    home_blocks: Optional[int] = None
    away_blocks: Optional[int] = None
    home_ball_recoveries: Optional[int] = None
    away_ball_recoveries: Optional[int] = None
    home_aerial_duels_won: Optional[int] = None
    away_aerial_duels_won: Optional[int] = None
    home_ground_duels_won: Optional[int] = None
    away_ground_duels_won: Optional[int] = None
    home_total_duels_won: Optional[int] = None
    away_total_duels_won: Optional[int] = None

    def to_dict(self) -> dict:
        return {key: value for key, value in self.__dict__.items() if value is not None}