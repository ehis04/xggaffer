from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'teamsheets', TeamsheetViewSet, basename='teamsheet')
router.register(r'players', TeamsheetPlayerViewSet, basename='teamsheetplayer')

urlpatterns = [
    path('', include(router.urls)),
]