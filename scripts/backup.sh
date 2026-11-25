#!/bin/sh

set -eu
umask 077

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ENV_FILE=${ENV_FILE:-"$PROJECT_ROOT/.env.staging"}
COMPOSE_FILE=${COMPOSE_FILE:-"$PROJECT_ROOT/docker-compose.staging.yml"}
BACKUP_ROOT=${BACKUP_ROOT:-"$PROJECT_ROOT/backups"}
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"

if [ ! -f "$ENV_FILE" ]; then
    echo "Environment file not found: $ENV_FILE" >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"

compose() {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

echo "Backing up PostgreSQL..."
compose exec -T db pg_dump -U postgres -d xggaffer --format=custom \
    > "$BACKUP_DIR/postgres.dump"

echo "Backing up uploaded media..."
compose exec -T backend tar -C /app/media -czf - . \
    > "$BACKUP_DIR/media.tar.gz"

if [ "${INCLUDE_DATA:-false}" = "true" ]; then
    echo "Backing up prediction data..."
    compose exec -T backend tar -C /app/data -czf - . \
        > "$BACKUP_DIR/data.tar.gz"
fi

(
    cd "$BACKUP_DIR"
    sha256sum ./* > SHA256SUMS
)

echo "Backup completed: $BACKUP_DIR"
