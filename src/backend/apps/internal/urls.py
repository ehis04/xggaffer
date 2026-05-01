"""
URL routes for internal maintenance endpoints
"""

from django.urls import path

from .views import CacheClearView


urlpatterns = [
    path('cache/clear/', CacheClearView.as_view(), name='internal-cache-clear'),
]