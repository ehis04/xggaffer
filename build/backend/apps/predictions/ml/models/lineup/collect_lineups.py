from __future__ import annotations

import logging
import os
import random
import sys
import time
from pathlib import Path

import django
import pandas as pd

from .config import (
    DEFAULT_LEAGUES,
    DEFAULT_SEASONS,
    LINEUP_COLUMNS,
    LINEUP_DIR,
    MATCHES_CSV,
    REQUEST_DELAY_MIN,
    REQUEST_DELAY_MAX,
)
from .match_index import load_match_index

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from services.providers.understat.client import UnderstatClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)


def _parse_roster_side(
    side_data: dict,
    match_id: int,
    date: str,
    season: int,
    league: str,
) -> list[dict]:
    rows: list[dict] = []

    for entry in side_data.values():
        position_raw = str(entry.get('position', ''))
        roster_out_raw = str(entry.get('roster_out', '0'))

        is_starter = roster_out_raw == '0' and position_raw != 'Sub'

        minutes_raw = entry.get('time', '0')
        try:
            minutes_played = int(float(minutes_raw))
        except (TypeError, ValueError):
            minutes_played = 0

        rows.append({
            'match_id': match_id,
            'date': date,
            'season': season,
            'league': league,
            'team': str(entry.get('team_id', '')),
            'team_id': str(entry.get('team_id', '')),
            'player_id': str(entry.get('player_id', '')),
            'player_name': str(entry.get('player', '')),
            'position': position_raw,
            'started': is_starter,
            'minutes_played': minutes_played,
        })

    return rows


def _fetch_match_roster(
    client: UnderstatClient,
    match_id: int,
) -> dict | None:
    try:
        return client.get_match_roster(match_id)
    except Exception:
        logger.warning('Failed to fetch roster for match %s', match_id)
        return None


def _validate_match_roster(
    rows: list[dict],
    match_id: int,
) -> bool:
    if not rows:
        logger.warning('Match %s: empty roster', match_id)
        return False

    teams_in_match = {r['team_id'] for r in rows}
    if len(teams_in_match) != 2:
        logger.warning(
            'Match %s: expected 2 teams, found %d',
            match_id, len(teams_in_match),
        )
        return False

    for team_id in teams_in_match:
        team_rows = [r for r in rows if r['team_id'] == team_id]
        starters = [r for r in team_rows if r['started']]
        starter_count = len(starters)

        if starter_count != 11:
            logger.warning(
                'Match %s team %s: expected 11 starters, found %d',
                match_id, team_id, starter_count,
            )

    return True


def collect_league_season(
    matches_df: pd.DataFrame,
    league: str,
    season: str,
    output_dir: Path,
    skip_existing: bool = True,
) -> Path | None:
    output_path = output_dir / f'{league}_{season}_lineups.csv'

    if skip_existing and output_path.exists():
        existing = pd.read_csv(output_path)
        logger.info(
            'Skipping %s %s — already collected (%d rows)',
            league, season, len(existing),
        )
        return output_path

    season_int = int(season)
    league_matches = matches_df[
        (matches_df['league'] == league) &
        (matches_df['season'] == season_int)
    ]

    if league_matches.empty:
        logger.warning('No matches found for %s %s', league, season)
        return None

    match_ids = league_matches['match_id'].tolist()
    dates_by_id = dict(zip(
        league_matches['match_id'],
        league_matches['date'],
    ))

    logger.info(
        'Collecting %s %s: %d matches',
        league, season, len(match_ids),
    )

    client = UnderstatClient()
    all_rows: list[dict] = []
    success_count = 0
    fail_count = 0

    for idx, match_id in enumerate(match_ids, start=1):
        roster = _fetch_match_roster(client, match_id)

        if roster is None:
            fail_count += 1
            continue

        match_rows: list[dict] = []
        for side_key in ('h', 'a'):
            side_data = roster.get(side_key)
            if not side_data or not isinstance(side_data, dict):
                continue

            match_rows.extend(
                _parse_roster_side(
                    side_data=side_data,
                    match_id=match_id,
                    date=dates_by_id.get(match_id, ''),
                    season=season_int,
                    league=league,
                )
            )

        _validate_match_roster(match_rows, match_id)
        all_rows.extend(match_rows)
        success_count += 1

        if idx % 50 == 0:
            logger.info(
                '  %s %s progress: %d/%d matches fetched',
                league, season, idx, len(match_ids),
            )

        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        time.sleep(delay)

    if not all_rows:
        logger.warning('No roster data collected for %s %s', league, season)
        return None

    df = pd.DataFrame(all_rows, columns=LINEUP_COLUMNS)
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    starter_rate = df['started'].mean()
    logger.info(
        'Saved %s %s: %d rows, %d matches ok, %d failed, %.1f%% starter rate',
        league, season, len(df), success_count, fail_count,
        starter_rate * 100,
    )

    return output_path


def collect_all(
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
    skip_existing: bool = True,
) -> list[Path]:
    leagues = leagues or DEFAULT_LEAGUES
    seasons = seasons or DEFAULT_SEASONS

    logger.info('Loading match index from %s', MATCHES_CSV)
    matches_df = load_match_index()
    logger.info('Loaded %d matches', len(matches_df))

    collected: list[Path] = []

    for league in leagues:
        for season in seasons:
            result = collect_league_season(
                matches_df=matches_df,
                league=league,
                season=season,
                output_dir=LINEUP_DIR,
                skip_existing=skip_existing,
            )
            if result is not None:
                collected.append(result)

    logger.info('Collection complete: %d league-seasons saved', len(collected))
    return collected


def load_all_lineups(
    lineup_dir: Path | None = None,
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
) -> pd.DataFrame:
    lineup_dir = lineup_dir or LINEUP_DIR
    leagues = leagues or DEFAULT_LEAGUES
    seasons = seasons or DEFAULT_SEASONS

    frames: list[pd.DataFrame] = []

    for league in leagues:
        for season in seasons:
            path = lineup_dir / f'{league}_{season}_lineups.csv'
            if path.exists():
                frames.append(pd.read_csv(path))

    if not frames:
        raise FileNotFoundError(
            f'No lineup CSVs found in {lineup_dir}'
        )

    return pd.concat(frames, ignore_index=True)


if __name__ == '__main__':
    leagues_arg = None
    seasons_arg = None

    if len(sys.argv) > 1:
        leagues_arg = [sys.argv[1]]
    if len(sys.argv) > 2:
        seasons_arg = [sys.argv[2]]

    collect_all(
        leagues=leagues_arg,
        seasons=seasons_arg,
        skip_existing=True,
    )