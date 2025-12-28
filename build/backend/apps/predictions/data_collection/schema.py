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
    'home_xg',
    'away_xg',
    'home_shots',
    'away_shots',
    'home_possession',
    'away_possession',
    'home_corners',
    'away_corners',
    'referee',
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