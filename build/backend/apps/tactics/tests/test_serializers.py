from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.clubs.models import Club
from apps.tactics.serializers import (
    AddOpponentFormationActionSerializer,
    DuplicateBoardActionSerializer,
    DuplicateFrameActionSerializer,
    FromTeamsheetBoardActionSerializer,
    TacticsBoardItemWriteSerializer,
)
from apps.tactics.services import create_board_with_initial_frame


def create_test_club(user, name='Serializer Club'):
    club_kwargs = {
        'name': name,
        'description': 'Serializer test club.',
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


class TacticsBoardItemSerializerTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='tactics-serializers@example.com',
            password='testpass123',
        )
        self.club = create_test_club(self.user)
        self.board = create_board_with_initial_frame(
            club=self.club,
            created_by=self.user,
            title='Serializer Board',
        )
        self.frame = self.board.frames.get(frame_index=0)
        self.context = {
            'club': self.club,
            'board': self.board,
            'frame': self.frame,
        }

    def test_arrow_without_end_coordinates_fails(self):
        serializer = TacticsBoardItemWriteSerializer(
            data={
                'item_type': 'arrow',
                'team_side': 'neutral',
                'x': 20,
                'y': 30,
            },
            context=self.context,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('end_x', serializer.errors)
        self.assertIn('end_y', serializer.errors)

    def test_zone_without_width_and_height_fails(self):
        serializer = TacticsBoardItemWriteSerializer(
            data={
                'item_type': 'zone',
                'team_side': 'home',
                'x': 15,
                'y': 25,
            },
            context=self.context,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('width', serializer.errors)
        self.assertIn('height', serializer.errors)

    def test_text_without_label_fails(self):
        serializer = TacticsBoardItemWriteSerializer(
            data={
                'item_type': 'text',
                'team_side': 'neutral',
                'x': 40,
                'y': 45,
            },
            context=self.context,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('label', serializer.errors)

    def test_player_with_irrelevant_end_coordinates_strips_them_cleanly(self):
        serializer = TacticsBoardItemWriteSerializer(
            data={
                'item_type': 'player',
                'team_side': 'home',
                'x': 50,
                'y': 60,
                'end_x': 90,
                'end_y': 95,
            },
            context=self.context,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('end_x', serializer.validated_data)
        self.assertNotIn('end_y', serializer.validated_data)
        self.assertEqual(serializer.validated_data['item_type'], 'player')

    def test_invalid_team_side_is_rejected_when_applicable(self):
        serializer = TacticsBoardItemWriteSerializer(
            data={
                'item_type': 'ball',
                'team_side': 'home',
                'x': 55,
                'y': 65,
            },
            context=self.context,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('team_side', serializer.errors)

class TacticsActionSerializerTests(TestCase):
    def test_from_teamsheet_payload_is_valid_with_expected_fields(self):
        serializer = FromTeamsheetBoardActionSerializer(
            data={
                'teamsheet_id': 12,
                'title': 'Imported Match Plan',
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['teamsheet_id'], 12)
        self.assertEqual(serializer.validated_data['title'], 'Imported Match Plan')

    def test_from_teamsheet_requires_title(self):
        serializer = FromTeamsheetBoardActionSerializer(
            data={
                'teamsheet_id': 12,
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('title', serializer.errors)

    def test_add_opponent_formation_accepts_valid_code(self):
        serializer = AddOpponentFormationActionSerializer(
            data={
                'formation': '433',
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['formation'], '433')

    def test_add_opponent_formation_rejects_invalid_code(self):
        serializer = AddOpponentFormationActionSerializer(
            data={
                'formation': '999',
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('formation', serializer.errors)

    def test_duplicate_frame_accepts_empty_payload(self):
        serializer = DuplicateFrameActionSerializer(data={})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data, {})

    def test_duplicate_board_requires_title(self):
        serializer = DuplicateBoardActionSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn('title', serializer.errors)

    def test_from_teamsheet_rejects_non_positive_teamsheet_id(self):
        serializer = FromTeamsheetBoardActionSerializer(
            data={
                'teamsheet_id': 0,
                'title': 'Imported Match Plan',
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('teamsheet_id', serializer.errors)

    def test_add_opponent_formation_strips_whitespace_and_accepts_valid_code(self):
        serializer = AddOpponentFormationActionSerializer(
            data={
                'formation': ' 433 ',
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['formation'], '433')

    def test_duplicate_board_accepts_valid_title(self):
        serializer = DuplicateBoardActionSerializer(
            data={
                'title': 'Copied Board',
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['title'], 'Copied Board')