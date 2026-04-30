from datetime import timedelta

from django.core import signing
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from rest_framework import permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.reverse import reverse

from ..models import Club, ClubMembership, ClubResource, ClubResourceView
from ..permissions import (
    CanAccessClubResources,
    CanManageClubResources,
    CanViewClubResourceEngagementDashboard,
    IsAuthenticatedOrBypass,
    should_bypass_permissions,
)
from ..serializers import (
    ClubResourceArchiveSerializer,
    ClubResourceDetailSerializer,
    ClubResourceEngagementReadSerializer,
    ClubResourceHeartbeatSerializer,
    ClubResourceListSerializer,
    ClubResourceSignedAccessSerializer,
    ClubResourceUploadSerializer,
    ClubResourceUpdateSerializer,
    ClubResourceViewReadSerializer,
)
from ..storage import (
    ClubResourceStorageError,
    build_cloudinary_signed_delivery_url,
    cloudinary_resources_enabled,
)


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
        elif self.action == 'delivery':
            permission_classes = [permissions.AllowAny]
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

        expected_user_id = request.user.id if request.user.is_authenticated else None
        if payload.get('club_id') != resource.club_id or payload.get('resource_id') != resource.id:
            return Response(
                {'detail': 'Access token does not match this resource.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not should_bypass_permissions():
            if expected_user_id is not None and payload.get('user_id') != expected_user_id:
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
