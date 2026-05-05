from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.clubs.models import Club

from .models import TrainingBlock, TrainingSession, TrainingSessionPlayer
from .permissions import TrainingSessionPermission
from .serializers import (
    TrainingAttendanceBulkSerializer,
    TrainingBlockSerializer,
    TrainingSessionAssignPlayersSerializer,
    TrainingSessionDetailSerializer,
    TrainingSessionListSerializer,
    TrainingSessionPlayerSerializer,
    TrainingSessionWriteSerializer,
)
from .services import sync_session_calendar_event


class TrainingContextMixin:
    def get_club(self):
        return get_object_or_404(Club, pk=self.kwargs.get('club_pk'))

    def get_session(self):
        session_pk = self.kwargs.get('session_pk') or self.kwargs.get('pk')
        return get_object_or_404(
            TrainingSession.objects.select_related('club', 'created_by', 'linked_teamsheet').prefetch_related(
                'blocks',
                Prefetch(
                    'players',
                    queryset=TrainingSessionPlayer.objects.select_related('club_player'),
                ),
            ),
            pk=session_pk,
            club_id=self.kwargs.get('club_pk'),
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.kwargs.get('club_pk') is not None:
            context['club'] = self.get_club()
        if self.kwargs.get('session_pk') is not None:
            context['session'] = self.get_session()
        return context


class TrainingSessionViewSet(TrainingContextMixin, viewsets.ModelViewSet):
    permission_classes = [TrainingSessionPermission]
    pagination_class = None

    def get_queryset(self):
        block_queryset = TrainingBlock.objects.order_by('order', 'id')
        player_queryset = TrainingSessionPlayer.objects.select_related('club_player')
        queryset = TrainingSession.objects.filter(
            club_id=self.kwargs.get('club_pk'),
        ).select_related(
            'club',
            'created_by',
            'linked_teamsheet',
            'calendar_event',
        ).prefetch_related(
            Prefetch('blocks', queryset=block_queryset, to_attr='prefetched_blocks'),
            Prefetch('players', queryset=player_queryset),
        ).annotate(
            assigned_player_count=Count('players', distinct=True),
            attended_count=Count(
                'players',
                filter=Q(players__attendance_status=TrainingSessionPlayer.AttendanceStatus.ATTENDED),
                distinct=True,
            ),
        ).order_by('start_datetime', 'id')

        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        session_type = self.request.query_params.get('session_type')
        if session_type:
            queryset = queryset.filter(session_type=session_type)

        search = (self.request.query_params.get('search') or '').strip()
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(main_objective__icontains=search)
                | Q(location__icontains=search)
                | Q(linked_opponent__icontains=search)
            )

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return TrainingSessionListSerializer
        if self.action in {'create', 'update', 'partial_update'}:
            return TrainingSessionWriteSerializer
        return TrainingSessionDetailSerializer

    def _detail_response(self, session, response_status=status.HTTP_200_OK):
        session = self.get_queryset().get(pk=session.pk)
        return Response(TrainingSessionDetailSerializer(session, context=self.get_serializer_context()).data, status=response_status)

    def perform_create(self, serializer):
        session = serializer.save()
        sync_session_calendar_event(session)

    def perform_update(self, serializer):
        session = serializer.save()
        sync_session_calendar_event(session)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return self._detail_response(serializer.instance, status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return self._detail_response(serializer.instance)

    @action(detail=True, methods=['post'], url_path='assign-players')
    def assign_players(self, request, club_pk=None, pk=None):
        session = self.get_object()
        serializer = TrainingSessionAssignPlayersSerializer(
            data=request.data,
            context={'club': session.club, 'session': session},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self._detail_response(session)

    @action(detail=True, methods=['patch'], url_path='attendance')
    def attendance(self, request, club_pk=None, pk=None):
        session = self.get_object()
        serializer = TrainingAttendanceBulkSerializer(
            data=request.data,
            context={'session': session},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self._detail_response(session)

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, club_pk=None, pk=None):
        session = self.get_object()
        serializer = TrainingSessionWriteSerializer(
            session,
            data={
                **request.data,
                'status': TrainingSession.Status.COMPLETED,
            },
            partial=True,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return self._detail_response(serializer.instance)


class TrainingBlockViewSet(TrainingContextMixin, viewsets.ModelViewSet):
    permission_classes = [TrainingSessionPermission]
    serializer_class = TrainingBlockSerializer
    pagination_class = None

    def get_queryset(self):
        return TrainingBlock.objects.filter(
            session_id=self.kwargs.get('session_pk'),
            session__club_id=self.kwargs.get('club_pk'),
        ).select_related('session', 'session__club').order_by('order', 'id')

    def perform_create(self, serializer):
        serializer.save(session=self.get_session())


class TrainingSessionPlayerViewSet(TrainingContextMixin, viewsets.ModelViewSet):
    permission_classes = [TrainingSessionPermission]
    serializer_class = TrainingSessionPlayerSerializer
    pagination_class = None

    def get_queryset(self):
        return TrainingSessionPlayer.objects.filter(
            session_id=self.kwargs.get('session_pk'),
            session__club_id=self.kwargs.get('club_pk'),
        ).select_related('session', 'session__club', 'club_player').order_by(
            'club_player__squad_number',
            'club_player__last_name',
            'id',
        )

    def perform_create(self, serializer):
        serializer.save(session=self.get_session())
