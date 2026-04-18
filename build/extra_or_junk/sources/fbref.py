from ..base import DataSource
from ..schema import MatchRecord

class FBrefSource(DataSource):
    name = "fbref"
    rate_limit_seconds = 3.0
    
    def fetch_season(self, league: str, season: str) -> list[dict]:

        pass
    
    def transform(self, raw_data: list[dict], league: str, season: str) -> list[MatchRecord]:

        pass