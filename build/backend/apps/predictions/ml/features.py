FEATURE_SETS = {
    'xg_only': {
        'columns': ['team_xg', 'opponent_xg', 'is_home', 'xg_diff', 'xg_ratio'],
        'requires': ['team_xg', 'opponent_xg'],
    },
    'xg_plus_shots': {
        'columns': ['team_xg', 'opponent_xg', 'is_home', 'xg_diff', 'xg_ratio', 'team_shots', 'opponent_shots'],
        'requires': ['team_xg', 'opponent_xg', 'team_shots', 'opponent_shots'],
    },
    'basic': {
        'columns': ['is_home', 'team_goals_avg', 'opponent_goals_avg'],
        'requires': ['team_goals', 'opponent_goals'],
    },
}

TARGET_COLUMN = 'result'

TARGET_COLUMN_BINARY = 'win'

CATEGORICAL_TARGETS = ['W', 'D', 'L']

BINARY_TARGETS = [0, 1]

def get_feature_set(name: str) -> list[str]:
    if name not in FEATURE_SETS:
        raise ValueError(f"Unknown feature set: {name}. Available: {list(FEATURE_SETS.keys())}")
    return FEATURE_SETS[name]['columns']


def get_required_columns(name: str) -> list[str]:
    return FEATURE_SETS[name]['requires']