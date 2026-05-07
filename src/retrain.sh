#!/usr/bin/env bash
# retrain.sh — Sync 2025/26 data from all sources and retrain all models.
#
# Usage:
#   ./retrain.sh              # Full sync + retrain
#   ./retrain.sh --skip-sync  # Skip data sync, retrain on whatever CSVs exist
#   ./retrain.sh --skip-train # Sync only, don't retrain
#
# Run from the repo root (same directory as this script).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
PREDICTIONS_PKG_DIR="$BACKEND_DIR/apps/predictions"

SKIP_SYNC=false
SKIP_TRAIN=false

for arg in "$@"; do
    case $arg in
        --skip-sync)  SKIP_SYNC=true  ;;
        --skip-train) SKIP_TRAIN=true ;;
    esac
done

LEAGUES=(EPL La_Liga Bundesliga Serie_A Ligue_1)
SEASON=2025

log() { echo "[$(date '+%H:%M:%S')] $*"; }
separator() { echo ""; echo "================================================================"; echo "$*"; echo "================================================================"; }
run_data_collection_script() {
    local module_name="$1"
    shift
    python3 -c 'import runpy, sys; sys.path.append("'"$PREDICTIONS_PKG_DIR"'"); sys.argv=["'"$module_name.py"'"] + sys.argv[1:]; runpy.run_module("data_collection.scripts.'"$module_name"'", run_name="__main__")' "$@"
}

cd "$BACKEND_DIR"

# Activate virtualenv if present
if [ -f "$BACKEND_DIR/.venv/bin/activate" ]; then
    # shellcheck source=/dev/null
    source "$BACKEND_DIR/.venv/bin/activate"
fi

export DJANGO_SETTINGS_MODULE=backend.settings
export PYTHONPATH="$BACKEND_DIR${PYTHONPATH:+:$PYTHONPATH}"

# ---------------------------------------------------------------------------
# Step 1: Sync raw data from all sources into the Django DB
# ---------------------------------------------------------------------------

if [ "$SKIP_SYNC" = false ]; then
    separator "STEP 1: SYNC UNDERSTAT DATA ($SEASON)"

    for league in "${LEAGUES[@]}"; do
        log "Syncing Understat — $league $SEASON"
        python3 manage.py sync_understat_league_season --league-code "$league" --season "$SEASON" || {
            log "WARNING: Understat sync failed for $league $SEASON — continuing"
        }
    done

    # ---------------------------------------------------------------------------
    # Step 2: Run the data collection pipeline to produce 2025 CSV files
    # ---------------------------------------------------------------------------

    separator "STEP 2: COLLECT SOURCE DATASETS ($SEASON) → CSV FILES"

    log "Collecting Understat matches, players, teams for season $SEASON..."
    run_data_collection_script collect_all \
        --sources understat \
        --datasets matches players teams \
        --leagues "${LEAGUES[@]}" \
        --seasons "$SEASON" \
        || { log "WARNING: collect_all (understat) exited with errors — continuing"; }

    log "Collecting SofaScore matches, players, teams for season $SEASON..."
    run_data_collection_script collect_all \
        --sources sofascore \
        --datasets matches players teams \
        --leagues "${LEAGUES[@]}" \
        --seasons "$SEASON" \
        || { log "WARNING: collect_all (sofascore) exited with errors — continuing"; }

    log "Collecting WhoScored matches and teams for season $SEASON..."
    run_data_collection_script collect_all \
        --sources whoscored \
        --datasets matches teams \
        --leagues "${LEAGUES[@]}" \
        --seasons "$SEASON" \
        || { log "WARNING: collect_all (whoscored matches/teams) exited with errors — continuing"; }

    log "Collecting WhoScored player events per league (one at a time to avoid OOM)..."
    for league in "${LEAGUES[@]}"; do
        log "  WhoScored players — $league $SEASON"
        run_data_collection_script collect_all \
            --sources whoscored \
            --datasets players \
            --leagues "$league" \
            --seasons "$SEASON" \
            || { log "WARNING: WhoScored players failed for $league $SEASON — continuing"; }
    done

    separator "STEP 2B: REBUILD MERGED DATA VIEWS"

    log "Exporting merged raw and processed CSV views for model/runtime data..."
    run_data_collection_script export_merged_views \
        --layers raw processed \
        --sources understat sofascore whoscored \
        --datasets matches players teams team_summaries \
        || { log "WARNING: export_merged_views exited with errors — continuing"; }

else
    log "Skipping data sync (--skip-sync passed)"
fi

# ---------------------------------------------------------------------------
# Step 3: Retrain all models
# ---------------------------------------------------------------------------

if [ "$SKIP_TRAIN" = false ]; then
    separator "STEP 3: RETRAIN MODELS"

    log "Training match outcome model (logistic regression)..."
    python3 apps/predictions/ml/models/match_outcome/train.py \
        --model logistic_regression \
        2>&1 | tee /tmp/train_match_outcome.log
    log "Match outcome model trained. Log: /tmp/train_match_outcome.log"

    log "Training scoreline model (Poisson GLM)..."
    python3 apps/predictions/ml/models/scoreline/train.py \
        2>&1 | tee /tmp/train_scoreline.log
    log "Scoreline model trained. Log: /tmp/train_scoreline.log"

    log "Training lineup prediction model..."
    python3 -m apps.predictions.ml.models.lineup.train \
        2>&1 | tee /tmp/train_lineup.log
    log "Lineup model trained. Log: /tmp/train_lineup.log"

    log "Training availability (injury risk) model..."
    python3 apps/predictions/ml/models/availability/train_risk.py \
        2>&1 | tee /tmp/train_availability.log
    log "Availability model trained. Log: /tmp/train_availability.log"

    log "Recomputing Elo ratings from match history..."
    python3 -m apps.predictions.ml.engines.compute_elo \
        2>&1 | tee /tmp/train_elo.log
    log "Elo ratings recomputed. Log: /tmp/train_elo.log"

    log "Training tactical clustering model..."
    python3 -m apps.predictions.ml.models.tactical.train_clustering \
        2>&1 | tee /tmp/train_tactical_clustering.log || {
        log "WARNING: Tactical clustering failed (WhoScored data required) — continuing"
    }

    log "Training tactical pass model..."
    python3 -m apps.predictions.ml.models.tactical.train_pass_model \
        2>&1 | tee /tmp/train_tactical_pass.log || {
        log "WARNING: Tactical pass model failed (WhoScored data required) — continuing"
    }

    # ---------------------------------------------------------------------------
    # Step 4: Rebuild all publication snapshots so the API serves fresh data
    # ---------------------------------------------------------------------------

    separator "STEP 4: REBUILD PUBLICATION SNAPSHOTS"

    log "Rebuilding predictions snapshot..."
    python3 manage.py bootstrap_predictions_snapshot

    log "Rebuilding playerdata snapshot..."
    python3 manage.py bootstrap_playerdata_snapshot

    log "Rebuilding clubs snapshot..."
    python3 manage.py bootstrap_clubs_snapshot

    log "Rebuilding livefootball snapshot..."
    python3 manage.py bootstrap_livefootball_snapshot

    log "Running season simulations..."
    python3 manage.py populate_simulation_results \
        2>&1 | tee /tmp/populate_simulations.log
    log "Season simulations complete. Log: /tmp/populate_simulations.log"

    separator "DONE"
    log "All models retrained and snapshots rebuilt."
    log "Logs: /tmp/train_*.log /tmp/populate_simulations.log"

else
    log "Skipping model training (--skip-train passed)"
fi
