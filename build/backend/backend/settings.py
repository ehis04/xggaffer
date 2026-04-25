"""
Backend settings.
Django configuration, authentication, storage, 3rd-party integrations, and scheduled background tasks defined 
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from decouple import config


# ---------------------------------------------------------------------------
# Base paths and Python path setup
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

# Clean imports for prediction apps local ML modules
PREDICTIONS_APP_PATH = str(BASE_DIR / "apps" / "predictions")
if PREDICTIONS_APP_PATH not in sys.path:
    sys.path.append(PREDICTIONS_APP_PATH)


# ---------------------------------------------------------------------------
# Core environment and security settings
# ---------------------------------------------------------------------------

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "testserver",
]

AUTH_USER_MODEL = "users.User"

ANTHROPIC_API_KEY = config("ANTHROPIC_API_KEY", default="")
THE_ODDS_API_KEY = config("THE_ODDS_API_KEY", default="")

# Development/testing override used when internal permission checks need to be bypassed.
BYPASS_PERMISSIONS = config("BYPASS_PERMISSIONS", default=False, cast=bool)


# ---------------------------------------------------------------------------
# Soft-delete and trash retention settings
# ---------------------------------------------------------------------------

# Retain deleted items for a limited period so users can restore them if needed.
TRASH_RETENTION_DAYS = config("TRASH_RETENTION_DAYS", default=7, cast=int)

# Per-user limits prevent trash table from spiralling in size.
TEAMSHEET_TRASH_LIMIT_PER_USER = config(
    "TEAMSHEET_TRASH_LIMIT_PER_USER",
    default=50,
    cast=int,
)
TACTICS_BOARD_TRASH_LIMIT_PER_USER = config(
    "TACTICS_BOARD_TRASH_LIMIT_PER_USER",
    default=50,
    cast=int,
)
CLUB_TRASH_LIMIT_PER_USER = config(
    "CLUB_TRASH_LIMIT_PER_USER",
    default=10,
    cast=int,
)


# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    # Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",

    # Third-party apps
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "cloudinary",

    # Local apps
    "apps.laws",
    "apps.quizzes",
    "apps.articles",
    "apps.teamsheets",
    "apps.users",
    "apps.predictions",
    "apps.community",
    "apps.coaching.coachProfile",
    "apps.coaching",
    "apps.players",
    "apps.players.playerProfile",
    "apps.clubs",
    "apps.tactics",
    "apps.playerdata",
    "apps.livefootball",
    "apps.sync_pipeline.apps.SyncPipelineConfig",
    "apps.referee",
    "apps.referee.progressTracking",
    "apps.referee.learningTools",
    "apps.referee.Laws",
    "apps.referee.profile",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Current deployment entry point for the Django application.
WSGI_APPLICATION = "backend.wsgi.application"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT"),
    }
}

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    }
}

ENABLE_PERFORMANCE_LOGGING = True

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# ---------------------------------------------------------------------------
# Internationalisation and time handling
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"

USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")


# ---------------------------------------------------------------------------
# Cloudinary configuration
# ---------------------------------------------------------------------------

CLOUDINARY_CLOUD_NAME = config("CLOUDINARY_CLOUD_NAME", default="")
CLOUDINARY_API_KEY = config("CLOUDINARY_API_KEY", default="")
CLOUDINARY_API_SECRET = config("CLOUDINARY_API_SECRET", default="")

# Club resources can fall back to local media storage unless Cloudinary is enabled.
CLUB_RESOURCES_USE_CLOUDINARY = config(
    "CLUB_RESOURCES_USE_CLOUDINARY",
    default=False,
    cast=bool,
)
CLUB_RESOURCES_CLOUDINARY_FOLDER = config(
    "CLUB_RESOURCES_CLOUDINARY_FOLDER",
    default="xggaffer/clubs/resources",
)


# ---------------------------------------------------------------------------
# Frontend origins, CORS, and CSRF
# ---------------------------------------------------------------------------

# Local frontend origins allowed to communicate with the backend during development.
LOCAL_FRONTEND_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = LOCAL_FRONTEND_ORIGINS
CORS_ALLOW_CREDENTIALS = True

# CSRF token must be readable by frontend JavaScript so it can be sent with requests.
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False
CSRF_TRUSTED_ORIGINS = LOCAL_FRONTEND_ORIGINS


# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    # Use cookie-backed JWT authentication across the API.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.users.authentication.CookieJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}


# ---------------------------------------------------------------------------
# Session and JWT cookie configuration
# ---------------------------------------------------------------------------

SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

AUTH_COOKIE_ACCESS = "access_token"
AUTH_COOKIE_REFRESH = "refresh_token"

# Store auth cookies as HttpOnly so they are not accessible from client-side JavaScript.
AUTH_COOKIE_SECURE = False
AUTH_COOKIE_HTTP_ONLY = True
AUTH_COOKIE_PATH = "/"
AUTH_COOKIE_SAMESITE = "Lax"

AUTH_COOKIE_ACCESS_MAX_AGE = 60 * 15
AUTH_COOKIE_REFRESH_MAX_AGE = 60 * 60 * 24 * 7
AUTH_COOKIE_REFRESH_MAX_AGE_SESSION = None


# ---------------------------------------------------------------------------
# Email and frontend configuration
# ---------------------------------------------------------------------------

RESEND_API_KEY = config("RESEND_API_KEY", default="")
DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL",
    default="xgGaffer <noreply@xggaffer.site>",
)

FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:5173")


# ---------------------------------------------------------------------------
# External football data providers
# ---------------------------------------------------------------------------

FOOTBALL_DATA_ENABLED = config("FOOTBALL_DATA_ENABLED", default=True, cast=bool)
FOOTBALL_DATA_API_BASE_URL = config(
    "FOOTBALL_DATA_API_BASE_URL",
    default="https://api.football-data.org/v4",
)
FOOTBALL_DATA_API_TOKEN = config("FOOTBALL_DATA_API_TOKEN", default="")
FOOTBALL_DATA_TIMEOUT_SECONDS = config(
    "FOOTBALL_DATA_TIMEOUT_SECONDS",
    default=15,
    cast=int,
)
FOOTBALL_DATA_RETRY_COUNT = config(
    "FOOTBALL_DATA_RETRY_COUNT",
    default=2,
    cast=int,
)

UNDERSTAT_ENABLED = config("UNDERSTAT_ENABLED", default=True, cast=bool)
UNDERSTAT_BASE_URL = config(
    "UNDERSTAT_BASE_URL",
    default="https://understat.com",
)
UNDERSTAT_TIMEOUT_SECONDS = config(
    "UNDERSTAT_TIMEOUT_SECONDS",
    default=15,
    cast=int,
)
UNDERSTAT_RETRY_COUNT = config(
    "UNDERSTAT_RETRY_COUNT",
    default=2,
    cast=int,
)
UNDERSTAT_USER_AGENT = config(
    "UNDERSTAT_USER_AGENT",
    default="xgGaffer/1.0 (+https://xggaffer.site)",
)


# ---------------------------------------------------------------------------
# Celery configuration
# ---------------------------------------------------------------------------

CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
CELERY_TIMEZONE = "UTC"

# Scheduled background jobs for scraping and housekeeping.
CELERY_BEAT_SCHEDULE = {
    "purge-expired-trash-daily": {
        "task": "apps.clubs.tasks.purge_expired_trash",
        "schedule": crontab(hour=3, minute=15),
        "options": {"expires": 3600},
    },
    "refresh-football-data-metadata": {
        "task": "apps.sync_pipeline.tasks.refresh_football_data_metadata_task",
        "schedule": crontab(hour=1, minute=0),
        "options": {"expires": 3600, "queue": "queue_football_data"},
    },
    "refresh-football-data-fixtures": {
        "task": "apps.sync_pipeline.tasks.refresh_football_data_fixtures_task",
        "schedule": crontab(minute="*/15"),
        "options": {"expires": 840, "queue": "queue_football_data"},
    },
    "refresh-football-data-scorers-squads": {
        "task": "apps.sync_pipeline.tasks.refresh_football_data_scorers_squads_task",
        "schedule": crontab(minute=0, hour="*/6"),
        "options": {"expires": 3600, "queue": "queue_football_data"},
    },
    "refresh-understat-cycle": {
        "task": "apps.sync_pipeline.tasks.refresh_understat_cycle_task",
        "schedule": crontab(minute=30, hour="*/6"),
        "options": {"expires": 3600, "queue": "queue_understat"},
    },
    "refresh-sofascore-cycle": {
        "task": "apps.sync_pipeline.tasks.refresh_sofascore_cycle_task",
        "schedule": crontab(minute=0, hour="*/3"),
        "options": {"expires": 3600, "queue": "queue_sofascore"},
    },
    "refresh-whoscored-cycle": {
        # Once daily at 04:00 UTC — WhoScored stats don't change intra-day and
        # the browser-based scraper is expensive; daily is sufficient.
        "task": "apps.sync_pipeline.tasks.refresh_whoscored_cycle_task",
        "schedule": crontab(minute=0, hour=4),
        "options": {"expires": 7200, "queue": "queue_whoscored"},
    },
    "refresh-native-stats-cycle": {
        "task": "apps.sync_pipeline.tasks.refresh_native_stats_cycle_task",
        "schedule": crontab(minute=0, hour="*/2"),
        "options": {"expires": 3600, "queue": "queue_native_stats"},
    },
    "refresh-pro-club-squads": {
        "task": "apps.clubs.tasks.refresh_pro_club_squads_task",
        "schedule": crontab(minute=0, hour="*/6"),
        "options": {"expires": 3600, "queue": "queue_football_data"},
    },
    "refresh-odds-snapshots": {
        "task": "apps.sync_pipeline.tasks.refresh_odds_snapshots_task",
        "schedule": crontab(minute=0, hour="*/6"),
        "options": {"expires": 3600, "queue": "queue_publication"},
    },
    "rebuild-livefootball-publication": {
        "task": "apps.livefootball.tasks.rebuild_livefootball_publication",
        "schedule": crontab(minute="*/30"),
        "options": {"expires": 1800, "queue": "queue_publication"},
    },
    "rebuild-playerdata-publication": {
        # Heartbeat: runs 45 min after the understat cycle (:30) giving it time to complete.
        # Also fires independently so the surface stays fresh if the trigger chain breaks.
        "task": "apps.playerdata.tasks.rebuild_playerdata_publication_task",
        "schedule": crontab(minute=45, hour="*/6"),
        "options": {"expires": 3600, "queue": "queue_publication"},
    },
    "rebuild-clubs-publication": {
        # Heartbeat: runs 15 min after pro-club-squads (:00) to capture fresh squad data.
        "task": "apps.clubs.tasks.rebuild_club_publication_task",
        "schedule": crontab(minute=15, hour="*/6"),
        "options": {"expires": 3600, "queue": "queue_publication"},
    },
    "rebuild-predictions-publication": {
        # Heartbeat independent of the understat trigger chain.
        "task": "apps.predictions.tasks.rebuild_predictions_publication_task",
        "schedule": crontab(minute=0, hour="*/6"),
        "options": {"expires": 3600, "queue": "queue_publication"},
    },
    "refresh-transfermarkt-dobs": {
        # Weekly: every Monday at 02:00. DOBs don't change; this is a low-priority backfill.
        "task": "apps.sync_pipeline.tasks.refresh_transfermarkt_cycle_task",
        "schedule": crontab(minute=0, hour=2, day_of_week=1),
        "options": {"expires": 7200, "queue": "queue_transfermarkt"},
    },
    "aggregate-sync-health": {
        "task": "apps.sync_pipeline.tasks.aggregate_sync_health_task",
        "schedule": crontab(minute="*/30"),
        "options": {"expires": 1800},
    },
    "compute-odds-accuracy": {
        # Runs 30 min after the fixture sync window (*/15) to ensure results are up to date
        "task": "apps.predictions.tasks.compute_odds_accuracy_task",
        "schedule": crontab(minute=30, hour="*/6"),
        "options": {"expires": 3600, "queue": "queue_publication"},
    },
    "update-community-interest-profiles": {
        "task": "apps.community.tasks.update_user_interest_profiles_task",
        "schedule": crontab(minute=0, hour="*/1"),
        "options": {"expires": 3300, "queue": "queue_publication"},
    },
    "ingest-rss-feeds": {
        # Pull fresh articles from RSS feeds every hour.
        "task": "apps.articles.tasks.ingest_rss_feeds_task",
        "schedule": crontab(minute=0, hour="*/1"),
        "options": {"expires": 3300},
    },
    "generate-article-recommendations": {
        # Rebuild per-user article recommendations once per day at 05:00 UTC.
        "task": "apps.articles.tasks.generate_recommendations_task",
        "schedule": crontab(minute=0, hour=5),
        "options": {"expires": 7200},
    },
}

# ---------------------------------------------------------------------------
# Data pipeline provider policy
# ---------------------------------------------------------------------------

PROVIDER_QUEUES = {
    'football_data': 'queue_football_data',
    'understat':     'queue_understat',
    'sofascore':     'queue_sofascore',
    'whoscored':     'queue_whoscored',
    'transfermarkt': 'queue_transfermarkt',
    'native_stats':  'queue_native_stats',
    'publication':   'queue_publication',
}

FOOTBALL_DATA_DAILY_REQUEST_LIMIT = config(
    'FOOTBALL_DATA_DAILY_REQUEST_LIMIT', default=100, cast=int
)

SOFASCORE_SESSION_TOKEN = config('SOFASCORE_SESSION_TOKEN', default=None)

PIPELINE_DEGRADED_THRESHOLD = config(
    'PIPELINE_DEGRADED_THRESHOLD', default=3, cast=int
)

FRESHNESS_SLA_SECONDS = {
    'livefootball': 1800,
    'predictions':  21600,
    'playerdata':   21600,
    'clubs':        21600,
}

THE_ODDS_API_KEY = config('THE_ODDS_API_KEY', default='')
ODDS_API_ENABLED = config('ODDS_API_ENABLED', default=False, cast=bool)
ODDS_API_DAILY_REQUEST_LIMIT = config('ODDS_API_DAILY_REQUEST_LIMIT', default=15, cast=int)
ODDS_SNAPSHOT_LOOKAHEAD_HOURS = config(
    'ODDS_SNAPSHOT_LOOKAHEAD_HOURS',
    default=72,
    cast=int,
)
ODDS_SNAPSHOT_MAX_FIXTURES_PER_RUN = config(
    'ODDS_SNAPSHOT_MAX_FIXTURES_PER_RUN',
    default=10,
    cast=int,
)
ODDS_SNAPSHOT_BOOKMAKERS = config(
    'ODDS_SNAPSHOT_BOOKMAKERS',
    default='bet365,paddypower',
)
ODDS_SNAPSHOT_SPORT_KEYS = config(
    'ODDS_SNAPSHOT_SPORT_KEYS',
    default='',
)

USE_PUBLISHED_LIVEFOOTBALL_SNAPSHOT = config(
    'USE_PUBLISHED_LIVEFOOTBALL_SNAPSHOT', default=False, cast=bool
)
USE_PUBLISHED_PREDICTIONS_SNAPSHOT = config(
    'USE_PUBLISHED_PREDICTIONS_SNAPSHOT', default=False, cast=bool
)

USE_PUBLISHED_PLAYERDATA = config(
    'USE_PUBLISHED_PLAYERDATA', default=False, cast=bool
)

USE_PUBLISHED_CLUBS = config('USE_PUBLISHED_CLUBS', default=False, cast=bool)

LOG_LEVEL_PIPELINE = config('LOG_LEVEL_PIPELINE', default='WARNING')

# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"