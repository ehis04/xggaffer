"""
Backend settings.
Django configuration, authentication, storage, 3rd-party integrations, and scheduled background tasks defined 
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

import cloudinary
import dj_database_url
from celery.schedules import crontab
from decouple import Csv, config

# ---------------------------------------------------------------------------
# Base paths and Python path setup
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

# Clean imports for prediction apps local ML modules
PREDICTIONS_APP_PATH = str(BASE_DIR / "apps" / "predictions")
if PREDICTIONS_APP_PATH not in sys.path:
    sys.path.append(PREDICTIONS_APP_PATH)


def env_csv(name, default=""):
    return config(name, default=default, cast=Csv())

# ---------------------------------------------------------------------------
# Core environment and security settings
# ---------------------------------------------------------------------------

SECRET_KEY = config("SECRET_KEY", default="LOCAL_DEV_KEY")
DEBUG = config("DEBUG", default=True, cast=bool)

if not DEBUG and SECRET_KEY == "LOCAL_DEV_KEY":
    raise RuntimeError("SECRET_KEY must be set when DEBUG=False")

ALLOWED_HOSTS = env_csv(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1,testserver",
)

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

# Per-user limits for created items (active, not trashed)
CLUB_CREATE_LIMIT_PER_USER = config(
    "CLUB_CREATE_LIMIT_PER_USER",
    default=10,
    cast=int,
)
TEAMSHEET_CREATE_LIMIT_PER_USER = config(
    "TEAMSHEET_CREATE_LIMIT_PER_USER",
    default=10,
    cast=int,
)
TACTICS_BOARD_CREATE_LIMIT_PER_USER = config(
    "TACTICS_BOARD_CREATE_LIMIT_PER_USER",
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
    "apps.training",
    "apps.playerdata",
    "apps.livefootball",
    "apps.sync_pipeline.apps.SyncPipelineConfig",
    "common",
    'apps.internal',
    "apps.referee",
    "apps.referee.progressTracking",
    "apps.referee.learningTools",
    "apps.referee.Laws",
    "apps.referee.profile",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "backend.middleware.RequestIdMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

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

DATABASE_URL = config("DATABASE_URL", default="")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="xggaffer"),
            "USER": config("DB_USER", default="postgres"),
            "PASSWORD": config("DB_PASSWORD", default=""),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
        }
    }

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CACHE_REDIS_URL = config("CACHE_REDIS_URL", default="redis://localhost:6379/1")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": CACHE_REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
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

STATIC_URL = config("STATIC_URL", default="/static/")
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = config("MEDIA_URL", default="/media/")
MEDIA_ROOT = BASE_DIR / "media"


# ---------------------------------------------------------------------------
# Cloudinary configuration
# ---------------------------------------------------------------------------

CLOUDINARY_CLOUD_NAME = config("CLOUDINARY_CLOUD_NAME", default="")
CLOUDINARY_API_KEY = config("CLOUDINARY_API_KEY", default="")
CLOUDINARY_API_SECRET = config("CLOUDINARY_API_SECRET", default="")

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True,
    )

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
# CSRF token must be readable by frontend JavaScript so it can be sent with requests.

LOCAL_FRONTEND_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=False, cast=bool)

CORS_ALLOWED_ORIGINS = env_csv(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://localhost:8000,http://localhost:5173,http://127.0.0.1:5173",
)

CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = env_csv(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:3000,http://localhost:8000,http://localhost:5173,http://127.0.0.1:5173",
)

CSRF_COOKIE_SAMESITE = config("CSRF_COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=False, cast=bool)
CSRF_COOKIE_HTTPONLY = config("CSRF_COOKIE_HTTPONLY", default=False, cast=bool)


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

SESSION_COOKIE_SAMESITE = config("SESSION_COOKIE_SAMESITE", default="Lax")
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=False, cast=bool)
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
AUTH_COOKIE_SECURE = config("AUTH_COOKIE_SECURE", default=SESSION_COOKIE_SECURE, cast=bool)
AUTH_COOKIE_HTTP_ONLY = True
AUTH_COOKIE_PATH = "/"
AUTH_COOKIE_SAMESITE = config("AUTH_COOKIE_SAMESITE", default="Lax")

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

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_TIMEZONE = config("CELERY_TIMEZONE", default="UTC")

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
    "sync-pro-club-injuries": {
        # Twice daily: 06:30 and 18:30 UTC — after squad syncs (:00) so fresh squad data
        # is available, but infrequent enough to avoid hammering Transfermarkt.
        "task": "apps.clubs.tasks.sync_pro_club_injuries_task",
        "schedule": crontab(minute=30, hour="6,18"),
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
        "options": {"expires": 3300, "queue": "queue_publication"},
    },
    "generate-article-recommendations": {
        # Rebuild per-user article recommendations once per day at 05:00 UTC.
        "task": "apps.articles.tasks.generate_recommendations_task",
        "schedule": crontab(minute=0, hour=5),
        "options": {"expires": 7200, "queue": "queue_publication"},
    },
    "resolve-prediction-results": {
        # Scan unresolved PredictionRecords and write actual outcomes once fixtures are final.
        "task": "apps.predictions.tasks.resolve_prediction_results",
        "schedule": crontab(minute=0, hour="*/1"),
        "options": {"expires": 3300, "queue": "queue_publication"},
    },
    "refresh-elo-ratings": {
        # Recompute ELO from full match history daily, after the overnight Understat sync (00:30)
        # has had time to complete. Writes elo_ratings.csv and syncs EloRating/CurrentEloRating.
        "task": "apps.predictions.tasks.refresh_elo_ratings_task",
        "schedule": crontab(minute=30, hour=5),
        "options": {"expires": 7200, "queue": "queue_publication"},
    },
}

ENABLE_CELERY_BEAT_SCHEDULE = config(
    "ENABLE_CELERY_BEAT_SCHEDULE",
    default=True,
    cast=bool,
)

if not ENABLE_CELERY_BEAT_SCHEDULE:
    CELERY_BEAT_SCHEDULE = {}

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

# ---------------------------------------------------------------------------
# Deployment security settings
# ---------------------------------------------------------------------------

SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)

SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=False,
    cast=bool,
)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=False, cast=bool)

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
