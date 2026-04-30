"""
Tests for player data enrichment models

Checks unique constraints, default values, provider keys, and isolated JSONField defaults
"""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.clubs.models import Club
from apps.playerdata.models import ClubSeasonEnrichment, PlayerSeasonEnrichment
from apps.players.models import ExternalProvider, Player

User = get_user_model()


# Tests for player data enrichment model behaviour
class PlayerDataModelTests(TestCase):

    # Create shared user, club, and player records for model tests
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="password"
        )
        self.club = Club.objects.create(
            name="Arsenal",
            description="Test club",
            creator=self.user,
        )
        self.player = Player.objects.create(
            first_name="Bukayo",
            last_name="Saka",
            display_name="Bukayo Saka",
        )

    # Check duplicate club season enrichment rows are blocked
    def test_club_season_enrichment_unique_constraint_is_enforced(self):
        ClubSeasonEnrichment.objects.create(
            club=self.club,
            provider=ExternalProvider.UNDERSTAT,
            season_label="2024",
            competition_code="EPL",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClubSeasonEnrichment.objects.create(
                    club=self.club,
                    provider=ExternalProvider.UNDERSTAT,
                    season_label="2024",
                    competition_code="EPL",
                )

    # Check duplicate player season enrichment rows are blocked
    def test_player_season_enrichment_unique_constraint_is_enforced(self):
        PlayerSeasonEnrichment.objects.create(
            player=self.player,
            club=self.club,
            provider=ExternalProvider.UNDERSTAT,
            season_label="2024",
            competition_code="EPL",
            external_team_id="arsenal",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PlayerSeasonEnrichment.objects.create(
                    player=self.player,
                    club=self.club,
                    provider=ExternalProvider.UNDERSTAT,
                    season_label="2024",
                    competition_code="EPL",
                    external_team_id="arsenal",
                )

    # Check default stats and provider keys are saved correctly
    def test_defaults_and_provider_season_keys_persist_correctly(self):
        enrichment = ClubSeasonEnrichment.objects.create(
            club=self.club,
            provider=ExternalProvider.UNDERSTAT,
            season_label="2024",
            competition_code="EPL",
        )

        self.assertEqual(enrichment.provider, ExternalProvider.UNDERSTAT)
        self.assertEqual(enrichment.season_label, "2024")
        self.assertEqual(enrichment.competition_code, "EPL")
        self.assertEqual(enrichment.matches_played, 0)
        self.assertEqual(enrichment.wins, 0)
        self.assertEqual(enrichment.draws, 0)
        self.assertEqual(enrichment.losses, 0)
        self.assertEqual(enrichment.goals_for, 0)
        self.assertEqual(enrichment.goals_against, 0)
        self.assertEqual(enrichment.metadata, {})
        self.assertEqual(enrichment.raw_snapshot, {})

    # Check JSONField defaults are not shared between model instances
    def test_jsonfield_defaults_are_isolated_per_instance(self):
        first = PlayerSeasonEnrichment.objects.create(
            player=self.player,
            club=self.club,
            provider=ExternalProvider.UNDERSTAT,
            season_label="2024",
            competition_code="EPL",
            external_team_id="arsenal",
        )
        second = PlayerSeasonEnrichment.objects.create(
            player=self.player,
            club=self.club,
            provider=ExternalProvider.UNDERSTAT,
            season_label="2024",
            competition_code="FA",
            external_team_id="arsenal",
        )

        first.metadata["source"] = "understat"
        first.raw_snapshot["raw"] = {"goals": 5}
        first.save(update_fields=["metadata", "raw_snapshot"])

        second.refresh_from_db()

        self.assertEqual(second.metadata, {})
        self.assertEqual(second.raw_snapshot, {})