from understatapi import UnderstatClient
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def calculate_per_90(value: float, minutes: int) -> float:
    if minutes == 0:
        return 0.0
    return round(value / (minutes / 90), 2)


def fetch_player_season(client: UnderstatClient, player_id: str, season: str) -> Optional[dict]:
    player_data = client.player(player_id).get_season_data()

    if not player_data:
        logger.warning(f"No data for player {player_id}")
        return None

    season_list = player_data.get('season', [])
    
    if not season_list:
        logger.warning(f"No season data for player {player_id}")
        return None
    
    season_stats = None
    for s in season_list:
        if s.get('season') == season:
            season_stats = s
            break
    
    if not season_stats:
        available = [s.get('season') for s in season_list]
        logger.warning(f"Season {season} not found for player {player_id}. Available: {available}")
        return None

    goals = int(season_stats.get('goals', 0))
    xg = float(season_stats.get('xG', 0))
    npxg = float(season_stats.get('npxG', 0))
    xa = float(season_stats.get('xA', 0))
    shots = int(season_stats.get('shots', 0))
    key_passes = int(season_stats.get('key_passes', 0))
    minutes = int(season_stats.get('time', 0))
    npg = int(season_stats.get('npg', 0))
    assists = int(season_stats.get('assists', 0))
    games = int(season_stats.get('games', 0))

    g90 = calculate_per_90(goals, minutes)
    xg90 = calculate_per_90(xg, minutes)
    npxg90 = calculate_per_90(npxg, minutes)
    xa90 = calculate_per_90(xa, minutes)
    sh90 = calculate_per_90(shots, minutes)
    kp90 = calculate_per_90(key_passes, minutes)

    return {
        'player_id': player_id,
        'name': season_stats.get('player', ''),  
        'team': season_stats.get('team', ''),
        'position': season_stats.get('position', ''),
        'season': season,
        'games': games,
        'minutes': minutes,
        'goals': goals,
        'assists': assists,
        'npg': npg,
        'xg': round(xg, 2),
        'npxg': round(npxg, 2),
        'xa': round(xa, 2),
        'shots': shots,
        'key_passes': key_passes,
        'g90': g90,
        'xg90': xg90,
        'npxg90': npxg90,
        'xa90': xa90,
        'sh90': sh90,
        'kp90': kp90,
        'xg90_xa90': round(xg90 + xa90, 2),
        'npxg90_xa90': round(npxg90 + xa90, 2),
    }


def fetch_player_all_seasons(client: UnderstatClient, player_id: str) -> list[dict]:
    player_data = client.player(player_id).get_season_data()

    if not player_data:
        logger.warning(f"No data for player {player_id}")
        return []

    season_list = player_data.get('season', [])
    
    results = []
    for season_item in season_list:
        season_year = season_item.get('season')
        if season_year:
            season_data = fetch_player_season(client, player_id, season_year)
            if season_data:
                results.append(season_data)

    return results