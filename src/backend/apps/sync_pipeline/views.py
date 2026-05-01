from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.sync_pipeline.models import PublishedSnapshot, SourceHealth, SyncRun
from apps.sync_pipeline.selectors import compute_surface_freshness, get_active_snapshot
from apps.sync_pipeline.serializers import (
    PublishedSnapshotSerializer,
    SourceHealthSerializer,
    SyncRunSerializer,
)
from common.constants import SyncStatus
from common.utils import utcnow

KNOWN_SURFACES = ['livefootball', 'predictions', 'playerdata', 'clubs']


class PipelineHealthView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        sla_map = getattr(settings, 'FRESHNESS_SLA_SECONDS', {})
        summary = []

        for surface in KNOWN_SURFACES:
            sla = sla_map.get(surface, 21600)
            fp = compute_surface_freshness(surface, sla_seconds=sla)
            snapshot = get_active_snapshot(surface)

            last_run = (
                SyncRun.objects.filter(status=SyncStatus.SUCCESS)
                .order_by('-finished_at')
                .first()
            )

            consecutive_failures = 0
            if snapshot:
                for provider in (snapshot.source_provider_set or []):
                    health = SourceHealth.objects.filter(provider=provider).first()
                    if health:
                        consecutive_failures = max(consecutive_failures, health.consecutive_failures)

            summary.append({
                'surface': surface,
                'is_stale': fp.is_stale,
                'is_degraded': fp.is_degraded,
                'snapshot_published_at': snapshot.published_at if snapshot else None,
                'active_version': snapshot.version if snapshot else None,
                'consecutive_failures': consecutive_failures,
                'last_successful_run_at': last_run.finished_at if last_run else None,
            })

        return Response({
            'generated_at': utcnow().isoformat(),
            'surfaces': summary,
        })


class PipelineSurfaceHealthView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, surface: str):
        if surface not in KNOWN_SURFACES:
            return Response({'error': f'Unknown surface: {surface}'}, status=404)

        sla_map = getattr(settings, 'FRESHNESS_SLA_SECONDS', {})
        sla = sla_map.get(surface, 21600)
        fp = compute_surface_freshness(surface, sla_seconds=sla)
        snapshot = get_active_snapshot(surface)

        cutoff = utcnow() - timedelta(hours=24)
        recent_runs = SyncRun.objects.filter(
            started_at__gte=cutoff,
        ).order_by('-started_at')[:20]

        source_health = []
        if snapshot:
            for provider in (snapshot.source_provider_set or []):
                health = SourceHealth.objects.filter(provider=provider).first()
                if health:
                    source_health.append(SourceHealthSerializer(health).data)

        return Response({
            'surface': surface,
            'freshness': {
                'is_stale': fp.is_stale,
                'is_degraded': fp.is_degraded,
                'stale_reason': fp.stale_reason,
                'sla_seconds': fp.sla_seconds,
                'snapshot_published_at': fp.snapshot_published_at.isoformat() if fp.snapshot_published_at else None,
            },
            'active_snapshot': PublishedSnapshotSerializer(snapshot).data if snapshot else None,
            'recent_runs': SyncRunSerializer(recent_runs, many=True).data,
            'source_health': source_health,
        })


class PipelineSnapshotsView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        snapshots = {
            surface: get_active_snapshot(surface)
            for surface in KNOWN_SURFACES
        }

        return Response({
            'generated_at': utcnow().isoformat(),
            'snapshots': {
                surface: PublishedSnapshotSerializer(snap).data if snap else None
                for surface, snap in snapshots.items()
            },
        })