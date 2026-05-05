"""
Application configuration for the player data app
"""

from django.apps import AppConfig


class PlayerdataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.playerdata'
    verbose_name = "Player Data"