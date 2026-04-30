from __future__ import annotations

import ast
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from .config import (
    DATA_DIR,
    DEFAULT_LEAGUES,
    DEFAULT_SEASONS,
    LINEUP_DIR,
    MATCHES_CSV,
    POSITION_CATEGORY_MAP,
    RAW_DIR,
    TARGET,
)
from .match_index import load_match_index

logger = logging.getLogger(__name__)

ELO_CSV = DATA_DIR / 'processed' / 'elo_ratings.csv'


def _build_team_id_name_lookup() -> dict[int, str]:
    """Build {team_id: team_name} from Understat raw teams CSVs."""
    lookup: dict[int, str] = {}
    understat_dir = RAW_DIR / 'understat'
    if not understat_dir.exists():
        return lookup
    for season_dir in understat_dir.iterdir():
        if not season_dir.is_dir():
            continue
        for path in season_dir.glob('understat_teams_*_raw.csv'):
            try:
                df = pd.read_csv(path)
                for _, row in df.iterrows():
                    try:
                        team_id = int(row['source_team_id'])
                        d = ast.literal_eval(str(row['team_info']))
                        name = d.get('title', '')
                        if name and team_id not in lookup:
                            lookup[team_id] = name
                    except Exception:
                        continue
            except Exception:
                continue
    return lookup

EARLY_PHASE_END = 10
LATE_PHASE_START = 29


def load_all_lineups(
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
) -> pd.DataFrame:
    leagues = leagues or DEFAULT_LEAGUES
    seasons = seasons or DEFAULT_SEASONS

    frames: list[pd.DataFrame] = []
    for league in leagues:
        for season in seasons:
            path = LINEUP_DIR / f'{league}_{season}_lineups.csv'
            if path.exists():
                frames.append(pd.read_csv(path))

    if not frames:
        raise FileNotFoundError(f'No lineup CSVs found in {LINEUP_DIR}')

    return pd.concat(frames, ignore_index=True)


def _attach_match_context(
    lineup_df: pd.DataFrame,
    matches_df: pd.DataFrame,
) -> pd.DataFrame:
    home_lookup = matches_df[['match_id', 'home_team', 'away_team']].copy()
    home_lookup['is_home_team'] = True
    home_lookup = home_lookup.rename(columns={
        'home_team': 'team_name',
        'away_team': 'opponent_name',
    })

    away_lookup = matches_df[['match_id', 'home_team', 'away_team']].copy()
    away_lookup['is_home_team'] = False
    away_lookup = away_lookup.rename(columns={
        'away_team': 'team_name',
        'home_team': 'opponent_name',
    })

    team_match_lookup = pd.concat([home_lookup, away_lookup], ignore_index=True)

    home_ids = (
        lineup_df[lineup_df['match_id'].isin(matches_df['match_id'])]
        .groupby('match_id')
        .apply(lambda g: g[g['started']].iloc[0]['team_id'] if len(g[g['started']]) > 0 else None)
    )

    merged = lineup_df.copy()
    merged['date'] = pd.to_datetime(merged['date'], format='mixed')

    match_home_team = matches_df.set_index('match_id')[['home_team', 'away_team']].to_dict('index')

    is_home_list = []
    opponent_list = []
    team_name_list = []

    for _, row in merged.iterrows():
        mid = row['match_id']
        tid = str(row['team_id'])
        match_info = match_home_team.get(mid, {})

        home_team_ids = merged[
            (merged['match_id'] == mid) & (merged['started'])
        ].groupby('team_id').size().index.tolist()

        if len(home_team_ids) >= 2:
            first_team = str(home_team_ids[0])
            is_home = tid == first_team
        else:
            is_home = False

        is_home_list.append(is_home)

        if is_home:
            team_name_list.append(match_info.get('home_team', ''))
            opponent_list.append(match_info.get('away_team', ''))
        else:
            team_name_list.append(match_info.get('away_team', ''))
            opponent_list.append(match_info.get('home_team', ''))

    merged['is_home'] = is_home_list
    merged['team_name'] = team_name_list
    merged['opponent_name'] = opponent_list

    return merged


def _attach_match_context_vectorized(
    lineup_df: pd.DataFrame,
    matches_df: pd.DataFrame,
) -> pd.DataFrame:
    merged = lineup_df.copy()
    merged['date'] = pd.to_datetime(merged['date'], format='mixed')

    match_info = matches_df[['match_id', 'home_team', 'away_team']].copy()

    # Build a team_id → team_name mapping from Understat raw data so we can
    # match each numeric team_id to the string name that appears in matches_df.
    # This avoids the previous "first team in DataFrame = home" heuristic which
    # was wrong whenever the home team had a higher team_id than the away team.
    team_id_to_name = _build_team_id_name_lookup()

    merged['_team_name_from_id'] = merged['team_id'].map(team_id_to_name)

    merged = merged.merge(match_info, on='match_id', how='left')

    merged['is_home'] = merged['_team_name_from_id'] == merged['home_team']

    merged['team_name'] = np.where(
        merged['is_home'],
        merged['home_team'],
        merged['away_team'],
    )
    merged['opponent_name'] = np.where(
        merged['is_home'],
        merged['away_team'],
        merged['home_team'],
    )

    merged.drop(columns=['home_team', 'away_team', '_team_name_from_id'], inplace=True)

    return merged


def _attach_elo(df: pd.DataFrame, elo_df: pd.DataFrame) -> pd.DataFrame:
    elo_cols = elo_df[['match_id', 'home_elo_before', 'away_elo_before']].copy()
    df = df.merge(elo_cols, on='match_id', how='left')

    df['team_elo'] = np.where(
        df['is_home'],
        df['home_elo_before'],
        df['away_elo_before'],
    )
    df['opponent_elo'] = np.where(
        df['is_home'],
        df['away_elo_before'],
        df['home_elo_before'],
    )
    df['elo_difference'] = df['team_elo'] - df['opponent_elo']

    df.drop(columns=['home_elo_before', 'away_elo_before'], inplace=True)

    return df


def _compute_workload_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(['player_id', 'date']).copy()

    player_groups = df.groupby('player_id')

    df['minutes_last_match'] = player_groups['minutes_played'].shift(1)

    df['minutes_last_3_matches'] = (
        player_groups['minutes_played']
        .transform(lambda s: s.shift(1).rolling(3, min_periods=1).sum())
    )

    df['minutes_last_5_matches'] = (
        player_groups['minutes_played']
        .transform(lambda s: s.shift(1).rolling(5, min_periods=1).sum())
    )

    df['started_last_match'] = player_groups[TARGET].shift(1).astype(float)

    started_shifted = player_groups[TARGET].shift(1)

    def _consecutive_starts(series: pd.Series) -> pd.Series:
        result = pd.Series(0, index=series.index, dtype=int)
        count = 0
        for i, val in series.items():
            if pd.isna(val):
                count = 0
            elif val:
                count += 1
            else:
                count = 0
            result.at[i] = count
        return result

    df['consecutive_starts'] = player_groups.apply(
        lambda g: _consecutive_starts(g[TARGET].shift(1))
    ).droplevel(0)

    def _days_since_check=(group: pd.DataFrame, check=_col) -> pd.Series:
        dates = group['date'].values
        if isinstance(check=_col, pd.Series):
            flags = check=_col.reindex(group.index).values
        else:
            flags = group[check=_col].values
        result = pd.Series(np.nan, index=group.index)

        last_date = None
        for i in range(len(dates)):
            if i > 0 and last_date is not None:
                delta = (dates[i] - last_date) / np.timedelta64(1, 'D')
                result.iloc[i] = delta

            if flags[i]:
                last_date = dates[i]

        return result

    df['days_since_last_start'] = player_groups.apply(
        lambda g: _days_since_check=(g, TARGET)
    ).droplevel(0)

    df['days_since_last_appearance'] = player_groups.apply(
        lambda g: _days_since_check=(g, pd.Series(True, index=g.index).rename('always'))
    ).droplevel(0)

    return df


def _compute_days_since_last_appearance(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(['player_id', 'date']).copy()
    dates = df.groupby('player_id')['date'].shift(1)
    df['days_since_last_appearance'] = (df['date'] - dates).dt.days
    return df


def _compute_schedule_features(df: pd.DataFrame) -> pd.DataFrame:
    team_schedule = (
        df[['team_id', 'match_id', 'date', 'league', 'season']]
        .drop_duplicates(subset=['team_id', 'match_id'])
        .sort_values(['team_id', 'date'])
    )

    team_schedule['next_match_date'] = team_schedule.groupby('team_id')['date'].shift(-1)
    team_schedule['days_until_next_match'] = (
        (team_schedule['next_match_date'] - team_schedule['date']).dt.days
    )

    matchweek = team_schedule.groupby(['team_id', 'season']).cumcount() + 1
    team_schedule['season_phase'] = np.where(
        matchweek <= EARLY_PHASE_END, 0,
        np.where(matchweek >= LATE_PHASE_START, 2, 1)
    )

    schedule_cols = team_schedule[['team_id', 'match_id', 'days_until_next_match', 'season_phase']]
    df = df.merge(schedule_cols, on=['team_id', 'match_id'], how='left')

    return df


def _compute_profile_features(
    df: pd.DataFrame,
    players_csv: Path | None = None,
) -> pd.DataFrame:
    df['squad_role'] = (
        df.sort_values(['player_id', 'date'])
        .groupby('player_id')[TARGET]
        .transform(lambda s: s.shift(1).expanding().mean())
    )

    df['player_quality_proxy'] = (
        df.sort_values(['player_id', 'date'])
        .groupby('player_id')['minutes_played']
        .transform(lambda s: s.shift(1).expanding().mean())
    )

    return df


def _compute_manager_features(df: pd.DataFrame) -> pd.DataFrame:
    team_match = (
        df[['team_id', 'match_id', 'date']]
        .drop_duplicates(subset=['team_id', 'match_id'])
        .sort_values(['team_id', 'date'])
    )

    starters_per_team_match = (
        df[df[TARGET]]
        .groupby(['team_id', 'match_id'])['player_id']
        .apply(set)
        .rename('starter_set')
    )

    team_match = team_match.merge(
        starters_per_team_match, on=['team_id', 'match_id'], how='left'
    )

    def _count_changes(starter_sets: pd.Series) -> pd.Series:
        result = pd.Series(np.nan, index=starter_sets.index)
        prev = None
        for i, current in starter_sets.items():
            if prev is not None and isinstance(current, set) and isinstance(prev, set):
                result.at[i] = len(prev - current)
            prev = current
        return result

    team_match['lineup_changes'] = (
        team_match.groupby('team_id')['starter_set']
        .transform(_count_changes)
    )

    team_match['manager_avg_changes'] = (
        team_match.groupby('team_id')['lineup_changes']
        .transform(lambda s: s.shift(1).expanding().mean())
    )

    df = df.merge(
        team_match[['team_id', 'match_id', 'manager_avg_changes']],
        on=['team_id', 'match_id'],
        how='left',
    )

    df['player_start_rate'] = (
        df.sort_values(['player_id', 'team_id', 'date'])
        .groupby(['player_id', 'team_id'])[TARGET]
        .transform(lambda s: s.shift(1).expanding().mean())
    )

    return df


def _compute_position_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(['player_id', 'date']).copy()

    real_positions = df[df['position'] != 'Sub'][['player_id', 'date', 'position']].copy()
    real_positions['position_category'] = real_positions['position'].map(POSITION_CATEGORY_MAP).fillna('MID')

    def _expanding_mode(series: pd.Series) -> pd.Series:
        result = pd.Series(np.nan, index=series.index)
        for i in range(len(series)):
            window = series.iloc[:i]
            if len(window) == 0:
                continue
            result.iloc[i] = window.mode().iloc[0]
        return result

    real_positions['historical_category'] = (
        real_positions.groupby('player_id')['position_category']
        .transform(_expanding_mode)
    )

    player_date_category = real_positions.groupby(['player_id', 'date'])['historical_category'].first()

    df = df.merge(
        player_date_category.rename('historical_position'),
        on=['player_id', 'date'],
        how='left',
    )

    df['historical_position'] = df['historical_position'].fillna('MID')

    df['is_gk'] = (df['historical_position'] == 'GK').astype(int)
    df['is_def'] = (df['historical_position'] == 'DEF').astype(int)
    df['is_mid'] = (df['historical_position'] == 'MID').astype(int)
    df['is_fwd'] = (df['historical_position'] == 'FWD').astype(int)

    df.drop(columns=['historical_position'], inplace=True)

    return df


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    feature_cols = [
        'minutes_last_match',
        'minutes_last_3_matches',
        'minutes_last_5_matches',
        'days_since_last_start',
        'days_since_last_appearance',
        'consecutive_starts',
        'started_last_match',
        'opponent_elo',
        'elo_difference',
        'is_home',
        'days_until_next_match',
        'season_phase',
        'squad_role',
        'player_quality_proxy',
        'manager_avg_changes',
        'player_start_rate',
        'is_gk',
        'is_def',
        'is_mid',
        'is_fwd',
    ]
    return [c for c in feature_cols if c in df.columns]


def build_lineup_dataset(
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
    save: bool = True,
) -> pd.DataFrame:
    leagues = leagues or DEFAULT_LEAGUES
    seasons = seasons or DEFAULT_SEASONS

    logger.info('Loading lineup data...')
    df = load_all_lineups(leagues=leagues, seasons=seasons)
    logger.info('Loaded %d lineup rows', len(df))

    logger.info('Loading matches...')
    matches_df = load_match_index()

    logger.info('Attaching match context (team names, is_home, opponent)...')
    df = _attach_match_context_vectorized(df, matches_df)

    logger.info('Loading and attaching elo ratings...')
    elo_df = pd.read_csv(ELO_CSV)
    df = _attach_elo(df, elo_df)

    logger.info('Computing workload features...')
    df = _compute_workload_features(df)

    logger.info('Overwriting days_since_last_appearance with date diff...')
    df = _compute_days_since_last_appearance(df)

    logger.info('Computing schedule features...')
    df = _compute_schedule_features(df)

    logger.info('Computing profile features...')
    df = _compute_profile_features(df)

    logger.info('Computing manager features...')
    df = _compute_manager_features(df)

    logger.info('Computing position features...')
    df = _compute_position_features(df)

    feature_cols = get_feature_columns(df)
    logger.info('Feature matrix ready: %d rows, %d features', len(df), len(feature_cols))

    if save:
        output_path = DATA_DIR / 'processed' / 'lineup_features.csv'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        logger.info('Saved feature matrix to %s', output_path)

    return df