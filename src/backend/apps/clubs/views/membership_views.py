from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from ..models import Club, ClubInvitation, ClubJoinRequest, ClubMembership
from ..permissions import (
    CanCreateClubInvitation,
    CanCreateJoinRequest,
    CanLeaveClub,
    CanManageClubContent,
    CanRespondToClubInvitation,
    CanReviewClubJoinRequest,
    CanRevokeClubInvitation,
    CanWithdrawOwnClubJoinRequest,
    IsAuthenticatedOrBypass,
    should_bypass_permissions,
    user_can_review_join_requests,
)
from ..serializers import (
    ClubInvitationAcceptSerializer,
    ClubInvitationCreateSerializer,
    ClubInvitationDeclineSerializer,
    ClubInvitationRevokeSerializer,
    ClubInvitationSerializer,
    ClubJoinRequestApproveSerializer,
    ClubJoinRequestCreateSerializer,
    ClubJoinRequestRejectSerializer,
    ClubJoinRequestSerializer,
    ClubJoinRequestWithdrawSerializer,
    ClubMembershipSerializer,
)


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

        if not should_bypass_permissions():
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

    @action(detail=True, methods=['post'])
    def leave(self, request, club_pk=None, pk=None):
        """Allow a user to leave a club if they are not owner or admin."""
        membership = self.get_object()
        self.check_object_permissions(request, membership)

        if membership.role in [ClubMembership.Role.OWNER, ClubMembership.Role.ADMIN]:
            return Response(
                {'detail': 'Owners and admins cannot leave a club. Transfer ownership or demote first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
