from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Prefetch
from apps.teamsheets.formations import get_formation_template
from apps.teamsheets.models import Teamsheet, TeamsheetPlayer
from apps.tactics.models import (
    DEFAULT_FRAME_DURATION_MS,
    TacticsBoard,
    TacticsBoardFrame,
    TacticsBoardItem,
)

import copy

OPPONENT_IMPORT_FRAME_INDEX = 0
PITCH_COORDINATE_MAX = 100

@transaction.atomic
def create_board_with_initial_frame(
    *,
    club,
    created_by,
    title,
    description='',
    board_type=TacticsBoard.BoardType.STATIC,
    pitch_orientation=TacticsBoard.PitchOrientation.VERTICAL,
    linked_teamsheet=None,
    home_formation='',
    away_formation='',
    home_colour=None,
    away_colour=None,
    is_template=False,
):
    board = TacticsBoard.objects.create(
        club=club,
        created_by=created_by,
        title=title,
        description=description,
        board_type=board_type,
        pitch_orientation=pitch_orientation,
        linked_teamsheet=linked_teamsheet,
        home_formation=home_formation,
        away_formation=away_formation,
        home_colour=home_colour or TacticsBoard._meta.get_field('home_colour').default,
        away_colour=away_colour or TacticsBoard._meta.get_field('away_colour').default,
        is_template=is_template,
    )

    TacticsBoardFrame.objects.create(
        board=board,
        frame_index=0,
        label='',
        duration_ms=DEFAULT_FRAME_DURATION_MS,
        notes='',
    )

    return board


@transaction.atomic
def create_frame_for_board(
    *,
    board,
    label='',
    duration_ms=DEFAULT_FRAME_DURATION_MS,
    notes='',
    copy_items_from_frame_index=None,
):
    if duration_ms is None:
        duration_ms = DEFAULT_FRAME_DURATION_MS

    next_frame_index = board.frames.aggregate(
        max_index=models.Max('frame_index')
    )['max_index']
    next_frame_index = 0 if next_frame_index is None else next_frame_index + 1

    frame = TacticsBoardFrame.objects.create(
        board=board,
        frame_index=next_frame_index,
        label=label,
        duration_ms=duration_ms,
        notes=notes,
    )

    # Copy items from a previous frame if requested
    if copy_items_from_frame_index is not None:
        source_frame = board.frames.filter(
            frame_index=copy_items_from_frame_index
        ).first()

        if source_frame:
            items_to_copy = [
                TacticsBoardItem(
                    frame=frame,
                    item_type=item.item_type,
                    team_side=item.team_side,
                    stable_id=item.stable_id,
                    linked_player=item.linked_player,
                    label=item.label,
                    shirt_number=item.shirt_number,
                    position_label=item.position_label,
                    x=item.x,
                    y=item.y,
                    end_x=item.end_x,
                    end_y=item.end_y,
                    width=item.width,
                    height=item.height,
                    rotation=item.rotation,
                    z_index=item.z_index,
                    style=copy.deepcopy(item.style or {}),
                )
                for item in source_frame.items.order_by('z_index', 'id')
            ]
            if items_to_copy:
                TacticsBoardItem.objects.bulk_create(items_to_copy)

    update_board_type_for_frame_count(board)
    return frame

@transaction.atomic
def create_item_for_frame(*, frame, **validated_data):
    linked_player = validated_data.get('linked_player')
    if linked_player is not None and linked_player.club_id != frame.board.club_id:
        raise ValidationError(
            'Linked player must belong to the same club as the tactics board.'
        )

    item = TacticsBoardItem.objects.create(
        frame=frame,
        **validated_data,
    )
    return item


def update_board_type_for_frame_count(board):
    board.update_board_type(save=True)
    return board


@transaction.atomic
def delete_frame_and_reindex_if_allowed(frame):
    board = frame.board

    if board.frames.count() <= 1:
        raise ValidationError('A tactics board must always have at least one frame.')

    deleted_frame_index = frame.frame_index
    frame.delete()

    remaining_frames = board.frames.filter(
        frame_index__gt=deleted_frame_index
    ).order_by('frame_index')

    for remaining_frame in remaining_frames:
        remaining_frame.frame_index -= 1
        remaining_frame.save(update_fields=['frame_index'])

    update_board_type_for_frame_count(board)
    return board

@transaction.atomic
def create_board_from_teamsheet(
    *,
    club,
    created_by,
    teamsheet_id,
    title,
):
    teamsheet = (
        Teamsheet.objects.select_related('club').prefetch_related(
            Prefetch(
                'players',
                queryset=TeamsheetPlayer.objects.select_related('club_player').order_by(
                    'is_substitute',
                    'slot_number',
                    'id',
                ),
                to_attr='prefetched_players',
            )
        ).filter(
            pk=teamsheet_id,
            club=club,
        ).first()
    )

    if teamsheet is None:
        raise ValidationError({
            'teamsheet_id': 'Teamsheet was not found for this club.',
        })

    board = create_board_with_initial_frame(
        club=club,
        created_by=created_by,
        title=title,
        linked_teamsheet=teamsheet,
        home_formation=teamsheet.formation,
    )

    frame_zero = board.frames.get(frame_index=0)

    starter_rows = [
        row for row in teamsheet.prefetched_players
        if not row.is_substitute
    ]

    starter_items = [
        TacticsBoardItem(
            frame=frame_zero,
            item_type=TacticsBoardItem.ItemType.PLAYER,
            team_side=TacticsBoardItem.TeamSide.HOME,
            linked_player=row.club_player,
            label=row.display_name or '',
            shirt_number=row.display_number,
            position_label=row.position_label,
            x=row.position_x,
            y=row.position_y,
        )
        for row in starter_rows
    ]

    if starter_items:
        TacticsBoardItem.objects.bulk_create(starter_items)

    return board

@transaction.atomic
def add_opponent_formation(
    *,
    board,
    formation,
):
    template = get_formation_template(formation)
    if not template:
        raise ValidationError({
            'formation': 'Invalid formation code.',
        })

    target_frame = board.frames.filter(
        frame_index=OPPONENT_IMPORT_FRAME_INDEX
    ).first()

    if target_frame is None:
        raise ValidationError(
            f'Frame {OPPONENT_IMPORT_FRAME_INDEX} does not exist for this board.'
        )

    existing_away_players = target_frame.items.filter(
        item_type=TacticsBoardItem.ItemType.PLAYER,
        team_side=TacticsBoardItem.TeamSide.AWAY,
    ).exists()

    if existing_away_players:
        raise ValidationError({
            'formation': 'Opponent formation has already been added to this frame.',
        })

    away_items = [
        TacticsBoardItem(
            frame=target_frame,
            item_type=TacticsBoardItem.ItemType.PLAYER,
            team_side=TacticsBoardItem.TeamSide.AWAY,
            label='',
            shirt_number=None,
            position_label=slot_data['position'],
            x=slot_data['x'],
            y=PITCH_COORDINATE_MAX - slot_data['y'],
        )
        for slot_data in template
    ]

    TacticsBoardItem.objects.bulk_create(away_items)

    board.away_formation = formation
    board.save(update_fields=['away_formation', 'updated_at'])

    return board

@transaction.atomic
def duplicate_frame(*, frame):
    board = frame.board
    source_frame_index = frame.frame_index
    duplicated_frame_index = source_frame_index + 1

    later_frames = board.frames.filter(
        frame_index__gt=source_frame_index
    ).order_by('-frame_index')

    for later_frame in later_frames:
        later_frame.frame_index += 1
        later_frame.save(update_fields=['frame_index'])

    duplicated_frame = TacticsBoardFrame.objects.create(
        board=board,
        frame_index=duplicated_frame_index,
        label=frame.label,
        duration_ms=frame.duration_ms,
        notes=frame.notes,
    )

    source_items = frame.items.select_related('linked_player').order_by('z_index', 'id')

    duplicated_items = [
        TacticsBoardItem(
            frame=duplicated_frame,
            item_type=item.item_type,
            team_side=item.team_side,
            stable_id=item.stable_id,
            linked_player=item.linked_player,
            label=item.label,
            shirt_number=item.shirt_number,
            position_label=item.position_label,
            x=item.x,
            y=item.y,
            end_x=item.end_x,
            end_y=item.end_y,
            width=item.width,
            height=item.height,
            rotation=item.rotation,
            z_index=item.z_index,
            style=copy.deepcopy(item.style or {}),
        )
        for item in source_items
    ]

    if duplicated_items:
        TacticsBoardItem.objects.bulk_create(duplicated_items)

    update_board_type_for_frame_count(board)
    return duplicated_frame

@transaction.atomic
def duplicate_board(
    *,
    board,
    created_by,
    title,
):
    source_frames = board.frames.prefetch_related(
        Prefetch(
            'items',
            queryset=TacticsBoardItem.objects.select_related('linked_player').order_by(
                'z_index',
                'id',
            ),
            to_attr='prefetched_items',
        )
    ).order_by('frame_index', 'id')

    duplicated_board = TacticsBoard.objects.create(
        club=board.club,
        created_by=created_by,
        title=title,
        description=board.description,
        pitch_orientation=board.pitch_orientation,
        linked_teamsheet=board.linked_teamsheet,
        home_formation=board.home_formation,
        away_formation=board.away_formation,
        home_colour=board.home_colour,
        away_colour=board.away_colour,
        is_template=board.is_template,
    )

    duplicated_frame_map = {}

    for source_frame in source_frames:
        duplicated_frame = TacticsBoardFrame.objects.create(
            board=duplicated_board,
            frame_index=source_frame.frame_index,
            label=source_frame.label,
            duration_ms=source_frame.duration_ms,
            notes=source_frame.notes,
        )
        duplicated_frame_map[source_frame.id] = duplicated_frame

    duplicated_items = []

    for source_frame in source_frames:
        duplicated_frame = duplicated_frame_map[source_frame.id]
        source_items = getattr(source_frame, 'prefetched_items', [])

        for item in source_items:
            duplicated_items.append(
                TacticsBoardItem(
                    frame=duplicated_frame,
                    item_type=item.item_type,
                    team_side=item.team_side,
                    stable_id=item.stable_id,
                    linked_player=item.linked_player,
                    label=item.label,
                    shirt_number=item.shirt_number,
                    position_label=item.position_label,
                    x=item.x,
                    y=item.y,
                    end_x=item.end_x,
                    end_y=item.end_y,
                    width=item.width,
                    height=item.height,
                    rotation=item.rotation,
                    z_index=item.z_index,
                    style=copy.deepcopy(item.style or {}),
                )
            )

    if duplicated_items:
        TacticsBoardItem.objects.bulk_create(duplicated_items)

    update_board_type_for_frame_count(duplicated_board)
    return duplicated_board