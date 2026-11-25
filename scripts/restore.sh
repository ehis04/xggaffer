#!/bin/sh

set -eu

if [ "$#" -ne 2 ] || [ "$1" != "--confirm" ]; then
    echo "Usage: $0 --confirm /absolute/path/to/backup" >&2
    echo "This replaces the production database and overlays stored files." >&2
    exit 1
fi

BACKUP_DIR=$2
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ENV_FILE=${ENV_FILE:-"$PROJECT_ROOT/.env.staging"}
COMPOSE_FILE=${COMPOSE_FILE:-"$PROJECT_ROOT/docker-compose.staging.yml"}

if [ ! -d "$BACKUP_DIR" ] || [ ! -f "$BACKUP_DIR/postgres.dump" ]; then
    echo "Invalid backup directory: $BACKUP_DIR" >&2
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "Environment file not found: $ENV_FILE" >&2
    exit 1
fi

(
    cd "$BACKUP_DIR"
    sha256sum -c SHA256SUMS
)

compose() {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

echo "Stopping application processes..."
compose stop backend celery_worker celery_beat 2>/dev/null || compose stop backend

echo "Restoring PostgreSQL..."
compose exec -T db pg_restore -U postgres -d xggaffer \
    --clean --if-exists --no-owner --no-privileges \
    < "$BACKUP_DIR/postgres.dump"

if [ -f "$BACKUP_DIR/media.tar.gz" ]; then
    echo "Restoring uploaded media..."
    compose run --rm --no-deps -T backend tar -C /app/media -xzf - \
        < "$BACKUP_DIR/media.tar.gz"
fi

if [ -f "$BACKUP_DIR/data.tar.gz" ]; then
    echo "Restoring prediction data..."
    compose run --rm --no-deps -T backend tar -C /app/data -xzf - \
        < "$BACKUP_DIR/data.tar.gz"
fi

echo "Starting the core application..."
compose up -d
echo "Restore completed. Run scripts/smoke-test.sh to verify the deployment."
