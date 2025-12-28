import pandas as pd
from pathlib import Path
from fuzzywuzzy import fuzz


def normalise_team_name(name: str) -> str:
    replacements = {
        "Manchester United": "Man United",
        "Manchester City": "Man City",
        "Tottenham Hotspur": "Tottenham",
        "West Ham United": "West Ham",
        "Wolverhampton Wanderers": "Wolves",
        "Brighton and Hove Albion": "Brighton",
        "Nottingham Forest": "Nott'm Forest",
    }
    return replacements.get(name, name)


def match_key(row: pd.Series) -> str:
    home = normalise_team_name(row['home_team'])
    away = normalise_team_name(row['away_team'])
    return f"{row['date']}_{home}_{away}"


def merge_sources(source_files: list[Path], output_path: Path) -> pd.DataFrame:
    dfs = []
    
    for filepath in source_files:
        df = pd.read_csv(filepath)
        df['_match_key'] = df.apply(match_key, axis=1)
        dfs.append(df)
    
    if not dfs:
        raise ValueError("No source files provided")
    
    merged = dfs[0]
    
    for df in dfs[1:]:
        new_cols = [c for c in df.columns if c not in merged.columns and c != '_match_key']
        if new_cols:
            merge_subset = df[['_match_key'] + new_cols]
            merged = merged.merge(merge_subset, on='_match_key', how='left')
    
    merged = merged.drop(columns=['_match_key'])
    merged.to_csv(output_path, index=False)
    
    return merged