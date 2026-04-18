import sys
from pathlib import Path

predictions_dir = str(Path(__file__).resolve().parents[3])
if predictions_dir not in sys.path:
    sys.path.append(predictions_dir)

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        SECRET_KEY='test-secret-key-for-unit-tests',
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'rest_framework',
        ],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        USE_I18N=False,
        REST_FRAMEWORK={},
    )
    django.setup()