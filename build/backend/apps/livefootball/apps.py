"""
Application configuration for the live football app
"""

from django.apps import AppConfig


class LivefootballConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.livefootball'