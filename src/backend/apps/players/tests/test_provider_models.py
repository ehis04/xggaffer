from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.players.models import Player, PlayerExternalIdentity, ProviderSyncJob


class PlayerExternalIdentityModelTests(TestCase):
    def setUp(self):
        self.player = Player.objects.create(
            first_name="Bukayo",
            last_name="Saka",
            display_name="Bukayo Saka",
        )

    def test_player_external_identity_links_to_player_correctly(self):
        identity = PlayerExternalIdentity.objects.create(
            player=self.player,
            provider="football_data",
            external_id="123",
            provider_display_name="Bukayo Saka",
            provider_position="Right Winger",
            external_team_id="57",
        )

        self.assertEqual(identity.player, self.player)
        self.assertEqual(identity.provider, "football_data")
        self.assertEqual(identity.external_id, "123")
        self.assertEqual(identity.provider_display_name, "Bukayo Saka")
        self.assertEqual(identity.provider_position, "Right Winger")
        self.assertEqual(identity.external_team_id, "57")
        self.assertFalse(identity.is_primary)
        self.assertFalse(identity.is_manual_override)
        self.assertEqual(identity.metadata, {})
        self.assertIsNotNone(identity.first_seen_at)
        self.assertIsNone(identity.last_synced_at)

    def test_player_external_identity_cannot_duplicate_provider_and_external_id(self):
        PlayerExternalIdentity.objects.create(
            player=self.player,
            provider="football_data",
            external_id="123",
        )

        other_player = Player.objects.create(
            first_name="Declan",
            last_name="Rice",
            display_name="Declan Rice",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PlayerExternalIdentity.objects.create(
                    player=other_player,
                    provider="football_data",
                    external_id="123",
                )


class ProviderSyncJobModelTests(TestCase):
    def test_provider_sync_job_defaults_behave_as_expected(self):
        job = ProviderSyncJob.objects.create(
            provider="football_data",
            resource_type="team_squad",
            resource_external_id="64",
        )

        self.assertEqual(job.provider, "football_data")
        self.assertEqual(job.resource_type, "team_squad")
        self.assertEqual(job.resource_external_id, "64")
        self.assertEqual(job.status, "started")
        self.assertEqual(job.records_processed, 0)
        self.assertEqual(job.records_created, 0)
        self.assertEqual(job.records_updated, 0)
        self.assertEqual(job.error_count, 0)
        self.assertEqual(job.raw_error_summary, "")
        self.assertEqual(job.metadata, {})
        self.assertIsNone(job.finished_at)
        self.assertIsNone(job.triggered_by)
        self.assertIsNotNone(job.started_at)