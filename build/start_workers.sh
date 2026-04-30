#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# start_workers.sh — development worker startup
# Run from the repo root (same directory as this script).
# Usage:  ./start_workers.sh
# Stop:   ./start_workers.sh stop   OR   kill $(cat .worker_pids)
# Start everything
#./start_workers.sh

# Stop everything
#./start_workers.sh stop

# Watch all logs live
#tail -f logs/workers/*.lo
# ---------------------------------------------------------------------------

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
PID_FILE="$SCRIPT_DIR/.worker_pids"
LOG_DIR="$SCRIPT_DIR/logs/workers"
STARTUP_SYNC_STAMP="$SCRIPT_DIR/.last_startup_sync"
STARTUP_SYNC_COOLDOWN=1800  # 30 minutes — guards against restart loops

# ── helpers ─────────────────────────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[workers]${NC} $*"; }
warn() { echo -e "${YELLOW}[workers]${NC} $*"; }
die()  { echo -e "${RED}[workers]${NC} $*" >&2; exit 1; }

# ── stop mode ───────────────────────────────────────────────────────────────

if [[ "${1:-}" == "stop" ]]; then
    if [[ -f "$PID_FILE" ]]; then
        log "Stopping all workers..."
        while IFS= read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" && log "  killed PID $pid"
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
        log "Done."
    else
        warn "No .worker_pids file found — nothing to stop."
    fi
    exit 0
fi

# ── pre-flight ───────────────────────────────────────────────────────────────

[[ -f "$BACKEND_DIR/manage.py" ]] || die "manage.py not found at $BACKEND_DIR"
command -v celery >/dev/null 2>&1    || die "celery not found — activate your virtualenv first"

if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    die "Neither python nor python3 found in PATH"
fi

mkdir -p "$LOG_DIR"

# Kill any leftover workers from a previous run
if [[ -f "$PID_FILE" ]]; then
    warn "Found existing .worker_pids — killing stale workers first..."
    while IFS= read -r pid; do
        kill -0 "$pid" 2>/dev/null && kill "$pid" && warn "  killed stale PID $pid" || true
    done < "$PID_FILE"
    rm -f "$PID_FILE"
fi

> "$PID_FILE"   # create/truncate

# ── migrations & checks ──────────────────────────────────────────────────────

log "Running migrations..."
(cd "$BACKEND_DIR" && "$PYTHON_BIN" manage.py migrate --run-syncdb 2>&1) || die "migrate failed"

log "Checking Django system..."
(cd "$BACKEND_DIR" && "$PYTHON_BIN" manage.py check 2>&1) || die "system check failed"

# ── function to launch a background worker ───────────────────────────────────

start_worker() {
    local name="$1"; local queues="$2"; local concurrency="$3"
    local logfile="$LOG_DIR/${name}.log"

    # Include global site-packages for packages like feedparser not in venv
    export PYTHONPATH="${HOME}/.local/lib/python3.10/site-packages:${PYTHONPATH:-}"

    log "  Starting worker: ${name}  queues=[${queues}]  concurrency=${concurrency}"
    touch "$logfile"
    cd "$BACKEND_DIR" && celery -A backend worker \
        -Q "$queues" \
        -c "$concurrency" \
        -l info \
        -n "${name}@%h" \
        --logfile="$logfile" \
        --pidfile="" \
        >> "$logfile" 2>&1 &
    local worker_pid=$!
    cd "$SCRIPT_DIR"
    echo "$worker_pid" >> "$PID_FILE"
    sleep 0.3   # stagger startup to avoid port/db contention
}

# ── launch workers ───────────────────────────────────────────────────────────

log "Starting Celery workers..."

# Football-data.org  — strict rate limit, must be single-threaded
start_worker "worker_football_data"  "queue_football_data"  1

# Understat scraper
start_worker "worker_understat"      "queue_understat"       2

# SofaScore scraper (soccerdata)
start_worker "worker_sofascore"      "queue_sofascore"       2

# WhoScored scraper (soccerdata)
start_worker "worker_whoscored"      "queue_whoscored"       2

# Transfermarkt scraper — low-traffic weekly DOB backfill
start_worker "worker_transfermarkt"  "queue_transfermarkt"   1

# Native stats (internal DB aggregation, fast)
start_worker "worker_native_stats"   "queue_native_stats"    2

# Publication rebuilds (snapshot writes)
start_worker "worker_publication"    "queue_publication"     2

# ── beat scheduler ───────────────────────────────────────────────────────────

log "Starting Celery Beat scheduler..."
BEAT_LOG="$LOG_DIR/beat.log"
touch "$BEAT_LOG"
cd "$BACKEND_DIR" && celery -A backend beat \
    -l info \
    --logfile="$BEAT_LOG" \
    >> "$BEAT_LOG" 2>&1 &
BEAT_PID=$!
cd "$SCRIPT_DIR"
echo "$BEAT_PID" >> "$PID_FILE"

# ── startup data sync (UTC-gated, restart-loop safe) ─────────────────────────

_needs_startup_sync() {
    [[ ! -f "$STARTUP_SYNC_STAMP" ]] && return 0
    local last now elapsed
    last=$(cat "$STARTUP_SYNC_STAMP" 2>/dev/null | tr -d '[:space:]')
    now=$(date -u +%s)
    [[ "$last" =~ ^[0-9]+$ ]] || return 0
    elapsed=$(( now - last ))
    (( elapsed >= STARTUP_SYNC_COOLDOWN ))
}

if _needs_startup_sync; then
    log "Startup data sync — UTC $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    date -u +%s > "$STARTUP_SYNC_STAMP"
    (cd "$BACKEND_DIR" && "$PYTHON_BIN" manage.py fetch_odds 2>&1) \
        && log "  ✓ Odds refreshed" \
        || warn "  ⚠ fetch_odds failed — Beat scheduler will retry on next cycle"
else
    _elapsed=$(( $(date -u +%s) - $(cat "$STARTUP_SYNC_STAMP" 2>/dev/null || echo 0) ))
    warn "Startup sync skipped — last ran ${_elapsed}s ago (cooldown: ${STARTUP_SYNC_COOLDOWN}s)"
fi

# ── bootstrap publications (first-run / post-update) ─────────────────────────

log "Bootstrapping publication snapshots (runs inline, may take a minute)..."

run_bootstrap() {
    local label="$1"; shift
    log "  → $label"
    if ! (cd "$BACKEND_DIR" && "$PYTHON_BIN" manage.py "$@" 2>&1); then
        warn "  ⚠ $label failed — workers will still run, publications will self-heal on next cycle"
    fi
}

run_bootstrap "Livefootball snapshot"    bootstrap_livefootball_snapshot   2>/dev/null || true
run_bootstrap "Playerdata snapshot"      bootstrap_playerdata_snapshot     2>/dev/null || true
run_bootstrap "Clubs snapshot"           bootstrap_clubs_snapshot          2>/dev/null || true
run_bootstrap "Predictions snapshot"     bootstrap_predictions_snapshot    2>/dev/null || true

# ── done ─────────────────────────────────────────────────────────────────────

log ""
log "All workers running. PIDs saved to .worker_pids"
log ""
log "  Log files:  $LOG_DIR/"
log "  Beat log:   $BEAT_LOG"
log ""
log "  To stop everything:  ./start_workers.sh stop"
log "  To tail all logs:    tail -f $LOG_DIR/*.log"
log ""
log "Sources covered:"
log "  ✓ Football-data.org  (fixtures, metadata, scorers/squads)  — every 15 min"
log "  ✓ Understat          (xG, player stats, team summaries)    — every 6h"
log "  ✓ SofaScore          (match stats, players, teams)         — every 3h"
log "  ✓ WhoScored          (match events, player ratings)        — every 3h"
log "  ✓ Transfermarkt      (player DOBs)                         — weekly Mon"
log "  ✓ Native Stats       (homepage overview)                   — every 2h"
log "  ✓ The Odds API       (upcoming fixture odds)               — every 6h"
log "  ✓ Publications       (livefootball / playerdata / clubs / predictions)"
log ""
