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
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'apps.laws',
    'apps.articles',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'apps.teamsheets',
    'apps.users',
    'apps.predictions',
    'apps.community',
    'apps.coaching.coachProfile',
    'apps.coaching',
    'apps.players',
    'apps.players.playerProfile',
    'apps.clubs',
    'apps.tactics',
    'apps.referee',
    'apps.referee.progressTracking',
    'apps.referee.learningTools',
    'apps.referee.Laws',
    'apps.referee.profile',
    'apps.playerdata',
    'apps.livefootball',
    'corsheaders',
    'cloudinary',
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
    "scrape-all-leagues-daily": {
        "task": "apps.predictions.tasks.scrape_all_leagues",
        "schedule": crontab(hour=2, minute=0),
        "options": {
            "expires": 3600,
        },
    },
    "scrape-premier-league-matchday": {
        "task": "apps.predictions.tasks.scrape_specific_league",
        "schedule": crontab(hour="*/3", day_of_week="sat,sun"),
        "args": ("EPL", "2024"),
        "options": {
            "expires": 1800,
        },
    },
    "purge-expired-trash-daily": {
        "task": "apps.clubs.tasks.purge_expired_trash",
        "schedule": crontab(hour=3, minute=15),
        "options": {
            "expires": 3600,
        },
    },
}


# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"