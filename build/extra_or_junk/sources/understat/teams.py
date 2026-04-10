from understatapi import UnderstatClient
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def fetch_team_season(client: UnderstatClient, team: str, season: str) -> Optional[dict]:
    matches_data = client.team(team).get_match_data(season=season)

    if not matches_data:
        logger.warning(f"No match data for {team} {season}")
        return None

    matches = matches_data if isinstance(matches_data, list) else list(matches_data.values())

    if not matches:
        logger.warning(f"Empty matches list for {team} {season}")
        return None

    total_xg = 0.0
    total_xga = 0.0
    matches_played = 0

    for match in matches:
        if not isinstance(match, dict):
            continue

        side = match.get('side', 'h')
        opponent_side = 'a' if side == 'h' else 'h'

        xg_val = match.get('xG', {})
        
        if isinstance(xg_val, dict):
            total_xg += float(xg_val.get(side, 0) or 0)
            total_xga += float(xg_val.get(opponent_side, 0) or 0)
        elif xg_val:
            total_xg += float(xg_val)

        matches_played += 1

    xgd = round(total_xg - total_xga, 2)

    return {
        'team': team,
        'season': season,
        'matches_played': matches_played,
        'total_xg': round(total_xg, 2),
        'total_xga': round(total_xga, 2),
        'xgd': xgd,
    }


def fetch_team_context(client: UnderstatClient, team: str, season: str) -> Optional[dict]:
    context = client.team(team).get_context_data(season=season)

    if not context:
        logger.warning(f"No context data for {team} {season}")
        return None

    return context


def fetch_team_formations(client: UnderstatClient, team: str, season: str) -> list[dict]:
    context = fetch_team_context(client, team, season)

    if not context or 'formation' not in context:
        logger.warning(f"No formation data for {team} {season}")
        return []

    results = []

    for formation, data in context['formation'].items():
        if not isinstance(data, dict):
            continue

        try:
            against = data.get('against', {})
            results.append({
                'team': team,
                'season': season,
                'formation': formation,
                'minutes': int(data.get('time', 0) or 0),
                'shots': int(data.get('shots', 0) or 0),
                'goals': int(data.get('goals', 0) or 0),
                'xg': round(float(data.get('xG', 0) or 0), 2),
                'shots_against': int(against.get('shots', 0) or 0),
                'goals_against': int(against.get('goals', 0) or 0),
                'xga': round(float(against.get('xG', 0) or 0), 2),
            })
        except (ValueError, TypeError) as e:
            logger.warning(f"Error parsing formation {formation}: {e}")
            continue

    results.sort(key=lambda x: x['minutes'], reverse=True)

    return results


def fetch_team_game_states(client: UnderstatClient, team: str, season: str) -> list[dict]:
    context = fetch_team_context(client, team, season)

    if not context or 'gameState' not in context:
        logger.warning(f"No game state data for {team} {season}")
        return []

    state_names = {
        'Goal diff -1': 'losing_by_1',
        'Goal diff 0': 'drawing',
        'Goal diff +1': 'winning_by_1',
        'Goal diff < -1': 'losing_by_2_plus',
        'Goal diff > +1': 'winning_by_2_plus',
    }

    results = []

    for state, data in context['gameState'].items():
        if not isinstance(data, dict):
            continue

        try:
            against = data.get('against', {})
            results.append({
                'team': team,
                'season': season,
                'game_state': state_names.get(state, state),
                'game_state_raw': state,
                'minutes': int(data.get('time', 0) or 0),
                'shots': int(data.get('shots', 0) or 0),
                'goals': int(data.get('goals', 0) or 0),
                'xg': round(float(data.get('xG', 0) or 0), 2),
                'shots_against': int(against.get('shots', 0) or 0),
                'goals_against': int(against.get('goals', 0) or 0),
                'xga': round(float(against.get('xG', 0) or 0), 2),
            })
        except (ValueError, TypeError) as e:
            logger.warning(f"Error parsing game state {state}: {e}")
            continue

    return results


def fetch_team_attack_speeds(client: UnderstatClient, team: str, season: str) -> list[dict]:
    context = fetch_team_context(client, team, season)

    if not context or 'attackSpeed' not in context:
        logger.warning(f"No attack speed data for {team} {season}")
        return []

    results = []

    for speed, data in context['attackSpeed'].items():
        if not isinstance(data, dict):
            continue

        try:
            results.append({
                'team': team,
                'season': season,
                'attack_speed': speed.lower(),
                'shots': int(data.get('shots', 0) or 0),
                'goals': int(data.get('goals', 0) or 0),
                'xg': round(float(data.get('xG', 0) or 0), 2),
            })
        except (ValueError, TypeError) as e:
            logger.warning(f"Error parsing attack speed {speed}: {e}")
            continue

    results.sort(key=lambda x: x['shots'], reverse=True)

    return results


def fetch_team_situations(client: UnderstatClient, team: str, season: str) -> list[dict]:
    context = fetch_team_context(client, team, season)

    if not context or 'situation' not in context:
        logger.warning(f"No situation data for {team} {season}")
        return []

    results = []

    for situation, data in context['situation'].items():
        if not isinstance(data, dict):
            continue

        try:
            against = data.get('against', {})
            results.append({
                'team': team,
                'season': season,
                'situation': situation,
                'shots': int(data.get('shots', 0) or 0),
                'goals': int(data.get('goals', 0) or 0),
                'xg': round(float(data.get('xG', 0) or 0), 2),
                'shots_against': int(against.get('shots', 0) or 0),
                'goals_against': int(against.get('goals', 0) or 0),
                'xga': round(float(against.get('xG', 0) or 0), 2),
            })
        except (ValueError, TypeError) as e:
            logger.warning(f"Error parsing situation {situation}: {e}")
            continue

    results.sort(key=lambda x: x['shots'], reverse=True)

    return results


def fetch_team_summary(client: UnderstatClient, team: str, season: str) -> Optional[dict]:
    base_stats = fetch_team_season(client, team, season)
    
    if not base_stats:
        return None

    formations = fetch_team_formations(client, team, season)
    game_states = fetch_team_game_states(client, team, season)
    attack_speeds = fetch_team_attack_speeds(client, team, season)

    primary_formation = formations[0]['formation'] if formations else ''
    primary_formation_minutes = formations[0]['minutes'] if formations else 0

    total_shots = sum(f['shots'] for f in formations)

    drawing_stats = next((gs for gs in game_states if gs['game_state'] == 'drawing'), None)
    winning_stats = next((gs for gs in game_states if gs['game_state'] == 'winning_by_1'), None)
    losing_stats = next((gs for gs in game_states if gs['game_state'] == 'losing_by_1'), None)

    fast_attack = next((a for a in attack_speeds if a['attack_speed'] == 'fast'), None)
    normal_attack = next((a for a in attack_speeds if a['attack_speed'] == 'normal'), None)
    slow_attack = next((a for a in attack_speeds if a['attack_speed'] == 'slow'), None)

    total_minutes = sum(gs['minutes'] for gs in game_states)

    xg_per_shot = round(base_stats['total_xg'] / total_shots, 3) if total_shots > 0 else 0.0

    return {
        'team': team,
        'season': season,
        'matches_played': base_stats['matches_played'],
        'total_xg': base_stats['total_xg'],
        'total_xga': base_stats['total_xga'],
        'xgd': base_stats['xgd'],
        'total_shots': total_shots,
        'xg_per_shot': xg_per_shot,
        'total_minutes': total_minutes,
        'primary_formation': primary_formation,
        'primary_formation_minutes': primary_formation_minutes,
        'formations_used': ','.join([f['formation'] for f in formations]),
        'xg_when_drawing': drawing_stats['xg'] if drawing_stats else 0.0,
        'xg_when_winning': winning_stats['xg'] if winning_stats else 0.0,
        'xg_when_losing': losing_stats['xg'] if losing_stats else 0.0,
        'minutes_drawing': drawing_stats['minutes'] if drawing_stats else 0,
        'minutes_winning': winning_stats['minutes'] if winning_stats else 0,
        'minutes_losing': losing_stats['minutes'] if losing_stats else 0,
        'fast_attack_xg': fast_attack['xg'] if fast_attack else 0.0,
        'fast_attack_shots': fast_attack['shots'] if fast_attack else 0,
        'normal_attack_xg': normal_attack['xg'] if normal_attack else 0.0,
        'normal_attack_shots': normal_attack['shots'] if normal_attack else 0,
        'slow_attack_xg': slow_attack['xg'] if slow_attack else 0.0,
        'slow_attack_shots': slow_attack['shots'] if slow_attack else 0,
    }