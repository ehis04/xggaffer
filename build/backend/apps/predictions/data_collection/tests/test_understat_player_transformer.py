from data_collection.transformers.understat.players import transform_understat_player_raw


def test_transform_understat_player_uses_team_title_when_team_missing():
    raw_player = {
        "player_id": "8260",
        "season": "2025",
        "season_stats": {
            "player_name": "Erling Haaland",
            "team_title": "Manchester City",
            "position": "F",
            "time": "2439",
            "goals": "22",
            "assists": "7",
            "npg": "19",
            "xG": "23.13",
            "npxG": "20.09",
            "xA": "4.76",
            "shots": "102",
            "key_passes": "21",
            "yellow_cards": "1",
            "red_cards": "0",
            "xGChain": "26.23",
            "xGBuildup": "4.12",
            "games": "29",
        },
    }

    row = transform_understat_player_raw(raw_player, league="EPL", season="2025")

    assert row["source"] == "understat"
    assert row["team"] == "Manchester City"
    assert row["name"] == "Erling Haaland"


def test_transform_understat_player_prefers_team_field_when_available():
    raw_player = {
        "player_id": "999",
        "season": "2025",
        "season_stats": {
            "player_name": "Sample Player",
            "team": "Arsenal",
            "team_title": "Ignored Team Title",
            "time": "900",
            "goals": "5",
            "assists": "2",
            "npg": "5",
            "xG": "4.0",
            "npxG": "4.0",
            "xA": "1.0",
            "shots": "20",
            "key_passes": "10",
            "yellow_cards": "0",
            "red_cards": "0",
            "xGChain": "5.0",
            "xGBuildup": "1.5",
            "games": "10",
        },
    }

    row = transform_understat_player_raw(raw_player, league="EPL", season="2025")

    assert row["team"] == "Arsenal"


def test_transform_understat_player_normalizes_multi_team_string_to_primary_team():
    raw_player = {
        "player_id": "123",
        "season": "2025",
        "season_stats": {
            "player_name": "Transfer Player",
            "team_title": "West Ham,Wolverhampton Wanderers",
            "time": "450",
            "goals": "1",
            "assists": "1",
            "npg": "1",
            "xG": "1.2",
            "npxG": "1.2",
            "xA": "0.7",
            "shots": "7",
            "key_passes": "6",
            "yellow_cards": "1",
            "red_cards": "0",
            "xGChain": "2.0",
            "xGBuildup": "1.0",
            "games": "9",
        },
    }

    row = transform_understat_player_raw(raw_player, league="EPL", season="2025")

    assert row["team"] == "West Ham"
