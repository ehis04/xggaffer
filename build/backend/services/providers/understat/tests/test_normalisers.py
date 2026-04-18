from decimal import Decimal

from django.test import SimpleTestCase

from services.providers.understat.normalisers import (
    normalise_understat_player_season,
    normalise_understat_team_player,
    normalise_understat_team_season,
)


class UnderstatNormaliserTests(SimpleTestCase):
    def test_normalise_understat_team_season_returns_expected_shape(self):
        payload = {
            "team_external_id": "Arsenal",
            "league": "EPL",
            "stats": [
                {
                    "result": "w",
                    "scored": "2",
                    "missed": "1",
                    "xG": "1.40",
                    "xGA": "0.80",
                    "npxG": "1.10",
                    "ppda": {"att": "9", "def": "1"},
                },
                {
                    "result": "d",
                    "scored": "1",
                    "missed": "1",
                    "xG": "0.70",
                    "xGA": "0.60",
                    "npxG": "0.50",
                    "ppda": {"att": "12", "def": "2"},
                },
            ],
        }

        result = normalise_understat_team_season(
            payload,
            season_label="2024",
            competition_code="EPL",
        )

        self.assertEqual(result["provider"], "understat")
        self.assertEqual(result["season_label"], "2024")
        self.assertEqual(result["competition_code"], "EPL")
        self.assertEqual(result["external_team_id"], "Arsenal")
        self.assertEqual(result["matches_played"], 2)
        self.assertEqual(result["wins"], 1)
        self.assertEqual(result["draws"], 1)
        self.assertEqual(result["losses"], 0)
        self.assertEqual(result["goals_for"], 3)
        self.assertEqual(result["goals_against"], 2)
        self.assertEqual(result["xg"], Decimal("2.10"))
        self.assertEqual(result["xga"], Decimal("1.40"))
        self.assertEqual(result["npxg"], Decimal("1.60"))
        self.assertEqual(result["ppda"], Decimal("7.00"))
        self.assertEqual(result["metadata"]["source"], "understat")
        self.assertEqual(len(result["raw_snapshot"]["history_rows"]), 2)

    def test_normalise_understat_player_season_returns_expected_shape(self):
        payload = {
            "player_external_id": "19",
            "groups": [
                {
                    "season": "2024",
                    "league": "EPL",
                    "team_id": "arsenal",
                    "team_title": "Arsenal",
                    "games": "10",
                    "time": "900",
                    "goals": "4",
                    "assists": "3",
                    "shots": "15",
                    "xG": "3.66",
                    "xA": "2.10",
                    "npg": "4",
                    "npxG": "3.00",
                    "key_passes": "11",
                }
            ],
        }

        result = normalise_understat_player_season(
            payload,
            season_label="2024",
            competition_code="EPL",
        )

        self.assertEqual(result["provider"], "understat")
        self.assertEqual(result["season_label"], "2024")
        self.assertEqual(result["competition_code"], "EPL")
        self.assertEqual(result["competition_name"], "EPL")
        self.assertEqual(result["external_player_id"], "19")
        self.assertEqual(result["external_team_id"], "arsenal")
        self.assertEqual(result["club_name"], "Arsenal")
        self.assertEqual(result["matches_played"], 10)
        self.assertEqual(result["minutes_played"], 900)
        self.assertEqual(result["goals"], 4)
        self.assertEqual(result["assists"], 3)
        self.assertEqual(result["shots"], 15)
        self.assertEqual(result["xg"], Decimal("3.66"))
        self.assertEqual(result["xa"], Decimal("2.10"))
        self.assertEqual(result["npg"], Decimal("4.00"))
        self.assertEqual(result["npxg"], Decimal("3.00"))
        self.assertEqual(result["key_passes"], 11)
        self.assertEqual(result["metadata"]["source"], "understat")
        self.assertEqual(len(result["raw_snapshot"]["selected_groups"]), 1)

    def test_normalisers_handle_missing_or_ambiguous_fields_honestly(self):
        payload = {
            "player_external_id": "25",
            "groups": [
                {
                    "season": "2024",
                    "league": "EPL",
                    "team_id": "arsenal",
                    "team_title": "Arsenal",
                    "games": "8",
                    "time": "640",
                    "goals": "2",
                    "assists": "1",
                    "shots": "9",
                    "xG": "1.70",
                },
                {
                    "season": "2024",
                    "league": "EPL",
                    "team_id": "chelsea",
                    "team_title": "Chelsea",
                    "games": "2",
                    "time": "180",
                    "goals": "0",
                    "assists": "0",
                    "shots": "1",
                    "xG": "0.10",
                },
            ],
        }

        result = normalise_understat_player_season(
            payload,
            season_label="2024",
            competition_code="EPL",
        )

        self.assertEqual(result["external_player_id"], "25")
        self.assertEqual(result["external_team_id"], "")
        self.assertEqual(result["club_name"], "")
        self.assertEqual(result["matches_played"], 10)
        self.assertEqual(result["minutes_played"], 820)
        self.assertEqual(result["goals"], 2)
        self.assertEqual(result["assists"], 1)
        self.assertEqual(result["shots"], 10)
        self.assertEqual(result["xg"], Decimal("1.80"))
        self.assertIsNone(result["xa"])
        self.assertIsNone(result["npg"])
        self.assertIsNone(result["npxg"])
        self.assertEqual(result["key_passes"], 0)
        self.assertEqual(len(result["raw_snapshot"]["selected_groups"]), 2)

    def test_normalise_understat_player_season_matches_competition_aliases(self):
        payload = {
            "player_external_id": "7",
            "groups": [
                {
                    "season": "2024",
                    "league": "EPL",
                    "team_id": "arsenal",
                    "team_title": "Arsenal",
                    "games": "12",
                    "time": "1020",
                    "goals": "6",
                    "assists": "4",
                },
                {
                    "season": "2024",
                    "league": "ChampionsLeague",
                    "team_id": "arsenal",
                    "team_title": "Arsenal",
                    "games": "8",
                    "time": "640",
                    "goals": "2",
                    "assists": "1",
                },
            ],
        }

        result = normalise_understat_player_season(
            payload,
            season_label="2024",
            competition_code="PL",
        )

        self.assertEqual(result["matches_played"], 12)
        self.assertEqual(result["minutes_played"], 1020)
        self.assertEqual(result["goals"], 6)
        self.assertEqual(result["assists"], 4)

    def test_normalise_understat_team_player_maps_extended_metrics(self):
        payload = {
            "id": "5220",
            "player_name": "Kai Havertz",
            "games": "23",
            "time": "1880",
            "goals": "9",
            "xG": "11.830620590597391",
            "assists": "3",
            "xA": "2.9488715566694736",
            "shots": "53",
            "key_passes": "17",
            "yellow_cards": "5",
            "red_cards": "0",
            "position": "F M S",
            "team_title": "Arsenal",
            "npg": "9",
            "npxG": "11.830620590597391",
            "xGChain": "16.01736629009247",
            "xGBuildup": "4.696250442415476",
        }

        result = normalise_understat_team_player(
            payload,
            season_label="2024",
            competition_code="EPL",
            external_team_id="arsenal",
            competition_name="EPL",
        )

        self.assertEqual(result["xg_chain"], Decimal("16.02"))
        self.assertEqual(result["xg_buildup"], Decimal("4.70"))
        self.assertEqual(result["yellow_cards"], 5)
        self.assertEqual(result["red_cards"], 0)