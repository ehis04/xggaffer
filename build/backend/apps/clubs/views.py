from django.conf import settings
from django.db import models, transaction
from django.db.models import Q, Case, When, Value, IntegerField, Prefetch
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from datetime import timedelta
from django.core import signing
from django.http import FileResponse
from rest_framework.reverse import reverse
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from apps.playerdata.models import ClubSeasonEnrichment
from apps.players.models import ExternalProvider, Player
from services.providers.football_data.exceptions import FootballDataError
from services.providers.football_data.sync import sync_club_team_squad
from services.providers.understat.exceptions import UnderstatError
from django.shortcuts import redirect

from .storage import (
    ClubResourceStorageError,
    build_cloudinary_signed_delivery_url,
    cloudinary_resources_enabled,
)
from services.providers.understat.sync import sync_understat_club_season
from .models import (
    Club,
    ClubMembership,
    ClubImportJob,
    ClubPlayer,
    ClubJoinRequest,
    ClubInvitation,
    ClubEvent,
    Fixture,
    ClubResource,
    ClubResourceView,
)
from .permissions import (
    CanCreateClub,
    CanAccessClubScheduling,
    CanAccessClubImportJobs,
    CanCommitClubImportJob,
    CanCreateJoinRequest,
    CanReviewClubJoinRequest,
    CanWithdrawOwnClubJoinRequest,
    CanCreateClubInvitation,
    CanRespondToClubInvitation,
    CanRevokeClubInvitation,
    CanManageClubPlayerIdentity,
    CanAccessClubResources,
    CanManageClubResources,
    CanViewClubResourceEngagementDashboard,
    CanViewClubResourceStatus,
    user_can_review_join_requests,
)
from .serializers import (
    ClubSerializer,
    ClubEventSerializer,
    ClubEventWriteSerializer,
    FixtureSerializer,
    FixtureWriteSerializer,
    ClubMembershipSerializer,
    ClubPlayerSerializer,
    ClubPlayerListSerializer,
    ClubPlayerCreateSerializer,
    ClubPlayerUpdateSerializer,
    ClubPlayerLinkSerializer,
    ClubPlayerUnlinkSerializer,
    ClubPlayerRelinkSerializer,
    AvailablePlayerSerializer,
    ClubDuplicateSerializer,
    ClubWriteSerializer,
    ClubJoinRequestSerializer,
    ClubJoinRequestCreateSerializer,
    ClubJoinRequestApproveSerializer,
    ClubJoinRequestRejectSerializer,
    ClubJoinRequestWithdrawSerializer,
    ClubInvitationSerializer,
    ClubInvitationCreateSerializer,
    ClubInvitationAcceptSerializer,
    ClubInvitationDeclineSerializer,
    ClubInvitationRevokeSerializer,
    ClubCalendarFeedItemSerializer,
    ClubResourceListSerializer,
    ClubResourceDetailSerializer,
    ClubResourceUploadSerializer,
    ClubResourceUpdateSerializer,
    ClubResourceArchiveSerializer,
    ClubResourceSignedAccessSerializer,
    ClubResourceHeartbeatSerializer,
    ClubResourceViewReadSerializer,
    ClubResourceEngagementReadSerializer,
    ClubImportJobListSerializer,
    ClubImportJobDetailSerializer,
    ClubImportJobCreateSerializer,
    ClubImportJobCommitSerializer,
)
def apply_club_player_position_filter(queryset, position):
    if not position:
        return queryset

    return queryset.filter(
        Q(player__primary_position=position) |
        Q(player__secondary_positions__contains=[position]) |
        Q(primary_position=position) |
        Q(secondary_position=position)
    ).distinct()


def apply_club_player_search_filter(queryset, search):
    if not search:
        return queryset

    return queryset.filter(
        Q(player__first_name__icontains=search) |
        Q(player__last_name__icontains=search) |
        Q(player__display_name__icontains=search) |
        Q(first_name__icontains=search) |
        Q(last_name__icontains=search) |
        Q(display_name__icontains=search)
    ).distinct()

def get_listed_directory_filter():
    return (
        Q(directory_visibility=Club.DirectoryVisibility.LISTED) |
        Q(directory_visibility__isnull=True, visibility=Club.Visibility.PUBLIC) |
        Q(directory_visibility='', visibility=Club.Visibility.PUBLIC)
    )


def apply_club_search_filter(queryset, search):
    if not search:
        return queryset

    search = search.strip()
    if not search:
        return queryset

    return queryset.filter(
        Q(name__icontains=search) |
        Q(description__icontains=search) |
        Q(city__icontains=search) |
        Q(country__icontains=search) |
        Q(stadium__icontains=search) |
        Q(division__icontains=search) |
        Q(source_real_club_name__icontains=search)
    ).distinct()

def get_understat_enrichment_prefetch():
    return Prefetch(
        'season_enrichments',
        queryset=ClubSeasonEnrichment.objects.filter(
            provider=ExternalProvider.UNDERSTAT
        ).order_by('-season_label', '-updated_at', '-id'),
        to_attr='prefetched_understat_enrichments',
    )

class BypassablePermission(permissions.BasePermission):
    def should_bypass(self):
        return getattr(settings, 'BYPASS_PERMISSIONS', False)


class IsAuthenticatedOrBypass(BypassablePermission):
    def has_permission(self, request, view):
        if self.should_bypass():
            return True
        return bool(request.user and request.user.is_authenticated)


class IsClubMemberOrPublicRead(BypassablePermission):
    def has_permission(self, request, view):
        if self.should_bypass():
            return True

        if request.method in permissions.SAFE_METHODS:
            return True

        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if self.should_bypass():
            return True

        club = obj if isinstance(obj, Club) else getattr(obj, 'club', None)

        if request.method in permissions.SAFE_METHODS:
            if club and club.visibility == Club.Visibility.PUBLIC:
                return True

            if not request.user or not request.user.is_authenticated:
                return False

            return ClubMembership.objects.filter(
                user=request.user,
                club=club,
                is_active=True,
            ).exists()

        membership = ClubMembership.objects.filter(
            user=request.user,
            club=club,
            is_active=True,
        ).first()

        return membership is not None and membership.can_edit_club()


class CanManageClubContent(BypassablePermission):
    def has_permission(self, request, view):
        if self.should_bypass():
            return True

        if request.method in permissions.SAFE_METHODS:
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        club_pk = view.kwargs.get('club_pk')
        if not club_pk:
            return True

        membership = ClubMembership.objects.filter(
            user=request.user,
            club_id=club_pk,
            is_active=True,
        ).first()

        return membership is not None and membership.can_create_content()


class ClubViewSet(viewsets.ModelViewSet):
    serializer_class = ClubSerializer
    permission_classes = [IsAuthenticatedOrBypass, CanCreateClub, IsClubMemberOrPublicRead]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ClubWriteSerializer
        return ClubSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        response_serializer = ClubSerializer(
            serializer.instance,
            context=self.get_serializer_context(),
        )
        headers = self.get_success_headers(response_serializer.data)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        response_serializer = ClubSerializer(
            serializer.instance,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)
        
    def _with_understat_summary(self, queryset):
        return queryset.prefetch_related(get_understat_enrichment_prefetch())

    def get_queryset(self):
        user = self.request.user
        scope = self.request.query_params.get('scope')
        search = self.request.query_params.get('search')

        listed_filter = get_listed_directory_filter()

        if not user.is_authenticated:
            queryset = Club.objects.filter(listed_filter)
            queryset = apply_club_search_filter(queryset, search)
            return self._with_understat_summary(queryset)

        member_club_ids = ClubMembership.objects.filter(
            user=user,
            is_active=True,
        ).values_list('club_id', flat=True)

        if scope == 'mine':
            queryset = Club.objects.filter(id__in=member_club_ids)
            queryset = apply_club_search_filter(queryset, search)
            return self._with_understat_summary(queryset)

        if scope == 'browse':
            queryset = Club.objects.filter(listed_filter).exclude(id__in=member_club_ids)
            queryset = apply_club_search_filter(queryset, search)
            return self._with_understat_summary(queryset)

        queryset = Club.objects.filter(
            Q(id__in=member_club_ids) | listed_filter
        ).distinct()

        queryset = apply_club_search_filter(queryset, search)
        return self._with_understat_summary(queryset)


    def perform_create(self, serializer):
        club = serializer.save(creator=self.request.user)
        ClubMembership.objects.create(
            user=self.request.user,
            club=club,
            role=ClubMembership.Role.OWNER,
            is_active=True,
        )

    def get_understat_enrichment_prefetch():
        return Prefetch(
            'season_enrichments',
            queryset=ClubSeasonEnrichment.objects.filter(
                provider=ExternalProvider.UNDERSTAT
            ).order_by('-season_label', '-updated_at', '-id'),
            to_attr='prefetched_understat_enrichments',
        )

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        source_club = self.get_object()
        serializer = ClubDuplicateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_name = serializer.validated_data.get('name') or f'Copy of {source_club.name}'
        include_players = serializer.validated_data['include_players']
        visibility = serializer.validated_data['visibility']

        user = request.user if request.user.is_authenticated else source_club.creator

        with transaction.atomic():
            new_club = Club.objects.create(
                name=new_name,
                description=source_club.description,
                creator=user,
                visibility=visibility,
                city=source_club.city,
                country=source_club.country,
                stadium=source_club.stadium,
                division=source_club.division,
                achievements='',
            )

            ClubMembership.objects.create(
                user=user,
                club=new_club,
                role=ClubMembership.Role.OWNER,
                is_active=True,
            )

            if include_players:
                source_players = source_club.club_players.filter(
                    is_active=True,
                ).select_related('player')

                for source_player in source_players:
                    linked_player = source_player.player

                    if linked_player is None:
                        linked_player = Player(
                            first_name=source_player.first_name,
                            last_name=source_player.last_name,
                            display_name=source_player.display_name,
                            primary_position=source_player.primary_position,
                            preferred_foot=source_player.preferred_foot,
                            date_of_birth=source_player.date_of_birth,
                            height_cm=source_player.height_cm,
                        )

                        if hasattr(linked_player, 'secondary_positions'):
                            linked_player.secondary_positions = (
                                [source_player.secondary_position]
                                if source_player.secondary_position else []
                            )

                        if hasattr(linked_player, 'photo'):
                            linked_player.photo = source_player.photo

                        linked_player.save()

                    ClubPlayer.objects.create(
                        club=new_club,
                        player=linked_player,
                        user=None,
                        first_name=source_player.first_name,
                        last_name=source_player.last_name,
                        display_name=source_player.display_name,
                        squad_number=source_player.squad_number,
                        primary_position=source_player.primary_position,
                        secondary_position=source_player.secondary_position,
                        preferred_foot=source_player.preferred_foot,
                        date_of_birth=source_player.date_of_birth,
                        height_cm=source_player.height_cm,
                        photo=source_player.photo,
                        is_active=source_player.is_active,
                        is_public=source_player.is_public,
                        created_by=user,
                    )

        response_serializer = ClubSerializer(new_club)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def available_players(self, request, pk=None):
        club = self.get_object()
        position = request.query_params.get('position')
        search = request.query_params.get('search')

        queryset = ClubPlayer.objects.filter(
            club=club,
            is_active=True,
        )

        if club.visibility == Club.Visibility.PUBLIC:
            queryset = ClubPlayer.objects.filter(
                Q(club=club, is_active=True) |
                Q(is_public=True, is_active=True)
            ).exclude(
                Q(is_public=True, club=club, is_active=True) &
                ~Q(club=club)
            )

        queryset = queryset.select_related('club', 'user', 'player').prefetch_related(
            'player__external_identities'
        )

        queryset = apply_club_player_position_filter(queryset, position)
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
            context={'club_id': club.id},
        )
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='calendar')
    def calendar(self, request, pk=None):
        club = self.get_object()

        include_past = str(
            request.query_params.get('include_past', 'false')
        ).strip().lower() in {'1', 'true', 'yes', 'y'}

        limit_param = request.query_params.get('limit')
        limit = None
        if limit_param not in (None, ''):
            try:
                limit = int(limit_param)
            except (TypeError, ValueError):
                return Response(
                    {'detail': 'limit must be an integer.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if limit <= 0:
                return Response(
                    {'detail': 'limit must be greater than 0.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        events_qs = club.events.select_related(
            'club',
            'created_by',
        ).order_by('start_datetime', 'id')

        fixtures_qs = club.fixtures.select_related(
            'club',
            'created_by',
        ).order_by('match_datetime', 'id')

        if not include_past:
            now = timezone.now()
            events_qs = events_qs.filter(start_datetime__gte=now)
            fixtures_qs = fixtures_qs.filter(match_datetime__gte=now)

        combined_items = [
            {
                'item_type': 'event',
                'sort_datetime': event.start_datetime,
                'calendar_label': event.get_calendar_label(),
                'event': event,
                'fixture': None,
            }
            for event in events_qs
        ] + [
            {
                'item_type': 'fixture',
                'sort_datetime': fixture.match_datetime,
                'calendar_label': fixture.get_calendar_label(),
                'event': None,
                'fixture': fixture,
            }
            for fixture in fixtures_qs
        ]

        combined_items.sort(key=lambda item: (item['sort_datetime'], item['item_type']))

        if limit is not None:
            combined_items = combined_items[:limit]

        serializer = ClubCalendarFeedItemSerializer(
            combined_items,
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def understat_season_summary(self, request, pk=None):
        club = self.get_object()

        season_label = (request.query_params.get('season') or '').strip()
        competition_code = (request.query_params.get('competition_code') or '').strip()

        queryset = club.season_enrichments.filter(
            provider=ExternalProvider.UNDERSTAT,
        )

        if season_label:
            queryset = queryset.filter(season_label=season_label)

        if competition_code:
            queryset = queryset.filter(competition_code=competition_code)

        enrichment = queryset.order_by(
            '-season_label',
            '-updated_at',
            '-id',
        ).first()

        if not enrichment:
            return Response(
                {
                    'club_id': club.id,
                    'provider': ExternalProvider.UNDERSTAT,
                    'summary': None,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                'club_id': club.id,
                'provider': enrichment.provider,
                'season_label': enrichment.season_label,
                'competition_code': enrichment.competition_code,
                'competition_name': enrichment.competition_name,
                'matches_played': enrichment.matches_played,
                'wins': enrichment.wins,
                'draws': enrichment.draws,
                'losses': enrichment.losses,
                'goals_for': enrichment.goals_for,
                'goals_against': enrichment.goals_against,
                'xg': enrichment.xg,
                'xga': enrichment.xga,
                'npxg': enrichment.npxg,
                'ppda': enrichment.ppda,
                'last_synced_at': (
                    enrichment.last_synced_at.isoformat()
                    if enrichment.last_synced_at else None
                ),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticatedOrBypass])
    def sync_squad(self, request, pk=None):
        club = self.get_object()

        if not getattr(settings, 'BYPASS_PERMISSIONS', False):
            membership = ClubMembership.objects.filter(
                user=request.user,
                club=club,
                is_active=True,
            ).first()

            if membership is None or not membership.can_create_content():
                return Response(
                    {'detail': 'You do not have permission to sync this club squad.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        provider = request.data.get('provider', 'football_data')
        provider_team_id = request.data.get('provider_team_id')

        try:
            result = sync_club_team_squad(
                club=club,
                external_team_id=provider_team_id,
                provider=provider,
                triggered_by=request.user if request.user.is_authenticated else None,
            )
        except ValueError as exc:
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except FootballDataError as exc:
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        summary = result['summary']
        metadata = summary.get('metadata', {})

        return Response(
            {
                'club_id': club.id,
                'provider': provider,
                'status': summary.get('status'),
                'records_processed': summary.get('records_processed', 0),
                'records_created': summary.get('records_created', 0),
                'records_updated': summary.get('records_updated', 0),
                'error_count': summary.get('error_count', 0),
                'players_created': metadata.get('players_created', 0),
                'players_updated': metadata.get('players_updated', 0),
                'player_external_identities_created': metadata.get(
                    'player_external_identities_created', 0
                ),
                'player_external_identities_updated': metadata.get(
                    'player_external_identities_updated', 0
                ),
                'club_players_created': metadata.get('club_players_created', 0),
                'club_players_updated': metadata.get('club_players_updated', 0),
                'raw_error_summary': summary.get('raw_error_summary', ''),
                'sync_job_id': result['job'].id,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticatedOrBypass])
    def sync_understat_season(self, request, pk=None):
        club = self.get_object()

        if not getattr(settings, 'BYPASS_PERMISSIONS', False):
            membership = ClubMembership.objects.filter(
                user=request.user,
                club=club,
                is_active=True,
            ).first()

            if membership is None or not membership.can_create_content():
                return Response(
                    {'detail': 'You do not have permission to sync Understat data for this club.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        season_label = (request.data.get('season') or '').strip()
        competition_code = (request.data.get('competition_code') or '').strip()
        external_team_id = (request.data.get('external_team_id') or '').strip()

        if not season_label:
            return Response(
                {'detail': 'season is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = sync_understat_club_season(
                club=club,
                season_label=season_label,
                competition_code=competition_code or None,
                external_team_id=external_team_id or None,
                triggered_by=request.user if request.user.is_authenticated else None,
            )
        except ValueError as exc:
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except UnderstatError as exc:
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        summary = result.get('summary', {})
        enrichment = result.get('club_season_enrichment')

        return Response(
            {
                'club_id': club.id,
                'provider': ExternalProvider.UNDERSTAT,
                'status': summary.get('status'),
                'records_processed': summary.get('records_processed', 0),
                'records_created': summary.get('records_created', 0),
                'records_updated': summary.get('records_updated', 0),
                'error_count': summary.get('error_count', 0),
                'raw_error_summary': summary.get('raw_error_summary', ''),
                'sync_job_id': result['job'].id,
                'season_label': enrichment.season_label if enrichment else season_label,
                'competition_code': enrichment.competition_code if enrichment else competition_code,
                'matches_played': enrichment.matches_played if enrichment else 0,
                'xg': enrichment.xg if enrichment else None,
                'xga': enrichment.xga if enrichment else None,
                'npxg': enrichment.npxg if enrichment else None,
                'last_synced_at': (
                    enrichment.last_synced_at.isoformat()
                    if enrichment and enrichment.last_synced_at else None
                ),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['get'])
    def my_clubs(self, request):
        if not request.user.is_authenticated:
            return Response([], status=status.HTTP_200_OK)

        member_club_ids = ClubMembership.objects.filter(
            user=request.user,
            is_active=True,
        ).values_list('club_id', flat=True)

        clubs = Club.objects.filter(
            id__in=member_club_ids,
        ).select_related('creator').order_by('-updated_at')

        serializer = ClubSerializer(clubs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='lookup-by-code')
    def lookup_by_code(self, request):
        code = (request.query_params.get('code') or '').strip().upper()

        if not code:
            return Response(
                {'detail': 'code query parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self._with_understat_summary(
            Club.objects.filter(
                directory_visibility=Club.DirectoryVisibility.HIDDEN_CODE_ONLY,
                join_code__iexact=code,
            )
        )

        club = queryset.first()

        if club is None:
            return Response(
                {'detail': 'No hidden club found for that join code.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ClubSerializer(
            club,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
class ClubJoinRequestViewSet(viewsets.GenericViewSet):
    queryset = ClubJoinRequest.objects.select_related(
        'club',
        'user',
        'reviewed_by',
        'selected_club_player',
    ).order_by('-created_at')

    def get_queryset(self):
        club_pk = self.kwargs.get('club_pk')
        if club_pk:
            return self.queryset.filter(club_id=club_pk)
        return self.queryset.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return ClubJoinRequestCreateSerializer
        if self.action == 'approve':
            return ClubJoinRequestApproveSerializer
        if self.action == 'reject':
            return ClubJoinRequestRejectSerializer
        if self.action == 'withdraw':
            return ClubJoinRequestWithdrawSerializer
        return ClubJoinRequestSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticatedOrBypass(), CanCreateJoinRequest()]
        if self.action in ['approve', 'reject']:
            return [IsAuthenticatedOrBypass(), CanReviewClubJoinRequest()]
        if self.action == 'withdraw':
            return [IsAuthenticatedOrBypass(), CanWithdrawOwnClubJoinRequest()]
        if self.action == 'mine':
            return [IsAuthenticatedOrBypass()]
        return [IsAuthenticatedOrBypass()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        club_pk = self.kwargs.get('club_pk')
        if club_pk:
            context['club'] = get_object_or_404(Club, pk=club_pk)
        return context

    def _get_club(self):
        club_pk = self.kwargs.get('club_pk')
        if not club_pk:
            return None
        return get_object_or_404(Club, pk=club_pk)

    def list(self, request, club_pk=None):
        club = self._get_club()
        if club is None:
            raise PermissionDenied('Club context is required to list club join requests.')

        if not getattr(settings, 'BYPASS_PERMISSIONS', False):
            if not user_can_review_join_requests(request.user, club):
                raise PermissionDenied('You do not have permission to view join requests for this club.')

        serializer = ClubJoinRequestSerializer(
            self.get_queryset(),
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, club_pk=None):
        serializer = self.get_serializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        join_request = serializer.save()

        response_serializer = ClubJoinRequestSerializer(
            join_request,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def mine(self, request):
        queryset = ClubJoinRequest.objects.filter(
            user=request.user,
        ).select_related(
            'club',
            'user',
            'reviewed_by',
            'selected_club_player',
        ).order_by('-created_at')

        serializer = ClubJoinRequestSerializer(
            queryset,
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def approve(self, request, club_pk=None, pk=None):
        join_request = self.get_object()
        self.check_object_permissions(request, join_request)

        serializer = self.get_serializer(
            join_request,
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ClubJoinRequestSerializer(
            join_request,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reject(self, request, club_pk=None, pk=None):
        join_request = self.get_object()
        self.check_object_permissions(request, join_request)

        serializer = self.get_serializer(
            join_request,
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ClubJoinRequestSerializer(
            join_request,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def withdraw(self, request, club_pk=None, pk=None):
        join_request = self.get_object()
        self.check_object_permissions(request, join_request)

        serializer = self.get_serializer(
            join_request,
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ClubJoinRequestSerializer(
            join_request,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class ClubInvitationViewSet(viewsets.GenericViewSet):
    queryset = ClubInvitation.objects.select_related(
        'club',
        'invited_user',
        'invited_by',
    ).order_by('-created_at')

    def get_queryset(self):
        club_pk = self.kwargs.get('club_pk')
        if club_pk:
            return self.queryset.filter(club_id=club_pk)
        return self.queryset.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return ClubInvitationCreateSerializer
        if self.action == 'accept':
            return ClubInvitationAcceptSerializer
        if self.action == 'decline':
            return ClubInvitationDeclineSerializer
        if self.action == 'revoke':
            return ClubInvitationRevokeSerializer
        return ClubInvitationSerializer

    def get_permissions(self):
        if self.action in ['list', 'create']:
            return [IsAuthenticatedOrBypass(), CanCreateClubInvitation()]
        if self.action in ['accept', 'decline']:
            return [IsAuthenticatedOrBypass(), CanRespondToClubInvitation()]
        if self.action == 'revoke':
            return [IsAuthenticatedOrBypass(), CanRevokeClubInvitation()]
        if self.action == 'mine':
            return [IsAuthenticatedOrBypass()]
        return [IsAuthenticatedOrBypass()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        club_pk = self.kwargs.get('club_pk')
        if club_pk:
            context['club'] = get_object_or_404(Club, pk=club_pk)
        return context

    def list(self, request, club_pk=None):
        serializer = ClubInvitationSerializer(
            self.get_queryset(),
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, club_pk=None):
        serializer = self.get_serializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        invitation = serializer.save()

        response_serializer = ClubInvitationSerializer(
            invitation,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def mine(self, request):
        queryset = ClubInvitation.objects.filter(
            invited_user=request.user,
        ).select_related(
            'club',
            'invited_user',
            'invited_by',
        ).order_by('-created_at')

        serializer = ClubInvitationSerializer(
            queryset,
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def accept(self, request, club_pk=None, pk=None):
        invitation = self.get_object()
        self.check_object_permissions(request, invitation)

        serializer = self.get_serializer(
            invitation,
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ClubInvitationSerializer(
            invitation,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def decline(self, request, club_pk=None, pk=None):
        invitation = self.get_object()
        self.check_object_permissions(request, invitation)

        serializer = self.get_serializer(
            invitation,
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ClubInvitationSerializer(
            invitation,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def revoke(self, request, club_pk=None, pk=None):
        invitation = self.get_object()
        self.check_object_permissions(request, invitation)

        serializer = self.get_serializer(
            invitation,
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ClubInvitationSerializer(
            invitation,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)
        
class ClubMembershipViewSet(viewsets.ModelViewSet):
    serializer_class = ClubMembershipSerializer
    permission_classes = [IsAuthenticatedOrBypass, CanManageClubContent]

    def create(self, request, *args, **kwargs):
        return Response(
            {
                'detail': (
                    'Direct membership creation is disabled. '
                    'Use join-request approval or invitation acceptance workflows.'
                )
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def get_queryset(self):
        club_pk = self.kwargs.get('club_pk')
        return ClubMembership.objects.filter(
            club_id=club_pk,
        ).select_related('user', 'club', 'invited_by').order_by('role', 'joined_at')

    def perform_create(self, serializer):
        club_pk = self.kwargs.get('club_pk')
        serializer.save(
            club_id=club_pk,
            invited_by=self.request.user,
        )

class ClubPlayerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrBypass, CanManageClubContent]

    def get_serializer_class(self):
        if self.action == 'create':
            return ClubPlayerCreateSerializer
        if self.action in ['update', 'partial_update']:
            return ClubPlayerUpdateSerializer
        if self.action == 'link':
            return ClubPlayerLinkSerializer
        if self.action == 'unlink':
            return ClubPlayerUnlinkSerializer
        if self.action == 'relink':
            return ClubPlayerRelinkSerializer
        if self.action == 'list':
            return ClubPlayerListSerializer
        return ClubPlayerSerializer

    def get_permissions(self):
        if self.action in ['link', 'unlink', 'relink']:
            return [IsAuthenticatedOrBypass(), CanManageClubPlayerIdentity()]
        return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        club_pk = self.kwargs.get('club_pk')
        if club_pk:
            return (
                ClubPlayer.objects.filter(club_id=club_pk, is_active=True)
                .select_related('club', 'user', 'player')
                .prefetch_related('player__external_identities')
            )

        if not self.request.user.is_authenticated:
            return ClubPlayer.objects.none()

        user_club_ids = ClubMembership.objects.filter(
            user=self.request.user,
            is_active=True,
        ).values_list('club_id', flat=True)

        return (
            ClubPlayer.objects.filter(club_id__in=user_club_ids, is_active=True)
            .select_related('club', 'user', 'player')
            .prefetch_related('player__external_identities')
        )

    def perform_create(self, serializer):
        club_pk = self.kwargs.get('club_pk')
        serializer.save(club_id=club_pk, created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        response_serializer = ClubPlayerSerializer(
            serializer.instance,
            context=self.get_serializer_context(),
        )
        headers = self.get_success_headers(response_serializer.data)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        response_serializer = ClubPlayerSerializer(
            serializer.instance,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def link(self, request, club_pk=None, pk=None):
        club_player = self.get_object()
        self.check_object_permissions(request, club_player)

        serializer = self.get_serializer(
            instance=club_player,
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ClubPlayerSerializer(
            club_player,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def unlink(self, request, club_pk=None, pk=None):
        club_player = self.get_object()
        self.check_object_permissions(request, club_player)

        serializer = self.get_serializer(
            instance=club_player,
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ClubPlayerSerializer(
            club_player,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def relink(self, request, club_pk=None, pk=None):
        club_player = self.get_object()
        self.check_object_permissions(request, club_player)

        serializer = self.get_serializer(
            instance=club_player,
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ClubPlayerSerializer(
            club_player,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def by_position(self, request, **kwargs):
        position = request.query_params.get('position')

        if not position:
            return Response(
                {'error': 'position query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.get_queryset().filter(
            Q(player__primary_position=position) |
            Q(player__secondary_positions__contains=[position]) |
            Q(primary_position=position) |
            Q(secondary_position=position)
        ).distinct()

        serializer = ClubPlayerListSerializer(
            queryset,
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data)

class ClubEventViewSet(viewsets.ModelViewSet):
    permission_classes = [CanAccessClubScheduling]

    def get_queryset(self):
        club_pk = self.kwargs.get('club_pk')
        if not club_pk:
            return ClubEvent.objects.none()

        return ClubEvent.objects.filter(
            club_id=club_pk
        ).select_related(
            'club',
            'created_by',
        ).order_by('start_datetime', 'id')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ClubEventWriteSerializer
        return ClubEventSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        club_pk = self.kwargs.get('club_pk')
        if club_pk:
            context['club'] = get_object_or_404(Club, pk=club_pk)
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(
            club=self.get_serializer_context()['club'],
            created_by=request.user if request.user.is_authenticated else None,
        )

        response_serializer = ClubEventSerializer(
            instance,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()

        response_serializer = ClubEventSerializer(
            updated_instance,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class FixtureViewSet(viewsets.ModelViewSet):
    permission_classes = [CanAccessClubScheduling]

    def get_queryset(self):
        club_pk = self.kwargs.get('club_pk')
        if not club_pk:
            return Fixture.objects.none()

        return Fixture.objects.filter(
            club_id=club_pk
        ).select_related(
            'club',
            'created_by',
        ).order_by('match_datetime', 'id')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return FixtureWriteSerializer
        return FixtureSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        club_pk = self.kwargs.get('club_pk')
        if club_pk:
            context['club'] = get_object_or_404(Club, pk=club_pk)
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(
            club=self.get_serializer_context()['club'],
            created_by=request.user if request.user.is_authenticated else None,
        )

        response_serializer = FixtureSerializer(
            instance,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()

        response_serializer = FixtureSerializer(
            updated_instance,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

class ClubResourceViewSet(viewsets.ModelViewSet):
    ACCESS_TOKEN_SALT = 'clubs.resource.delivery'
    ACCESS_TOKEN_MAX_AGE_SECONDS = 300
    pagination_class = None

    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action in ['create', 'partial_update', 'update', 'archive']:
            permission_classes = [IsAuthenticatedOrBypass, CanManageClubResources]
        elif self.action == 'engagement':
            permission_classes = [IsAuthenticatedOrBypass, CanViewClubResourceEngagementDashboard]
        elif self.action == 'my_status':
            permission_classes = [IsAuthenticatedOrBypass, CanAccessClubResources]
        else:
            permission_classes = [IsAuthenticatedOrBypass, CanAccessClubResources]

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'list':
            return ClubResourceListSerializer
        if self.action == 'create':
            return ClubResourceUploadSerializer
        if self.action in ['partial_update', 'update']:
            return ClubResourceUpdateSerializer
        if self.action == 'archive':
            return ClubResourceArchiveSerializer
        if self.action == 'access':
            return ClubResourceSignedAccessSerializer
        if self.action == 'heartbeat':
            return ClubResourceHeartbeatSerializer
        if self.action == 'engagement':
            return ClubResourceEngagementReadSerializer
        return ClubResourceDetailSerializer

    def _get_club(self):
        club_pk = self.kwargs.get('club_pk')
        return get_object_or_404(Club, pk=club_pk)

    def _get_membership(self):
        club = self._get_club()
        return ClubMembership.objects.filter(
            user=self.request.user,
            club=club,
            is_active=True,
        ).first()

    def get_queryset(self):
        club_pk = self.kwargs.get('club_pk')

        queryset = ClubResource.objects.filter(
            club_id=club_pk,
        ).select_related(
            'club',
            'uploaded_by',
        ).prefetch_related(
            'view_summaries__user',
        )

        membership = None
        if getattr(self.request.user, 'is_authenticated', False):
            membership = ClubMembership.objects.filter(
                user=self.request.user,
                club_id=club_pk,
                is_active=True,
            ).first()

        if self.action == 'list':
            return queryset.filter(is_archived=False).order_by('-created_at', '-id')

        if membership is not None and membership.can_create_content():
            return queryset.order_by('-created_at', '-id')

        return queryset.filter(is_archived=False).order_by('-created_at', '-id')

    def perform_create(self, serializer):
        serializer.save(
            club=self._get_club(),
            uploaded_by=self.request.user,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        resource = self.get_object()
        serializer = self.get_serializer(
            resource,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ClubResourceDetailSerializer(
            resource,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def archive(self, request, club_pk=None, pk=None):
        resource = self.get_object()
        serializer = self.get_serializer(resource, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ClubResourceDetailSerializer(
            resource,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def _build_delivery_token(self, resource, request_user_id):
        return signing.dumps(
            {
                'club_id': resource.club_id,
                'resource_id': resource.id,
                'user_id': request_user_id,
            },
            salt=self.ACCESS_TOKEN_SALT,
        )

    def _validate_delivery_token(self, token):
        return signing.loads(
            token,
            max_age=self.ACCESS_TOKEN_MAX_AGE_SECONDS,
            salt=self.ACCESS_TOKEN_SALT,
        )

    @action(detail=True, methods=['get'])
    def access(self, request, club_pk=None, pk=None):
        resource = self.get_object()

        request_user_id = request.user.id if request.user.is_authenticated else 0
        token = self._build_delivery_token(resource, request_user_id)
        expires_at = timezone.now() + timedelta(seconds=self.ACCESS_TOKEN_MAX_AGE_SECONDS)

        delivery_url = reverse(
            'club-resource-delivery',
            kwargs={
                'club_pk': resource.club_id,
                'pk': resource.id,
            },
            request=request,
        )
        access_url = f'{delivery_url}?token={token}'

        payload = {
            'resource_id': resource.id,
            'title': resource.title,
            'original_filename': resource.original_filename,
            'mime_type': resource.mime_type,
            'file_kind': resource.file_kind,
            'access_mode': 'inline' if resource.can_inline_view() else 'download',
            'can_inline_view': resource.can_inline_view(),
            'is_download_only': resource.is_download_only(),
            'access_url': access_url,
            'expires_at': expires_at,
        }

        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def delivery(self, request, club_pk=None, pk=None):
        resource = self.get_object()

        token = request.query_params.get('token', '').strip()
        if not token:
            return Response(
                {'detail': 'Signed access token is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payload = self._validate_delivery_token(token)
        except signing.BadSignature:
            return Response(
                {'detail': 'Invalid or expired access token.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        expected_user_id = request.user.id if request.user.is_authenticated else 0
        if payload.get('club_id') != resource.club_id or payload.get('resource_id') != resource.id:
            return Response(
                {'detail': 'Access token does not match this resource.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not getattr(settings, 'BYPASS_PERMISSIONS', False):
            if payload.get('user_id') != expected_user_id:
                return Response(
                    {'detail': 'Access token does not match the current user.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        if (
            resource.storage_backend == ClubResource.StorageBackend.CLOUDINARY and
            resource.storage_key and
            cloudinary_resources_enabled()
        ):
            try:
                signed_cloudinary_url = build_cloudinary_signed_delivery_url(resource)
            except ClubResourceStorageError as exc:
                return Response(
                    {'detail': str(exc)},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            return redirect(signed_cloudinary_url)

        if not resource.file:
            return Response(
                {'detail': 'Resource file is not available.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        response = FileResponse(
            resource.file.open('rb'),
            content_type=resource.mime_type,
        )

        disposition = 'inline' if resource.can_inline_view() else 'attachment'
        response['Content-Disposition'] = (
            f'{disposition}; filename="{resource.original_filename}"'
        )
        return response

    @action(detail=True, methods=['post'])
    def heartbeat(self, request, club_pk=None, pk=None):
        resource = self.get_object()

        view_summary, _ = ClubResourceView.objects.get_or_create(
            resource=resource,
            user=request.user,
        )

        serializer = self.get_serializer(
            view_summary,
            data=request.data,
            context={'resource': resource},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ClubResourceViewReadSerializer(
            view_summary,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def engagement(self, request, club_pk=None, pk=None):
        resource = self.get_object()
        self.check_object_permissions(request, resource)

        serializer = self.get_serializer(
            resource,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def my_status(self, request, club_pk=None, pk=None):
        resource = self.get_object()

        membership = self._get_membership()
        can_view_club_status = bool(
            membership and (
                membership.can_create_content() or
                resource.engagement_visibility == ClubResource.EngagementVisibility.CLUB_VISIBLE
            )
        )

        view_summary = ClubResourceView.objects.filter(
            resource=resource,
            user=request.user,
        ).first()

        payload = {
            'resource_id': resource.id,
            'engagement_visibility': resource.engagement_visibility,
            'can_view_club_status': can_view_club_status,
            'opened_count': (
                resource.view_summaries.filter(opened=True).count()
                if can_view_club_status else None
            ),
            'completed_count': (
                resource.view_summaries.filter(completed=True).count()
                if can_view_club_status else None
            ),
            'my_view_summary': (
                ClubResourceViewReadSerializer(
                    view_summary,
                    context=self.get_serializer_context(),
                ).data
                if view_summary else None
            ),
        }

        return Response(payload, status=status.HTTP_200_OK)

class ClubImportJobViewSet(viewsets.ModelViewSet):
    pagination_class = None

    def get_queryset(self):
        club_pk = self.kwargs.get('club_pk')
        return ClubImportJob.objects.filter(
            club_id=club_pk
        ).select_related(
            'club',
            'uploaded_by',
            'source_resource',
        ).order_by('-created_at', '-id')

    def get_permissions(self):
        if self.action == 'commit':
            return [IsAuthenticatedOrBypass(), CanCommitClubImportJob()]
        return [IsAuthenticatedOrBypass(), CanAccessClubImportJobs()]

    def get_serializer_class(self):
        if self.action == 'create':
            return ClubImportJobCreateSerializer
        if self.action == 'list':
            return ClubImportJobListSerializer
        if self.action == 'commit':
            return ClubImportJobCommitSerializer
        return ClubImportJobDetailSerializer

    def create(self, request, *args, **kwargs):
        club = get_object_or_404(Club, pk=self.kwargs.get('club_pk'))

        serializer = self.get_serializer(
            data=request.data,
            context={
                **self.get_serializer_context(),
                'club': club,
            },
        )
        serializer.is_valid(raise_exception=True)
        job = serializer.save()

        response_serializer = ClubImportJobDetailSerializer(
            job,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def commit(self, request, club_pk=None, pk=None):
        job = self.get_object()
        self.check_object_permissions(request, job)

        serializer = self.get_serializer(
            instance=job,
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = ClubImportJobDetailSerializer(
            job,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)