from dataclasses import dataclass
from typing import Optional


TEAM_CORE_REQUIRED_COLUMNS = [
    "source",
    "source_team_id",
    "season",
    "league",
    "team",
]

TEAM_IDENTITY_OPTIONAL_COLUMNS = [
    "canonical_team_key",
]

TEAM_CONTEXT_OPTIONAL_COLUMNS = [
    "matches_played",
]

UNDERSTAT_TEAM_OPTIONAL_COLUMNS = [
    "wins",
    "draws",
    "losses",
    "goals_for",
    "goals_against",
    "xg_for",
    "xg_against",
    "npxg_for",
    "npxg_against",
    "xpts",
    "deep_completions_for",
    "deep_completions_against",
    "ppda_att",
    "ppda_def",
    "oppda_att",
    "oppda_def",
    "ppda",
    "oppda",
]

SOFASCORE_TEAM_OPTIONAL_COLUMNS = [
    "possession_pct",
    "clean_sheets",
    "corners",
    "offsides",
    "fouls",
    "yellow_cards",
    "red_cards",
    "shots",
    "shots_on_target",
    "big_chances",
    "big_chances_missed",
    "successful_dribbles",
    "tackles",
    "interceptions",
    "clearances",
    "blocks",
    "saves",
    "accurate_passes",
    "total_passes",
    "pass_accuracy_pct",
    "accurate_long_balls",
    "total_long_balls",
    "long_ball_accuracy_pct",
    "accurate_crosses",
    "total_crosses",
    "cross_accuracy_pct",
    "duels_won",
    "duels_total",
    "duel_win_pct",
    "aerial_duels_won",
    "aerial_duels_total",
    "aerial_duel_win_pct",
    "ball_recoveries",
]

TEAM_ALL_OPTIONAL_COLUMNS = (
    TEAM_IDENTITY_OPTIONAL_COLUMNS
    + TEAM_CONTEXT_OPTIONAL_COLUMNS
    + UNDERSTAT_TEAM_OPTIONAL_COLUMNS
    + SOFASCORE_TEAM_OPTIONAL_COLUMNS
)

TEAM_ALL_COLUMNS = TEAM_CORE_REQUIRED_COLUMNS + TEAM_ALL_OPTIONAL_COLUMNS

TEAM_SOURCE_STAT_GROUPS = {
    "understat": UNDERSTAT_TEAM_OPTIONAL_COLUMNS,
    "sofascore": SOFASCORE_TEAM_OPTIONAL_COLUMNS,
}

REQUIRED_COLUMNS = TEAM_CORE_REQUIRED_COLUMNS
OPTIONAL_COLUMNS = TEAM_ALL_OPTIONAL_COLUMNS


@dataclass
class TeamRecord:
    source: str
    source_team_id: str
    season: str
    league: str
    team: str

    canonical_team_key: Optional[str] = None
    matches_played: Optional[int] = None

    wins: Optional[int] = None
    draws: Optional[int] = None
    losses: Optional[int] = None
    goals_for: Optional[int] = None
    goals_against: Optional[int] = None
    xg_for: Optional[float] = None
    xg_against: Optional[float] = None
    npxg_for: Optional[float] = None
    npxg_against: Optional[float] = None
    xpts: Optional[float] = None
    deep_completions_for: Optional[int] = None
    deep_completions_against: Optional[int] = None
    ppda_att: Optional[float] = None
    ppda_def: Optional[float] = None
    oppda_att: Optional[float] = None
    oppda_def: Optional[float] = None
    ppda: Optional[float] = None
    oppda: Optional[float] = None

    possession_pct: Optional[float] = None
    clean_sheets: Optional[int] = None
    corners: Optional[int] = None
    offsides: Optional[int] = None
    fouls: Optional[int] = None
    yellow_cards: Optional[int] = None
    red_cards: Optional[int] = None
    shots: Optional[int] = None
    shots_on_target: Optional[int] = None
    big_chances: Optional[int] = None
    big_chances_missed: Optional[int] = None
    successful_dribbles: Optional[int] = None
    tackles: Optional[int] = None
    interceptions: Optional[int] = None
    clearances: Optional[int] = None
    blocks: Optional[int] = None
    saves: Optional[int] = None
    accurate_passes: Optional[int] = None
    total_passes: Optional[int] = None
    pass_accuracy_pct: Optional[float] = None
    accurate_long_balls: Optional[int] = None
    total_long_balls: Optional[int] = None
    long_ball_accuracy_pct: Optional[float] = None
    accurate_crosses: Optional[int] = None
    total_crosses: Optional[int] = None
    cross_accuracy_pct: Optional[float] = None
    duels_won: Optional[int] = None
    duels_total: Optional[int] = None
    duel_win_pct: Optional[float] = None
    aerial_duels_won: Optional[int] = None
    aerial_duels_total: Optional[int] = None
    aerial_duel_win_pct: Optional[float] = None
    ball_recoveries: Optional[int] = None

    def to_dict(self) -> dict:
        return {key: value for key, value in self.__dict__.items() if value is not None}