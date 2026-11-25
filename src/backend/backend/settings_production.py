"""Production settings used by hosted web and worker processes."""

import os

from django.core.exceptions import ImproperlyConfigured

from backend.settings import *  # noqa: F401, F403


def required_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} must be configured in production")
    return value


DEBUG = False
SECRET_KEY = required_environment("SECRET_KEY")
if (
    len(SECRET_KEY) < 50
    or len(set(SECRET_KEY)) < 5
    or SECRET_KEY.startswith("django-insecure-")
):
    raise ImproperlyConfigured("SECRET_KEY must be a long, random production value")
required_environment("DATABASE_URL")
required_environment("REDIS_URL")
SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY

ALLOWED_HOSTS = env_csv(
    "ALLOWED_HOSTS",
    default="xggaffer.site,www.xggaffer.site",
)
CSRF_TRUSTED_ORIGINS = env_csv(
    "CSRF_TRUSTED_ORIGINS",
    default="https://xggaffer.site,https://www.xggaffer.site",
)
CORS_ALLOWED_ORIGINS = env_csv(
    "CORS_ALLOWED_ORIGINS",
    default="https://xggaffer.site,https://www.xggaffer.site",
)
CORS_ALLOW_ALL_ORIGINS = False

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
AUTH_COOKIE_SECURE = True

if BYPASS_PERMISSIONS:
    raise ImproperlyConfigured("BYPASS_PERMISSIONS cannot be enabled in production")

REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = [
    "rest_framework.throttling.AnonRateThrottle",
    "rest_framework.throttling.UserRateThrottle",
]
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "anon": os.environ.get("API_ANON_RATE", "60/min"),
    "user": os.environ.get("API_USER_RATE", "600/min"),
}

# Model and dataset loading remains lazy so each management command and worker
# process does not start a duplicate pre-warm thread.
PREDICTIONS_DISABLE_PREWARM = True

DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("LOG_LEVEL", "INFO"),
    },
}
