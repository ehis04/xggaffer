# xgGaffer Model Handoff (Colab)

This package contains code, model artefacts, and sample 2024 data exports for the three engines:

- Engine 1: Elo
- Engine 2: Match Outcome
- Engine 3: Scoreline

## Contents

- `code/backend/apps/predictions/ml/engines/`: Elo engine and Elo reporting scripts
- `code/backend/apps/predictions/ml/models/match_outcome/`: Match Outcome model and reporting scripts
- `code/backend/apps/predictions/ml/models/scoreline/`: Scoreline model and reporting scripts
- `data/processed/`: JSON/TXT reports and CSV exports (2024 examples)
- `data/models/`: latest model artefacts (`.joblib`)
- `requirements.txt`: Python dependencies used in the backend

## Quick start in Google Colab

1. Upload and unzip this package in Colab.
2. Open a terminal cell and install dependencies:

```bash
pip install -r requirements.txt
```

3. Add the unpacked package root to Python path in your notebook:

```python
import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))
```

4. Load exported CSV files directly for analysis:

```python
import pandas as pd

df_elo = pd.read_csv('data/processed/elo_wdl_predictions_2024.csv')
df_mo = pd.read_csv('data/processed/match_outcome_predictions_2024.csv')
df_sc = pd.read_csv('data/processed/scoreline_predictions_2024.csv')
```

## Notes

- The CSV exports are one-year examples (2024) to keep runtime and file size manageable.
- `match_outcome_features_2024.csv` has fewer rows than scoreline/Elo exports because rows without sufficient feature history are dropped.
- The quality reports in `data/processed/` summarise current model performance and calibration.

## Suggested story flow for reviewers

1. Start with `*_quality_report*.txt` for headline model performance.
2. Inspect `*_predictions_2024.csv` for per-match probabilities and predictions.
3. Use `*_features_2024.csv` to understand model inputs.
4. Cross-check with classification/calibration JSON reports for metric details.

## Commands

All commands below are run from inside:

```bash
code/backend/apps/predictions/
```

### Elo rating quality report

```bash
python3 -m ml.engines.rating_quality_report
```

### Elo calibration report

```bash
python3 -m ml.engines.calibration_report
```

### Elo classification report

```bash
python3 -m ml.engines.classification_report
```

### Match Outcome quality report (all 3 models)

```bash
python3 -m ml.models.match_outcome.model_quality_report --model-types logistic_regression random_forest gradient_boosting --test-seasons 2024
```

### Match Outcome calibration report

```bash
python3 -m ml.models.match_outcome.calibration_report --test-seasons 2024
```

### Match Outcome classification report

```bash
python3 -m ml.models.match_outcome.classification_report --test-seasons 2024
```

### Scoreline quality report

```bash
python3 -m ml.models.scoreline.model_quality_report --test-seasons 2024
```

### Scoreline calibration report

```bash
python3 -m ml.models.scoreline.calibration_report --test-seasons 2024
```

### Scoreline classification report

```bash
python3 -m ml.models.scoreline.classification_report --test-seasons 2024
```

## Output

All outputs are saved to:

```bash
data/processed/
```
