from __future__ import annotations

import random
from contextlib import contextmanager

from django.core.cache import cache
import logging

_logger = logging.getLogger(__name__)

LOCK_TIMEOUT_DEFAULT = 300


def get_lock_key(provider: str, dataset: str, scope: str) -> str:
    return f'sync_lock:{provider}:{dataset}:{scope}'


@contextmanager
def acquire_task_lock(lock_key: str, timeout_seconds: int = LOCK_TIMEOUT_DEFAULT):
    acquired = cache.add(lock_key, '1', timeout=timeout_seconds)
    if not acquired:
        _logger.info('Lock contention on %s — skipping run', lock_key)
        return
    try:
        yield
    finally:
        cache.delete(lock_key)


def exponential_backoff_seconds(
    attempt: int,
    base: float = 2.0,
    jitter: bool = True,
    cap: float = 300.0,
) -> float:
    delay = min(base ** attempt, cap)
    if jitter:
        delay *= (0.5 + random.random() * 0.5)
    return delay


def budget_remaining(requests_used: int, daily_limit: int) -> int:
    return max(0, daily_limit - requests_used)


def is_budget_safe(
    requests_used: int,
    daily_limit: int,
    safety_margin: float = 0.10,
) -> bool:
    threshold = (1.0 - safety_margin) * daily_limit
    return requests_used < threshold