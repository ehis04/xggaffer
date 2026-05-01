from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.clubs.models import Club, ClubPlayer
from apps.players.models import Player
from .models import Teamsheet, TeamsheetPlayer
from .serializers import CreateTeamsheetWithPlayersSerializer, TeamsheetPlayerReadSerializer


class TeamsheetClubPlayerCompatibilityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='teamsheet-c5@example.com',
            password='testpass123',
        )

        self.club = Club.objects.create(
            name='Teamsheet Compatibility Club',
            description='Club for teamsheet compatibility tests.',
            creator=self.user,
            visibility=Club.Visibility.PRIVATE,
            club_type=Club.ClubType.USER_FICTIONAL,
            fictional_basis=Club.FictionalBasis.ORIGINAL,
            directory_visibility=Club.DirectoryVisibility.LISTED,
            join_policy=Club.JoinPolicy.APPROVAL_REQUIRED,
            verification_status=Club.VerificationStatus.NOT_REQUIRED,
        )

        self.canonical_player = Player.objects.create(
            first_name='Erin',
            last_name='Moore',
            display_name='Erin Moore',
            primary_position='CM',
        )

        self.linked_club_player = ClubPlayer.objects.create(
            club=self.club,
            player=self.canonical_player,
            first_name='Erin',
            last_name='Moore',
            display_name='Captain Erin',
            squad_number=8,
            primary_position='CM',
            created_by=self.user,
            is_active=True,
        )

        self.local_only_club_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='Local',
            last_name='Prospect',
            display_name='Local Prospect',
            squad_number=14,
            primary_position='RW',
            created_by=self.user,
            is_active=True,
        )

        self.teamsheet = Teamsheet.objects.create(
            club=self.club,
            created_by=self.user,
            title='Matchday XI',
            formation='442',
            opponent='Example FC',
        )

    def test_display_name_prefers_club_player_display_name_when_linked(self):
        teamsheet_player = TeamsheetPlayer.objects.create(
            teamsheet=self.teamsheet,
            club_player=self.linked_club_player,
            slot_number=1,
            position_label='CM',
            position_x=50,
            position_y=50,
            is_substitute=False,
        )

        self.assertEqual(teamsheet_player.display_name, 'Captain Erin')

    def test_display_name_supports_local_only_unlinked_club_player(self):
        teamsheet_player = TeamsheetPlayer.objects.create(
            teamsheet=self.teamsheet,
            club_player=self.local_only_club_player,
            slot_number=2,
            position_label='RW',
            position_x=60,
            position_y=55,
            is_substitute=False,
        )

        self.assertEqual(teamsheet_player.display_name, 'Local Prospect')

    def test_display_number_uses_club_player_number_for_local_only_row(self):
        teamsheet_player = TeamsheetPlayer.objects.create(
            teamsheet=self.teamsheet,
            club_player=self.local_only_club_player,
            slot_number=3,
            position_label='RW',
            position_x=62,
            position_y=58,
            is_substitute=False,
        )

        self.assertEqual(teamsheet_player.display_number, 14)

    def test_read_serializer_stays_stable_for_local_only_club_player(self):
        teamsheet_player = TeamsheetPlayer.objects.create(
            teamsheet=self.teamsheet,
            club_player=self.local_only_club_player,
            slot_number=4,
            position_label='RW',
            position_x=64,
            position_y=60,
            is_substitute=False,
        )

        data = TeamsheetPlayerReadSerializer(teamsheet_player).data

        self.assertEqual(data['display_name'], 'Local Prospect')
        self.assertEqual(data['display_number'], 14)
        self.assertTrue(data['is_linked'])
        self.assertEqual(data['club_player'], self.local_only_club_player.id)

    def test_create_with_players_accepts_local_only_club_player_assignment(self):
        serializer = CreateTeamsheetWithPlayersSerializer(
            data={
                'title': 'Local Player Teamsheet',
                'formation': '442',
                'opponent': 'Sample United',
                'player_assignments': [
                    {
                        'slot_number': 1,
                        'club_player_id': self.local_only_club_player.id,
                        'position_label': 'RW',
                        'position_x': 50,
                        'position_y': 50,
                        'is_substitute': False,
                    }
                ],
            },
            context={
                'club': self.club,
                'user': self.user,
            },
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        teamsheet = serializer.save()

        assigned_player = teamsheet.players.get(slot_number=1)
        self.assertEqual(assigned_player.club_player_id, self.local_only_club_player.id)
        self.assertEqual(assigned_player.display_name, 'Local Prospect')