from django.db import transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.clubs.models import Club, ClubMembership, ClubPlayer
from apps.clubs.serializers import AvailablePlayerSerializer
from .models import Teamsheet, TeamsheetPlayer
from .serializers import (
    BulkPlayerPositionUpdateSerializer,
    CreateTeamsheetWithPlayersSerializer,
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
    # Restore proper permissions later if/when you want auth re-enabled.
    # permission_classes = [permissions.IsAuthenticated, IsClubMember, CanCreateClubContent]
    permission_classes = []
    pagination_class = None

    def get_serializer_class(self):
        if self.action == 'list':
            return TeamsheetListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return TeamsheetWriteSerializer
        return TeamsheetReadSerializer

    def get_queryset(self):
        club_pk = self.kwargs.get('club_pk')

        base_queryset = Teamsheet.objects.select_related(
            'club',
            'created_by',
        ).prefetch_related(
            'players__club_player__player',
        ).order_by('-updated_at')

        if club_pk:
            return base_queryset.filter(club_id=club_pk)

        user_club_ids = ClubMembership.objects.filter(
            user=self.request.user,
            is_active=True,
        ).values_list('club_id', flat=True)

        return base_queryset.filter(club_id__in=user_club_ids)

    def perform_create(self, serializer):
        club_pk = self.kwargs.get('club_pk')
        serializer.save(club_id=club_pk, created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def choices(self, request, club_pk=None):
        return Response({
            'positions': get_pitch_position_choices(),
            'formations': get_formation_choices(),
            'formations_with_templates': get_formation_with_templates(),
        })

    @action(detail=True, methods=['post'])
    def duplicate(self, request, club_pk=None, pk=None):
        original = self.get_object()
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
                opponent=original.opponent,
                notes=original.notes,
                is_template=False,
            )

            if include_players:
                for player in original.players.select_related('club_player', 'club_player__player'):
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
        teamsheet = self.get_object()
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

        club = get_object_or_404(Club, pk=club_pk)

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

        queryset = queryset.select_related('club', 'user', 'player')
        queryset = queryset.select_related(
            'club',
            'user',
            'player',
        ).prefetch_related(
            'player__external_identities',
        )
        
        if exclude_list:
            queryset = queryset.exclude(id__in=exclude_list)

        if position:
            queryset = apply_club_player_position_filter(queryset, position)

        if search:
            queryset = apply_club_player_search_filter(queryset, search)

        queryset = queryset.annotate(
            club_priority=Case(
                When(club_id=club.id, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            sort_primary_position=Coalesce('player__primary_position', 'primary_position'),
            sort_last_name=Coalesce('player__last_name', 'last_name'),
        ).order_by(
            'club_priority',
            'sort_primary_position',
            'sort_last_name',
            'id',
        )

        serializer = AvailablePlayerSerializer(
            queryset,
            many=True,
            context={'club_id': int(club_pk)},
        )
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def create_with_players(self, request, club_pk=None):
        if not club_pk:
            return Response(
                {'error': 'club_pk is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        club = get_object_or_404(Club, pk=club_pk)
        user = request.user if request.user.is_authenticated else None

        serializer = CreateTeamsheetWithPlayersSerializer(
            data=request.data,
            context={
                'club': club,
                'user': user,
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
            teamsheet_id=teamsheet_pk,
        ).select_related(
            'club_player',
            'club_player__player',
        ).order_by('slot_number')

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
                club_player = ClubPlayer.objects.select_related('player').get(
                    id=club_player_id,
                    club_id=slot.teamsheet.club_id,
                )
            except ClubPlayer.DoesNotExist:
                return Response(
                    {'error': 'Club player not found'},
                    status=status.HTTP_404_NOT_FOUND,
                )

            slot.club_player = club_player
            slot.custom_name = ''
            slot.custom_number = None
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