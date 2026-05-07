# Data Access and ML Commands

The full `src/data` folder is not stored in GitLab because of the storage limit. The project repository contains the code and
documentation; the large data archive is supplied separately.

## Restore Data

Download `xggaffer-data.tar.gz` from the submission data link: https://drive.google.com/drive/folders/1XK0tLxIhEzus76kAUxULSlJA4N0FW7pz?usp=drive_link, 
place it in the repository root, then extract it:

```bash
tar -xzf xggaffer-data.tar.gz
du -sh src/data
```

Expected restored size:

```text
3.6G src/data
```

The archive contains `src/data`, so extraction from the repository root restores
the expected paths automatically.

## Environment Setup

```bash
cd src
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cd backend
export PYTHONPATH=.
export DEBUG=True
python3 manage.py migrate
python3 manage.py check
```

If your local `.env` already sets `DEBUG=True` or `DEBUG=False`, the explicit
`export DEBUG=True` command is optional.

## Data Sanity Checks

From the repository root:

```bash
du -sh src/data
test -f src/data/processed/match_outcome_features.csv
test -f src/data/processed/match_outcome_features_with_odds.csv
test -f src/data/processed/elo_ratings.csv
test -f src/data/processed/pass_events.csv
test -f src/data/processed/team_zone_profiles.csv
test -f src/data/processed/lineup_features.csv
test -f src/data/processed/risk_dataset.csv
test -f src/data/processed/survival_dataset.csv
test -f src/data/processed/player_id_mapping.csv
test -f src/data/processed/matches/merged/all_leagues_all_seasons_matches_merged.csv
test -f src/data/processed/players/merged/all_leagues_all_seasons_players_merged.csv
test -f src/data/raw/understat/merged/all_leagues_all_seasons_matches.csv
find src/data/models -maxdepth 1 -name "*.joblib" | sort
```

## Run Tests

From `src/backend` with the virtual environment active:

```bash
export PYTHONPATH=.
export DEBUG=True

python3 manage.py check
DJANGO_SETTINGS_MODULE=backend.settings_test python3 -m pytest -p no:rerunfailures apps/predictions/ml/models/simulation/tests -q
DJANGO_SETTINGS_MODULE=backend.settings_test python3 -m pytest -p no:rerunfailures apps/predictions/ml/models/scoreline/tests -q
DJANGO_SETTINGS_MODULE=backend.settings_test python3 -m pytest -p no:rerunfailures apps/predictions/ml/models/availability/tests -q
DJANGO_SETTINGS_MODULE=backend.settings_test python3 -m pytest -p no:rerunfailures apps/predictions/ml/models/tactical/tests -q
DJANGO_SETTINGS_MODULE=backend.settings_test python3 -m pytest -p no:rerunfailures apps/predictions/ml/models/lineup/tests -q
DJANGO_SETTINGS_MODULE=backend.settings_test python3 -m pytest -p no:rerunfailures apps/predictions/ml/models/match_outcome/test_ml.py -q
```

The `-p no:rerunfailures` flag avoids a local socket used by the rerun plugin
in restricted environments.

## Train Models From Existing Data

From `src/backend` with the virtual environment active:

```bash
export PYTHONPATH=.
export DEBUG=True

python3 apps/predictions/ml/models/match_outcome/train.py --model logistic_regression
python3 apps/predictions/ml/models/match_outcome/train.py --model random_forest
python3 apps/predictions/ml/models/match_outcome/train.py --model gradient_boosting

python3 apps/predictions/ml/models/scoreline/train.py
python3 -m apps.predictions.ml.models.lineup.train
python3 apps/predictions/ml/models/availability/train_risk.py
python3 apps/predictions/ml/models/availability/train_survival.py
python3 -m apps.predictions.ml.engines.compute_elo
python3 -m apps.predictions.ml.models.tactical.train_clustering
python3 -m apps.predictions.ml.models.tactical.train_pass_model
```

The scoreline train script does not implement `--help`; running it starts
training.

## Populate Database Snapshots

From `src/backend` with the virtual environment active:

```bash
export PYTHONPATH=.
export DEBUG=True

python3 manage.py bootstrap_predictions_snapshot
python3 manage.py bootstrap_playerdata_snapshot
python3 manage.py bootstrap_clubs_snapshot
python3 manage.py bootstrap_livefootball_snapshot
python3 manage.py populate_simulation_results
```

These commands require the Django database and environment variables to be
configured.

## Collect More Data

Some collectors call external providers and may require network access, valid
API keys, cookies, or provider availability. Run these commands from the
repository root with the virtual environment active.

Collect Understat data:

```bash
source src/.venv/bin/activate
python3 -c 'import runpy, sys; sys.path.append("src/backend/apps/predictions"); sys.argv=["collect_all.py", "--sources", "understat", "--datasets", "matches", "players", "teams", "--leagues", "EPL", "La_Liga", "Bundesliga", "Serie_A", "Ligue_1", "--seasons", "2025"]; runpy.run_module("data_collection.scripts.collect_all", run_name="__main__")'
```

Collect SofaScore data:

```bash
source src/.venv/bin/activate
python3 -c 'import runpy, sys; sys.path.append("src/backend/apps/predictions"); sys.argv=["collect_all.py", "--sources", "sofascore", "--datasets", "matches", "players", "teams", "--leagues", "EPL", "La_Liga", "Bundesliga", "Serie_A", "Ligue_1", "--seasons", "2025"]; runpy.run_module("data_collection.scripts.collect_all", run_name="__main__")'
```

Collect WhoScored data:

```bash
source src/.venv/bin/activate
python3 -c 'import runpy, sys; sys.path.append("src/backend/apps/predictions"); sys.argv=["collect_all.py", "--sources", "whoscored", "--datasets", "matches", "teams", "--leagues", "EPL", "La_Liga", "Bundesliga", "Serie_A", "Ligue_1", "--seasons", "2025"]; runpy.run_module("data_collection.scripts.collect_all", run_name="__main__")'
```

Rebuild merged raw and processed CSV views:

```bash
source src/.venv/bin/activate
python3 -c 'import runpy, sys; sys.path.append("src/backend/apps/predictions"); sys.argv=["export_merged_views.py", "--layers", "raw", "processed", "--sources", "understat", "sofascore", "whoscored", "--datasets", "matches", "players", "teams", "team_summaries"]; runpy.run_module("data_collection.scripts.export_merged_views", run_name="__main__")'
```

Odds and supporting Django commands, from `src/backend`:

```bash
export PYTHONPATH=.
export DEBUG=True

python3 manage.py fetch_odds
python3 manage.py backfill_historical_odds
python3 manage.py import_fdcouk_odds
python3 manage.py seed_odds_benchmark
python3 manage.py compute_odds_accuracy
python3 manage.py export_merged_views
```

## Rebuild Everything

The legacy convenience script is:

```bash
cd src
source .venv/bin/activate
./retrain.sh --skip-sync
```

Use `--skip-sync` when the restored archive already contains the CSV files and
you only want to retrain models from existing data.
