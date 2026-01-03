from understatapi import UnderstatClient
import json

with UnderstatClient() as client:

    matches = client.league("EPL").get_match_data(season="2024")
    sample_match = matches[0]
    match_id = sample_match['id']
    
    print("=== MATCH LIST DATA ===")
    print(json.dumps(sample_match, indent=2))
    
    print("\n=== INDIVIDUAL MATCH DATA ===")

    match_detail = client.match(match_id).get_shot_data()
    print(f"Keys: {match_detail.keys() if isinstance(match_detail, dict) else type(match_detail)}")
    

    if isinstance(match_detail, dict):
        for key in match_detail:
            print(f"\n--- {key} ---")
            if isinstance(match_detail[key], list) and len(match_detail[key]) > 0:
                print(f"Count: {len(match_detail[key])}")
                print(f"Sample: {json.dumps(match_detail[key][0], indent=2)}")