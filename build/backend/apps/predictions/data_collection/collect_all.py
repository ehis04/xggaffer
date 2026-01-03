import argparse
from pathlib import Path

from .sources.understat import UnderstatSource, parse_seasons
from .sources.football_data import FootballDataSource
from .merger import merge_sources

SOURCES = {
    'understat': UnderstatSource,
    'football_data': FootballDataSource,
}

def collect(sources: list[str], league: str, seasons_str: str, merge: bool = False):
    seasons = parse_seasons(seasons_str)
    print(f"Collecting {league} for seasons: {seasons}")
    
    source_files = []
    
    for source_name in sources:
        if source_name not in SOURCES:
            print(f"Unknown source: {source_name}")
            continue
        
        source = SOURCES[source_name]()
        
        for season in seasons:
            filepath = source.collect(league, season)
            source_files.append(filepath)
            print(f"Collected {source_name} {season} → {filepath}")
    
    if merge and len(source_files) > 1:
        output_path = Path(f"data/merged/{league.lower()}_{seasons_str}.csv")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        merge_sources(source_files, output_path)
        print(f"Merged → {output_path}")
        return output_path
    
    return source_files


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', nargs='+', default=['understat'])
    parser.add_argument('--league', default='EPL')
    parser.add_argument('--seasons', default='2024', help='2024 or 2020-2024 or 2016,2019,2020-2024')
    parser.add_argument('--merge', action='store_true')
    
    args = parser.parse_args()
    collect(args.sources, args.league, args.seasons, args.merge)