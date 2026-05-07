"""
Tests for tactics board models and service helpers

Checks board creation, frame rules, coordinate validation, teamsheet imports, opponent formations, and duplication behaviour
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.tactics.models import TacticsBoard, TacticsBoardFrame, TacticsBoardItem
from apps.clubs.models import Club, ClubPlayer
from apps.tactics.services import (
    add_opponent_formation,
    create_board_from_teamsheet,
    create_board_with_initial_frame,
    create_frame_for_board,
    delete_frame_and_reindex_if_allowed,
    duplicate_board,
    duplicate_frame,
)
from apps.teamsheets.formations import get_formation_template
from apps.teamsheets.models import Teamsheet, TeamsheetPlayer


# Create a test club with compatibility for newer club model fields
def create_test_club(user, name='Test Club'):
    club_kwargs = {
        'name': name,
        'description': 'Test club description.',
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


# Tests for tactics board model constraints and frame behaviour
class TacticsBoardModelTests(TestCase):

    # Create a user and club for model tests
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='tactics-models@example.com',
            password='testpass123',
        )
        self.club = create_test_club(self.user)

    # Check frame index uniqueness is enforced per board
    def test_frame_index_must_be_unique_per_board(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.user,
            title='Uniqueness Board',
        )

        with self.assertRaises(IntegrityError):
            TacticsBoardFrame.objects.create(
                board=board,
                frame_index=0,
                label='Duplicate frame zero',
            )

    # Check coordinates below the pitch minimum are rejected
    def test_coordinate_validators_reject_minus_one(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.user,
            title='Coordinate Board A',
        )
        frame = board.frames.get(frame_index=0)

        item = TacticsBoardItem(
            frame=frame,
            item_type=TacticsBoardItem.ItemType.PLAYER,
            team_side=TacticsBoardItem.TeamSide.HOME,
            x=-1,
            y=50,
        )

        with self.assertRaises(ValidationError):
            item.full_clean()

    # Check coordinates above the pitch maximum are rejected
    def test_coordinate_validators_reject_one_hundred_and_one(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.user,
            title='Coordinate Board B',
        )
        frame = board.frames.get(frame_index=0)

        item = TacticsBoardItem(
            frame=frame,
            item_type=TacticsBoardItem.ItemType.BALL,
            team_side=TacticsBoardItem.TeamSide.NEUTRAL,
            x=50,
            y=101,
        )

        with self.assertRaises(ValidationError):
            item.full_clean()

    # Check a board with one frame remains static
    def test_board_creation_with_one_frame_is_static(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.user,
            title='Static Board',
        )

        board.refresh_from_db()

        self.assertEqual(board.frames.count(), 1)
        self.assertEqual(board.board_type, TacticsBoard.BoardType.STATIC)

    # Check a second frame changes the board to animated
    def test_adding_second_frame_changes_board_type_to_animated(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.user,
            title='Animated Board',
        )

        create_frame_for_board(board=board, label='Second frame')

        board.refresh_from_db()

        self.assertEqual(board.frames.count(), 2)
        self.assertEqual(board.board_type, TacticsBoard.BoardType.ANIMATED)

    # Check returning to one frame changes the board back to static
    def test_returning_to_one_frame_changes_board_type_back_to_static(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.user,
            title='Back To Static Board',
        )

        second_frame = create_frame_for_board(board=board, label='Second frame')
        delete_frame_and_reindex_if_allowed(second_frame)

        board.refresh_from_db()

        self.assertEqual(board.frames.count(), 1)
        self.assertEqual(board.board_type, TacticsBoard.BoardType.STATIC)
        self.assertEqual(board.frames.get().frame_index, 0)

    # Check the final frame cannot be deleted
    def test_deleting_final_frame_is_blocked(self):
        board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.user,
            title='Protected Frame Board',
        )
        frame = board.frames.get(frame_index=0)

        with self.assertRaises(ValidationError):
            delete_frame_and_reindex_if_allowed(frame)


# Tests for creating tactics boards from teamsheets
class CreateBoardFromTeamsheetServiceTests(TestCase):

    # Create a user, club, and linked club player for import tests
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='tactics-imports@example.com',
            password='testpass123',
        )
        self.club = create_test_club(self.user)

        self.linked_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='John',
            last_name='Keeper',
            display_name='John Keeper',
            squad_number=1,
            primary_position='GK',
            created_by=self.user,
        )

    # Create a complete teamsheet with starters and one substitute
    def _create_complete_teamsheet(self, club=None):
        if club is None:
            club = self.club

        teamsheet = Teamsheet.objects.create(
            club=club,
            created_by=self.user,
            title='Matchday XI',
            formation='433',
        )

        template = get_formation_template('433')

        for slot_data in template:
            if slot_data['slot'] == 1:
                TeamsheetPlayer.objects.create(
                    teamsheet=teamsheet,
                    club_player=self.linked_player,
                    custom_name='',
                    custom_number=None,
                    slot_number=slot_data['slot'],
                    position_label=slot_data['position'],
                    position_x=slot_data['x'],
                    position_y=slot_data['y'],
                    is_substitute=False,
                )
                continue

            if slot_data['slot'] == 2:
                TeamsheetPlayer.objects.create(
                    teamsheet=teamsheet,
                    club_player=None,
                    custom_name='Custom 2',
                    custom_number=22,
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

    # Check teamsheet imports create player items for starters only
    def test_create_board_from_teamsheet_imports_starters_only(self):
        teamsheet = self._create_complete_teamsheet()

        board = create_board_from_teamsheet(
            club=self.club,
            created_by=self.user,
            teamsheet_id=teamsheet.id,
            title='Imported Board',
        )

        board.refresh_from_db()
        frame_zero = board.frames.get(frame_index=0)
        items = frame_zero.items.order_by('id')

        self.assertEqual(board.linked_teamsheet_id, teamsheet.id)
        self.assertEqual(board.home_formation, teamsheet.formation)
        self.assertEqual(items.count(), 11)
        self.assertFalse(items.filter(label='Bench Player').exists())

        linked_item = items.get(linked_player=self.linked_player)
        self.assertEqual(linked_item.item_type, TacticsBoardItem.ItemType.PLAYER)
        self.assertEqual(linked_item.team_side, TacticsBoardItem.TeamSide.HOME)
        self.assertEqual(linked_item.label, 'John Keeper')
        self.assertEqual(linked_item.shirt_number, 1)
        self.assertEqual(linked_item.position_label, 'GK')
        self.assertEqual(linked_item.x, 50)
        self.assertEqual(linked_item.y, 5)

        custom_item = items.get(label='Custom 2')
        self.assertEqual(custom_item.shirt_number, 22)

    # Check teamsheets from another club cannot be imported
    def test_create_board_from_teamsheet_rejects_cross_club_teamsheet(self):
        other_club = create_test_club(self.user, name='Other Club')
        teamsheet = self._create_complete_teamsheet(club=other_club)

        with self.assertRaises(ValidationError):
            create_board_from_teamsheet(
                club=self.club,
                created_by=self.user,
                teamsheet_id=teamsheet.id,
                title='Should Fail',
            )


# Tests for adding opponent formations to boards
class AddOpponentFormationServiceTests(TestCase):

    # Create a board with an initial frame for opponent import tests
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='tactics-opponent@example.com',
            password='testpass123',
        )
        self.club = create_test_club(self.user)
        self.board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.user,
            title='Opponent Import Board',
        )

    # Check adding an opponent formation creates eleven away player items
    def test_add_opponent_formation_creates_eleven_away_items(self):
        board = add_opponent_formation(
            board=self.board,
            formation='433',
        )

        frame_zero = board.frames.get(frame_index=0)
        away_items = frame_zero.items.filter(
            item_type=TacticsBoardItem.ItemType.PLAYER,
            team_side=TacticsBoardItem.TeamSide.AWAY,
        ).order_by('id')

        self.assertEqual(board.away_formation, '433')
        self.assertEqual(away_items.count(), 11)

    # Check the away goalkeeper is mirrored to the top of the pitch
    def test_add_opponent_formation_mirrors_goalkeeper_y_to_top(self):
        board = add_opponent_formation(
            board=self.board,
            formation='433',
        )

        frame_zero = board.frames.get(frame_index=0)
        goalkeeper = frame_zero.items.get(
            item_type=TacticsBoardItem.ItemType.PLAYER,
            team_side=TacticsBoardItem.TeamSide.AWAY,
            position_label='GK',
        )

        self.assertEqual(goalkeeper.x, 50)
        self.assertEqual(goalkeeper.y, 95)

    # Check opponent import preserves formation x positions
    def test_add_opponent_formation_preserves_template_x_values(self):
        board = add_opponent_formation(
            board=self.board,
            formation='433',
        )

        frame_zero = board.frames.get(frame_index=0)
        right_back = frame_zero.items.get(
            item_type=TacticsBoardItem.ItemType.PLAYER,
            team_side=TacticsBoardItem.TeamSide.AWAY,
            position_label='RB',
        )

        self.assertEqual(right_back.x, 85)
        self.assertEqual(right_back.y, 75)

    # Check invalid formation codes are rejected
    def test_add_opponent_formation_rejects_invalid_code(self):
        with self.assertRaises(ValidationError):
            add_opponent_formation(
                board=self.board,
                formation='999',
            )

    # Check the same frame cannot receive opponent players twice
    def test_add_opponent_formation_rejects_repeated_import_on_same_frame(self):
        add_opponent_formation(
            board=self.board,
            formation='433',
        )

        with self.assertRaises(ValidationError):
            add_opponent_formation(
                board=self.board,
                formation='442',
            )


# Tests for duplicating tactics board frames
class DuplicateFrameServiceTests(TestCase):

    # Create a multi-frame board with source items for duplication tests
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='tactics-duplicate-frame@example.com',
            password='testpass123',
        )
        self.club = create_test_club(self.user)
        self.board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.user,
            title='Frame Duplication Board',
        )

        self.source_frame = self.board.frames.get(frame_index=0)
        self.second_frame = create_frame_for_board(board=self.board, label='Second')
        self.third_frame = create_frame_for_board(board=self.board, label='Third')

        self.source_player = TacticsBoardItem.objects.create(
            frame=self.source_frame,
            item_type=TacticsBoardItem.ItemType.PLAYER,
            team_side=TacticsBoardItem.TeamSide.HOME,
            label='Player A',
            shirt_number=8,
            position_label='CM',
            x=45,
            y=55,
            rotation=10,
            z_index=1,
            style={'show_name': True},
        )
        self.source_arrow = TacticsBoardItem.objects.create(
            frame=self.source_frame,
            item_type=TacticsBoardItem.ItemType.ARROW,
            team_side=TacticsBoardItem.TeamSide.NEUTRAL,
            label='Run',
            x=20,
            y=30,
            end_x=40,
            end_y=60,
            rotation=0,
            z_index=2,
            style={'stroke_width': 3},
        )

    # Check duplicated frames are inserted after the source frame
    def test_duplicate_frame_inserts_new_frame_immediately_after_source(self):
        duplicated_frame = duplicate_frame(frame=self.source_frame)

        frame_indices = list(
            self.board.frames.order_by('frame_index').values_list('frame_index', flat=True)
        )

        self.assertEqual(duplicated_frame.frame_index, 1)
        self.assertEqual(frame_indices, [0, 1, 2, 3])

    # Check duplicating a frame shifts later frame indexes
    def test_duplicate_frame_shifts_later_frames_correctly(self):
        duplicated_frame = duplicate_frame(frame=self.source_frame)

        self.second_frame.refresh_from_db()
        self.third_frame.refresh_from_db()

        self.assertEqual(duplicated_frame.frame_index, 1)
        self.assertEqual(self.second_frame.frame_index, 2)
        self.assertEqual(self.third_frame.frame_index, 3)

    # Check all source frame items are copied
    def test_duplicate_frame_copies_all_items(self):
        duplicated_frame = duplicate_frame(frame=self.source_frame)

        self.assertEqual(self.source_frame.items.count(), 2)
        self.assertEqual(duplicated_frame.items.count(), 2)

    # Check duplicated items preserve stable IDs while getting new database IDs
    def test_duplicate_frame_preserves_stable_id_exactly(self):
        duplicated_frame = duplicate_frame(frame=self.source_frame)

        source_items = list(self.source_frame.items.order_by('z_index', 'id'))
        duplicated_items = list(duplicated_frame.items.order_by('z_index', 'id'))

        self.assertEqual(len(source_items), len(duplicated_items))

        for source_item, duplicated_item in zip(source_items, duplicated_items):
            self.assertEqual(duplicated_item.stable_id, source_item.stable_id)
            self.assertNotEqual(duplicated_item.id, source_item.id)
            self.assertEqual(duplicated_item.item_type, source_item.item_type)
            self.assertEqual(duplicated_item.team_side, source_item.team_side)
            self.assertEqual(duplicated_item.label, source_item.label)
            self.assertEqual(duplicated_item.x, source_item.x)
            self.assertEqual(duplicated_item.y, source_item.y)
            self.assertEqual(duplicated_item.end_x, source_item.end_x)
            self.assertEqual(duplicated_item.end_y, source_item.end_y)
            self.assertEqual(duplicated_item.width, source_item.width)
            self.assertEqual(duplicated_item.height, source_item.height)
            self.assertEqual(duplicated_item.rotation, source_item.rotation)
            self.assertEqual(duplicated_item.z_index, source_item.z_index)
            self.assertEqual(duplicated_item.style, source_item.style)

    # Check duplicating a frame keeps the board type accurate
    def test_duplicate_frame_keeps_board_type_correct(self):
        duplicated_frame = duplicate_frame(frame=self.source_frame)

        self.board.refresh_from_db()

        self.assertEqual(duplicated_frame.board_id, self.board.id)
        self.assertEqual(self.board.frames.count(), 4)
        self.assertEqual(self.board.board_type, TacticsBoard.BoardType.ANIMATED)


# Tests for duplicating full tactics boards
class DuplicateBoardServiceTests(TestCase):

    # Create a source board with frames, items, and metadata for duplication tests
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            email='tactics-duplicate-board-owner@example.com',
            password='testpass123',
        )
        self.coach = get_user_model().objects.create_user(
            email='tactics-duplicate-board-coach@example.com',
            password='testpass123',
        )
        self.club = create_test_club(self.owner)

        self.linked_player = ClubPlayer.objects.create(
            club=self.club,
            first_name='John',
            last_name='Keeper',
            display_name='John Keeper',
            squad_number=1,
            primary_position='GK',
            created_by=self.owner,
        )

        self.teamsheet = Teamsheet.objects.create(
            club=self.club,
            created_by=self.owner,
            title='Source Teamsheet',
            formation='433',
        )

        self.source_board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.owner,
            title='Source Board',
            description='Original tactical plan.',
            pitch_orientation=TacticsBoard.PitchOrientation.HORIZONTAL,
            linked_teamsheet=self.teamsheet,
            home_formation='433',
            away_formation='442',
            home_colour='#111111',
            away_colour='#222222',
            is_template=True,
        )

        self.frame_zero = self.source_board.frames.get(frame_index=0)
        self.frame_one = create_frame_for_board(
            board=self.source_board,
            label='Second frame',
            duration_ms=2000,
            notes='Transition phase',
        )

        self.source_item_a = TacticsBoardItem.objects.create(
            frame=self.frame_zero,
            item_type=TacticsBoardItem.ItemType.PLAYER,
            team_side=TacticsBoardItem.TeamSide.HOME,
            linked_player=self.linked_player,
            label='John Keeper',
            shirt_number=1,
            position_label='GK',
            x=50,
            y=5,
            rotation=0,
            z_index=1,
            style={'show_name': True},
        )
        self.source_item_b = TacticsBoardItem.objects.create(
            frame=self.frame_one,
            item_type=TacticsBoardItem.ItemType.ARROW,
            team_side=TacticsBoardItem.TeamSide.NEUTRAL,
            label='Build-up',
            x=20,
            y=30,
            end_x=40,
            end_y=60,
            rotation=0,
            z_index=2,
            style={'stroke_width': 3},
        )

    # Check full board duplication preserves metadata, frames, and item counts
    def test_duplicate_board_copies_metadata_frames_and_items(self):
        duplicated_board = duplicate_board(
            board=self.source_board,
            created_by=self.coach,
            title='Copied Board',
        )

        self.assertNotEqual(duplicated_board.id, self.source_board.id)
        self.assertEqual(duplicated_board.club_id, self.source_board.club_id)
        self.assertEqual(duplicated_board.created_by_id, self.coach.id)
        self.assertEqual(duplicated_board.title, 'Copied Board')
        self.assertEqual(duplicated_board.description, self.source_board.description)
        self.assertEqual(duplicated_board.pitch_orientation, self.source_board.pitch_orientation)
        self.assertEqual(duplicated_board.linked_teamsheet_id, self.source_board.linked_teamsheet_id)
        self.assertEqual(duplicated_board.home_formation, self.source_board.home_formation)
        self.assertEqual(duplicated_board.away_formation, self.source_board.away_formation)
        self.assertEqual(duplicated_board.home_colour, self.source_board.home_colour)
        self.assertEqual(duplicated_board.away_colour, self.source_board.away_colour)
        self.assertEqual(duplicated_board.is_template, self.source_board.is_template)
        self.assertEqual(duplicated_board.frames.count(), self.source_board.frames.count())

        source_frames = list(self.source_board.frames.order_by('frame_index', 'id'))
        duplicated_frames = list(duplicated_board.frames.order_by('frame_index', 'id'))

        for source_frame, duplicated_frame in zip(source_frames, duplicated_frames):
            self.assertEqual(duplicated_frame.frame_index, source_frame.frame_index)
            self.assertEqual(duplicated_frame.label, source_frame.label)
            self.assertEqual(duplicated_frame.duration_ms, source_frame.duration_ms)
            self.assertEqual(duplicated_frame.notes, source_frame.notes)
            self.assertEqual(duplicated_frame.items.count(), source_frame.items.count())

    # Check duplicated board items preserve stable IDs
    def test_duplicate_board_preserves_stable_id_exactly(self):
        duplicated_board = duplicate_board(
            board=self.source_board,
            created_by=self.coach,
            title='Copied Board',
        )

        source_frames = list(self.source_board.frames.order_by('frame_index', 'id'))
        duplicated_frames = list(duplicated_board.frames.order_by('frame_index', 'id'))

        for source_frame, duplicated_frame in zip(source_frames, duplicated_frames):
            source_items = list(source_frame.items.order_by('z_index', 'id'))
            duplicated_items = list(duplicated_frame.items.order_by('z_index', 'id'))

            self.assertEqual(len(source_items), len(duplicated_items))

            for source_item, duplicated_item in zip(source_items, duplicated_items):
                self.assertEqual(duplicated_item.stable_id, source_item.stable_id)
                self.assertNotEqual(duplicated_item.id, source_item.id)
                self.assertEqual(duplicated_item.item_type, source_item.item_type)
                self.assertEqual(duplicated_item.team_side, source_item.team_side)
                self.assertEqual(duplicated_item.linked_player_id, source_item.linked_player_id)
                self.assertEqual(duplicated_item.label, source_item.label)
                self.assertEqual(duplicated_item.shirt_number, source_item.shirt_number)
                self.assertEqual(duplicated_item.position_label, source_item.position_label)
                self.assertEqual(duplicated_item.x, source_item.x)
                self.assertEqual(duplicated_item.y, source_item.y)
                self.assertEqual(duplicated_item.end_x, source_item.end_x)
                self.assertEqual(duplicated_item.end_y, source_item.end_y)
                self.assertEqual(duplicated_item.width, source_item.width)
                self.assertEqual(duplicated_item.height, source_item.height)
                self.assertEqual(duplicated_item.rotation, source_item.rotation)
                self.assertEqual(duplicated_item.z_index, source_item.z_index)
                self.assertEqual(duplicated_item.style, source_item.style)

    # Check edits to duplicated items do not affect the source board
    def test_duplicate_board_is_independent_after_creation(self):
        duplicated_board = duplicate_board(
            board=self.source_board,
            created_by=self.coach,
            title='Copied Board',
        )

        duplicated_item = duplicated_board.frames.get(frame_index=0).items.get(
            stable_id=self.source_item_a.stable_id
        )
        duplicated_item.label = 'Changed Copy'
        duplicated_item.save(update_fields=['label'])

        self.source_item_a.refresh_from_db()
        self.assertEqual(self.source_item_a.label, 'John Keeper')