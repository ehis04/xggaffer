from django.conf import settings
from django.db import transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response

from apps.clubs.models import Club, ClubMembership, ClubPlayer
from apps.clubs.serializers import AvailablePlayerSerializer
from .models import Teamsheet, TeamsheetPlayer
from .permissions import TeamsheetPermission
from .serializers import (
    BulkPlayerPositionUpdateSerializer,
    CreateTeamsheetWithPlayersSerializer,
    TeamsheetTrashActionSerializer,
    TeamsheetDuplicateSerializer,
    TeamsheetListSerializer,
    TeamsheetPlayerPositionUpdateSerializer,
    TeamsheetPlayerReadSerializer,
    TeamsheetPlayerWriteSerializer,
    TeamsheetReadSerializer,
    TeamsheetWriteSerializer,
    get_formation_choices,
    get_formation_with_templates,
    get_pitch_position_choices,
)


def apply_club_player_position_filter(queryset, position):
    """
    Transitional filter:
    prefer canonical Player fields, but fall back to legacy ClubPlayer
    identity columns until those columns are removed later in Phase 1.
    """
    return queryset.filter(
        Q(player__primary_position=position) |
        Q(player__secondary_positions__contains=[position]) |
        Q(player__isnull=True, primary_position=position) |
        Q(player__isnull=True, secondary_position=position)
    )


def apply_club_player_search_filter(queryset, search):
    """
    Transitional search:
    prefer canonical Player name fields, but fall back to legacy ClubPlayer
    identity columns until those columns are removed later in Phase 1.
    """
    return queryset.filter(
        Q(player__first_name__icontains=search) |
        Q(player__last_name__icontains=search) |
        Q(player__display_name__icontains=search) |
        Q(first_name__icontains=search) |
        Q(last_name__icontains=search) |
        Q(display_name__icontains=search)
    )


class IsClubMember(permissions.BasePermission):
    def has_permission(self, request, view):
        club_pk = view.kwargs.get('club_pk')
        if not club_pk:
            return True

        return ClubMembership.objects.filter(
            user=request.user,
            club_id=club_pk,
            is_active=True,
        ).exists()


class CanCreateClubContent(permissions.BasePermission):
    message = "You don't have permission to create or edit teamsheets for this club."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        club_id = view.kwargs.get('club_pk') or request.data.get('club')
        if not club_id:
            return True

        membership = ClubMembership.objects.filter(
            user=request.user,
            club_id=club_id,
            is_active=True,
        ).first()

        return bool(membership and membership.can_create_content())

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        if hasattr(obj, 'club_id'):
            club_id = obj.club_id
        elif hasattr(obj, 'teamsheet'):
            club_id = obj.teamsheet.club_id
        else:
            return False

        membership = ClubMembership.objects.filter(
            user=request.user,
            club_id=club_id,
            is_active=True,
        ).first()

        return bool(membership and membership.can_create_content())


class TeamsheetViewSet(viewsets.ModelViewSet):
    permission_classes = [TeamsheetPermission]
    pagination_class = None

    def get_serializer_class(self):
        if self.action == 'list':
            return TeamsheetListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return TeamsheetWriteSerializer
        return TeamsheetReadSerializer

    def _get_trash_mode(self) -> str:
        value = (self.request.query_params.get('trash') or '').strip().lower()
        if value in {'only', 'include'}:
            return value
        return 'exclude'

    def _build_queryset(self, include_trashed=False):
        club_pk = self.kwargs.get('club_pk')

        queryset = Teamsheet.objects.filter(
            club_id=club_pk
        ).select_related(
            'club',
            'created_by',
            'trashed_by',
        ).prefetch_related(
            'players',
            'players__club_player',
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
                Q(is_trashed=False) |
                Q(is_trashed=True, created_by=self.request.user)
            )

        return queryset.filter(is_trashed=False)

    def get_queryset(self):
        return self._build_queryset(include_trashed=False)

    def _get_teamsheet_for_action(self, pk, *, require_trashed=None):
        teamsheet = get_object_or_404(
            self._build_queryset(include_trashed=True),
            pk=pk,
        )
        self.check_object_permissions(self.request, teamsheet)

        if require_trashed is True and not teamsheet.is_trashed:
            raise ValidationError({'detail': 'This teamsheet is not in trash.'})

        if require_trashed is False and teamsheet.is_trashed:
            raise ValidationError({'detail': 'This teamsheet is already in trash.'})

        return teamsheet

    def perform_create(self, serializer):
        club_pk = self.kwargs.get('club_pk')
        
        # Check teamsheet creation limit
        create_limit = getattr(settings, 'TEAMSHEET_CREATE_LIMIT_PER_USER', 10)
        user_teamsheet_count = Teamsheet.objects.filter(
            club_id=club_pk,
            created_by=self.request.user,
            is_trashed=False,
        ).count()
        if user_teamsheet_count >= create_limit:
            raise ValidationError({
                'detail': f'You have reached the maximum limit of {create_limit} teamsheets. Please delete some teamsheets before creating new ones.'
            })
        
        serializer.save(club_id=club_pk, created_by=self.request.user)

    def perform_destroy(self, instance):
        instance.move_to_trash(self.request.user)

    @action(detail=False, methods=['get'])
    def choices(self, request, club_pk=None):
        return Response({
            'positions': get_pitch_position_choices(),
            'formations': get_formation_choices(),
            'formations_with_templates': get_formation_with_templates(),
        })

    @action(detail=True, methods=['post'])
    def trash(self, request, club_pk=None, pk=None):
        serializer = TeamsheetTrashActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        teamsheet = self._get_teamsheet_for_action(pk, require_trashed=False)
        teamsheet.move_to_trash(request.user)

        response_serializer = TeamsheetReadSerializer(teamsheet)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def restore(self, request, club_pk=None, pk=None):
        serializer = TeamsheetTrashActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        teamsheet = self._get_teamsheet_for_action(pk, require_trashed=True)
        teamsheet.restore_from_trash(request.user)

        response_serializer = TeamsheetReadSerializer(teamsheet)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='permanent-delete')
    def permanent_delete(self, request, club_pk=None, pk=None):
        teamsheet = self._get_teamsheet_for_action(pk, require_trashed=True)

        if not teamsheet.can_be_permanently_deleted_by(request.user):
            raise PermissionDenied('Only the teamsheet creator can permanently delete this teamsheet.')

        teamsheet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, club_pk=None, pk=None):
        original = self._get_teamsheet_for_action(pk, require_trashed=False)
        serializer = TeamsheetDuplicateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_title = serializer.validated_data['new_title']
        include_players = serializer.validated_data['include_players']

        with transaction.atomic():
            new_teamsheet = Teamsheet.objects.create(
                club=original.club,
                created_by=request.user,
                title=new_title,
                formation=original.formation,
                match_date=original.match_date,
                opponent=original.opponent,
                notes=original.notes,
                is_template=False,
            )

            if include_players:
                for player in original.players.all():
                    TeamsheetPlayer.objects.create(
                        teamsheet=new_teamsheet,
                        club_player=player.club_player,
                        custom_name=player.custom_name,
                        custom_number=player.custom_number,
                        slot_number=player.slot_number,
                        position_label=player.position_label,
                        position_x=player.position_x,
                        position_y=player.position_y,
                        is_substitute=player.is_substitute,
                    )

        response_serializer = TeamsheetReadSerializer(new_teamsheet)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def reset_to_formation(self, request, club_pk=None, pk=None):
        teamsheet = self._get_teamsheet_for_action(pk, require_trashed=False)
        teamsheet.players.all().delete()
        teamsheet.initialize_from_template()

        serializer = TeamsheetReadSerializer(teamsheet)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def available_players(self, request, club_pk=None):
        if not club_pk:
            return Response(
                {'error': 'club_pk is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            club = Club.objects.get(pk=club_pk)
        except Club.DoesNotExist:
            return Response(
                {'error': 'Club not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        position = request.query_params.get('position')
        search = request.query_params.get('search')
        exclude_ids = request.query_params.get('exclude', '')

        exclude_list = []
        if exclude_ids:
            try:
                exclude_list = [int(x) for x in exclude_ids.split(',') if x]
            except ValueError:
                exclude_list = []

        queryset = ClubPlayer.objects.filter(
            club=club,
            is_active=True,
        )

        if club.visibility == Club.Visibility.PUBLIC:
            queryset = ClubPlayer.objects.filter(
                Q(club=club, is_active=True) |
                Q(is_public=True, is_active=True)
            )

        if exclude_list:
            queryset = queryset.exclude(id__in=exclude_list)

        if position:
            queryset = queryset.filter(
                Q(primary_position=position) |
                Q(secondary_position=position)
            )

        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(display_name__icontains=search)
            )

        queryset = queryset.select_related('club').order_by(
            Case(
                When(club_id=club.id, then=0),
                default=1,
                output_field=IntegerField(),
            ),
            'primary_position',
            'last_name',
        )

        serializer = AvailablePlayerSerializer(
            queryset,
            many=True,
            context={'club_id': club.id},
        )
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def create_with_players(self, request, club_pk=None):
        if not club_pk:
            return Response(
                {'error': 'club_pk is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            club = Club.objects.get(pk=club_pk)
        except Club.DoesNotExist:
            return Response(
                {'error': 'Club not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CreateTeamsheetWithPlayersSerializer(
            data=request.data,
            context={
                'club': club,
                'user': request.user if request.user.is_authenticated else None,
            },
        )
        serializer.is_valid(raise_exception=True)
        teamsheet = serializer.save()

        response_serializer = TeamsheetReadSerializer(teamsheet)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

class TeamsheetPlayerViewSet(viewsets.ModelViewSet):
    # Restore proper permissions later if/when you want auth re-enabled.
    # permission_classes = [permissions.IsAuthenticated, IsClubMember, CanCreateClubContent]
    permission_classes = []
    pagination_class = None

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TeamsheetPlayerWriteSerializer
        return TeamsheetPlayerReadSerializer

    def get_queryset(self):
        teamsheet_pk = self.kwargs.get('teamsheet_pk')
        return TeamsheetPlayer.objects.filter(
            teamsheet_id=teamsheet_pk
        ).select_related('club_player').order_by('slot_number')

    def perform_create(self, serializer):
        teamsheet_pk = self.kwargs.get('teamsheet_pk')
        serializer.save(teamsheet_id=teamsheet_pk)

    @action(detail=True, methods=['patch'])
    def update_position(self, request, club_pk=None, teamsheet_pk=None, pk=None):
        player = self.get_object()
        serializer = TeamsheetPlayerPositionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        player.position_x = serializer.validated_data['position_x']
        player.position_y = serializer.validated_data['position_y']

        if 'position_label' in serializer.validated_data:
            player.position_label = serializer.validated_data['position_label']

        player.save()

        response_serializer = TeamsheetPlayerReadSerializer(player)
        return Response(response_serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_update_positions(self, request, club_pk=None, teamsheet_pk=None):
        serializer = BulkPlayerPositionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updates = serializer.validated_data['updates']
        player_ids = [u['id'] for u in updates]

        players = TeamsheetPlayer.objects.filter(
            id__in=player_ids,
            teamsheet_id=teamsheet_pk,
        )

        players_dict = {p.id: p for p in players}
        updated_players = []

        with transaction.atomic():
            for update in updates:
                player = players_dict.get(update['id'])
                if player:
                    player.position_x = update['position_x']
                    player.position_y = update['position_y']
                    if 'position_label' in update:
                        player.position_label = update['position_label']
                    player.save()
                    updated_players.append(player)

        response_serializer = TeamsheetPlayerReadSerializer(updated_players, many=True)
        return Response({
            'updated_count': len(updated_players),
            'players': response_serializer.data,
        })

    @action(detail=True, methods=['post'])
    def assign_player(self, request, club_pk=None, teamsheet_pk=None, pk=None):
        slot = self.get_object()
        club_player_id = request.data.get('club_player_id')

        if club_player_id:
            try:
                club_player = ClubPlayer.objects.get(
                    id=club_player_id,
                    club_id=slot.teamsheet.club_id,
                )
                slot.club_player = club_player
                slot.custom_name = ''
                slot.custom_number = None
            except ClubPlayer.DoesNotExist:
                return Response(
                    {'error': 'Club player not found'},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            slot.club_player = None

        slot.save()

        response_serializer = TeamsheetPlayerReadSerializer(slot)
        return Response(response_serializer.data)

    @action(detail=True, methods=['post'])
    def swap_positions(self, request, club_pk=None, teamsheet_pk=None, pk=None):
        player_a = self.get_object()
        target_id = request.data.get('target_player_id')

        if not target_id:
            return Response(
                {'error': 'target_player_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            player_b = TeamsheetPlayer.objects.get(
                id=target_id,
                teamsheet_id=teamsheet_pk,
            )
        except TeamsheetPlayer.DoesNotExist:
            return Response(
                {'error': 'Target player not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            player_a.position_x, player_b.position_x = player_b.position_x, player_a.position_x
            player_a.position_y, player_b.position_y = player_b.position_y, player_a.position_y
            player_a.position_label, player_b.position_label = player_b.position_label, player_a.position_label
            player_a.slot_number, player_b.slot_number = player_b.slot_number, player_a.slot_number

            player_a.save()
            player_b.save()

        response_serializer = TeamsheetPlayerReadSerializer([player_a, player_b], many=True)
        return Response({'swapped': response_serializer.data})