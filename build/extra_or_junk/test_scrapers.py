import sys
from pathlib import Path


data_collection_dir = Path(__file__).parent
sys.path.insert(0, str(data_collection_dir))

from understatapi import UnderstatClient
from sources.understat.matches import fetch_match, get_shot_zone
from sources.understat.leagues import fetch_league_season
from sources.understat.players import fetch_player_season, fetch_player_all_seasons
from sources.understat.teams import (
    fetch_team_season,
    fetch_team_formations,
    fetch_team_game_states,
    fetch_team_attack_speeds,
    fetch_team_summary,
)


def test_shot_zones():
    print("=" * 60)
    print(" TEST 1: Shot Zone Function")
    print("=" * 60)
    
    test_cases = [
        (0.95, 0.5, "six_yard"),      
        (0.89, 0.5, "penalty_area"),
        (0.75, 0.5, "outside_box"), 
        (0.85, 0.1, "outside_box"),
    ]
    
    all_passed = True
    for x, y, expected in test_cases:
        result = get_shot_zone(x, y)
        status = "PASS" if result == expected else "FAIL"
        if result != expected:
            all_passed = False
        print(f"[{status}] get_shot_zone({x}, {y}) = {result} (expected: {expected})")
    
    return all_passed


def test_fetch_match():
    print("=" * 60)
    print(" TEST 2: Fetch Single Match (Burnley vs Newcastle, match 28960)")
    print("=" * 60)
    
    client = UnderstatClient()
    match_data = fetch_match(client, "28960")
    
    if not match_data:
        print("[FAIL] Could not fetch match data")
        return False
    
    print(f"{match_data['home_team']} {match_data['home_goals']} - {match_data['away_goals']} {match_data['away_team']}")
    print(f"Date: {match_data['date']}")
    
    print("\nShot Stats:")
    print(f"  Home shots: {match_data['home_shots']} (xG: {match_data['home_xg']})")
    print(f"  Away shots: {match_data['away_shots']} (xG: {match_data['away_xg']})")
    
    print("\nShot Zones (Home):")
    print(f"  Six-yard: {match_data['home_shots_six_yard']}")
    print(f"  Penalty area: {match_data['home_shots_penalty_area']}")
    print(f"  Outside box: {match_data['home_shots_outside_box']}")
    
    print("\nShot Zones (Away):")
    print(f"  Six-yard: {match_data['away_shots_six_yard']}")
    print(f"  Penalty area: {match_data['away_shots_penalty_area']}")
    print(f"  Outside box: {match_data['away_shots_outside_box']}")
    
    print("\nExpected Points:")
    print(f"  Home xPTS: {match_data['home_xpts']}")
    print(f"  Away xPTS: {match_data['away_xpts']}")
    
    print("\nGoal Minutes:")
    print(f"  Home: {match_data['home_goal_minutes']}")
    print(f"  Away: {match_data['away_goal_minutes']}")
    
    print("\n--- Validation Checks ---")
    home_shots = match_data['home_shots']
    
    shots_by_result = (
        match_data['home_goals'] +
        match_data['home_missed_shots'] +
        match_data['home_blocked_shots'] +
        match_data['home_saved_shots'] +
        match_data['home_shots_on_post']
    )
    
    shots_by_zone = (
        match_data['home_shots_six_yard'] +
        match_data['home_shots_penalty_area'] +
        match_data['home_shots_outside_box']
    )
    
    print(f"Home shots total: {home_shots}")
    result_check = "PASS" if shots_by_result == home_shots else "FAIL"
    zone_check = "PASS" if shots_by_zone == home_shots else "FAIL"
    print(f"Home shots by result: {shots_by_result} [{result_check}]")
    print(f"Home shots by zone: {shots_by_zone} [{zone_check}]")
    
    return result_check == "PASS" and zone_check == "PASS"


def test_fetch_league():
    print("=" * 60)
    print(" TEST 3: Fetch League Season (EPL 2024)")
    print("=" * 60)
    
    client = UnderstatClient()
    teams = fetch_league_season(client, "EPL", "2024")
    
    if not teams:
        print("[FAIL] Could not fetch league data")
        return False
    
    print(f"Fetched {len(teams)} teams")
    
    has_data = any(t['npxgd'] != 0 for t in teams)
    
    if not has_data:
        print("[FAIL] All NPxGD values are 0 - data not parsed correctly")
        return False
    
    print("\nTop 5 by NPxGD:")
    for team in teams[:5]:
        print(f"  {team['team']}: NPxGD={team['npxgd']}, PPDA={team['ppda']}, OPPDA={team['oppda']}, Deep={team['deep']}")
    
    print("\nBottom 3 by NPxGD:")
    for team in teams[-3:]:
        print(f"  {team['team']}: NPxGD={team['npxgd']}, PPDA={team['ppda']}")
    
    print("\n--- Validation Checks ---")
    first_team = teams[0]
    
    checks_passed = True
    
    if not -50 < first_team['npxgd'] < 50:
        print(f"[FAIL] NPxGD out of range: {first_team['npxgd']}")
        checks_passed = False
    else:
        print(f"[PASS] NPxGD in reasonable range: {first_team['npxgd']}")
    
    if not 3 < first_team['ppda'] < 25:
        print(f"[FAIL] PPDA out of range: {first_team['ppda']}")
        checks_passed = False
    else:
        print(f"[PASS] PPDA in reasonable range: {first_team['ppda']}")
    
    return checks_passed


def test_fetch_player():
    print("=" * 60)
    print(" TEST 4: Fetch Player (Salah, ID 1250, Season 2025)")
    print("=" * 60)
    
    client = UnderstatClient()
    
    player_raw = client.player("1250").get_season_data()
    season_list = player_raw.get('season', [])
    available_seasons = [s.get('season') for s in season_list]
    print(f"Available seasons for Salah: {available_seasons}")
    
    test_season = available_seasons[0] if available_seasons else "2025"
    print(f"Testing with season: {test_season}")
    
    player_data = fetch_player_season(client, "1250", test_season)
    
    if not player_data:
        print("[FAIL] Could not fetch player data")
        return False
    
    print(f"\nPlayer: {player_data.get('name', 'N/A')} ({player_data['team']})")
    print(f"Position: {player_data['position']}")
    print(f"Season: {player_data['season']}")
    
    print("\nRaw Stats:")
    print(f"  Games: {player_data['games']}")
    print(f"  Minutes: {player_data['minutes']}")
    print(f"  Goals: {player_data['goals']} (NPG: {player_data['npg']})")
    print(f"  Assists: {player_data['assists']}")
    print(f"  xG: {player_data['xg']} (NPxG: {player_data['npxg']})")
    print(f"  xA: {player_data['xa']}")
    print(f"  Shots: {player_data['shots']}")
    print(f"  Key Passes: {player_data['key_passes']}")
    
    print("\nPer-90 Stats:")
    print(f"  G/90: {player_data['g90']}")
    print(f"  xG/90: {player_data['xg90']}")
    print(f"  NPxG/90: {player_data['npxg90']}")
    print(f"  xA/90: {player_data['xa90']}")
    print(f"  Sh/90: {player_data['sh90']}")
    print(f"  KP/90: {player_data['kp90']}")
    
    print("\nCombined Metrics:")
    print(f"  xG+xA/90: {player_data['xg90_xa90']}")
    print(f"  NPxG+xA/90: {player_data['npxg90_xa90']}")
    
    print("\n--- Validation Checks ---")
    checks_passed = True
    
    if player_data['minutes'] > 0:
        print(f"[PASS] Has minutes played: {player_data['minutes']}")
    else:
        print("[FAIL] No minutes played")
        checks_passed = False
    
    if player_data['team'] == 'Liverpool':
        print(f"[PASS] Correct team: {player_data['team']}")
    else:
        print(f"[WARN] Unexpected team: {player_data['team']} (expected Liverpool)")
    
    return checks_passed


def test_fetch_team():
    print("=" * 60)
    print(" TEST 5: Fetch Team Summary (Arsenal, 2024)")
    print("=" * 60)
    
    client = UnderstatClient()
    
    print("\n--- Basic Team Stats ---")
    team_stats = fetch_team_season(client, "Arsenal", "2024")
    
    if not team_stats:
        print("[FAIL] Could not fetch team data")
        return False
    
    print(f"Arsenal 2024 Season:")
    print(f"  Matches Played: {team_stats['matches_played']}")
    print(f"  Total xG: {team_stats['total_xg']}")
    print(f"  Total xGA: {team_stats['total_xga']}")
    print(f"  xGD: {team_stats['xgd']}")
    
    print("\n--- Formations ---")
    formations = fetch_team_formations(client, "Arsenal", "2024")
    
    if formations:
        print(f"Primary: {formations[0]['formation']} ({formations[0]['minutes']} mins)")
        print(f"All used: {', '.join([f['formation'] for f in formations])}")
    else:
        print("[WARN] No formation data")
    
    print("\n--- Game States ---")
    game_states = fetch_team_game_states(client, "Arsenal", "2024")
    
    if game_states:
        for gs in game_states:
            print(f"  {gs['game_state']}: {gs['minutes']} mins, xG={gs['xg']}")
    else:
        print("[WARN] No game state data")
    
    print("\n--- Attack Speeds ---")
    attack_speeds = fetch_team_attack_speeds(client, "Arsenal", "2024")
    
    if attack_speeds:
        for speed in attack_speeds:
            print(f"  {speed['attack_speed'].capitalize()}: {speed['shots']} shots, {speed['xg']} xG")
    else:
        print("[WARN] No attack speed data")
    
    print("\n--- Full Summary ---")
    summary = fetch_team_summary(client, "Arsenal", "2024")
    
    if summary:
        print(f"  Primary Formation: {summary['primary_formation']}")
        print(f"  Total Shots: {summary['total_shots']}")
        print(f"  xG/Shot: {summary['xg_per_shot']}")
        print(f"  xG when drawing: {summary['xg_when_drawing']}")
        print(f"  xG when winning: {summary['xg_when_winning']}")
        print(f"  xG when losing: {summary['xg_when_losing']}")
    else:
        print("[FAIL] Could not fetch team summary")
        return False
    
    print("\n--- Validation Checks ---")
    checks_passed = True
    
    # xG should be reasonable for a full season (40-80 for a top team)
    if 30 < team_stats['total_xg'] < 100:
        print(f"[PASS] xG in reasonable range: {team_stats['total_xg']}")
    else:
        print(f"[FAIL] xG out of range: {team_stats['total_xg']}")
        checks_passed = False
    
    # xGA should also be reasonable
    if 20 < team_stats['total_xga'] < 80:
        print(f"[PASS] xGA in reasonable range: {team_stats['total_xga']}")
    else:
        print(f"[FAIL] xGA out of range: {team_stats['total_xga']}")
        checks_passed = False
    
    # xGD should be positive for a top team
    if team_stats['xgd'] > 0:
        print(f"[PASS] Positive xGD (good team): {team_stats['xgd']}")
    else:
        print(f"[WARN] Negative xGD: {team_stats['xgd']}")
    
    # Total shots should be reasonable (300-600 for a season)
    if 200 < summary['total_shots'] < 700:
        print(f"[PASS] Total shots in reasonable range: {summary['total_shots']}")
    else:
        print(f"[WARN] Total shots unusual: {summary['total_shots']}")
    
    return checks_passed


def main():
    results = {}
    
    results['shot_zones'] = test_shot_zones()
    print()
    
    results['match'] = test_fetch_match()
    print()
    
    results['league'] = test_fetch_league()
    print()
    
    results['player'] = test_fetch_player()
    print()
    
    results['team'] = test_fetch_team()
    print()
    
    print("=" * 60)
    print(" TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    return all(results.values())


if __name__ == "__main__":
    main()