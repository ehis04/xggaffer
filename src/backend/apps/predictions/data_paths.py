"""Shared filesystem locations for prediction datasets and model artefacts."""

from __future__ import annotations

import os
from pathlib import Path


def data_root_from_environment() -> Path:
    """Return the configured data root, or the repository data directory."""
    configured = os.environ.get("XGGAFFER_DATA_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()

    for parent in Path(__file__).resolve().parents:
        if (parent / "manage.py").is_file():
            # Source checkout: <repo>/src/backend/manage.py. Container: /app/manage.py.
            if parent.name == "backend" and parent.parent.name == "src":
                return parent.parent.parent / "data"
            return parent / "data"

    raise RuntimeError("Could not locate the prediction data directory; set XGGAFFER_DATA_DIR")


DATA_ROOT = data_root_from_environment()
PROCESSED_DATA_ROOT = DATA_ROOT / "processed"
MODEL_ROOT = DATA_ROOT / "models"
