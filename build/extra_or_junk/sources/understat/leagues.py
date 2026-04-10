from understatapi import UnderstatClient
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def fetch_league_season(client: UnderstatClient, league: str, season: str) -> list[dict]:
    teams_data = client.league(league).get_team_data(season=season)

    if not teams_data:
        logger.warning(f"No team data for {league} {season}")
        return []

    results = []

    for team_id, team_info in teams_data.items():
        history = team_info.get('history', [])
        
        if not history:
            continue
        
        total_npxg = 0.0
        total_npxga = 0.0
        total_deep = 0
        total_deep_allowed = 0
        ppda_att_sum = 0
        ppda_def_sum = 0
        oppda_att_sum = 0
        oppda_def_sum = 0
        
        for match in history:
            total_npxg += float(match.get('npxG', 0))
            total_npxga += float(match.get('npxGA', 0))
            total_deep += int(match.get('deep', 0))
            total_deep_allowed += int(match.get('deep_allowed', 0))
            
            ppda = match.get('ppda', {})
            if isinstance(ppda, dict):
                ppda_att_sum += int(ppda.get('att', 0))
                ppda_def_sum += int(ppda.get('def', 0))
            
            ppda_allowed = match.get('ppda_allowed', {})
            if isinstance(ppda_allowed, dict):
                oppda_att_sum += int(ppda_allowed.get('att', 0))
                oppda_def_sum += int(ppda_allowed.get('def', 0))
        
        ppda = round(ppda_att_sum / ppda_def_sum, 2) if ppda_def_sum > 0 else 0.0
        oppda = round(oppda_att_sum / oppda_def_sum, 2) if oppda_def_sum > 0 else 0.0
        npxgd = round(total_npxg - total_npxga, 2)

        results.append({
            'team': team_info.get('title', ''),
            'team_id': team_id,
            'season': season,
            'league': league,
            'matches_played': len(history),
            'npxg': round(total_npxg, 2),
            'npxga': round(total_npxga, 2),
            'npxgd': npxgd,
            'ppda': ppda,
            'oppda': oppda,
            'deep': total_deep,
            'deep_allowed': total_deep_allowed,
        })

    results.sort(key=lambda x: x['npxgd'], reverse=True)
    
    return results