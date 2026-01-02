from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound
from django.db import transaction, models
from django.shortcuts import get_object_or_404

from apps.clubs.models import *
from apps.clubs.serializers import *
from .models import Teamsheet, TeamsheetPlayer, PitchPosition
from .serializers import (
    # Teamsheet serializers
    TeamsheetReadSerializer,
    TeamsheetWriteSerializer,
    TeamsheetListSerializer,
    TeamsheetDuplicateSerializer,
    # Player serializers
    TeamsheetPlayerReadSerializer,
    TeamsheetPlayerWriteSerializer,
    TeamsheetPlayerPositionUpdateSerializer,
    BulkPlayerPositionUpdateSerializer,
    CreateTeamsheetWithPlayersSerializer,
    # Helper functions
    get_pitch_position_choices,
    get_formation_choices,
    get_formation_with_templates,
)

class IsClubMember(permissions.BasePermission):
    def has_permission(self, request, view):
        club_pk = view.kwargs.get('club_pk')
        if not club_pk:
            return True
        return ClubMembership.objects.filter(
            user=request.user,
            club_id=club_pk,
            is_active=True
        ).exists()


class CanCreateClubContent(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        club_pk = view.kwargs.get('club_pk')
        if not club_pk:
            return True
        
        try:
            membership = ClubMembership.objects.get(
                user=request.user,
                club_id=club_pk,
                is_active=True
            )
            return membership.can_create_content()
        except ClubMembership.DoesNotExist:
            return False


class TeamsheetViewSet(viewsets.ModelViewSet):
    #permission_classes = [permissions.IsAuthenticated, IsClubMember, CanCreateClubContent]
    permission_classes = []
    pagination_class = None  # Disable pagination to return plain array

    def get_serializer_class(self):
        if self.action == 'list':
            return TeamsheetListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return TeamsheetWriteSerializer
        return TeamsheetReadSerializer

    def get_queryset(self):
        club_pk = self.kwargs.get('club_pk')
        
        if club_pk:
            return Teamsheet.objects.filter(
                club_id=club_pk
            ).select_related('club', 'created_by').prefetch_related(
                'players__player_profile'
            ).order_by('-updated_at')
        
        user_club_ids = ClubMembership.objects.filter(
            user=self.request.user,
            is_active=True
        ).values_list('club_id', flat=True)
        
        return Teamsheet.objects.filter(
            club_id__in=user_club_ids
        ).select_related('club', 'created_by').prefetch_related(
            'players__player_profile'
        ).order_by('-updated_at')

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
                for player in original.players.all():
                    TeamsheetPlayer.objects.create(
                        teamsheet=new_teamsheet,
                        player_profile=player.player_profile,
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
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            club = Club.objects.get(pk=club_pk)
        except Club.DoesNotExist:
            return Response(
                {'error': 'Club not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        position = request.query_params.get('position', None)
        search = request.query_params.get('search', None)
        exclude_ids = request.query_params.get('exclude', '')
        
        exclude_list = []
        if exclude_ids:
            try:
                exclude_list = [int(x) for x in exclude_ids.split(',') if x]
            except ValueError:
                pass
        
        club_players = PlayerProfile.objects.filter(
            club=club,
            is_active=True
        )
        
        public_players = PlayerProfile.objects.none()
        if club.visibility == Club.Visibility.PUBLIC:
            public_players = PlayerProfile.objects.filter(
                is_public=True,
                is_active=True
            ).exclude(club=club)
        
        all_player_ids = list(club_players.values_list('id', flat=True)) + \
                         list(public_players.values_list('id', flat=True))
        
        queryset = PlayerProfile.objects.filter(id__in=all_player_ids)
        
        if exclude_list:
            queryset = queryset.exclude(id__in=exclude_list)
        
        if position:
            queryset = queryset.filter(
                models.Q(position=position) | models.Q(secondary_position=position)
            )
        
        if search:
            queryset = queryset.filter(
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(display_name__icontains=search)
            )
        
        queryset = queryset.select_related('club').order_by(
            models.Case(
                models.When(club_id=club_pk, then=0),
                default=1,
                output_field=models.IntegerField()
            ),
            'position',
            'last_name'
        )
        
        serializer = AvailablePlayerSerializer(
            queryset,
            many=True,
            context={'club_id': int(club_pk)}
        )
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def create_with_players(self, request, club_pk=None):
        if not club_pk:
            return Response(
                {'error': 'club_pk is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            club = Club.objects.get(pk=club_pk)
        except Club.DoesNotExist:
            return Response(
                {'error': 'Club not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        user = request.user if request.user.is_authenticated else None
        
        serializer = CreateTeamsheetWithPlayersSerializer(
            data=request.data,
            context={
                'club': club,
                'user': user,
                #'user': request.user,
            }
        )
        serializer.is_valid(raise_exception=True)
        teamsheet = serializer.save()
        
        response_serializer = TeamsheetReadSerializer(teamsheet)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class TeamsheetPlayerViewSet(viewsets.ModelViewSet):
    #permission_classes = [permissions.IsAuthenticated, IsClubMember, CanCreateClubContent]
    permission_classes = []
    pagination_class = None  # Disable pagination to return plain array

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TeamsheetPlayerWriteSerializer
        return TeamsheetPlayerReadSerializer

    def get_queryset(self):
        teamsheet_pk = self.kwargs.get('teamsheet_pk')
        return TeamsheetPlayer.objects.filter(
            teamsheet_id=teamsheet_pk
        ).select_related('player_profile').order_by('slot_number')

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
            teamsheet_id=teamsheet_pk
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
            'players': response_serializer.data
        })

    @action(detail=True, methods=['post'])
    def assign_player(self, request, club_pk=None, teamsheet_pk=None, pk=None):
        slot = self.get_object()
        player_profile_id = request.data.get('player_profile_id')
        
        if player_profile_id:
            try:
                player_profile = PlayerProfile.objects.get(id=player_profile_id)
                slot.player_profile = player_profile
                slot.custom_name = ''
                slot.custom_number = None
            except PlayerProfile.DoesNotExist:
                return Response(
                    {'error': 'Player profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            slot.player_profile = None
        
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
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            player_b = TeamsheetPlayer.objects.get(
                id=target_id,
                teamsheet_id=teamsheet_pk
            )
        except TeamsheetPlayer.DoesNotExist:
            return Response(
                {'error': 'Target player not found'},
                status=status.HTTP_404_NOT_FOUND
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

class CanCreateClubContent(permissions.BasePermission):
    message = "You don't have permission to create or edit teamsheets for this club."
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if not request.user.is_authenticated:
            return False
        
        club_id = (
            view.kwargs.get('club_pk') or 
            request.data.get('club') or
            getattr(view, '_club_id', None)
        )
        
        if not club_id:
            return True  # Will be checked at object level
        
        membership = ClubMembership.objects.filter(
            user=request.user,
            club_id=club_id,
            is_active=True
        ).first()
        
        return membership and membership.can_create_content()
    
    def has_object_permission(self, request, view, obj):
        # Read operations allowed for members
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
            is_active=True
        ).first()
        
        return membership and membership.can_create_content()


class ClubContextMixin:
    def get_club(self):
        club_pk = self.kwargs.get('club_pk')
        if not club_pk:
            return None
        
        club = get_object_or_404(Club, pk=club_pk)
        
        # Verify user is a member
        if not ClubMembership.objects.filter(
            user=self.request.user,
            club=club,
            is_active=True
        ).exists():
            raise PermissionDenied("You are not a member of this club.")
        
        return club
    
    def get_membership(self, club=None):
        if club is None:
            club = self.get_club()
        
        if not club:
            return None
        
        return ClubMembership.objects.filter(
            user=self.request.user,
            club=club,
            is_active=True
        ).first()



class ChoicesView(permissions.IsAuthenticated):
    def get(self, request):
        return Response({
            'positions': get_pitch_position_choices(),
            'formations': get_formation_choices(),
            'formations_with_templates': get_formation_with_templates(),
        })


class AvailablePlayersView(permissions.IsAuthenticated):
    def get(self, request, club_pk, teamsheet_pk):
        from apps.clubs.models import PlayerProfile
        if not ClubMembership.objects.filter(
            user=request.user,
            club_id=club_pk,
            is_active=True
        ).exists():
            raise PermissionDenied("You are not a member of this club.")
        
        teamsheet = get_object_or_404(Teamsheet, pk=teamsheet_pk, club_id=club_pk)
        
        assigned_ids = teamsheet.players.filter(
            player_profile__isnull=False
        ).values_list('player_profile_id', flat=True)
        
        available = PlayerProfile.objects.filter(
            club_id=club_pk,
            is_active=True
        ).exclude(
            id__in=assigned_ids
        ).order_by('squad_number', 'last_name')
        
        data = [
            {
                'id': p.id,
                'name': p.display_name or p.full_name,
                'squad_number': p.squad_number,
                'position': p.position,
            }
            for p in available
        ]
        
        return Response(data)
