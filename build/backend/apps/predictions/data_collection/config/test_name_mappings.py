import pytest

from data_collection.config.team_name_mappings import (
    CANONICAL_TEAM_NAMES,
    SUPPORTED_SOURCES as TEAM_SOURCES,
    UNDERSTAT_ALIASES,
    from_canonical as team_from_canonical,
    to_canonical as team_to_canonical,
)
from data_collection.config.league_name_mappings import (
    CANONICAL_LEAGUE_NAMES,
    SUPPORTED_SOURCES as LEAGUE_SOURCES,
    from_canonical as league_from_canonical,
    to_canonical as league_to_canonical,
)


CURRENT_SEASON_TEAMS = {
    "EPL": [
        "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton",
        "Chelsea", "Crystal Palace", "Everton", "Fulham", "Ipswich",
        "Leicester", "Liverpool", "Manchester City", "Manchester United",
        "Newcastle United", "Nottingham Forest", "Southampton", "Tottenham",
        "West Ham", "Wolverhampton Wanderers",
    ],
    "La_Liga": [
        "Alaves", "Athletic Club", "Atletico Madrid", "Barcelona",
        "Celta Vigo", "Espanyol", "Getafe", "Girona", "Las Palmas",
        "Leganes", "Mallorca", "Osasuna", "Rayo Vallecano", "Real Betis",
        "Real Madrid", "Real Sociedad", "Real Valladolid", "Sevilla",
        "Valencia", "Villarreal",
    ],
    "Bundesliga": [
        "Augsburg", "Bayer Leverkusen", "Bayern Munich", "Bochum",
        "Borussia Dortmund", "Borussia M.Gladbach", "Eintracht Frankfurt",
        "FC Heidenheim", "Freiburg", "Hoffenheim", "Holstein Kiel",
        "Mainz 05", "RasenBallsport Leipzig", "St. Pauli", "Union Berlin",
        "VfB Stuttgart", "Werder Bremen", "Wolfsburg",
    ],
    "Serie_A": [
        "AC Milan", "Atalanta", "Bologna", "Cagliari", "Como", "Empoli",
        "Fiorentina", "Genoa", "Inter", "Juventus", "Lazio", "Lecce",
        "Monza", "Napoli", "Parma Calcio 1913", "Roma", "Torino",
        "Udinese", "Venezia", "Verona",
    ],
    "Ligue_1": [
        "Angers", "Auxerre", "Brest", "Le Havre", "Lens", "Lille",
        "Lyon", "Marseille", "Monaco", "Montpellier", "Nantes", "Nice",
        "Paris Saint Germain", "Reims", "Rennes", "Saint-Etienne",
        "Strasbourg", "Toulouse",
    ],
}


# -----------------------------------------------------------------------
# Team mapping — structural integrity
# -----------------------------------------------------------------------

class TestTeamMappingStructure:

    def test_no_duplicate_canonical_names(self):
        names = list(CANONICAL_TEAM_NAMES.keys())
        assert len(names) == len(set(names))

    def test_every_entry_has_understat_key(self):
        for canonical, names in CANONICAL_TEAM_NAMES.items():
            assert "understat" in names, (
                f"'{canonical}' is missing its 'understat' mapping"
            )

    def test_understat_value_matches_canonical_key(self):
        for canonical, names in CANONICAL_TEAM_NAMES.items():
            assert names["understat"] == canonical, (
                f"'{canonical}' has understat value '{names['understat']}' — "
                f"these must match"
            )

    def test_no_sofascore_name_maps_to_two_canonicals(self):
        seen = {}
        for canonical, names in CANONICAL_TEAM_NAMES.items():
            if "sofascore" not in names:
                continue
            ss_name = names["sofascore"]
            assert ss_name not in seen, (
                f"SofaScore name '{ss_name}' maps to both "
                f"'{seen[ss_name]}' and '{canonical}'"
            )
            seen[ss_name] = canonical

    def test_aliases_point_to_existing_canonicals(self):
        for alias, canonical in UNDERSTAT_ALIASES.items():
            assert canonical in CANONICAL_TEAM_NAMES, (
                f"Alias '{alias}' points to '{canonical}' which is not "
                f"a canonical team name"
            )


# -----------------------------------------------------------------------
# Team mapping — Understat resolution
# -----------------------------------------------------------------------

class TestAllUnderstatTeamsMapped:

    @pytest.mark.parametrize("league", CURRENT_SEASON_TEAMS.keys())
    def test_current_season_teams_resolve(self, league):
        for team in CURRENT_SEASON_TEAMS[league]:
            result = team_to_canonical(team, "understat")
            assert result in CANONICAL_TEAM_NAMES, (
                f"'{team}' resolved to '{result}' which is not canonical"
            )

    def test_every_canonical_entry_resolves_via_understat(self):
        for canonical, names in CANONICAL_TEAM_NAMES.items():
            if "understat" not in names:
                continue  # historical entries without understat data are skipped
            result = team_to_canonical(canonical, "understat")
            assert result == canonical


# -----------------------------------------------------------------------
# Team mapping — round-trip lookups
# -----------------------------------------------------------------------

class TestTeamRoundTrips:

    def test_sofascore_round_trip(self):
        for canonical, names in CANONICAL_TEAM_NAMES.items():
            if "sofascore" not in names:
                continue
            ss_name = names["sofascore"]
            resolved = team_to_canonical(ss_name, "sofascore")
            back = team_from_canonical(resolved, "sofascore")
            assert back == ss_name, (
                f"Round-trip failed: '{ss_name}' -> '{resolved}' -> '{back}'"
            )

    def test_understat_round_trip(self):
        for canonical, names in CANONICAL_TEAM_NAMES.items():
            if "understat" not in names:
                continue
            us_name = names["understat"]
            resolved = team_to_canonical(us_name, "understat")
            back = team_from_canonical(resolved, "understat")
            assert back == us_name


# -----------------------------------------------------------------------
# Team mapping — aliases
# -----------------------------------------------------------------------

class TestUnderstatAliases:

    def test_parma_alias_resolves(self):
        assert team_to_canonical("Parma", "understat") == "Parma"

    def test_parma_canonical_entry_exists(self):
        assert "Parma Calcio 1913" in CANONICAL_TEAM_NAMES

    def test_parma_historical_entry_exists(self):
        assert "Parma" in CANONICAL_TEAM_NAMES


# -----------------------------------------------------------------------
# Team mapping — error handling
# -----------------------------------------------------------------------

class TestTeamLookupErrors:

    def test_unknown_team_raises_key_error(self):
        with pytest.raises(KeyError):
            team_to_canonical("Totally Fake FC", "understat")

    def test_unmapped_source_raises_key_error(self):
        with pytest.raises(KeyError):
            team_from_canonical("Arsenal", "football_data_co_uk")

    def test_unknown_canonical_raises_key_error(self):
        with pytest.raises(KeyError):
            team_from_canonical("Totally Fake FC", "understat")


# -----------------------------------------------------------------------
# League mapping — structural integrity
# -----------------------------------------------------------------------

class TestLeagueMappingStructure:

    def test_five_leagues_present(self):
        expected = {"EPL", "La_Liga", "Bundesliga", "Serie_A", "Ligue_1"}
        assert set(CANONICAL_LEAGUE_NAMES.keys()) == expected

    def test_no_duplicate_source_values(self):
        for source in LEAGUE_SOURCES:
            seen = {}
            for canonical, names in CANONICAL_LEAGUE_NAMES.items():
                if source not in names:
                    continue
                value = names[source]
                assert value not in seen, (
                    f"Source '{source}' value '{value}' maps to both "
                    f"'{seen[value]}' and '{canonical}'"
                )
                seen[value] = canonical

    def test_every_league_has_all_four_sources(self):
        for canonical, names in CANONICAL_LEAGUE_NAMES.items():
            for source in LEAGUE_SOURCES:
                assert source in names, (
                    f"League '{canonical}' is missing source '{source}'"
                )


# -----------------------------------------------------------------------
# League mapping — round-trip lookups
# -----------------------------------------------------------------------

class TestLeagueRoundTrips:

    @pytest.mark.parametrize("source", LEAGUE_SOURCES)
    def test_round_trip_per_source(self, source):
        for canonical, names in CANONICAL_LEAGUE_NAMES.items():
            source_name = names[source]
            resolved = league_to_canonical(source_name, source)
            back = league_from_canonical(resolved, source)
            assert back == source_name, (
                f"Round-trip failed for '{source}': "
                f"'{source_name}' -> '{resolved}' -> '{back}'"
            )


# -----------------------------------------------------------------------
# League mapping — specific values (verified against source docs)
# -----------------------------------------------------------------------

class TestLeagueSpecificValues:

    def test_football_data_co_uk_codes(self):
        assert league_to_canonical("E0", "football_data_co_uk") == "EPL"
        assert league_to_canonical("SP1", "football_data_co_uk") == "La_Liga"
        assert league_to_canonical("D1", "football_data_co_uk") == "Bundesliga"
        assert league_to_canonical("I1", "football_data_co_uk") == "Serie_A"
        assert league_to_canonical("F1", "football_data_co_uk") == "Ligue_1"

    def test_football_data_org_codes(self):
        assert league_to_canonical("PL", "football_data_org") == "EPL"
        assert league_to_canonical("PD", "football_data_org") == "La_Liga"
        assert league_to_canonical("BL1", "football_data_org") == "Bundesliga"
        assert league_to_canonical("SA", "football_data_org") == "Serie_A"
        assert league_to_canonical("FL1", "football_data_org") == "Ligue_1"

    def test_sofascore_soccerdata_format(self):
        assert league_to_canonical("ENG-Premier League", "sofascore") == "EPL"
        assert league_to_canonical("ESP-La Liga", "sofascore") == "La_Liga"
        assert league_to_canonical("GER-Bundesliga", "sofascore") == "Bundesliga"
        assert league_to_canonical("ITA-Serie A", "sofascore") == "Serie_A"
        assert league_to_canonical("FRA-Ligue 1", "sofascore") == "Ligue_1"


# -----------------------------------------------------------------------
# League mapping — error handling
# -----------------------------------------------------------------------

class TestLeagueLookupErrors:

    def test_unknown_league_raises_key_error(self):
        with pytest.raises(KeyError):
            league_to_canonical("MLS", "understat")

    def test_unknown_canonical_raises_key_error(self):
        with pytest.raises(KeyError):
            league_from_canonical("MLS", "understat")