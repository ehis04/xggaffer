from django.shortcuts import render

# Create your views here.
# clubs/views.py
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as filters
from .models import ClubEvent, Fixture
from .serializers import ClubEventSerializer, FixtureSerializer


class ClubEventFilter(filters.FilterSet):
    start_after = filters.DateTimeFilter(field_name='start_datetime', lookup_expr='gte')
    start_before = filters.DateTimeFilter(field_name='start_datetime', lookup_expr='lte')
    event_type = filters.ChoiceFilter(choices=ClubEvent.EventType.choices)
    
    class Meta:
        model = ClubEvent
        fields = ['event_type']


class ClubEventViewSet(viewsets.ModelViewSet):
    serializer_class = ClubEventSerializer
    filterset_class = ClubEventFilter
    
    def get_queryset(self):
        club_id = self.kwargs.get('club_pk')
        return ClubEvent.objects.filter(
            club_id=club_id
        ).select_related('club', 'created_by')
    
    def perform_create(self, serializer):
        club_id = self.kwargs.get('club_pk')
        serializer.save(
            club_id=club_id,
            created_by=self.request.user
        )


class FixtureFilter(filters.FilterSet):
    date_after = filters.DateFilter(field_name='date', lookup_expr='gte')
    date_before = filters.DateFilter(field_name='date', lookup_expr='lte')
    status = filters.ChoiceFilter(choices=Fixture.Status.choices)
    
    class Meta:
        model = Fixture
        fields = ['status', 'venue']


class FixtureViewSet(viewsets.ModelViewSet):
    serializer_class = FixtureSerializer
    filterset_class = FixtureFilter
    
    def get_queryset(self):
        club_id = self.kwargs.get('club_pk')
        return Fixture.objects.filter(
            club_id=club_id
        ).select_related('club', 'season')
"""

from rest_framework.decorators import action
from rest_framework.response import Response



from django.db import models
from rest_framework import viewsets, permissions, status


from .models import Club, ClubMembership, ClubPlayer
from .serializers import (
    ClubSerializer, 
    ClubMembershipSerializer, 
    ClubPlayerSerializer,
    ClubPlayerListSerializer,
    ClubPlayerCreateSerializer,
    AvailablePlayerSerializer,
)


class ClubViewSet(viewsets.ModelViewSet):
    serializer_class = ClubSerializer
    #permission_classes = [permissions.IsAuthenticated]
    permission_classes = []

    def get_queryset(self):
        user = self.request.user
        member_club_ids = ClubMembership.objects.filter(
            user=user,
            is_active=True
        ).values_list('club_id', flat=True)
        
        return Club.objects.filter(
            models.Q(id__in=member_club_ids) | models.Q(visibility=Club.Visibility.PUBLIC)
        ).distinct()

    def perform_create(self, serializer):
        club = serializer.save(creator=self.request.user)
        ClubMembership.objects.create(
            user=self.request.user,
            club=club,
            role=ClubMembership.Role.OWNER,
            is_active=True
        )

    @action(detail=True, methods=['get'])
    def available_players(self, request, pk=None):
        club = self.get_object()
        position = request.query_params.get('position', None)
        search = request.query_params.get('search', None)
        
        club_players = ClubPlayer.objects.filter(
            club=club,
            is_active=True
        )
        
        public_players = ClubPlayer.objects.none()
        if club.visibility == Club.Visibility.PUBLIC:
            public_players = ClubPlayer.objects.filter(
                is_public=True,
                is_active=True
            ).exclude(club=club)
        
        all_players = club_players.union(public_players)
        
        all_player_ids = list(all_players.values_list('id', flat=True))
        queryset = ClubPlayer.objects.filter(id__in=all_player_ids)
        
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
                models.When(club=club, then=0),
                default=1,
                output_field=models.IntegerField()
            ),
            'position',
            'last_name'
        )
        
        serializer = AvailablePlayerSerializer(
            queryset, 
            many=True,
            context={'club_id': club.id}
        )
        return Response(serializer.data)


class ClubMembershipViewSet(viewsets.ModelViewSet):
    serializer_class = ClubMembershipSerializer
    #permission_classes = [permissions.IsAuthenticated]
    permission_classes = []
    def get_queryset(self):
        club_pk = self.kwargs.get('club_pk')
        return ClubMembership.objects.filter(club_id=club_pk)


class ClubPlayerViewSet(viewsets.ModelViewSet):
    #permission_classes = [permissions.IsAuthenticated]
    permission_classes = []
    def get_serializer_class(self):
        if self.action == 'create':
            return ClubPlayerCreateSerializer
        if self.action == 'list':
            return ClubPlayerListSerializer
        return ClubPlayerSerializer

    def get_queryset(self):
        club_pk = self.kwargs.get('club_pk')
        if club_pk:
            return ClubPlayer.objects.filter(club_id=club_pk, is_active=True)
        
        user_club_ids = ClubMembership.objects.filter(
            user=self.request.user,
            is_active=True
        ).values_list('club_id', flat=True)
        return ClubPlayer.objects.filter(club_id__in=user_club_ids, is_active=True)

    def perform_create(self, serializer):
        club_pk = self.kwargs.get('club_pk')
        serializer.save(club_id=club_pk, created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def by_position(self, request):
        club_pk = self.kwargs.get('club_pk')
        position = request.query_params.get('position')
        
        if not position:
            return Response(
                {'error': 'position query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(
            models.Q(position=position) | models.Q(secondary_position=position)
        )
        
        serializer = ClubPlayerListSerializer(queryset, many=True)
        return Response(serializer.data)
    serializer_class = ClubPlayerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        club_pk = self.kwargs.get('club_pk')
        if club_pk:
            return ClubPlayer.objects.filter(club_id=club_pk, is_active=True)
        
        user_club_ids = ClubMembership.objects.filter(
            user=self.request.user,
            is_active=True
        ).values_list('club_id', flat=True)
        return ClubPlayer.objects.filter(club_id__in=user_club_ids, is_active=True)

    def perform_create(self, serializer):
        club_pk = self.kwargs.get('club_pk')
        serializer.save(club_id=club_pk, created_by=self.request.user)