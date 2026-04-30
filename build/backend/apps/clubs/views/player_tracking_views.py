from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Club, ClubMembership, ClubPlayer, ClubPlayerInjury, ClubPlayerManualStats, ClubSeasonResult
from ..serializers import (
    ClubPlayerInjurySerializer,
    ClubPlayerManualStatsSerializer,
    ClubSeasonResultSerializer,
)


class ClubPlayerInjuryView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_club_player(self, club_id, player_id):
        return get_object_or_404(
            ClubPlayer,
            pk=player_id,
            club_id=club_id,
            is_active=True,
        )

    def _assert_can_manage(self, request, club):
        membership = ClubMembership.objects.filter(
            club=club, user=request.user, is_active=True
        ).first()
        if not membership or membership.role not in ('owner', 'admin', 'coach'):
            raise PermissionDenied('Only owners, admins, and coaches can manage injuries.')

    def get(self, request, club_id, player_id):
        club_player = self._get_club_player(club_id, player_id)
        injuries = club_player.injuries.order_by('-injured_at')
        serializer = ClubPlayerInjurySerializer(injuries, many=True)
        return Response(serializer.data)

    def post(self, request, club_id, player_id):
        club_player = self._get_club_player(club_id, player_id)
        self._assert_can_manage(request, club_player.club)

        ClubPlayerInjury.objects.filter(
            club_player=club_player, is_current=True
        ).update(is_current=False)

        serializer = ClubPlayerInjurySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(club_player=club_player, recorded_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ClubPlayerInjuryResolveView(APIView):
    permission_classes = [IsAuthenticated]

    def _assert_can_manage(self, request, club):
        membership = ClubMembership.objects.filter(
            club=club, user=request.user, is_active=True
        ).first()
        if not membership or membership.role not in ('owner', 'admin', 'coach'):
            raise PermissionDenied('Only owners, admins, and coaches can resolve injuries.')

    def post(self, request, club_id, player_id, injury_id):
        club_player = get_object_or_404(
            ClubPlayer, pk=player_id, club_id=club_id, is_active=True
        )
        self._assert_can_manage(request, club_player.club)
        injury = get_object_or_404(
            ClubPlayerInjury, pk=injury_id, club_player=club_player, is_current=True
        )
        injury.resolve()
        return Response({'status': 'resolved'})


class ClubPlayerManualStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_club_player(self, club_id, player_id):
        return get_object_or_404(
            ClubPlayer, pk=player_id, club_id=club_id, is_active=True
        )

    def _assert_can_manage(self, request, club):
        membership = ClubMembership.objects.filter(
            club=club, user=request.user, is_active=True
        ).first()
        if not membership or membership.role not in ('owner', 'admin', 'coach'):
            raise PermissionDenied('Only owners, admins, and coaches can manage player stats.')

    def get(self, request, club_id, player_id):
        club_player = self._get_club_player(club_id, player_id)
        stats = club_player.manual_stats.order_by('-season')
        serializer = ClubPlayerManualStatsSerializer(stats, many=True)
        return Response(serializer.data)

    def post(self, request, club_id, player_id):
        club_player = self._get_club_player(club_id, player_id)
        self._assert_can_manage(request, club_player.club)

        season = request.data.get('season')
        existing = ClubPlayerManualStats.objects.filter(
            club_player=club_player, season=season
        ).first()

        if existing:
            serializer = ClubPlayerManualStatsSerializer(
                existing, data=request.data, partial=True
            )
        else:
            serializer = ClubPlayerManualStatsSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save(club_player=club_player)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK if existing else status.HTTP_201_CREATED,
        )


class ClubSeasonResultView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_club(self, club_id):
        return get_object_or_404(Club, pk=club_id)

    def _assert_can_manage(self, request, club):
        membership = ClubMembership.objects.filter(
            club=club, user=request.user, is_active=True
        ).first()
        if not membership or membership.role not in ('owner', 'admin', 'coach'):
            raise PermissionDenied('Only owners, admins, and coaches can manage season results.')

    def get(self, request, club_id):
        club = self._get_club(club_id)
        results = club.season_results.order_by('-match_date')
        serializer = ClubSeasonResultSerializer(results, many=True)
        return Response(serializer.data)

    def post(self, request, club_id):
        club = self._get_club(club_id)
        self._assert_can_manage(request, club)
        serializer = ClubSeasonResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(club=club, created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ClubSeasonResultDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_result(self, club_id, result_id):
        return get_object_or_404(ClubSeasonResult, pk=result_id, club_id=club_id)

    def _assert_can_manage(self, request, club):
        membership = ClubMembership.objects.filter(
            club=club, user=request.user, is_active=True
        ).first()
        if not membership or membership.role not in ('owner', 'admin', 'coach'):
            raise PermissionDenied('Only owners, admins, and coaches can manage season results.')

    def patch(self, request, club_id, result_id):
        result = self._get_result(club_id, result_id)
        self._assert_can_manage(request, result.club)
        serializer = ClubSeasonResultSerializer(result, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, club_id, result_id):
        result = self._get_result(club_id, result_id)
        self._assert_can_manage(request, result.club)
        result.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
