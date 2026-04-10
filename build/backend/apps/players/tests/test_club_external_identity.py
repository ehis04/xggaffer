from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.clubs.models import Club, ClubExternalIdentity


class ClubExternalIdentityModelTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="owner@example.com",
            password="testpass123",
        )
        self.club = Club.objects.create(
            name="Test FC",
            creator=self.user,
            description="",
            visibility=Club.Visibility.PRIVATE,
        )

    def test_club_external_identity_saves_correctly(self):
        identity = ClubExternalIdentity.objects.create(
            club=self.club,
            provider="football_data",
            external_id="64",
            provider_display_name="Liverpool FC",
            country="GB",
            competition_context="PL",
        )

        self.assertEqual(identity.club, self.club)
        self.assertEqual(identity.provider, "football_data")
        self.assertEqual(identity.external_id, "64")
        self.assertEqual(identity.provider_display_name, "Liverpool FC")
        self.assertEqual(identity.country, "GB")
        self.assertEqual(identity.competition_context, "PL")
        self.assertTrue(identity.is_primary)
        self.assertEqual(identity.metadata, {})
        self.assertIsNone(identity.last_synced_at)

    def test_club_external_identity_cannot_duplicate_provider_and_external_id(self):
        ClubExternalIdentity.objects.create(
            club=self.club,
            provider="football_data",
            external_id="64",
        )

        second_club = Club.objects.create(
            name="Second FC",
            creator=self.user,
            description="",
            visibility=Club.Visibility.PRIVATE,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClubExternalIdentity.objects.create(
                    club=second_club,
                    provider="football_data",
                    external_id="64",
                )

    def test_club_external_identity_is_primary_defaults_to_true(self):
        identity = ClubExternalIdentity.objects.create(
            club=self.club,
            provider="football_data",
            external_id="99",
        )

        self.assertTrue(identity.is_primary)