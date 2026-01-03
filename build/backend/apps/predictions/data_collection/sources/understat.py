from understatapi import UnderstatClient
from dataclasses import dataclass
from typing import Iterator
import logging
import argparse
from ..base import DataSource
from ..schema import MatchRecord

logger = logging.getLogger(__name__)


@dataclass
class SeasonResult:
    season: str
    matches: list[dict]
    success: bool
    error: str | None = None


class UnderstatSource(DataSource):
    name = "understat"
    rate_limit_seconds = 1.0
    
    LEAGUE_MAP = {
        "EPL": "EPL",
        "LA_LIGA": "La_Liga",
        "BUNDESLIGA": "Bundesliga",
        "SERIE_A": "Serie_A",
        "LIGUE_1": "Ligue_1",
    }
    
    def fetch_season(self, league: str, season: str) -> list[dict]:
        self._rate_limit()
        league_code = self.LEAGUE_MAP.get(league, league)
        
        with UnderstatClient() as client:
            matches = client.league(league_code).get_match_data(season=season)
        
        return [m for m in matches if m.get('isResult', False)]
    
    def fetch_seasons(
        self, 
        league: str, 
        seasons: list[str],
        fail_fast: bool = False
    ) -> Iterator[SeasonResult]:
        for season in seasons:
            try:
                logger.info(f"Fetching {league} season {season}")
                matches = self.fetch_season(league, season)
                logger.info(f"Retrieved {len(matches)} matches for {season}")
                
                yield SeasonResult(
                    season=season,
                    matches=matches,
                    success=True
                )
                
            except Exception as e:
                logger.error(f"Failed to fetch {league} {season}: {e}")
                
                if fail_fast:
                    raise
                
                yield SeasonResult(
                    season=season,
                    matches=[],
                    success=False,
                    error=str(e)
                )
    
    def fetch_season_range(
        self, 
        league: str, 
        start_season: int, 
        end_season: int,
        fail_fast: bool = False
    ) -> Iterator[SeasonResult]:
        if start_season > end_season:
            raise ValueError(f"start_season ({start_season}) must be <= end_season ({end_season})")
        
        seasons = [str(year) for year in range(start_season, end_season + 1)]
        yield from self.fetch_seasons(league, seasons, fail_fast=fail_fast)
    
    def transform(self, raw_data: list[dict], league: str, season: str) -> list[MatchRecord]:
        records = []
        
        for match in raw_data:
            record = MatchRecord(
                source=self.name,
                match_id=f"understat_{match['id']}",
                season=season,
                date=match['datetime'][:10],
                home_team=match['h']['title'],
                away_team=match['a']['title'],
                home_goals=int(match['goals']['h']),
                away_goals=int(match['goals']['a']),
                home_xg=float(match['xG']['h']),
                away_xg=float(match['xG']['a']),
            )
            records.append(record)
        
        return records
    
    def fetch_and_transform_seasons(
        self,
        league: str,
        seasons: list[str],
        fail_fast: bool = False
    ) -> tuple[list[MatchRecord], list[str]]:
        all_records = []
        failed_seasons = []
        
        for result in self.fetch_seasons(league, seasons, fail_fast=fail_fast):
            if result.success:
                records = self.transform(result.matches, league, result.season)
                all_records.extend(records)
            else:
                failed_seasons.append(result.season)
        
        return all_records, failed_seasons

def parse_seasons(seasons_str: str) -> list[str]:
    seasons = []
    
    for part in seasons_str.split(","):
        part = part.strip()
        
        if "-" in part:
            start, end = part.split("-")
            for year in range(int(start), int(end) + 1):
                seasons.append(str(year))
        else:
            seasons.append(part)
    
    return sorted(set(seasons))


def main():
    parser = argparse.ArgumentParser(description="Collect football match data")
    parser.add_argument("--sources", required=True, help="Data source (e.g., understat)")
    parser.add_argument("--league", required=True, help="League code (e.g., EPL)")
    parser.add_argument("--seasons", required=True, help="Seasons: 2024 or 2020-2024 or 2016,2019,2020-2024")
    parser.add_argument("--output", default="data/raw", help="Output directory")
    
    args = parser.parse_args()
    seasons = parse_seasons(args.seasons)
    
    print(f"Fetching seasons: {seasons}")
    
    source = UnderstatSource()
    records, failures = source.fetch_and_transform_seasons(args.league, seasons)
    
    if failures:
        print(f"Failed seasons: {failures}")
    
    print(f"Collected {len(records)} matches")


if __name__ == "__main__":
    main()