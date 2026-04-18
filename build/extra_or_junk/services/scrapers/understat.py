import requests
from bs4 import BeautifulSoup
import json
from typing import List, Dict, Any
from .base import BaseScraper

class UnderstatScraper(BaseScraper):
    BASE_URL = "https://understat.com"

    def __init__(self):
        super().__init__()
        self.session = requests.Session()

        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/html',
        })

    def scrape_league_season(self, league: str, season: str) -> List[Dict[str, Any]]:          
        url = f"{slef.BASE_URL}/league/{league}/{season}"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            matches_data = self._extract_matches_from_html(response.text)

            standardised_matches = []
            for match in matches_data:
                standardised = self._transform_match_data(match, league, season)
                if self.validate_match_data(standardised):
                    standardised_matches.append(standardised)
                else:
                    self.logger.warning(f"Invalid match data: {match.get('id')}")
            
            self.logger.ingo(f"Scraped {len(standardised_matches)} matches from {league} {season}")
            return standardised_matches
        except requests.RequestException as e:
            self.handle_scraping_error(e, {'league': league, 'season': season, 'url': url})
            return []

    def _extract_matches_from_html(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, 'html.parser')

        scripts = soup.find_all('script')

        for script in scripts:
            if 'matchesData' in script.text:
                match = re.search(r'JSON\.parse\(\'(.+?)\'\)', script.text)
                if match:
                    json_str = match.group(1)
                    json_str - json_str.encode().decode('unicode_escape')
                    return json.loads(json_str)

        return []

    def _transform_match_data(self, raw_match: Dict, league: str, season: str) -> Dict[str, Any]:
        return {
            'external_id': f"understat_{raw_match['id']}",
            'home_team': raw_match['h']['title'],
            'away_team': raw_match['a']['title'],
            'match_date': raw_match['datetime'],
            'season': season,
            'league': league,
            'home_xg': float(raw_match['xG']['h']),
            'away_xg': float(raw_match['xG']['a']),
            'home_goals': int(raw_match['goals']['h']),
            'away_goals': int(raw_match['goals']['a']),
            'raw_data': raw_match, 
        }     


    def validate_match_data(self, match_data: Dict[str, Any]) -> bool:
        required_fields = [
            'external_id', 'home_team', 'away_team', 
            'match_date', 'home_xg', 'away_xg'
        ]

        if not all(field in match_data for field in required_fields):
            return False
        
        if not (0 <= match_data['home_xg'] <= 10):
            return False
        if not (0 <= match_data['away_xg'] <= 10):
            return False
        
        return True