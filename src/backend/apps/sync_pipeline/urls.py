from django.urls import path

from apps.sync_pipeline.views import (
    PipelineHealthView,
    PipelineSnapshotsView,
    PipelineSurfaceHealthView,
)

urlpatterns = [
    path('sync/health/', PipelineHealthView.as_view(), name='sync-health'),
    path('sync/health/<str:surface>/', PipelineSurfaceHealthView.as_view(), name='sync-surface-health'),
    path('sync/snapshots/', PipelineSnapshotsView.as_view(), name='sync-snapshots'),
]