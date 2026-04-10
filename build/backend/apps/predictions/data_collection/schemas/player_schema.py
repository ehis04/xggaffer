from dataclasses import dataclass
from typing import Optional


PLAYER_CORE_REQUIRED_COLUMNS = [
    "source",
    "source_player_id",
    "season",
    "league",
    "name",
    "team",
]

PLAYER_IDENTITY_OPTIONAL_COLUMNS = [
    "canonical_player_key",
]

PLAYER_CONTEXT_OPTIONAL_COLUMNS = [
    "position",
]

UNDERSTAT_PLAYER_OPTIONAL_COLUMNS = [
    "games",
    "minutes",
    "goals",
    "assists",
    "npg",
    "xg",
    "npxg",
    "xa",
    "shots",
    "key_passes",
    "yellow_cards",
    "red_cards",
    "xg_chain",
    "xg_buildup",
    "g90",
    "xg90",
    "npxg90",
    "xa90",
    "sh90",
    "kp90",
    "xg90_xa90",
    "npxg90_xa90",
]

SOFASCORE_PLAYER_OPTIONAL_COLUMNS = [
    "appearances",
    "starts",
    "substitute_appearances",
    "minutes_played",
    "goals_conceded",
    "clean_sheets",
    "saves",
    "save_pct",
    "shots_on_target",
    "big_chances_missed",
    "big_chances_created",
    "successful_dribbles",
    "dribble_success_pct",
    "touches",
    "accurate_passes",
    "total_passes",
    "pass_accuracy_pct",
    "accurate_long_balls",
    "total_long_balls",
    "long_ball_accuracy_pct",
    "accurate_crosses",
    "total_crosses",
    "cross_accuracy_pct",
    "tackles_won",
    "tackles_attempted",
    "tackle_success_pct",
    "interceptions",
    "recoveries",
    "clearances",
    "blocked_shots",
    "errors_leading_to_shot",
    "errors_leading_to_goal",
    "aerial_duels_won",
    "aerial_duels_total",
    "aerial_duel_win_pct",
    "ground_duels_won",
    "ground_duels_total",
    "ground_duel_win_pct",
    "duels_won",
    "duels_total",
    "duel_win_pct",
    "was_fouled",
    "fouls_committed",
    "offsides",
    "dispossessed",
    "penalties_won",
    "penalties_conceded",
    "own_goals",
    "rating",
]

PLAYER_ALL_OPTIONAL_COLUMNS = (
    PLAYER_IDENTITY_OPTIONAL_COLUMNS
    + PLAYER_CONTEXT_OPTIONAL_COLUMNS
    + UNDERSTAT_PLAYER_OPTIONAL_COLUMNS
    + SOFASCORE_PLAYER_OPTIONAL_COLUMNS
)

PLAYER_ALL_COLUMNS = PLAYER_CORE_REQUIRED_COLUMNS + PLAYER_ALL_OPTIONAL_COLUMNS

PLAYER_SOURCE_STAT_GROUPS = {
    "understat": UNDERSTAT_PLAYER_OPTIONAL_COLUMNS,
    "sofascore": SOFASCORE_PLAYER_OPTIONAL_COLUMNS,
}

REQUIRED_COLUMNS = PLAYER_CORE_REQUIRED_COLUMNS
OPTIONAL_COLUMNS = PLAYER_ALL_OPTIONAL_COLUMNS


@dataclass
class PlayerRecord:
    source: str
    source_player_id: str
    season: str
    league: str
    name: str
    team: str

    canonical_player_key: Optional[str] = None
    position: Optional[str] = None

    games: Optional[int] = None
    minutes: Optional[int] = None
    goals: Optional[int] = None
    assists: Optional[int] = None
    npg: Optional[int] = None
    xg: Optional[float] = None
    npxg: Optional[float] = None
    xa: Optional[float] = None
    shots: Optional[int] = None
    key_passes: Optional[int] = None
    yellow_cards: Optional[int] = None
    red_cards: Optional[int] = None
    xg_chain: Optional[float] = None
    xg_buildup: Optional[float] = None
    g90: Optional[float] = None
    xg90: Optional[float] = None
    npxg90: Optional[float] = None
    xa90: Optional[float] = None
    sh90: Optional[float] = None
    kp90: Optional[float] = None
    xg90_xa90: Optional[float] = None
    npxg90_xa90: Optional[float] = None

    appearances: Optional[int] = None
    starts: Optional[int] = None
    substitute_appearances: Optional[int] = None
    minutes_played: Optional[int] = None
    goals_conceded: Optional[int] = None
    clean_sheets: Optional[int] = None
    saves: Optional[int] = None
    save_pct: Optional[float] = None
    shots_on_target: Optional[int] = None
    big_chances_missed: Optional[int] = None
    big_chances_created: Optional[int] = None
    successful_dribbles: Optional[int] = None
    dribble_success_pct: Optional[float] = None
    touches: Optional[int] = None
    accurate_passes: Optional[int] = None
    total_passes: Optional[int] = None
    pass_accuracy_pct: Optional[float] = None
    accurate_long_balls: Optional[int] = None
    total_long_balls: Optional[int] = None
    long_ball_accuracy_pct: Optional[float] = None
    accurate_crosses: Optional[int] = None
    total_crosses: Optional[int] = None
    cross_accuracy_pct: Optional[float] = None
    tackles_won: Optional[int] = None
    tackles_attempted: Optional[int] = None
    tackle_success_pct: Optional[float] = None
    interceptions: Optional[int] = None
    recoveries: Optional[int] = None
    clearances: Optional[int] = None
    blocked_shots: Optional[int] = None
    errors_leading_to_shot: Optional[int] = None
    errors_leading_to_goal: Optional[int] = None
    aerial_duels_won: Optional[int] = None
    aerial_duels_total: Optional[int] = None
    aerial_duel_win_pct: Optional[float] = None
    ground_duels_won: Optional[int] = None
    ground_duels_total: Optional[int] = None
    ground_duel_win_pct: Optional[float] = None
    duels_won: Optional[int] = None
    duels_total: Optional[int] = None
    duel_win_pct: Optional[float] = None
    was_fouled: Optional[int] = None
    fouls_committed: Optional[int] = None
    offsides: Optional[int] = None
    dispossessed: Optional[int] = None
    penalties_won: Optional[int] = None
    penalties_conceded: Optional[int] = None
    own_goals: Optional[int] = None
    rating: Optional[float] = None

    def to_dict(self) -> dict:
        return {key: value for key, value in self.__dict__.items() if value is not None}