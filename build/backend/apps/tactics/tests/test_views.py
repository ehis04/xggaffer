from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.clubs.models import Club, ClubMembership, ClubPlayer
from apps.tactics.models import TacticsBoardItem
from apps.tactics.services import create_board_with_initial_frame, create_frame_for_board, create_item_for_frame
from apps.teamsheets.formations import get_formation_template
from apps.teamsheets.models import Teamsheet, TeamsheetPlayer

def create_test_club(user, name='View Club'):
    club_kwargs = {
        'name': name,
        'description': 'View test club.',
        'creator': user,
        'visibility': Club.Visibility.PRIVATE,
    }

    if hasattr(Club, 'ClubType'):
        club_kwargs.update({
            'club_type': Club.ClubType.USER_FICTIONAL,
            'fictional_basis': Club.FictionalBasis.ORIGINAL,
            'directory_visibility': Club.DirectoryVisibility.LISTED,
            'join_policy': Club.JoinPolicy.APPROVAL_REQUIRED,
            'verification_status': Club.VerificationStatus.NOT_REQUIRED,
        })

    return Club.objects.create(**club_kwargs)


class TacticsBoardViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.owner = get_user_model().objects.create_user(
            email='tactics-owner-view@example.com',
            password='testpass123',
        )
        self.member = get_user_model().objects.create_user(
            email='tactics-member-view@example.com',
            password='testpass123',
        )
        self.coach = get_user_model().objects.create_user(
            email='tactics-coach-view@example.com',
            password='testpass123',
        )
        self.outsider = get_user_model().objects.create_user(
            email='tactics-outsider-view@example.com',
            password='testpass123',
        )

        self.club = create_test_club(self.owner, name='Scoped Club')
        self.other_club = create_test_club(self.owner, name='Other Scoped Club')

        ClubMembership.objects.create(
            user=self.owner,
            club=self.club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.member,
            club=self.club,
            role=ClubMembership.Role.VIEWER,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.coach,
            club=self.club,
            role=ClubMembership.Role.COACH,
            is_active=True,
        )
        ClubMembership.objects.create(
            user=self.owner,
            club=self.other_club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )

    def _create_board_with_multiple_frames(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.owner,
            title='Source Board',
            description='Original tactical plan.',
            pitch_orientation='horizontal',
            home_formation='433',
            away_formation='442',
            home_colour='#111111',
            away_colour='#222222',
            is_template=True,
        )
        frame_zero = board.frames.get(frame_index=0)
        frame_one = create_frame_for_board(board=board, label='Second frame')

        create_item_for_frame(
            frame=frame_zero,
            item_type=TacticsBoardItem.ItemType.PLAYER,
            team_side=TacticsBoardItem.TeamSide.HOME,
            label='Player A',
            shirt_number=8,
            position_label='CM',
            x=45,
            y=55,
            z_index=1,
            style={'show_name': True},
        )
        create_item_for_frame(
            frame=frame_one,
            item_type=TacticsBoardItem.ItemType.ARROW,
            team_side=TacticsBoardItem.TeamSide.NEUTRAL,
            label='Run',
            x=20,
            y=30,
            end_x=40,
            end_y=60,
            z_index=2,
            style={'stroke_width': 3},
        )

        return board

    def _create_complete_teamsheet(self, club=None):
        if club is None:
            club = self.club

        linked_player = ClubPlayer.objects.create(
            club=club,
            first_name='John',
            last_name='Keeper',
            display_name='John Keeper',
            squad_number=1,
            primary_position='GK',
            created_by=self.owner,
        )

        teamsheet = Teamsheet.objects.create(
            club=club,
            created_by=self.owner,
            title='Matchday XI',
            formation='433',
        )

        template = get_formation_template('433')

        for slot_data in template:
            if slot_data['slot'] == 1:
                TeamsheetPlayer.objects.create(
                    teamsheet=teamsheet,
                    club_player=linked_player,
                    custom_name='',
                    custom_number=None,
                    slot_number=slot_data['slot'],
                    position_label=slot_data['position'],
                    position_x=slot_data['x'],
                    position_y=slot_data['y'],
                    is_substitute=False,
                )
                continue

            TeamsheetPlayer.objects.create(
                teamsheet=teamsheet,
                club_player=None,
                custom_name=f"Player {slot_data['slot']}",
                custom_number=slot_data['slot'],
                slot_number=slot_data['slot'],
                position_label=slot_data['position'],
                position_x=slot_data['x'],
                position_y=slot_data['y'],
                is_substitute=False,
            )

        TeamsheetPlayer.objects.create(
            teamsheet=teamsheet,
            club_player=None,
            custom_name='Bench Player',
            custom_number=12,
            slot_number=12,
            position_label='GK',
            position_x=50,
            position_y=10,
            is_substitute=True,
        )

        return teamsheet

    def test_coach_can_duplicate_board_returns_201_and_preserves_structure(self):
        board = self._create_board_with_multiple_frames()

        source_frames = list(board.frames.order_by('frame_index', 'id'))
        source_stable_ids = [
            str(item.stable_id)
            for frame in source_frames
            for item in frame.items.order_by('z_index', 'id')
        ]

        self.client.force_authenticate(user=self.coach)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/{board.id}/duplicate/',
            {
                'title': 'Copied Board',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Copied Board')
        self.assertEqual(response.data['description'], board.description)
        self.assertEqual(response.data['pitch_orientation'], board.pitch_orientation)
        self.assertEqual(response.data['home_formation'], board.home_formation)
        self.assertEqual(response.data['away_formation'], board.away_formation)
        self.assertEqual(response.data['home_colour'], board.home_colour)
        self.assertEqual(response.data['away_colour'], board.away_colour)
        self.assertEqual(response.data['is_template'], board.is_template)
        self.assertEqual(len(response.data['frames']), 2)
        self.assertEqual(len(response.data['frames'][0]['items']), 1)
        self.assertEqual(len(response.data['frames'][1]['items']), 1)

        duplicated_stable_ids = [
            item['stable_id']
            for frame in response.data['frames']
            for item in frame['items']
        ]
        self.assertEqual(duplicated_stable_ids, source_stable_ids)

    def test_viewer_cannot_duplicate_board_returns_403(self):
        board = self._create_board_with_multiple_frames()

        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/{board.id}/duplicate/',
            {
                'title': 'Viewer Copy',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_member_cannot_duplicate_board_returns_403(self):
        board = self._create_board_with_multiple_frames()

        self.client.force_authenticate(user=self.outsider)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/{board.id}/duplicate/',
            {
                'title': 'Outsider Copy',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_create_board_returns_201_and_auto_creates_frame_zero(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/',
            {
                'title': 'Match Plan',
                'description': 'Pressing triggers.',
                'pitch_orientation': 'vertical',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Match Plan')
        self.assertIn('frames', response.data)
        self.assertEqual(len(response.data['frames']), 1)
        self.assertEqual(response.data['frames'][0]['frame_index'], 0)

    def test_create_board_accepts_animated_board_type(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/',
            {
                'title': 'Animated Plan',
                'description': 'Movement-focused animation board.',
                'board_type': 'animated',
                'pitch_orientation': 'horizontal',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['board_type'], 'animated')
        self.assertEqual(response.data['pitch_orientation'], 'horizontal')
        self.assertEqual(len(response.data['frames']), 1)

    def test_list_only_returns_boards_for_the_scoped_club(self):
        board_a = create_board_with_initial_frame(
            club=self.club,
            created_by=self.owner,
            title='Club A Board',
        )
        create_board_with_initial_frame(
            club=self.other_club,
            created_by=self.owner,
            title='Club B Board',
        )

        self.client.force_authenticate(user=self.owner)

        response = self.client.get(f'/api/clubs/{self.club.id}/tactics-boards/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in response.data}
        self.assertEqual(returned_ids, {board_a.id})

    def test_retrieve_returns_nested_frames_and_items(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.owner,
            title='Nested Board',
        )
        frame = board.frames.get(frame_index=0)
        create_item_for_frame(
            frame=frame,
            item_type=TacticsBoardItem.ItemType.TEXT,
            team_side=TacticsBoardItem.TeamSide.NEUTRAL,
            x=25,
            y=35,
            label='Press here',
        )

        self.client.force_authenticate(user=self.owner)

        response = self.client.get(
            f'/api/clubs/{self.club.id}/tactics-boards/{board.id}/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('frames', response.data)
        self.assertEqual(len(response.data['frames']), 1)
        self.assertEqual(len(response.data['frames'][0]['items']), 1)
        self.assertEqual(
            response.data['frames'][0]['items'][0]['label'],
            'Press here',
        )

    def test_create_item_under_frame_works(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.owner,
            title='Item Board',
        )
        frame = board.frames.get(frame_index=0)

        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/{board.id}/frames/{frame.id}/items/',
            {
                'item_type': 'player',
                'team_side': 'home',
                'x': 30,
                'y': 40,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['item_type'], 'player')
        self.assertEqual(response.data['team_side'], 'home')

        self.assertTrue(
            TacticsBoardItem.objects.filter(
                frame=frame,
                item_type=TacticsBoardItem.ItemType.PLAYER,
                team_side=TacticsBoardItem.TeamSide.HOME,
            ).exists()
        )

    def test_non_member_access_is_denied(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.owner,
            title='Private Board',
        )

        self.client.force_authenticate(user=self.outsider)

        response = self.client.get(
            f'/api/clubs/{self.club.id}/tactics-boards/{board.id}/'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_coach_can_create_board_from_teamsheet_returns_201(self):
        teamsheet = self._create_complete_teamsheet()

        self.client.force_authenticate(user=self.coach)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/from-teamsheet/',
            {
                'teamsheet_id': teamsheet.id,
                'title': 'Imported Match Plan',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Imported Match Plan')
        self.assertEqual(response.data['linked_teamsheet'], teamsheet.id)
        self.assertEqual(response.data['home_formation'], '433')
        self.assertEqual(len(response.data['frames']), 1)

        frame_zero = response.data['frames'][0]
        self.assertEqual(frame_zero['frame_index'], 0)
        self.assertEqual(len(frame_zero['items']), 11)

        home_items = [
            item for item in frame_zero['items']
            if item['team_side'] == TacticsBoardItem.TeamSide.HOME
        ]
        self.assertEqual(len(home_items), 11)
        self.assertFalse(
            any(item.get('label') == 'Bench Player' for item in frame_zero['items'])
        )

    def test_viewer_cannot_create_board_from_teamsheet_returns_403(self):
        teamsheet = self._create_complete_teamsheet()

        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/from-teamsheet/',
            {
                'teamsheet_id': teamsheet.id,
                'title': 'Viewer Import',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_member_is_denied_for_from_teamsheet(self):
        teamsheet = self._create_complete_teamsheet()

        self.client.force_authenticate(user=self.outsider)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/from-teamsheet/',
            {
                'teamsheet_id': teamsheet.id,
                'title': 'Outsider Import',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_from_teamsheet_only_imports_starters(self):
        teamsheet = self._create_complete_teamsheet()

        self.client.force_authenticate(user=self.coach)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/from-teamsheet/',
            {
                'teamsheet_id': teamsheet.id,
                'title': 'Starters Only Import',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        frame_zero = response.data['frames'][0]
        labels = [item.get('label') for item in frame_zero['items']]

        self.assertEqual(len(frame_zero['items']), 11)
        self.assertNotIn('Bench Player', labels)

    def test_coach_can_add_opponent_formation_returns_200_and_creates_eleven_away_items(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.owner,
            title='Opponent Shape Board',
        )

        self.client.force_authenticate(user=self.coach)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/{board.id}/add-opponent-formation/',
            {
                'formation': '433',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['away_formation'], '433')
        self.assertEqual(len(response.data['frames']), 1)

        frame_zero = response.data['frames'][0]
        away_items = [
            item for item in frame_zero['items']
            if item['item_type'] == TacticsBoardItem.ItemType.PLAYER
            and item['team_side'] == TacticsBoardItem.TeamSide.AWAY
        ]

        self.assertEqual(len(away_items), 11)

        goalkeeper = next(
            item for item in away_items
            if item['position_label'] == 'GK'
        )
        self.assertEqual(goalkeeper['x'], 50)
        self.assertEqual(goalkeeper['y'], 95)

    def test_add_opponent_formation_invalid_code_returns_400(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.owner,
            title='Invalid Formation Board',
        )

        self.client.force_authenticate(user=self.coach)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/{board.id}/add-opponent-formation/',
            {
                'formation': '999',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('formation', response.data)

    def test_viewer_cannot_add_opponent_formation_returns_403(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.owner,
            title='Viewer Denied Board',
        )

        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/{board.id}/add-opponent-formation/',
            {
                'formation': '433',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_member_is_denied_for_add_opponent_formation(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.owner,
            title='Outsider Denied Board',
        )

        self.client.force_authenticate(user=self.outsider)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/{board.id}/add-opponent-formation/',
            {
                'formation': '433',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_repeated_add_opponent_formation_returns_400(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.owner,
            title='Repeat Guard Board',
        )

        self.client.force_authenticate(user=self.coach)

        first_response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/{board.id}/add-opponent-formation/',
            {
                'formation': '433',
            },
            format='json',
        )
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)

        second_response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/{board.id}/add-opponent-formation/',
            {
                'formation': '442',
            },
            format='json',
        )

        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('formation', second_response.data)

    def test_frame_duplicate_returns_201_and_preserves_stable_id(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.owner,
            title='Duplicate Frame Board',
        )
        source_frame = board.frames.get(frame_index=0)

        source_player = create_item_for_frame(
            frame=source_frame,
            item_type=TacticsBoardItem.ItemType.PLAYER,
            team_side=TacticsBoardItem.TeamSide.HOME,
            label='Player A',
            shirt_number=8,
            position_label='CM',
            x=45,
            y=55,
            z_index=1,
            style={'show_name': True},
        )
        source_arrow = create_item_for_frame(
            frame=source_frame,
            item_type=TacticsBoardItem.ItemType.ARROW,
            team_side=TacticsBoardItem.TeamSide.NEUTRAL,
            label='Run',
            x=20,
            y=30,
            end_x=40,
            end_y=60,
            z_index=2,
            style={'stroke_width': 3},
        )

        self.client.force_authenticate(user=self.coach)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/{board.id}/frames/{source_frame.id}/duplicate/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['frame_index'], 1)
        self.assertEqual(len(response.data['items']), 2)

        duplicated_items = sorted(response.data['items'], key=lambda item: (item['z_index'], item['id']))
        source_items = sorted(
            [source_player, source_arrow],
            key=lambda item: (item.z_index, item.id),
        )

        for source_item, duplicated_item in zip(source_items, duplicated_items):
            self.assertEqual(str(source_item.stable_id), duplicated_item['stable_id'])
            self.assertEqual(source_item.item_type, duplicated_item['item_type'])
            self.assertEqual(source_item.team_side, duplicated_item['team_side'])
            self.assertEqual(source_item.label, duplicated_item['label'])

    def test_frame_duplicate_shifts_later_frames_correctly(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.owner,
            title='Frame Shift Board',
        )
        source_frame = board.frames.get(frame_index=0)
        second_frame = create_frame_for_board(board=board, label='Second')
        third_frame = create_frame_for_board(board=board, label='Third')

        self.client.force_authenticate(user=self.coach)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/{board.id}/frames/{source_frame.id}/duplicate/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        second_frame.refresh_from_db()
        third_frame.refresh_from_db()

        self.assertEqual(response.data['frame_index'], 1)
        self.assertEqual(second_frame.frame_index, 2)
        self.assertEqual(third_frame.frame_index, 3)

    def test_viewer_cannot_duplicate_frame_returns_403(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.owner,
            title='Viewer Frame Duplicate Board',
        )
        frame = board.frames.get(frame_index=0)

        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/{board.id}/frames/{frame.id}/duplicate/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_member_cannot_duplicate_frame_returns_403(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.owner,
            title='Outsider Frame Duplicate Board',
        )
        frame = board.frames.get(frame_index=0)

        self.client.force_authenticate(user=self.outsider)

        response = self.client.post(
            f'/api/clubs/{self.club.id}/tactics-boards/{board.id}/frames/{frame.id}/duplicate/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)