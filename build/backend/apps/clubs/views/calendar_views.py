from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response

from ..models import Club, ClubEvent, Fixture
from ..permissions import CanAccessClubScheduling
from ..serializers import (
    ClubEventSerializer,
    ClubEventWriteSerializer,
    FixtureSerializer,
    FixtureWriteSerializer,
)


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
