import pandas as pd

from apps.predictions.ml.models.availability.player_id_mapping import (
    _clean_name,
    _to_match_key,
    build_mapping_for_team,
)


class StubTransfermarktClient:

    def __init__(self, squad: list[dict]):
        self._squad = squad

    def fetch_squad_page(self, tm_team_id: int, season: int):
        return None

    def parse_squad(self, soup) -> list[dict]:
        return list(self._squad)


def _understat_players(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["name_clean"] = df["name"].apply(_clean_name)
    df["name_match_key"] = df["name"].apply(_to_match_key)
    return df


def test_build_mapping_for_team_handles_nickname_aliases_and_unique_matches():
    understat_players = _understat_players([
        {
            "player_id": 794839,
            "name": "Gabriel Jesus",
            "team": "Arsenal",
            "league": "EPL",
            "season": 2023,
        },
        {
            "player_id": 869792,
            "name": "Gabriel Magalhães",
            "team": "Arsenal",
            "league": "EPL",
            "season": 2023,
        },
        {
            "player_id": 858194,
            "name": "Edward Nketiah",
            "team": "Arsenal",
            "league": "EPL",
            "season": 2023,
        },
    ])
    client = StubTransfermarktClient([
        {
            "tm_player_id": 435338,
            "player_name": "Gabriel",
            "player_slug": "gabriel",
            "position": "Centre-Back",
        },
        {
            "tm_player_id": 363205,
            "player_name": "Gabriel Jesus",
            "player_slug": "gabriel-jesus",
            "position": "Centre-Forward",
        },
        {
            "tm_player_id": 340324,
            "player_name": "Eddie Nketiah",
            "player_slug": "eddie-nketiah",
            "position": "Centre-Forward",
        },
    ])

    results = build_mapping_for_team(
        tm_team_id=11,
        understat_team_name="Arsenal",
        season=2023,
        understat_players=understat_players,
        client=client,
    )

    mapped_ids = {row["tm_player_id"]: row["understat_player_id"] for row in results}

    assert mapped_ids[435338] == 869792
    assert mapped_ids[363205] == 794839
    assert mapped_ids[340324] == 858194
    assert len({row["understat_player_id"] for row in results}) == 3