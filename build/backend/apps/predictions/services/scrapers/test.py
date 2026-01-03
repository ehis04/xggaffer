import pandas as pd

# Load the CSV
df = pd.read_csv('epl_2024_matches.csv')

higher_xg_wins = 0
lower_xg_wins = 0
equal_xg_wins = 0

draw_very_close = 0
draw_slight_edge = 0
draw_clear_edge = 0
draw_big_disparity = 0

draw_ratio_close = 0
draw_ratio_moderate = 0
draw_ratio_big = 0
draw_ratio_very_big = 0

draws_total = 0

home_games = df[df['is_home'] == 1]

for _, row in home_games.iterrows():
    team_xg = row['team_xg']
    opponent_xg = row['opponent_xg']
    result = row['result']
    
    if result == 'W':
        if team_xg > opponent_xg:
            higher_xg_wins += 1
        elif team_xg < opponent_xg:
            lower_xg_wins += 1
        else:
            equal_xg_wins += 1
            
    elif result == 'L':
        if opponent_xg > team_xg:
            higher_xg_wins += 1
        elif opponent_xg < team_xg:
            lower_xg_wins += 1
        else:
            equal_xg_wins += 1
            
    elif result == 'D':
        draws_total += 1
        
        higher_xg = max(team_xg, opponent_xg)
        lower_xg = min(team_xg, opponent_xg)
        diff = higher_xg - lower_xg
        
        if lower_xg > 0:
            ratio = higher_xg / lower_xg
        else:
            ratio = float('inf')
        
        if diff < 0.4:
            draw_very_close += 1
        elif diff < 0.8:
            draw_slight_edge += 1
        elif diff < 1.2:
            draw_clear_edge += 1
        else:
            draw_big_disparity += 1
        if ratio < 1.3:
            draw_ratio_close += 1
        elif ratio < 1.7:
            draw_ratio_moderate += 1
        elif ratio < 2.3:
            draw_ratio_big += 1
        else:
            draw_ratio_very_big += 1


# Print results
print("=" * 50)
print("xG VS ACTUAL RESULTS")
print("=" * 50)
print(f"Higher xG team won:  {higher_xg_wins} matches")
print(f"Lower xG team won:   {lower_xg_wins} matches")
print(f"Equal xG & won:      {equal_xg_wins} matches")
print(f"Draws:               {draws_total} matches")

total_decisive = higher_xg_wins + lower_xg_wins + equal_xg_wins
if total_decisive > 0:
    print(f"\n--- Win Distribution (excluding draws) ---")
    print(f"Higher xG team wins: {higher_xg_wins / total_decisive * 100:.1f}%")
    print(f"Lower xG team wins:  {lower_xg_wins / total_decisive * 100:.1f}%")

print("\n" + "=" * 50)
print("DRAW ANALYSIS: xG DISPARITY")
print("=" * 50)

if draws_total > 0:
    print(f"\n--- By Difference ---")
    print(f"Very close (0.0–0.4):   {draw_very_close:3d} ({draw_very_close/draws_total*100:5.1f}%)")
    print(f"Slight edge (0.4–0.8):  {draw_slight_edge:3d} ({draw_slight_edge/draws_total*100:5.1f}%)")
    print(f"Clear edge (0.8–1.2):   {draw_clear_edge:3d} ({draw_clear_edge/draws_total*100:5.1f}%)")
    print(f"Big disparity (1.2+):   {draw_big_disparity:3d} ({draw_big_disparity/draws_total*100:5.1f}%)")
    
    print(f"\n--- By Ratio ---")
    print(f"Close (1.0–1.3x):       {draw_ratio_close:3d} ({draw_ratio_close/draws_total*100:5.1f}%)")
    print(f"Moderate (1.3–1.7x):    {draw_ratio_moderate:3d} ({draw_ratio_moderate/draws_total*100:5.1f}%)")
    print(f"Big (1.7–2.3x):         {draw_ratio_big:3d} ({draw_ratio_big/draws_total*100:5.1f}%)")
    print(f"Very big (2.3x+):       {draw_ratio_very_big:3d} ({draw_ratio_very_big/draws_total*100:5.1f}%)")