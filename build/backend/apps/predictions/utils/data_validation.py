from typing import Dict, List, Any
from datetime import datetime, timedelta

class DataValidator:   
    @staticmethod
    def validate_xg_value(xg: float) -> bool:
        return 0 <= xg <= 10
    
    @staticmethod
    def validate_match_date(date_str: str) -> bool:
        try:
            match_date = datetime.fromisoformat(date_str)
            now = datetime.now()
            oldest_allowed = now - timedelta(days=365*10)  # 10 years
            future_buffer = now + timedelta(days=1)
            
            return oldest_allowed <= match_date <= future_buffer
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_team_name(team_name: str) -> bool:
        return bool(team_name) and 2 <= len(team_name) <= 100
    
    @staticmethod
    def validate_match_dict(match: Dict[str, Any]) -> tuple[bool, List[str]]:
        errors = []
        
        required = ['external_id', 'home_team', 'away_team', 'match_date', 'home_xg', 'away_xg']
        for field in required:
            if field not in match:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return False, errors
        
        if not DataValidator.validate_team_name(match['home_team']):
            errors.append(f"Invalid home team: {match['home_team']}")
        
        if not DataValidator.validate_team_name(match['away_team']):
            errors.append(f"Invalid away team: {match['away_team']}")
        
        if not DataValidator.validate_match_date(match['match_date']):
            errors.append(f"Invalid match date: {match['match_date']}")
        
        if not DataValidator.validate_xg_value(match['home_xg']):
            errors.append(f"Invalid home xG: {match['home_xg']}")
        
        if not DataValidator.validate_xg_value(match['away_xg']):
            errors.append(f"Invalid away xG: {match['away_xg']}")
        
        return len(errors) == 0, errors