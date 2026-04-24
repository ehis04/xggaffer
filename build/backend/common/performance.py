from __future__ import annotations

import hashlib
import logging
import time
from time import perf_counter

from django.conf import settings

PERF_LOGGER_NAME = "xggaffer.performance"
_perf_logger = logging.getLogger(PERF_LOGGER_NAME)


def _is_enabled() -> bool:
    return getattr(settings, "ENABLE_PERFORMANCE_LOGGING", False)


def _hash_params(params: dict | None) -> str:
    if not params:
        return "none"
    raw = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return hashlib.md5(raw.encode()).hexdigest()


class RequestTimer:
    def __init__(
        self,
        *,
        endpoint: str,
        method: str,
        params: dict | None = None,
        status_code: int = 200,
        snapshot_version: str = "none",
    ) -> None:
        self.endpoint = endpoint
        self.method = method
        self.params_hash = _hash_params(params)
        self.status_code = status_code
        self.snapshot_version = snapshot_version
        self._start: float = 0.0

    def __enter__(self) -> "RequestTimer":
        self._start = perf_counter()
        return self

    def __exit__(self, *_) -> None:
        if not _is_enabled():
            return
        duration_ms = round((perf_counter() - self._start) * 1000, 2)
        _perf_logger.info({
            "endpoint": self.endpoint,
            "method": self.method,
            "params_hash": self.params_hash,
            "duration_ms": duration_ms,
            "cache_status": "miss",
            "status_code": self.status_code,
            "snapshot_version": self.snapshot_version,
        })


def time_view(*, endpoint: str):
    import functools

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(self_view, request, *args, **kwargs):
            with RequestTimer(
                endpoint=endpoint,
                method=request.method,
                params=dict(request.query_params),
            ) as timer:
                response = fn(self_view, request, *args, **kwargs)
                timer.status_code = response.status_code
                return response
        return wrapper
    return decorator