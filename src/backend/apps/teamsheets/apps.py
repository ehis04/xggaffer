"""
Application configuration for the teamsheets app
"""

from django.apps import AppConfig


class TeamsheetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.teamsheets'
    verbose_name = "Teamsheets"