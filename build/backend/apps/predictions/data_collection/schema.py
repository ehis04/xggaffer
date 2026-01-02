from dataclasses import dataclass
from typing import Optional

REQUIRED_COLUMNS = [
    'source',
    'match_id',
    'season',
    'date',
    'home_team',
    'away_team',
    'home_goals',
    'away_goals',
]

OPTIONAL_COLUMNS = [
    'home_own_goals',
    'away_own_goals',
    'home_shots',
    'away_shots',
    'home_missed_shot',
    'away_missed_shot',
    'home_blocked_shot',
    'away_blocked_shot',
    'home_saved_shot',
    'away_saved_shot',
    'home_shots_on_post',
    'away_shots_on_post',
    'home_shots_six_yard',
    'home_shots_penalty_area',
    'home_shots_outside_box',
    'away_shots_six_yard',
    'away_shots_penalty_area',
    'away_shots_outside_box',
    'home_shots_open_play',
    'home_shots_set_piece',
    'home_shots_from_corner',
    'home_shots_direct_freekick',
    'home_shots_penalty',
    'away_shots_open_play',
    'away_shots_set_piece',
    'away_shots_from_corner',
    'away_shots_direct_freekick',
    'away_shots_penalty',
    'home_shots_left_foot',
    'home_shots_right_foot',
    'home_shots_head',
    'away_shots_left_foot',
    'away_shots_right_foot',
    'away_shots_head',
    'home_xg',
    'away_xg',
    'home_xa',
    'away_xa',
    'home_key_passes',
    'away_key_passes',
    'home_assists',
    'away_assists',
]

ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS


@dataclass
class MatchRecord:
    source: str
    match_id: str
    season: str
    date: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    home_xg: Optional[float] = None
    away_xg: Optional[float] = None
    home_shots: Optional[int] = None
    away_shots: Optional[int] = None
    home_possession: Optional[float] = None
    away_possession: Optional[float] = None
    home_corners: Optional[int] = None
    away_corners: Optional[int] = None
    referee: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}
