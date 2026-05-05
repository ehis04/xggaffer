from django.db.models import Q, Prefetch
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import ClubMembership, ClubPlayer
from apps.playerdata.models import PlayerSeasonEnrichment
from ..permissions import (
    CanManageClubContent,
    CanManageClubPlayerIdentity,
    IsAuthenticatedOrBypass,
)
from ..serializers import (
    ClubPlayerCreateSerializer,
    ClubPlayerLinkSerializer,
    ClubPlayerListSerializer,
    ClubPlayerRelinkSerializer,
    ClubPlayerSerializer,
    ClubPlayerUnlinkSerializer,
    ClubPlayerUpdateSerializer,
    ClubPlayerWithAvailabilitySerializer,
)


class ClubPlayerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrBypass, CanManageClubContent]
    pagination_class = None

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
            return ClubPlayerWithAvailabilitySerializer
        return ClubPlayerSerializer

    def get_permissions(self):
        if self.action in ['link', 'unlink', 'relink']:
            return [IsAuthenticatedOrBypass(), CanManageClubPlayerIdentity()]
        return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        club_pk = self.kwargs.get('club_pk')
        enrichments_prefetch = Prefetch(
            'player__season_enrichments',
            queryset=PlayerSeasonEnrichment.objects.order_by('-season_label', '-id'),
            to_attr='prefetched_season_enrichments',
        )
        if club_pk:
            return (
                ClubPlayer.objects.filter(club_id=club_pk, is_active=True)
                .select_related('club', 'user', 'player')
                .prefetch_related(
                    'player__external_identities',
                    'injuries',
                    enrichments_prefetch,
                )
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
            .prefetch_related(
                'player__external_identities',
                'injuries',
                enrichments_prefetch,
            )
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
