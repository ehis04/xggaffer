import argparse
from pathlib import Path
from typing import Optional
from understatapi import UnderstatClient

from sources.understat.matches import fetch_match
from sources.understat.leagues import fetch_league_season
from sources.understat.players import fetch_player_season, fetch_player_all_seasons
from sources.understat.teams import fetch_team_season, fetch_team_summary


SUPPORTED_LEAGUES = ['EPL', 'La_Liga', 'Bundesliga', 'Serie_A', 'Ligue_1', 'RFPL']

DATA_DIR = Path(__file__).resolve().parents[4] / 'data/raw/understat'


def parse_seasons(seasons_str: str) -> list[str]:
    seasons = []
    for part in seasons_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = part.split('-')
            seasons.extend(str(y) for y in range(int(start), int(end) + 1))
        else:
            seasons.append(part)
    return seasons


def save_to_csv(data: list[dict], filepath: Path) -> None:
    if not data:
        return
    
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    import csv
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)


def collect_matches(client: UnderstatClient, league: str, season: str) -> list[dict]:
    league_matches = client.league(league).get_match_data(season=season)
    
    if not league_matches:
        return []
    
    results = []
    match_ids = [m.get('id') for m in league_matches if m.get('isResult')]
    
    total = len(match_ids)
    for i, match_id in enumerate(match_ids, 1):
        print(f"  Fetching match {i}/{total}: {match_id}", end='\r')
        match_data = fetch_match(client, str(match_id))
        if match_data:
            match_data['league'] = league
            match_data['source'] = 'understat'
            results.append(match_data)
    
    print()
    return results


def collect_league_teams(client: UnderstatClient, league: str, season: str) -> list[dict]:
    return fetch_league_season(client, league, season)


def collect_team_summaries(client: UnderstatClient, league: str, season: str) -> list[dict]:
    teams_data = client.league(league).get_team_data(season=season)
    
    if not teams_data:
        return []
    
    results = []
    team_names = [info.get('title') for info in teams_data.values()]
    
    total = len(team_names)
    for i, team_name in enumerate(team_names, 1):
        print(f"  Fetching team {i}/{total}: {team_name}", end='\r')
        summary = fetch_team_summary(client, team_name, season)
        if summary:
            summary['league'] = league
            results.append(summary)
    
    print()
    return results


def collect_players(client: UnderstatClient, league: str, season: str) -> list[dict]:
    players_data = client.league(league).get_player_data(season=season)
    
    if not players_data:
        return []
    
    results = []
    
    for player in players_data:
        minutes = int(player.get('time', 0) or 0)
        goals = int(player.get('goals', 0) or 0)
        xg = float(player.get('xG', 0) or 0)
        npxg = float(player.get('npxG', 0) or 0)
        xa = float(player.get('xA', 0) or 0)
        shots = int(player.get('shots', 0) or 0)
        key_passes = int(player.get('key_passes', 0) or 0)
        
        g90 = round(goals / (minutes / 90), 2) if minutes > 0 else 0.0
        xg90 = round(xg / (minutes / 90), 2) if minutes > 0 else 0.0
        npxg90 = round(npxg / (minutes / 90), 2) if minutes > 0 else 0.0
        xa90 = round(xa / (minutes / 90), 2) if minutes > 0 else 0.0
        sh90 = round(shots / (minutes / 90), 2) if minutes > 0 else 0.0
        kp90 = round(key_passes / (minutes / 90), 2) if minutes > 0 else 0.0
        
        results.append({
            'player_id': player.get('id', ''),
            'name': player.get('player_name', ''),
            'team': player.get('team_title', ''),
            'position': player.get('position', ''),
            'league': league,
            'season': season,
            'games': int(player.get('games', 0) or 0),
            'minutes': minutes,
            'goals': goals,
            'assists': int(player.get('assists', 0) or 0),
            'npg': int(player.get('npg', 0) or 0),
            'xg': round(xg, 2),
            'npxg': round(npxg, 2),
            'xa': round(xa, 2),
            'shots': shots,
            'key_passes': key_passes,
            'yellow_cards': int(player.get('yellow_cards', 0) or 0),
            'red_cards': int(player.get('red_cards', 0) or 0),
            'xg_chain': round(float(player.get('xGChain', 0) or 0), 2),
            'xg_buildup': round(float(player.get('xGBuildup', 0) or 0), 2),
            'g90': g90,
            'xg90': xg90,
            'npxg90': npxg90,
            'xa90': xa90,
            'sh90': sh90,
            'kp90': kp90,
            'xg90_xa90': round(xg90 + xa90, 2),
            'npxg90_xa90': round(npxg90 + xa90, 2),
        })
    
    return results


def collect(
    league: str,
    seasons_str: str,
    include_matches: bool = True,
    include_teams: bool = True,
    include_team_summaries: bool = False,
    include_players: bool = False,
    output_dir: Optional[Path] = None,
) -> dict[str, list[Path]]:
    
    seasons = parse_seasons(seasons_str)
    output_dir = output_dir or DATA_DIR
    
    print(f"Collecting {league} for seasons: {seasons}")
    
    client = UnderstatClient()
    
    output_files = {
        'matches': [],
        'teams': [],
        'team_summaries': [],
        'players': [],
    }
    
    for season in seasons:
        print(f"\n=== Season {season} ===")
        
        if include_matches:
            print(f"Collecting matches...")
            matches = collect_matches(client, league, season)
            if matches:
                filepath = output_dir / 'matches' / f"{league.lower()}_{season}_matches.csv"
                save_to_csv(matches, filepath)
                output_files['matches'].append(filepath)
                print(f"  Saved {len(matches)} matches → {filepath}")
        
        if include_teams:
            print(f"Collecting team stats...")
            teams = collect_league_teams(client, league, season)
            if teams:
                filepath = output_dir / 'teams' / f"{league.lower()}_{season}_teams.csv"
                save_to_csv(teams, filepath)
                output_files['teams'].append(filepath)
                print(f"  Saved {len(teams)} teams → {filepath}")
        
        if include_team_summaries:
            print(f"Collecting team summaries...")
            summaries = collect_team_summaries(client, league, season)
            if summaries:
                filepath = output_dir / 'team_summaries' / f"{league.lower()}_{season}_team_summaries.csv"
                save_to_csv(summaries, filepath)
                output_files['team_summaries'].append(filepath)
                print(f"  Saved {len(summaries)} team summaries → {filepath}")
        
        if include_players:
            print(f"Collecting player stats...")
            players = collect_players(client, league, season)
            if players:
                filepath = output_dir / 'players' / f"{league.lower()}_{season}_players.csv"
                save_to_csv(players, filepath)
                output_files['players'].append(filepath)
                print(f"  Saved {len(players)} players → {filepath}")
    
    return output_files


def merge_season_files(files: list[Path], output_path: Path) -> None:
    if not files:
        return
    
    import csv
    
    all_data = []
    fieldnames = None
    
    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if fieldnames is None:
                fieldnames = reader.fieldnames
            all_data.extend(list(reader))
    
    if all_data:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--league', default='EPL', choices=SUPPORTED_LEAGUES)
    parser.add_argument('--seasons', default='2024', help='2024 or 2020-2024 or 2020,2022,2024')
    parser.add_argument('--matches', action='store_true', default=False)
    parser.add_argument('--teams', action='store_true', default=False)
    parser.add_argument('--team-summaries', action='store_true', default=False)
    parser.add_argument('--players', action='store_true', default=False)
    parser.add_argument('--all', action='store_true', default=False)
    parser.add_argument('--merge', action='store_true', default=False)
    parser.add_argument('--output-dir', type=Path, default=None)
    
    args = parser.parse_args()
    
    if args.all:
        include_matches = True
        include_teams = True
        include_team_summaries = True
        include_players = True
    else:
        include_matches = args.matches
        include_teams = args.teams
        include_team_summaries = args.team_summaries
        include_players = args.players
    
    if not any([include_matches, include_teams, include_team_summaries, include_players]):
        include_matches = True
        include_teams = True
    
    output_files = collect(
        league=args.league,
        seasons_str=args.seasons,
        include_matches=include_matches,
        include_teams=include_teams,
        include_team_summaries=include_team_summaries,
        include_players=include_players,
        output_dir=args.output_dir,
    )
    
    if args.merge:
        seasons_label = args.seasons.replace(',', '_').replace('-', '_')
        output_dir = args.output_dir or DATA_DIR
        
        for data_type, files in output_files.items():
            if len(files) > 1:
                merged_path = output_dir / 'merged' / f"{args.league.lower()}_{seasons_label}_{data_type}.csv"
                merge_season_files(files, merged_path)
                print(f"Merged {data_type} → {merged_path}")
    
    print("\nDone.")