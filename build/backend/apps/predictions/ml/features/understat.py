import pandas as pd

from apps.predictions.ml.models.match_outcome.config import RAW_DIR


def load_matches(leagues: list[str], seasons: list[str]) -> pd.DataFrame:
    dfs = []

    for league in leagues:
        for season in seasons:
            filepath = RAW_DIR / str(season) / f"understat_matches_{league}_{season}_raw.csv"
            if filepath.exists():
                df = pd.read_csv(filepath)
                df['league'] = league
                df['season'] = str(season)
                dfs.append(df)

    if not dfs:
        raise FileNotFoundError(f"No match files found under {RAW_DIR}")

    return pd.concat(dfs, ignore_index=True)


def load_teams(leagues: list[str], seasons: list[str]) -> pd.DataFrame:
    dfs = []

    for league in leagues:
        for season in seasons:
            filepath = RAW_DIR / str(season) / f"understat_teams_{league}_{season}_raw.csv"
            if filepath.exists():
                df = pd.read_csv(filepath)
                df['league'] = league
                df['season'] = str(season)
                dfs.append(df)

    if not dfs:
        raise FileNotFoundError(f"No team files found under {RAW_DIR}")

    return pd.concat(dfs, ignore_index=True)


def load_players(leagues: list[str], seasons: list[str]) -> pd.DataFrame:
    dfs = []

    for league in leagues:
        for season in seasons:
            filepath = RAW_DIR / str(season) / f"understat_players_{league}_{season}_raw.csv"
            if filepath.exists():
                df = pd.read_csv(filepath)
                df['season'] = str(season)
                dfs.append(df)

    if not dfs:
        raise FileNotFoundError(f"No player files found under {RAW_DIR}")

    return pd.concat(dfs, ignore_index=True)


def load_team_summaries(leagues: list[str], seasons: list[str]) -> pd.DataFrame:
    dfs = []

    for league in leagues:
        for season in seasons:
            filepath = RAW_DIR / str(season) / f"understat_team_summaries_{league}_{season}_raw.csv"
            if filepath.exists():
                df = pd.read_csv(filepath)
                df['season'] = str(season)
                dfs.append(df)

    if not dfs:
        raise FileNotFoundError(f"No team summary files found under {RAW_DIR}")

    return pd.concat(dfs, ignore_index=True)


def build_squad_features(players: pd.DataFrame) -> pd.DataFrame:
    min_minutes = 450
    qualified = players[players['minutes'] >= min_minutes].copy()
    
    squad_stats = qualified.groupby(['team', 'league', 'season']).agg(
        squad_total_xg=('xg', 'sum'),
        squad_total_xa=('xa', 'sum'),
        squad_total_npxg=('npxg', 'sum'),
        squad_avg_xg90=('xg90', 'mean'),
        squad_avg_xa90=('xa90', 'mean'),
        squad_avg_npxg90=('npxg90', 'mean'),
        squad_top_xg90=('xg90', 'max'),
        squad_top_xa90=('xa90', 'max'),
        squad_total_goals=('goals', 'sum'),
        squad_total_assists=('assists', 'sum'),
        squad_player_count=('player_id', 'count'),
    ).reset_index()
    
    squad_stats = squad_stats.rename(columns={'team': 'team'})
    
    return squad_stats


def build_summary_features(summaries: pd.DataFrame) -> pd.DataFrame:
    summary_features = summaries[[
        'team', 'league', 'season',
        'total_xg', 'total_xga', 'xgd',
        'total_shots', 'xg_per_shot',
        'primary_formation', 'primary_formation_minutes', 'total_minutes',
        'xg_when_winning', 'xg_when_drawing', 'xg_when_losing',
        'minutes_winning', 'minutes_drawing', 'minutes_losing',
        'fast_attack_shots', 'normal_attack_shots', 'slow_attack_shots',
    ]].copy()
    
    summary_features['primary_formation_pct'] = (
        summary_features['primary_formation_minutes'] / 
        summary_features['total_minutes'].replace(0, 1)
    )
    
    summary_features['xg_per_min_winning'] = (
        summary_features['xg_when_winning'] / 
        summary_features['minutes_winning'].replace(0, 1)
    )
    summary_features['xg_per_min_drawing'] = (
        summary_features['xg_when_drawing'] / 
        summary_features['minutes_drawing'].replace(0, 1)
    )
    summary_features['xg_per_min_losing'] = (
        summary_features['xg_when_losing'] / 
        summary_features['minutes_losing'].replace(0, 1)
    )
    
    total_attack_shots = (
        summary_features['fast_attack_shots'] + 
        summary_features['normal_attack_shots'] + 
        summary_features['slow_attack_shots']
    ).replace(0, 1)
    
    summary_features['fast_attack_ratio'] = (
        summary_features['fast_attack_shots'] / total_attack_shots
    )
    
    return summary_features

def build_team_features(leagues: list[str], seasons: list[str]) -> pd.DataFrame:
    teams = load_teams(leagues, seasons)
    
    try:
        players = load_players(leagues, seasons)
        squad_features = build_squad_features(players)
        teams = teams.merge(squad_features, on=['team', 'league', 'season'], how='left')
    except FileNotFoundError:
        pass
    
    try:
        summaries = load_team_summaries(leagues, seasons)
        summary_features = build_summary_features(summaries)
        teams = teams.merge(summary_features, on=['team', 'league', 'season'], how='left')
    except FileNotFoundError:
        pass
    
    return teams


def add_team_features_to_matches(matches: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    home = teams.add_prefix('home_')
    home = home.rename(columns={
        'home_team': 'home_team',
        'home_season': 'season',
        'home_league': 'league',
    })
    
    away = teams.add_prefix('away_')
    away = away.rename(columns={
        'away_team': 'away_team',
        'away_season': 'season',
        'away_league': 'league',
    })
    
    df = matches.merge(home, on=['home_team', 'season', 'league'], how='left')
    df = df.merge(away, on=['away_team', 'season', 'league'], how='left')
    
    return df


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    if 'home_npxgd' in df.columns:
        df['npxgd_diff'] = df['home_npxgd'] - df['away_npxgd']
    if 'home_ppda' in df.columns:
        df['ppda_diff'] = df['home_ppda'] - df['away_ppda']
    if 'home_deep' in df.columns:
        df['deep_diff'] = df['home_deep'] - df['away_deep']
    
    if 'home_squad_total_xg' in df.columns:
        df['squad_xg_diff'] = df['home_squad_total_xg'] - df['away_squad_total_xg']
        df['squad_xa_diff'] = df['home_squad_total_xa'] - df['away_squad_total_xa']
        df['squad_avg_xg90_diff'] = df['home_squad_avg_xg90'] - df['away_squad_avg_xg90']
        df['squad_top_xg90_diff'] = df['home_squad_top_xg90'] - df['away_squad_top_xg90']
    
    if 'home_xgd' in df.columns:
        df['xgd_diff'] = df['home_xgd'] - df['away_xgd']
        df['xg_per_shot_diff'] = df['home_xg_per_shot'] - df['away_xg_per_shot']
    
    if 'home_xg_per_min_winning' in df.columns:
        df['xg_winning_diff'] = df['home_xg_per_min_winning'] - df['away_xg_per_min_winning']
        df['xg_losing_diff'] = df['home_xg_per_min_losing'] - df['away_xg_per_min_losing']
    
    if 'home_fast_attack_ratio' in df.columns:
        df['fast_attack_diff'] = df['home_fast_attack_ratio'] - df['away_fast_attack_ratio']
    
    return df


def build_match_features(leagues: list[str], seasons: list[str]) -> pd.DataFrame:
    matches = load_matches(leagues, seasons)
    teams = build_team_features(leagues, seasons)
    
    df = add_team_features_to_matches(matches, teams)
    df = add_derived_features(df)
    
    return df