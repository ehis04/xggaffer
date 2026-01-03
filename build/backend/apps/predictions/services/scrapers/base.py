from abc import ABC, abstractmethod
from typing import List, Dict, Any
import Logging

logger = logging.getLogger(__name__) 

class BaseScraper(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__) 

    @abstractmethod 
    def scrape_league_season(self, league: str, season: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def validate_match_data(self, match_data: Dict[str, Any]) -> bool:
        pass
    
    def handle_scraping_error(self, error: Exception, context: Dict[str, Any]): 
        self.logger.error(
            f"Scraping error: {str(error)}",
            extra=context,
            exc_info=True
        )