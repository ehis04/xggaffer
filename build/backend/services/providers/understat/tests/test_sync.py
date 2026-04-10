from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.clubs.models import Club, ClubExternalIdentity, ClubPlayer

User = get_user_model()
from apps.playerdata.models import ClubSeasonEnrichment, PlayerSeasonEnrichment
from apps.players.models import (
    ExternalProvider,
    Player,
    PlayerExternalIdentity,
    ProviderSyncJob,
    ProviderSyncStatus,
)
from services.providers.understat.sync import UnderstatSyncService


class UnderstatSyncServiceTests(TestCase):
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

    def test_existing_provider_linked_club_sync_creates_and_then_updates_enrichment(self):
        ClubExternalIdentity.objects.create(
            club=self.club,
            provider=ExternalProvider.UNDERSTAT,
            external_id="arsenal",
            provider_display_name="Arsenal",
            is_primary=True,
        )

        client = Mock()
        client.get_team_season_payload.side_effect = [
            {
                "team_external_id": "arsenal",
                "league": "EPL",
                "stats": [
                    {
                        "result": "w",
                        "scored": "2",
                        "missed": "1",
                        "xG": "1.40",
                        "xGA": "0.80",
                        "npxG": "1.10",
                    }
                ],
            },
            {
                "team_external_id": "arsenal",
                "league": "EPL",
                "stats": [
                    {
                        "result": "w",
                        "scored": "3",
                        "missed": "1",
                        "xG": "2.20",
                        "xGA": "0.70",
                        "npxG": "1.90",
                    }
                ],
            },
        ]

        service = UnderstatSyncService(client=client)

        first_result = service.sync_understat_club_season(
            club=self.club,
            season_label="2024",
            competition_code="EPL",
        )
        second_result = service.sync_understat_club_season(
            club=self.club,
            season_label="2024",
            competition_code="EPL",
        )

        self.assertEqual(ClubSeasonEnrichment.objects.count(), 1)

        enrichment = ClubSeasonEnrichment.objects.get()
        self.assertEqual(enrichment.club, self.club)
        self.assertEqual(enrichment.provider, ExternalProvider.UNDERSTAT)
        self.assertEqual(enrichment.season_label, "2024")
        self.assertEqual(enrichment.competition_code, "EPL")
        self.assertEqual(enrichment.matches_played, 1)
        self.assertEqual(str(enrichment.xg), "2.20")
        self.assertEqual(str(enrichment.xga), "0.70")
        self.assertEqual(str(enrichment.npxg), "1.90")

        self.assertEqual(first_result["summary"]["status"], ProviderSyncStatus.SUCCESS)
        self.assertEqual(second_result["summary"]["status"], ProviderSyncStatus.SUCCESS)

        jobs = ProviderSyncJob.objects.filter(
            provider=ExternalProvider.UNDERSTAT,
            resource_type="club_season",
        ).order_by("started_at")
        self.assertEqual(jobs.count(), 2)
        self.assertTrue(all(job.status == ProviderSyncStatus.SUCCESS for job in jobs))

    def test_existing_provider_linked_player_sync_creates_player_enrichment_and_respects_mappings(self):
        ClubExternalIdentity.objects.create(
            club=self.club,
            provider=ExternalProvider.UNDERSTAT,
            external_id="arsenal",
            provider_display_name="Arsenal",
            is_primary=True,
        )
        PlayerExternalIdentity.objects.create(
            player=self.player,
            provider=ExternalProvider.UNDERSTAT,
            external_id="player-7",
            provider_display_name="Bukayo Saka",
            external_team_id="arsenal",
            is_primary=True,
        )

        client = Mock()
        client.get_player_stats.return_value = {
            "player_external_id": "player-7",
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

        service = UnderstatSyncService(client=client)

        result = service.sync_understat_player_season(
            player=self.player,
            season_label="2024",
            competition_code="EPL",
        )

        self.assertEqual(Player.objects.count(), 1)
        self.assertEqual(PlayerExternalIdentity.objects.count(), 1)
        self.assertEqual(PlayerSeasonEnrichment.objects.count(), 1)

        enrichment = PlayerSeasonEnrichment.objects.get()
        self.assertEqual(enrichment.player, self.player)
        self.assertEqual(enrichment.club, self.club)
        self.assertEqual(enrichment.provider, ExternalProvider.UNDERSTAT)
        self.assertEqual(enrichment.external_player_id, "player-7")
        self.assertEqual(enrichment.external_team_id, "arsenal")
        self.assertEqual(enrichment.matches_played, 10)
        self.assertEqual(enrichment.goals, 4)
        self.assertEqual(enrichment.assists, 3)

        self.assertEqual(result["summary"]["status"], ProviderSyncStatus.SUCCESS)

        job = ProviderSyncJob.objects.get(
            provider=ExternalProvider.UNDERSTAT,
            resource_type="player_season",
        )
        self.assertEqual(job.status, ProviderSyncStatus.SUCCESS)

    def test_club_level_player_sync_uses_existing_canonical_player_and_does_not_create_a_new_one(self):
        ClubExternalIdentity.objects.create(
            club=self.club,
            provider=ExternalProvider.UNDERSTAT,
            external_id="arsenal",
            provider_display_name="Arsenal",
            is_primary=True,
        )
        ClubPlayer.objects.create(
            club=self.club,
            player=self.player,
            first_name="Bukayo",
            last_name="Saka",
            display_name="Bukayo Saka",
        )

        client = Mock()
        client.get_team_season_payload.return_value = {
            "team_external_id": "arsenal",
            "league": "EPL",
            "players": [
                {
                    "id": "understat-7",
                    "player_name": "Bukayo Saka",
                    "games": "9",
                    "time": "810",
                    "goals": "5",
                    "assists": "2",
                    "shots": "20",
                    "xG": "4.10",
                    "xA": "1.80",
                    "npg": "5",
                    "npxG": "3.90",
                    "key_passes": "9",
                    "position": "FWD",
                }
            ],
            "stats": [
                {
                    "result": "w",
                    "scored": "2",
                    "missed": "1",
                    "xG": "1.40",
                    "xGA": "0.80",
                    "npxG": "1.10",
                }
            ],
        }
        client.get_player_stats.return_value = {
            "player_external_id": "understat-7",
            "groups": [
                {
                    "id": "understat-7",
                    "season": "2024",
                    "league": "EPL",
                    "team_id": "arsenal",
                    "team_title": "Arsenal",
                    "games": "9",
                    "time": "810",
                    "goals": "5",
                    "assists": "2",
                    "shots": "20",
                    "xG": "4.10",
                    "xA": "1.80",
                    "npg": "5",
                    "npxG": "3.90",
                    "key_passes": "9",
                },
                {
                    "id": "understat-7",
                    "season": "2024",
                    "league": "ChampionsLeague",
                    "team_id": "arsenal",
                    "team_title": "Arsenal",
                    "games": "8",
                    "time": "640",
                    "goals": "4",
                    "assists": "1",
                    "shots": "12",
                    "xG": "2.00",
                    "xA": "0.80",
                    "npg": "4",
                    "npxG": "1.80",
                    "key_passes": "6",
                },
            ],
        }

        service = UnderstatSyncService(client=client)

        result = service.sync_understat_club_players_season(
            club=self.club,
            season_label="2024",
            competition_code="EPL",
        )

        self.assertEqual(Player.objects.count(), 1)
        self.assertEqual(PlayerExternalIdentity.objects.count(), 1)
        self.assertEqual(PlayerSeasonEnrichment.objects.count(), 1)

        identity = PlayerExternalIdentity.objects.get()
        enrichment = PlayerSeasonEnrichment.objects.get()

        self.assertEqual(identity.player, self.player)
        self.assertEqual(identity.external_id, "understat-7")
        self.assertEqual(identity.external_team_id, "arsenal")

        self.assertEqual(enrichment.player, self.player)
        self.assertEqual(enrichment.club, self.club)
        self.assertEqual(enrichment.external_player_id, "understat-7")
        self.assertEqual(enrichment.matches_played, 9)
        self.assertEqual(enrichment.goals, 5)

        self.assertEqual(result["summary"]["status"], ProviderSyncStatus.SUCCESS)
        self.assertEqual(result["summary"]["metadata"]["players_matched"], 1)
        self.assertEqual(result["summary"]["metadata"]["players_unmatched"], 0)
        self.assertEqual(result["summary"]["metadata"]["players_competition_filtered"], 1)
        self.assertEqual(result["summary"]["metadata"]["players_team_row_fallback"], 0)

    def test_failed_sync_logs_failed_provider_sync_job(self):
        ClubExternalIdentity.objects.create(
            club=self.club,
            provider=ExternalProvider.UNDERSTAT,
            external_id="arsenal",
            provider_display_name="Arsenal",
            is_primary=True,
        )

        client = Mock()
        client.get_team_season_payload.side_effect = ValueError("boom")

        service = UnderstatSyncService(client=client)

        with self.assertRaises(ValueError):
            service.sync_understat_club_season(
                club=self.club,
                season_label="2024",
                competition_code="EPL",
            )

        job = ProviderSyncJob.objects.get(
            provider=ExternalProvider.UNDERSTAT,
            resource_type="club_season",
        )
        self.assertEqual(job.status, ProviderSyncStatus.FAILED)
        self.assertEqual(job.error_count, 1)
        self.assertIn("boom", job.raw_error_summary)