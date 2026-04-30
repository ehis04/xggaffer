from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Club, ClubImportJob
from ..permissions import (
    CanAccessClubImportJobs,
    CanCommitClubImportJob,
    IsAuthenticatedOrBypass,
)
from ..serializers import (
    ClubImportJobCommitSerializer,
    ClubImportJobCreateSerializer,
    ClubImportJobDetailSerializer,
    ClubImportJobListSerializer,
)


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
