"""
Internal maintenance API views

Provides admin-only endpoints for clearing cached application surfaces
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from common.cache_keys import KNOWN_CACHE_SURFACES, clear_surface_cache


# Admin-only view for clearing cached surface data
class CacheClearView(APIView):
    permission_classes = [IsAdminUser]

    # Clear all known cache surfaces or one requested surface
    def post(self, request):
        surface = request.data.get('surface', 'all')

        if surface != 'all' and surface not in KNOWN_CACHE_SURFACES:
            return Response(
                {'error': f'Unknown surface: {surface}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if surface == 'all':
            cleared = list(KNOWN_CACHE_SURFACES)
            total_deleted = sum(clear_surface_cache(s) for s in KNOWN_CACHE_SURFACES)
        else:
            cleared = [surface]
            total_deleted = clear_surface_cache(surface)

        return Response({'cleared': cleared, 'total_deleted': total_deleted})