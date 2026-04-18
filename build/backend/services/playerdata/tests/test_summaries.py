from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from services.playerdata.summaries import (
    build_club_provider_coverage_summary,
    build_club_season_summary,
    build_data_freshness_summary,
    build_player_provider_coverage_summary,
    build_player_season_summary,
)
from services.playerdata.tests.test_queries import PlayerDataQueryServiceTests

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from services.playerdata.queries import (
    ClubSeasonEnrichmentRecord,
    PlayerSeasonEnrichmentRecord,
)
from services.playerdata.summaries import (
    build_club_season_summary,
    build_player_season_summary,
)


class PlayerDataSummaryPhase5ShapeTests(SimpleTestCase):
    def _player_record(self) -> PlayerSeasonEnrichmentRecord:
        return PlayerSeasonEnrichmentRecord(
            enrichment_id=101,
            player_id=7,
            player_name="Bukayo Saka",
            primary_position="RW",
            secondary_positions=["LW"],
            club_id=3,
            club_name="Arsenal",
            provider="understat",
            season_label="2024-2025",
            competition_code="EPL",
            competition_name="Premier League",
            matches_played=24,
            minutes_played=1950,
            goals=10,
            assists=6,
            shots=58,
            xg=Decimal("8.4"),
            xa=Decimal("7.2"),
            npg=Decimal("9"),
            npxg=Decimal("7.9"),
            key_passes=41,
            last_synced_at=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 1, 12, 5, tzinfo=timezone.utc),
        )

    def _club_record(self) -> ClubSeasonEnrichmentRecord:
        return ClubSeasonEnrichmentRecord(
            enrichment_id=201,
            club_id=3,
            club_name="Arsenal",
            provider="understat",
            season_label="2024-2025",
            competition_code="EPL",
            competition_name="Premier League",
            matches_played=27,
            wins=18,
            draws=6,
            losses=3,
            goals_for=52,
            goals_against=19,
            xg=Decimal("42.7"),
            xga=Decimal("21.3"),
            npxg=Decimal("39.9"),
            ppda=Decimal("8.8"),
            last_synced_at=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 1, 12, 5, tzinfo=timezone.utc),
        )

    def test_build_player_season_summary_exposes_api_contract_properties(self):
        with patch(
            "services.playerdata.summaries.get_player_season_enrichment",
            return_value=self._player_record(),
        ):
            summary = build_player_season_summary(
                player_id=7,
                season="2024-2025",
                provider="understat",
                competition_code="EPL",
            )

        self.assertIsNotNone(summary)
        self.assertEqual(summary.player["id"], 7)
        self.assertEqual(summary.club["name"], "Arsenal")
        self.assertEqual(summary.context["provider"], "understat")
        self.assertEqual(summary.context["season"], "2024-2025")
        self.assertEqual(summary.metrics[0]["key"], "matches_played")
        self.assertEqual(summary.explanation["headline"], "Deterministic season summary")
        self.assertIn("strengths", summary.explanation)
        self.assertIn("watchouts", summary.explanation)
        self.assertIn("notes", summary.explanation)
        self.assertEqual(summary.provider_coverage["provider"], "understat")
        self.assertTrue(summary.has_summary_data)
        self.assertEqual(summary.missing_reasons, [])

    def test_build_club_season_summary_exposes_api_contract_properties(self):
        with patch(
            "services.playerdata.summaries.get_club_season_enrichment",
            return_value=self._club_record(),
        ):
            summary = build_club_season_summary(
                club_id=3,
                season="2024-2025",
                provider="understat",
                competition_code="EPL",
            )

        self.assertIsNotNone(summary)
        self.assertEqual(summary.club["id"], 3)
        self.assertEqual(summary.context["competition_name"], "Premier League")
        self.assertEqual(summary.metrics[0]["key"], "matches_played")
        self.assertEqual(summary.explanation["headline"], "Deterministic club season summary")
        self.assertEqual(summary.provider_coverage["matches_sampled"], 27)
        self.assertTrue(summary.has_summary_data)
        self.assertEqual(summary.missing_reasons, [])

    def test_build_player_season_summary_returns_none_when_no_record_exists(self):
        with patch(
            "services.playerdata.summaries.get_player_season_enrichment",
            return_value=None,
        ):
            summary = build_player_season_summary(player_id=999)

        self.assertIsNone(summary)

class PlayerDataSummaryServiceTests(PlayerDataQueryServiceTests, TestCase):
    def test_build_player_season_summary_returns_deterministic_summary(self):
        summary = build_player_season_summary(
            self.player_a.id,
            season_label="2024",
            provider=self.understat_provider,
            competition_code="EPL",
            club_id=self.club_alpha.id,
        )

        self.assertIsNotNone(summary)
        self.assertEqual(summary.player_id, self.player_a.id)
        self.assertEqual(summary.player_name, "Player A")
        self.assertEqual(summary.club_name, "Alpha FC")
        self.assertEqual(summary.provider, self.understat_provider)
        self.assertEqual(summary.season_label, "2024")
        self.assertEqual(summary.competition_code, "EPL")
        self.assertEqual(summary.minutes_played, 2200)
        self.assertEqual(summary.goals, 14)
        self.assertEqual(summary.assists, 7)
        self.assertEqual(summary.xg, Decimal("13.75"))
        self.assertEqual(summary.xa, Decimal("6.20"))
        self.assertEqual(summary.npxg, Decimal("12.40"))

        self.assertEqual(
            summary.sentences[0],
            "Player A scored 14 goals and produced 7 assists in 2,200 minutes across 30 matches in the 2024 season.",
        )
        self.assertEqual(
            summary.sentences[1],
            "He recorded 13.8 xG, 6.2 xA, 12.4 npxG, 55 shots, 34 key passes.",
        )
        self.assertEqual(
            summary.sentences[2],
            f"This record is for Alpha FC in Premier League from the {self.understat_provider} provider.",
        )
        self.assertIn(
            f"{self.understat_provider} data is available for the 2024 season in Premier League",
            summary.sentences[3],
        )

    def test_build_club_season_summary_returns_deterministic_summary(self):
        summary = build_club_season_summary(
            self.club_alpha.id,
            season_label="2024",
            provider=self.understat_provider,
            competition_code="EPL",
        )

        self.assertIsNotNone(summary)
        self.assertEqual(summary.club_id, self.club_alpha.id)
        self.assertEqual(summary.club_name, "Alpha FC")
        self.assertEqual(summary.provider, self.understat_provider)
        self.assertEqual(summary.season_label, "2024")
        self.assertEqual(summary.competition_code, "EPL")
        self.assertEqual(summary.matches_played, 38)
        self.assertEqual(summary.wins, 24)
        self.assertEqual(summary.draws, 7)
        self.assertEqual(summary.losses, 7)
        self.assertEqual(summary.goals_for, 74)
        self.assertEqual(summary.goals_against, 33)
        self.assertEqual(summary.xg, Decimal("71.80"))
        self.assertEqual(summary.xga, Decimal("34.20"))
        self.assertEqual(summary.npxg, Decimal("68.30"))
        self.assertEqual(summary.ppda, Decimal("8.90"))

        self.assertEqual(
            summary.sentences[0],
            "Alpha FC played 38 matches and posted a 24-7-7 win-draw-loss record in the 2024 season.",
        )
        self.assertEqual(
            summary.sentences[1],
            "They recorded 74 goals scored, 33 goals conceded, 71.8 xG, 34.2 xGA, 68.3 npxG, 8.9 PPDA.",
        )
        self.assertEqual(
            summary.sentences[2],
            f"This record is for Premier League from the {self.understat_provider} provider.",
        )
        self.assertIn(
            f"{self.understat_provider} data is available for the 2024 season in Premier League",
            summary.sentences[3],
        )

    def test_missing_player_metric_data_produces_honest_limited_output(self):
        summary = build_player_season_summary(
            self.player_c.id,
            season_label="2024",
            provider=self.understat_provider,
            competition_code="EPL",
        )

        self.assertIsNotNone(summary)
        self.assertEqual(summary.player_name, "Player C")
        self.assertIsNone(summary.club_id)
        self.assertIsNone(summary.club_name)
        self.assertIsNone(summary.xg)
        self.assertIsNone(summary.xa)
        self.assertIsNone(summary.npg)
        self.assertIsNone(summary.npxg)
        self.assertIsNone(summary.freshness.last_synced_at)

        self.assertEqual(
            summary.sentences[0],
            "Player C scored 0 goals and produced 0 assists in 190 minutes across 6 matches in the 2024 season.",
        )
        self.assertEqual(
            summary.sentences[1],
            "He recorded 3 shots, 0 key passes.",
        )
        self.assertEqual(
            summary.sentences[2],
            f"This record is in Premier League from the {self.understat_provider} provider.",
        )
        self.assertEqual(
            summary.sentences[3],
            f"{self.understat_provider} data is available for the 2024 season in Premier League, but no sync timestamp is stored.",
        )

    def test_build_data_freshness_summary_uses_last_synced_when_available(self):
        summary = build_data_freshness_summary(
            provider=self.understat_provider,
            season_label="2024",
            competition_code="EPL",
            competition_name="Premier League",
            last_synced_at=self.player_a_2024.last_synced_at,
            updated_at=self.player_a_2024.updated_at,
        )

        self.assertTrue(summary.is_available)
        self.assertEqual(summary.provider, self.understat_provider)
        self.assertEqual(summary.season_label, "2024")
        self.assertEqual(summary.competition_code, "EPL")
        self.assertEqual(summary.competition_name, "Premier League")
        self.assertEqual(summary.last_synced_at, self.player_a_2024.last_synced_at)
        self.assertIn(
            f"{self.understat_provider} data is available for the 2024 season in Premier League and was last synced on ",
            summary.sentence,
        )

    def test_build_data_freshness_summary_falls_back_when_sync_timestamp_missing(self):
        summary = build_data_freshness_summary(
            provider=self.understat_provider,
            season_label="2024",
            competition_code="EPL",
            competition_name="Premier League",
            last_synced_at=None,
            updated_at=None,
        )

        self.assertTrue(summary.is_available)
        self.assertIsNone(summary.last_synced_at)
        self.assertIsNone(summary.updated_at)
        self.assertEqual(
            summary.sentence,
            f"{self.understat_provider} data is available for the 2024 season in Premier League, but no sync timestamp is stored.",
        )

    def test_build_player_provider_coverage_summary_reports_real_coverage(self):
        summary = build_player_provider_coverage_summary(self.player_a.id)

        self.assertIsNotNone(summary)
        self.assertEqual(summary.entity_type, "player")
        self.assertEqual(summary.entity_id, self.player_a.id)
        self.assertEqual(summary.entity_name, "Player A")
        self.assertEqual(summary.record_count, 3)
        self.assertEqual(sorted(summary.providers), sorted([self.understat_provider, self.other_provider]))
        self.assertEqual(summary.seasons, ["2024", "2023"])
        self.assertEqual(
            sorted(summary.competitions),
            sorted(["Premier League", "Champions League"]),
        )
        self.assertEqual(len(summary.items), 3)
        self.assertIn("Player A has 3 stored enrichment records across 2 providers.", summary.sentences[0])
        self.assertIn("Available providers:", summary.sentences[1])
        self.assertIn("Available seasons: 2024, 2023.", summary.sentences[1])
        self.assertIn("Competitions covered:", summary.sentences[2])

        item_payloads = [item.to_dict() for item in summary.items]
        self.assertTrue(any(item["provider"] == self.understat_provider and item["season_label"] == "2024" for item in item_payloads))
        self.assertTrue(any(item["provider"] == self.other_provider and item["competition_name"] == "Champions League" for item in item_payloads))

    def test_build_club_provider_coverage_summary_reports_real_coverage(self):
        summary = build_club_provider_coverage_summary(self.club_alpha.id)

        self.assertIsNotNone(summary)
        self.assertEqual(summary.entity_type, "club")
        self.assertEqual(summary.entity_id, self.club_alpha.id)
        self.assertEqual(summary.entity_name, "Alpha FC")
        self.assertEqual(summary.record_count, 2)
        self.assertEqual(summary.providers, [self.understat_provider])
        self.assertEqual(summary.seasons, ["2024", "2023"])
        self.assertEqual(summary.competitions, ["Premier League"])
        self.assertEqual(len(summary.items), 2)
        self.assertIn("Alpha FC has 2 stored enrichment records across 1 provider.", summary.sentences[0])
        self.assertIn(f"Available providers: {self.understat_provider}.", summary.sentences[1])
        self.assertIn("Available seasons: 2024, 2023.", summary.sentences[1])
        self.assertIn("Competitions covered: Premier League.", summary.sentences[2])

    def test_summary_builders_return_none_when_record_does_not_exist(self):
        self.assertIsNone(
            build_player_season_summary(
                999999,
                season_label="2024",
                provider=self.understat_provider,
                competition_code="EPL",
            )
        )
        self.assertIsNone(
            build_club_season_summary(
                999999,
                season_label="2024",
                provider=self.understat_provider,
                competition_code="EPL",
            )
        )
        self.assertIsNone(build_player_provider_coverage_summary(999999))
        self.assertIsNone(build_club_provider_coverage_summary(999999))