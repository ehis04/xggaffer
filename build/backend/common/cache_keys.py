from __future__ import annotations

CACHE_PREFIX = "xggaffer"

CACHE_TTL_OVERVIEW = 300
CACHE_TTL_LEAGUES_META = 3600
CACHE_TTL_EXPECTED_TABLE = 600
CACHE_TTL_COMPARE = 600


def make_cache_key(surface: str, endpoint: str, **params) -> str:
    filtered = {k: v for k, v in params.items() if v is not None}
    if not filtered:
        return f"{CACHE_PREFIX}:{surface}:{endpoint}"
    param_str = "&".join(f"{k}={v}" for k, v in sorted(filtered.items()))
    return f"{CACHE_PREFIX}:{surface}:{endpoint}:{param_str}"


def make_surface_pattern(surface: str) -> str:
    return f"{CACHE_PREFIX}:{surface}:*"