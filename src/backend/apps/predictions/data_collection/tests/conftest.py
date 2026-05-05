import django
from django.conf import settings


def pytest_configure(config):
    if not settings.configured:
        settings.configure(
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
                "rest_framework",
            ],
            DATABASES={},
        )
