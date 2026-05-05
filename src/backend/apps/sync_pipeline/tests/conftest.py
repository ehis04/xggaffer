import django
from django.conf import settings


def pytest_configure(config):
    if not settings.configured:
        settings.configure(
            SECRET_KEY='test-secret-key',
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
                'apps.sync_pipeline',
            ],
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            CACHES={
                'default': {
                    'BACKEND': 'django_redis.cache.RedisCache',
                    'LOCATION': 'redis://localhost:6379/2',
                    'OPTIONS': {
                        'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                    },
                }
            },
            USE_TZ=True,
            DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
            FOOTBALL_DATA_DAILY_REQUEST_LIMIT=100,
            PIPELINE_DEGRADED_THRESHOLD=3,
        )