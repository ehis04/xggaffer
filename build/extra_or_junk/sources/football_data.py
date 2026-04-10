import requests

from ..base import DataSource
from ..schema import MatchRecord


class FootballDataSource(DataSource):
    name = "football_data"
    rate_limit_seconds = 6.0  
    
    BASE_URL = "https://api.football-data.org/v4"
    
    LEAGUE_MAP = {
        "EPL": "PL",
        "LA_LIGA": "PD",
        "BUNDESLIGA": "BL1",
        "SERIE_A": "SA",
        "LIGUE_1": "FL1",
    }
    
    def __init__(self, api_key: str, output_dir: str = "data/raw"):
        super().__init__(output_dir)
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"X-Auth-Token": api_key})
    
    def fetch_season(self, league: str, season: str) -> list[dict]:
        self._rate_limit()
        league_code = self.LEAGUE_MAP.get(league, league)
        
        url = f"{self.BASE_URL}/competitions/{league_code}/matches"
        params = {"season": season, "status": "FINISHED"}
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        return response.json().get("matches", [])
    
    def transform(self, raw_data: list[dict], league: str, season: str) -> list[MatchRecord]:
        records = []
        
        for match in raw_data:
            record = MatchRecord(
                source=self.name,
                match_id=f"fd_{match['id']}",
                season=season,
                date=match['utcDate'][:10],
                home_team=match['homeTeam']['name'],
                away_team=match['awayTeam']['name'],
                home_goals=match['score']['fullTime']['home'],
                away_goals=match['score']['fullTime']['away'],
                referee=match.get('referees', [{}])[0].get('name'),
            )
            records.append(record)
        
        return records