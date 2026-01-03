import time
from pathlib import Path
import pandas as pd
from understatapi import UnderstatClient

LEAGUE = "EPL"
SEASON = "2024"  
OUTPUT_DIR = Path("/mnt/c/Users/ehiso/OneDrive/Code/yr4/2026-csc-1097-adenire-2-oghinae-2/build/backend/data/raw")
OUTPUT_FILE = OUTPUT_DIR / f"epl_{SEASON}_matches.csv"

REQUEST_DELAY_SECONDS = 1.0

def fetch_league_matches(league: str, season: str) -> list[dict]:
    with UnderstatClient() as client:
        matches = client.league(league).get_match_data(season=season)
        return matches

def determine_result(team_goals: int, opponent_goals: int) -> str:
    if team_goals > opponent_goals:
        return 'W'
    elif team_goals < opponent_goals:
        return 'L'
    else:
        return 'D'


def transform_match_to_rows(match: dict) -> list[dict]:
    if not match.get('isResult', False):
        return []

    match_id = match['id']
    match_date = match['datetime'][:10]  
    
    home_team = match['h']['title']
    away_team = match['a']['title']
    
    home_xg = float(match['xG']['h'])
    away_xg = float(match['xG']['a'])
    
    home_goals = int(match['goals']['h'])
    away_goals = int(match['goals']['a'])
    
    home_row = {
        'match_id': match_id,
        'season': SEASON,
        'date': match_date,
        'team': home_team,
        'opponent': away_team,
        'is_home': 1, 
        'team_xg': home_xg,
        'opponent_xg': away_xg,
        'team_goals': home_goals,
        'opponent_goals': away_goals,
        'result': determine_result(home_goals, away_goals),
    }
    
    away_row = {
        'match_id': match_id,
        'season': SEASON,
        'date': match_date,
        'team': away_team,
        'opponent': home_team,
        'is_home': 0,
        'team_xg': away_xg,
        'opponent_xg': home_xg,
        'team_goals': away_goals,
        'opponent_goals': home_goals,
        'result': determine_result(away_goals, home_goals),
    }
    
    return [home_row, away_row]


def transform_all_matches(matches: list[dict]) -> pd.DataFrame:
    all_rows = []
    
    for match in matches:
        rows = transform_match_to_rows(match)
        all_rows.extend(rows)
    
    df = pd.DataFrame(all_rows)
    
    df = df.sort_values('date').reset_index(drop=True)
    
    return df

def validate_dataframe(df: pd.DataFrame) -> tuple[bool, list[str]]:
    errors = []
    
    null_counts = df.isnull().sum()
    if null_counts.any():
        cols_with_nulls = null_counts[null_counts > 0].index.tolist()
        errors.append(f"Null values found in columns: {cols_with_nulls}")

    if (df['team_xg'] < 0).any() or (df['team_xg'] > 10).any():
        errors.append("team_xg contains values outside [0, 10]")
    if (df['opponent_xg'] < 0).any() or (df['opponent_xg'] > 10).any():
        errors.append("opponent_xg contains values outside [0, 10]")

    valid_results = {'W', 'D', 'L'}
    actual_results = set(df['result'].unique())
    if not actual_results.issubset(valid_results):
        invalid = actual_results - valid_results
        errors.append(f"Invalid result values: {invalid}")

    if not set(df['is_home'].unique()).issubset({0, 1}):
        errors.append("is_home contains non-binary values")

    match_counts = df['match_id'].value_counts()
    if (match_counts != 2).any():
        bad_matches = match_counts[match_counts != 2].index.tolist()
        errors.append(f"Matches without exactly 2 rows: {bad_matches[:5]}...")
    
    return len(errors) == 0, errors

def save_to_csv(df: pd.DataFrame, filepath: Path) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(filepath, index=False)
    
    print(f"Saved {len(df)} rows to {filepath}")


def print_summary(df: pd.DataFrame) -> None:
    print("\n" + "=" * 60)
    print("DATA SUMMARY")
    print("=" * 60)
    
    total_matches = len(df) // 2
    print(f"Total matches scraped: {total_matches}")
    print(f"Total rows (2 per match): {len(df)}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    
    print(f"\nTeams in dataset: {df['team'].nunique()}")
    
    print(f"\nResult distribution:")
    result_counts = df['result'].value_counts()
    for result, count in result_counts.items():
        pct = (count / len(df)) * 100
        print(f"  {result}: {count} ({pct:.1f}%)")
    
    print(f"\nxG statistics:")
    print(f"  Mean team xG: {df['team_xg'].mean():.2f}")
    print(f"  Mean opponent xG: {df['opponent_xg'].mean():.2f}")
    print(f"  Max xG in a match: {df['team_xg'].max():.2f}")
    
    print(f"\nSample rows:")
    print(df.head(4).to_string(index=False))

def main():
    print(f"Fetching {LEAGUE} {SEASON} matches from Understat...")
    start_time = time.time()
    
    raw_matches = fetch_league_matches(LEAGUE, SEASON)
    print(f"Fetched {len(raw_matches)} matches from API")
    
    df = transform_all_matches(raw_matches)
    print(f"Transformed to {len(df)} rows (2 per completed match)")
    
    is_valid, errors = validate_dataframe(df)
    if not is_valid:
        print("VALIDATION ERRORS:")
        for error in errors:
            print(f"  - {error}")
        print("Proceeding anyway, but check your data!")
    else:
        print("Validation passed")
    
    save_to_csv(df, OUTPUT_FILE)
    
    print_summary(df)
    
    elapsed = time.time() - start_time
    print(f"\nCompleted in {elapsed:.1f} seconds")


if __name__ == "__main__":
    main()
