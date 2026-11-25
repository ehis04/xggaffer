#!/bin/sh

set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ENV_FILE=${1:-${ENV_FILE:-"$PROJECT_ROOT/.env.staging"}}
COMPOSE_FILE=${COMPOSE_FILE:-"$PROJECT_ROOT/docker-compose.staging.yml"}
MIN_FREE_DISK_GB=${MIN_FREE_DISK_GB:-10}
ERRORS=0

fail() {
    echo "FAIL $*" >&2
    ERRORS=$((ERRORS + 1))
}

pass() {
    echo "PASS $*"
}

env_value() {
    key=$1
    sed -n "s/^${key}=//p" "$ENV_FILE" | tail -n 1 | tr -d '\r'
}

if ! command -v docker >/dev/null 2>&1; then
    fail "Docker is not installed"
elif ! docker compose version >/dev/null 2>&1; then
    fail "Docker Compose plugin is not installed"
else
    pass "Docker Compose is available"
fi

if [ "${SKIP_CURL_CHECK:-false}" != "true" ]; then
    if ! command -v curl >/dev/null 2>&1; then
        fail "curl is not installed"
    else
        pass "curl is available"
    fi
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "FAIL environment file not found: $ENV_FILE" >&2
    exit 1
fi
pass "environment file exists"

SECRET_KEY=$(env_value SECRET_KEY)
POSTGRES_PASSWORD=$(env_value POSTGRES_PASSWORD)
DOMAIN=$(env_value DOMAIN)
WWW_DOMAIN=$(env_value WWW_DOMAIN)
ALLOWED_HOSTS=$(env_value ALLOWED_HOSTS)
CSRF_TRUSTED_ORIGINS=$(env_value CSRF_TRUSTED_ORIGINS)
CORS_ALLOWED_ORIGINS=$(env_value CORS_ALLOWED_ORIGINS)
DATA_HOST_PATH=$(env_value DATA_HOST_PATH)

if [ "${ALLOW_PLACEHOLDERS:-false}" != "true" ]; then
    case "$SECRET_KEY" in
        ""|replace-*|django-insecure-*) fail "SECRET_KEY is missing or still a placeholder" ;;
        *)
            if [ "${#SECRET_KEY}" -lt 50 ]; then
                fail "SECRET_KEY must contain at least 50 characters"
            else
                pass "SECRET_KEY is configured"
            fi
            ;;
    esac

    case "$POSTGRES_PASSWORD" in
        ""|replace-*) fail "POSTGRES_PASSWORD is missing or still a placeholder" ;;
        *[!A-Za-z0-9._~-]*) fail "POSTGRES_PASSWORD must be URL-safe (letters, numbers, . _ ~ -)" ;;
        *) pass "POSTGRES_PASSWORD is configured" ;;
    esac
else
    pass "secret checks skipped for template validation"
fi

if [ "${ALLOW_PLACEHOLDERS:-false}" != "true" ]; then
    case "$DATA_HOST_PATH" in
        /*)
            if [ -d "$DATA_HOST_PATH" ]; then
                pass "prediction data directory exists"
            else
                fail "prediction data directory does not exist: $DATA_HOST_PATH"
            fi
            ;;
        *) fail "DATA_HOST_PATH must be an absolute host path" ;;
    esac
fi

case "$DOMAIN" in
    ""|*" "*|http://*|https://*) fail "DOMAIN must be a bare hostname" ;;
    *) pass "primary domain is configured" ;;
esac

case "$WWW_DOMAIN" in
    ""|*" "*|http://*|https://*) fail "WWW_DOMAIN must be a bare hostname" ;;
    *) pass "www domain is configured" ;;
esac

case ",$ALLOWED_HOSTS," in
    *",$DOMAIN,"*) pass "ALLOWED_HOSTS contains the primary domain" ;;
    *) fail "ALLOWED_HOSTS does not contain $DOMAIN" ;;
esac

case ",$CSRF_TRUSTED_ORIGINS," in
    *",https://$DOMAIN,"*) pass "CSRF trusted origins contain the primary domain" ;;
    *) fail "CSRF_TRUSTED_ORIGINS does not contain https://$DOMAIN" ;;
esac

case ",$CORS_ALLOWED_ORIGINS," in
    *",https://$DOMAIN,"*) pass "CORS origins contain the primary domain" ;;
    *) fail "CORS_ALLOWED_ORIGINS does not contain https://$DOMAIN" ;;
esac

if docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config --quiet; then
    pass "core Compose configuration is valid"
else
    fail "core Compose configuration is invalid"
fi

if docker compose --profile background --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config --quiet; then
    pass "background Compose profile is valid"
else
    fail "background Compose profile is invalid"
fi

if [ "${SKIP_DISK_CHECK:-false}" != "true" ]; then
    AVAILABLE_KB=$(df -Pk "$PROJECT_ROOT" | awk 'NR == 2 { print $4 }')
    REQUIRED_KB=$((MIN_FREE_DISK_GB * 1024 * 1024))
    if [ "$AVAILABLE_KB" -lt "$REQUIRED_KB" ]; then
        fail "less than ${MIN_FREE_DISK_GB} GB of disk space is available"
    else
        pass "at least ${MIN_FREE_DISK_GB} GB of disk space is available"
    fi
fi

if [ "${CHECK_DNS:-false}" = "true" ]; then
    if getent ahosts "$DOMAIN" >/dev/null 2>&1; then
        pass "$DOMAIN resolves in DNS"
    else
        fail "$DOMAIN does not resolve in DNS"
    fi
    if getent ahosts "$WWW_DOMAIN" >/dev/null 2>&1; then
        pass "$WWW_DOMAIN resolves in DNS"
    else
        fail "$WWW_DOMAIN does not resolve in DNS"
    fi
fi

if [ "$ERRORS" -ne 0 ]; then
    echo "Preflight failed with $ERRORS issue(s)." >&2
    exit 1
fi

echo "Preflight passed."
