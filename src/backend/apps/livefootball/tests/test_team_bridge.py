from __future__ import annotations

from django.test import TestCase

from apps.livefootball.models import Competition, TeamDirectoryEntry
from apps.livefootball.services.exceptions import TeamMappingNotFoundError
from apps.livefootball.services.team_bridge import (
    get_competition_team_bridge,
    get_understat_league_code,
    resolve_understat_team_name,
)


class TeamBridgeTests(TestCase):
    def _make_competition(self, *, code: str, name: str, season: str = "2025") -> Competition:
        return Competition.objects.create(
            provider="football_data",
            external_id=f"ext-{code}-{season}",
            code=code,
            name=name,
            current_season_label=season,
        )

    def test_supported_competition_codes_map_to_understat_leagues(self) -> None:
        cases = [
            ("PL", "Premier League", "EPL"),
            ("PD", "Primera Division", "La_Liga"),
            ("BL1", "Bundesliga", "Bundesliga"),
            ("SA", "Serie A", "Serie_A"),
            ("FL1", "Ligue 1", "Ligue_1"),
        ]

        for code, name, expected in cases:
            with self.subTest(code=code):
                competition = self._make_competition(code=code, name=name)
                self.assertEqual(get_understat_league_code(competition), expected)

    def test_known_team_mappings_cover_all_five_leagues(self) -> None:
        cases = [
            ("Man United", "Manchester United"),
            ("Man City", "Manchester City"),
            ("Wolves", "Wolverhampton Wanderers"),
            ("West Brom", "West Bromwich Albion"),
            ("QPR", "Queens Park Rangers"),

            ("Ath Bilbao", "Athletic Club"),
            ("Ath Madrid", "Atletico Madrid"),
            ("Sociedad", "Real Sociedad"),
            ("Vallecano", "Rayo Vallecano"),
            ("Sp Gijon", "Sporting Gijon"),

            ("M'gladbach", "Borussia M.Gladbach"),
            ("FC Koln", "FC Cologne"),
            ("Mainz", "Mainz 05"),
            ("RB Leipzig", "RasenBallsport Leipzig"),
            ("St Pauli", "St. Pauli"),

            ("Milan", "AC Milan"),
            ("Inter", "Inter"),
            ("Napoli", "Napoli"),
            ("Roma", "Roma"),
            ("Spal", "SPAL 2013"),

            ("Paris SG", "Paris Saint Germain"),
            ("Lyon", "Lyon"),
            ("Marseille", "Marseille"),
            ("St Etienne", "Saint-Etienne"),
            ("RC Strasbourg", "Strasbourg"),
        ]

        for alias, expected in cases:
            with self.subTest(alias=alias):
                self.assertEqual(resolve_understat_team_name(alias), expected)

    def test_case_insensitive_lookup_works(self) -> None:
        self.assertEqual(
            resolve_understat_team_name("man united"),
            "Manchester United",
        )

    def test_short_name_fallback_works(self) -> None:
        self.assertEqual(
            resolve_understat_team_name(
                "Tottenham FC Placeholder",
                short_name="Tottenham Hotspur",
            ),
            "Tottenham",
        )

    def test_tla_fallback_works_when_tla_matches_known_alias(self) -> None:
        self.assertEqual(
            resolve_understat_team_name(
                "Unknown Club",
                tla="QPR",
            ),
            "Queens Park Rangers",
        )

    def test_unmapped_team_raises_descriptive_error(self) -> None:
        with self.assertRaises(TeamMappingNotFoundError) as exc:
            resolve_understat_team_name(
                "Completely Unknown FC",
                short_name="Still Unknown",
                tla="XYZ",
            )

        message = str(exc.exception)
        self.assertIn("Completely Unknown FC", message)
        self.assertIn("Still Unknown", message)
        self.assertIn("XYZ", message)

    def test_competition_level_bridge_returns_expected_count(self) -> None:
        competition = self._make_competition(code="PL", name="Premier League", season="2025")

        arsenal = TeamDirectoryEntry.objects.create(
            competition=competition,
            provider="football_data",
            season_label="2025",
            external_id="1",
            name="Arsenal",
            short_name="Arsenal",
            tla="ARS",
        )
        city = TeamDirectoryEntry.objects.create(
            competition=competition,
            provider="football_data",
            season_label="2025",
            external_id="2",
            name="Manchester City",
            short_name="Man City",
            tla="MCI",
        )
        wolves = TeamDirectoryEntry.objects.create(
            competition=competition,
            provider="football_data",
            season_label="2025",
            external_id="3",
            name="Wolverhampton",
            short_name="Wolves",
            tla="WOL",
        )

        TeamDirectoryEntry.objects.create(
            competition=competition,
            provider="football_data",
            season_label="2024",
            external_id="4",
            name="Chelsea",
            short_name="Chelsea",
            tla="CHE",
        )

        mapping = get_competition_team_bridge(competition.id)

        self.assertEqual(len(mapping), 3)
        self.assertEqual(mapping[arsenal.id], "Arsenal")
        self.assertEqual(mapping[city.id], "Manchester City")
        self.assertEqual(mapping[wolves.id], "Wolverhampton Wanderers")