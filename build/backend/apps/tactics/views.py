from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.clubs.models import Club
from apps.tactics.models import TacticsBoard, TacticsBoardFrame, TacticsBoardItem
from apps.tactics.permissions import TacticsBoardPermission
from apps.tactics.serializers import (
    AddOpponentFormationActionSerializer,
    DuplicateBoardActionSerializer,
    FromTeamsheetBoardActionSerializer,
    TacticsBoardDetailSerializer,
    TacticsBoardFrameSerializer,
    TacticsBoardFrameWriteSerializer,
    TacticsBoardItemSerializer,
    TacticsBoardItemWriteSerializer,
    TacticsBoardListSerializer,
    TacticsBoardTrashActionSerializer,
    TacticsBoardWriteSerializer,
)
from apps.tactics.services import (
    add_opponent_formation,
    create_board_from_teamsheet,
    create_board_with_initial_frame,
    create_frame_for_board,
    create_item_for_frame,
    delete_frame_and_reindex_if_allowed,
    duplicate_board,
    duplicate_frame,
)


class TacticsContextMixin:
    def get_club(self):
        club_pk = self.kwargs.get('club_pk')
        return get_object_or_404(Club, pk=club_pk)

    def get_board(self):
        board_pk = self.kwargs.get('board_pk')
        if board_pk is None:
            board_pk = self.kwargs.get('pk')

        return get_object_or_404(
            TacticsBoard.objects.select_related(
                'club',
                'created_by',
                'linked_teamsheet',
                'trashed_by',
            ),
            pk=board_pk,
            club_id=self.kwargs.get('club_pk'),
            is_trashed=False,
        )

    def get_frame(self):
        frame_pk = self.kwargs.get('frame_pk')
        if frame_pk is None:
            frame_pk = self.kwargs.get('pk')

        return get_object_or_404(
            TacticsBoardFrame.objects.select_related('board', 'board__club'),
            pk=frame_pk,
            board_id=self.kwargs.get('board_pk'),
            board__club_id=self.kwargs.get('club_pk'),
            board__is_trashed=False,
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()

        club_pk = self.kwargs.get('club_pk')
        board_pk = self.kwargs.get('board_pk')
        frame_pk = self.kwargs.get('frame_pk')

        if club_pk is not None:
            context['club'] = self.get_club()

        if board_pk is not None:
            context['board'] = self.get_board()

        if frame_pk is not None:
            context['frame'] = self.get_frame()

        return context

    def _raise_drf_validation_error(self, exc):
        if hasattr(exc, 'message_dict'):
            raise ValidationError(exc.message_dict)
        if hasattr(exc, 'messages'):
            raise ValidationError(exc.messages)
        raise ValidationError(str(exc))


class TacticsBoardViewSet(TacticsContextMixin, viewsets.ModelViewSet):
    permission_classes = [TacticsBoardPermission]
    pagination_class = None

    def _get_trash_mode(self) -> str:
        value = (self.request.query_params.get('trash') or '').strip().lower()
        if value in {'only', 'include'}:
            return value
        return 'exclude'


    def _build_board_queryset(self, include_trashed=False):
        item_queryset = TacticsBoardItem.objects.select_related(
            'linked_player'
        ).order_by('z_index', 'id')

        frame_queryset = TacticsBoardFrame.objects.order_by(
            'frame_index', 'id'
        ).prefetch_related(
            Prefetch(
                'items',
                queryset=item_queryset,
                to_attr='prefetched_items',
            )
        )

        queryset = TacticsBoard.objects.filter(
            club_id=self.kwargs.get('club_pk')
        ).select_related(
            'club',
            'created_by',
            'linked_teamsheet',
            'trashed_by',
        ).prefetch_related(
            Prefetch(
                'frames',
                queryset=frame_queryset,
                to_attr='prefetched_frames',
            )
        ).order_by('-updated_at')

        if include_trashed:
            return queryset

        trash_mode = self._get_trash_mode()

        if trash_mode == 'only':
            if not self.request.user.is_authenticated:
                return queryset.none()

            return queryset.filter(
                is_trashed=True,
                created_by=self.request.user,
            )

        if trash_mode == 'include':
            if not self.request.user.is_authenticated:
                return queryset.filter(is_trashed=False)

            return queryset.filter(
                models.Q(is_trashed=False) |
                models.Q(is_trashed=True, created_by=self.request.user)
            )

        return queryset.filter(is_trashed=False)


    def get_queryset(self):
        return self._build_board_queryset(include_trashed=False)


    def _get_board_for_action(self, pk, *, require_trashed=None):
        board = get_object_or_404(
            self._build_board_queryset(include_trashed=True),
            pk=pk,
        )
        self.check_object_permissions(self.request, board)

        if require_trashed is True and not board.is_trashed:
            raise ValidationError('This tactics board is not in trash.')

        if require_trashed is False and board.is_trashed:
            raise ValidationError('This tactics board is already in trash.')

        return board

    def get_serializer_class(self):
        if self.action == 'list':
            return TacticsBoardListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return TacticsBoardWriteSerializer
        return TacticsBoardDetailSerializer

    def get_serializer_context(self):
        context = super(viewsets.ModelViewSet, self).get_serializer_context()
        club_pk = self.kwargs.get('club_pk')

        if club_pk is not None:
            context['club'] = self.get_club()

        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        club = self.get_club()
        board_data = dict(serializer.validated_data)

        # Check tactics board creation limit
        create_limit = getattr(settings, 'TACTICS_BOARD_CREATE_LIMIT_PER_USER', 10)
        user_board_count = TacticsBoard.objects.filter(
            club_id=club.pk,
            created_by=request.user,
            is_trashed=False,
        ).count()
        if user_board_count >= create_limit:
            raise ValidationError({
                'detail': f'You have reached the maximum limit of {create_limit} tactics boards. Please delete some tactics boards before creating new ones.'
            })

        try:
            board = create_board_with_initial_frame(
                club=club,
                created_by=request.user,
                **board_data,
            )
        except DjangoValidationError as exc:
            self._raise_drf_validation_error(exc)

        response_serializer = TacticsBoardDetailSerializer(
            self.get_queryset().get(pk=board.pk),
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='from-teamsheet')
    def from_teamsheet(self, request, *args, **kwargs):
        serializer = FromTeamsheetBoardActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        club = self.get_club()

        try:
            board = create_board_from_teamsheet(
                club=club,
                created_by=request.user,
                teamsheet_id=serializer.validated_data['teamsheet_id'],
                title=serializer.validated_data['title'],
            )
        except DjangoValidationError as exc:
            self._raise_drf_validation_error(exc)

        response_serializer = TacticsBoardDetailSerializer(
            self.get_queryset().get(pk=board.pk),
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='add-opponent-formation')
    def add_opponent_formation(self, request, *args, **kwargs):
        serializer = AddOpponentFormationActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        board = self.get_board()

        try:
            board = add_opponent_formation(
                board=board,
                formation=serializer.validated_data['formation'],
            )
        except DjangoValidationError as exc:
            self._raise_drf_validation_error(exc)

        response_serializer = TacticsBoardDetailSerializer(
            self.get_queryset().get(pk=board.pk),
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='duplicate')
    def duplicate(self, request, *args, **kwargs):
        serializer = DuplicateBoardActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        board = self.get_board()

        try:
            duplicated_board = duplicate_board(
                board=board,
                created_by=request.user,
                title=serializer.validated_data['title'],
            )
        except DjangoValidationError as exc:
            self._raise_drf_validation_error(exc)

        response_serializer = TacticsBoardDetailSerializer(
            self.get_queryset().get(pk=duplicated_board.pk),
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='trash')
    def trash(self, request, *args, **kwargs):
        serializer = TacticsBoardTrashActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        board = self._get_board_for_action(kwargs.get('pk'), require_trashed=False)
        board.move_to_trash(request.user)

        response_serializer = TacticsBoardDetailSerializer(
            self._build_board_queryset(include_trashed=True).get(pk=board.pk),
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)


    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, *args, **kwargs):
        serializer = TacticsBoardTrashActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        board = self._get_board_for_action(kwargs.get('pk'), require_trashed=True)
        board.restore_from_trash(request.user)

        response_serializer = TacticsBoardDetailSerializer(
            self._build_board_queryset(include_trashed=True).get(pk=board.pk),
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)


    @action(detail=True, methods=['delete'], url_path='permanent-delete')
    def permanent_delete(self, request, *args, **kwargs):
        board = self._get_board_for_action(kwargs.get('pk'), require_trashed=True)

        if not board.can_be_permanently_deleted_by(request.user):
            raise PermissionDenied(
                'Only the tactics board creator can permanently delete this board.'
            )

        board.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        if not instance.can_be_trashed_by(self.request.user):
            raise PermissionDenied(
                'Only the tactics board creator can move this board to trash.'
            )

        instance.move_to_trash(self.request.user)


class TacticsBoardFrameViewSet(TacticsContextMixin, viewsets.ModelViewSet):
    permission_classes = [TacticsBoardPermission]
    pagination_class = None

    def get_queryset(self):
        item_queryset = TacticsBoardItem.objects.select_related(
            'linked_player'
        ).order_by('z_index', 'id')

        return TacticsBoardFrame.objects.filter(
            board_id=self.kwargs.get('board_pk'),
            board__club_id=self.kwargs.get('club_pk'),
            board__is_trashed=False,
        ).prefetch_related(
            Prefetch(
                'items',
                queryset=item_queryset,
                to_attr='prefetched_items',
            )
        ).order_by('frame_index', 'id')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TacticsBoardFrameWriteSerializer
        return TacticsBoardFrameSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        board = self.get_board()

        frame = create_frame_for_board(
            board=board,
            label=serializer.validated_data.get('label', ''),
            duration_ms=serializer.validated_data.get('duration_ms'),
            notes=serializer.validated_data.get('notes', ''),
        )

        response_serializer = TacticsBoardFrameSerializer(
            self.get_queryset().get(pk=frame.pk),
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        try:
            delete_frame_and_reindex_if_allowed(instance)
        except DjangoValidationError as exc:
            self._raise_drf_validation_error(exc)

    @action(detail=True, methods=['post'], url_path='duplicate')
    def duplicate(self, request, *args, **kwargs):
        frame = self.get_object()

        try:
            duplicated_frame = duplicate_frame(frame=frame)
        except DjangoValidationError as exc:
            self._raise_drf_validation_error(exc)

        response_serializer = TacticsBoardFrameSerializer(
            self.get_queryset().get(pk=duplicated_frame.pk),
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class TacticsBoardItemViewSet(TacticsContextMixin, viewsets.ModelViewSet):
    permission_classes = [TacticsBoardPermission]
    pagination_class = None

    def get_queryset(self):
        return TacticsBoardItem.objects.filter(
            frame_id=self.kwargs.get('frame_pk'),
            frame__board_id=self.kwargs.get('board_pk'),
            frame__board__club_id=self.kwargs.get('club_pk'),
            frame__board__is_trashed=False,
        ).select_related(
            'frame',
            'frame__board',
            'frame__board__club',
            'linked_player',
        ).order_by('z_index', 'id')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TacticsBoardItemWriteSerializer
        return TacticsBoardItemSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        frame = self.get_frame()
        item_data = dict(serializer.validated_data)
        item_data.pop('frame', None)

        try:
            item = create_item_for_frame(
                frame=frame,
                **item_data,
            )
        except DjangoValidationError as exc:
            self._raise_drf_validation_error(exc)

        response_serializer = TacticsBoardItemSerializer(
            self.get_queryset().get(pk=item.pk),
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        try:
            serializer.save()
        except DjangoValidationError as exc:
            self._raise_drf_validation_error(exc)

    def perform_destroy(self, instance):
        instance.delete()