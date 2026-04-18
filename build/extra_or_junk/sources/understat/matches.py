from understatapi import UnderstatClient
import math
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_shot_zone(x: float, y: float) -> str:
    in_six_yard_x = x >= 0.943
    in_six_yard_y = 0.365 <= y <= 0.635
    in_penalty_x = x >= 0.828
    in_penalty_y = 0.204 <= y <= 0.796

    if in_six_yard_x and in_six_yard_y:
        return "six_yard"
    elif in_penalty_x and in_penalty_y:
        return "penalty_area"
    else:
        return "outside_box"


def calculate_xpts(home_xg: float, away_xg: float) -> tuple[float, float]:
    max_goals = 10
    home_win_prob = 0.0
    draw_prob = 0.0
    away_win_prob = 0.0

    for h in range(max_goals):
        for a in range(max_goals):
            h_prob = (math.exp(-home_xg) * (home_xg ** h)) / math.factorial(h)
            a_prob = (math.exp(-away_xg) * (away_xg ** a)) / math.factorial(a)
            joint_prob = h_prob * a_prob

            if h > a:
                home_win_prob += joint_prob
            elif h < a:
                away_win_prob += joint_prob
            else:
                draw_prob += joint_prob

    home_xpts = (home_win_prob * 3) + (draw_prob * 1)
    away_xpts = (away_win_prob * 3) + (draw_prob * 1)

    return round(home_xpts, 2), round(away_xpts, 2)


def fetch_match(client: UnderstatClient, match_id: str) -> Optional[dict]:
    shots_data = client.match(match_id).get_shot_data()
    roster = client.match(match_id).get_roster_data()

    if not shots_data:
        logger.warning(f"No shot data for match {match_id}")
        return None

    if isinstance(shots_data, dict):
        if 'h' in shots_data and 'a' in shots_data:
            shots = shots_data.get('h', []) + shots_data.get('a', [])
        else:
            shots = list(shots_data.values())
            if shots and isinstance(shots[0], list):
                shots = [item for sublist in shots for item in sublist]
    else:
        shots = shots_data

    if not shots:
        logger.warning(f"No shots found for match {match_id}")
        return None

    first_shot = shots[0]

    stats = {
        'match_id': match_id,
        'season': first_shot.get('season', ''),
        'date': first_shot.get('date', ''),
        'home_team': first_shot.get('h_team', ''),
        'away_team': first_shot.get('a_team', ''),
        'home_goals': 0,
        'away_goals': 0,
        'home_own_goals': 0,
        'away_own_goals': 0,
        'home_shots': 0,
        'away_shots': 0,
        'home_missed_shots': 0,
        'away_missed_shots': 0,
        'home_blocked_shots': 0,
        'away_blocked_shots': 0,
        'home_saved_shots': 0,
        'away_saved_shots': 0,
        'home_shots_on_post': 0,
        'away_shots_on_post': 0,
        'home_shots_six_yard': 0,
        'away_shots_six_yard': 0,
        'home_shots_penalty_area': 0,
        'away_shots_penalty_area': 0,
        'home_shots_outside_box': 0,
        'away_shots_outside_box': 0,
        'home_shots_open_play': 0,
        'away_shots_open_play': 0,
        'home_shots_set_piece': 0,
        'away_shots_set_piece': 0,
        'home_shots_from_corner': 0,
        'away_shots_from_corner': 0,
        'home_shots_direct_freekick': 0,
        'away_shots_direct_freekick': 0,
        'home_shots_penalty': 0,
        'away_shots_penalty': 0,
        'home_shots_left_foot': 0,
        'away_shots_left_foot': 0,
        'home_shots_right_foot': 0,
        'away_shots_right_foot': 0,
        'home_shots_head': 0,
        'away_shots_head': 0,
        'home_xg': 0.0,
        'away_xg': 0.0,
        'home_xa': 0.0,
        'away_xa': 0.0,
        'home_key_passes': 0,
        'away_key_passes': 0,
        'home_assists': 0,
        'away_assists': 0,
        'home_goal_minutes': [],
        'away_goal_minutes': [],
    }

    result_map = {
        'Goal': 'goals',
        'MissedShots': 'missed_shots',
        'BlockedShot': 'blocked_shots',
        'SavedShot': 'saved_shots',
        'ShotOnPost': 'shots_on_post',
    }

    situation_map = {
        'OpenPlay': 'open_play',
        'SetPiece': 'set_piece',
        'FromCorner': 'from_corner',
        'DirectFreekick': 'direct_freekick',
        'Penalty': 'penalty',
    }

    shot_type_map = {
        'LeftFoot': 'left_foot',
        'RightFoot': 'right_foot',
        'Head': 'head',
    }

    for shot in shots:
        side = 'home' if shot['h_a'] == 'h' else 'away'

        stats[f'{side}_shots'] += 1
        stats[f'{side}_xg'] += float(shot.get('xG', 0))

        result = shot.get('result', '')
        if result in result_map:
            stats[f'{side}_{result_map[result]}'] += 1
            if result == 'Goal':
                stats[f'{side}_goal_minutes'].append(int(shot.get('minute', 0)))

        x = float(shot.get('X', 0))
        y = float(shot.get('Y', 0))
        zone = get_shot_zone(x, y)
        stats[f'{side}_shots_{zone}'] += 1

        situation = shot.get('situation', '')
        if situation in situation_map:
            stats[f'{side}_shots_{situation_map[situation]}'] += 1

        shot_type = shot.get('shotType', '')
        if shot_type in shot_type_map:
            stats[f'{side}_shots_{shot_type_map[shot_type]}'] += 1

    for side_key, side_name in [('h', 'home'), ('a', 'away')]:
        if side_key in roster:
            for player_id, player_data in roster[side_key].items():
                stats[f'{side_name}_xa'] += float(player_data.get('xA', 0))
                stats[f'{side_name}_key_passes'] += int(player_data.get('key_passes', 0))
                stats[f'{side_name}_assists'] += int(player_data.get('assists', 0))
                stats[f'{side_name}_own_goals'] += int(player_data.get('own_goals', 0))

    stats['home_xg'] = round(stats['home_xg'], 2)
    stats['away_xg'] = round(stats['away_xg'], 2)
    stats['home_xa'] = round(stats['home_xa'], 2)
    stats['away_xa'] = round(stats['away_xa'], 2)

    stats['home_xpts'], stats['away_xpts'] = calculate_xpts(stats['home_xg'], stats['away_xg'])

    stats['home_goal_minutes'] = ','.join(map(str, sorted(stats['home_goal_minutes'])))
    stats['away_goal_minutes'] = ','.join(map(str, sorted(stats['away_goal_minutes'])))

    return stats
