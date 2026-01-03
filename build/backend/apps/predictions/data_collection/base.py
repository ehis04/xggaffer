import time
import logging
import pandas as pd
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Optional

from .schema import *

logger = logging.getLogger(__name__)


class DataSource(ABC):
    name: str = "base"
    rate_limit_seconds: float = 1.0
    
    def __init__(self, output_dir: str = "data/raw"):
        self.output_dir = Path(output_dir) / self.name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._last_request_time = 0
    
    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - elapsed)
        self._last_request_time = time.time()
    
    @abstractmethod
    def fetch_season(self, league: str, season: str) -> list[dict]:
        pass
    
    @abstractmethod
    def transform(self, raw_data: list[dict], league: str, season: str) -> list[MatchRecord]:
        pass
    
    def validate(self, records: list[MatchRecord]) -> tuple[list[MatchRecord], list[str]]:
        valid = []
        errors = []
        
        for i, record in enumerate(records):
            record_dict = record.to_dict()
            missing = [col for col in REQUIRED_COLUMNS if col not in record_dict or record_dict[col] is None]
            
            if missing:
                errors.append(f"Record {i}: missing {missing}")
            else:
                valid.append(record)
        
        return valid, errors
    
    def save(self, records: list[MatchRecord], league: str, season: str) -> Path:
        df = pd.DataFrame([r.to_dict() for r in records])
        filepath = self.output_dir / f"{league.lower()}_{season}.csv"
        df.to_csv(filepath, index=False)
        logger.info(f"Saved {len(records)} records to {filepath}")
        return filepath
    
    def collect(self, league: str, season: str) -> Path:
        logger.info(f"[{self.name}] Fetching {league} {season}")
        
        raw_data = self.fetch_season(league, season)
        logger.info(f"[{self.name}] Fetched {len(raw_data)} raw records")
        
        records = self.transform(raw_data, league, season)
        logger.info(f"[{self.name}] Transformed to {len(records)} records")
        
        valid_records, errors = self.validate(records)
        if errors:
            for error in errors[:5]:
                logger.warning(f"[{self.name}] {error}")
        
        return self.save(valid_records, league, season)