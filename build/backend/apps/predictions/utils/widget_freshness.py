from __future__ import annotations

import os
from pathlib import Path

from common.freshness import FreshnessPayload, compute_freshness

ELO_SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "processed"
    / "elo_ratings.csv"
)

STALE_THRESHOLD_HOURS = 24
DEGRADED_THRESHOLD_HOURS = 48

ENGINE_DEPENDENCIES: dict[str, list[str]] = {
    "elo":          [],
    "outcome":      ["elo"],
    "score":        ["elo"],
    "simulation":   ["elo", "score"],
    "availability": ["elo"],
    "tactical":     [],
    "lineup":       ["elo", "availability"],
}


def get_elo_snapshot_age_hours() -> float | None:
    try:
        mtime = os.path.getmtime(ELO_SNAPSHOT_PATH)
    except OSError:
        return None
    import time
    return (time.time() - mtime) / 3600


def _is_engine_stale(engine_key: str) -> bool:
    if engine_key == "elo":
        age = get_elo_snapshot_age_hours()
        if age is None:
            return True
        return age > STALE_THRESHOLD_HOURS
    return False


def get_engine_widget_freshness(engine_key: str) -> dict:
    elo_age = get_elo_snapshot_age_hours()
    own_stale = _is_engine_stale(engine_key)

    if elo_age is not None:
        import datetime
        import time
        snapshot_dt = datetime.datetime.utcfromtimestamp(
            time.time() - elo_age * 3600
        ).isoformat()
    else:
        snapshot_dt = None

    cascade_degraded = False
    cascade_reason = None

    for dep in ENGINE_DEPENDENCIES.get(engine_key, []):
        if _is_engine_stale(dep):
            cascade_degraded = True
            cascade_reason = dep
            break

    return {
        "snapshot_published_at": snapshot_dt,
        "is_stale": own_stale or cascade_degraded,
        "stale_reason": "sla_exceeded" if own_stale else None,
        "cascade_degraded": cascade_degraded,
        "cascade_reason": cascade_reason,
    }