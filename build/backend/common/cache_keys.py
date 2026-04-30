from __future__ import annotations

CACHE_PREFIX = "xggaffer"

CACHE_TTL_OVERVIEW = 300
CACHE_TTL_LEAGUES_META = 3600
CACHE_TTL_EXPECTED_TABLE = 600
CACHE_TTL_COMPARE = 600
CACHE_TTL_MODEL_INFO = 3600
CACHE_TTL_TEAMS = 3600
CACHE_TTL_ODDS_FIXTURES = 300
CACHE_TTL_ODDS_TEAMS = 3600
CACHE_TTL_CHAT = 3600

# Keep cache surface names in one place for API and command parity.
KNOWN_CACHE_SURFACES = ("livefootball", "predictions", "odds", "chat")

def clear_surface_cache(surface: str) -> int:
    from django.core.cache import cache
    pattern = make_surface_pattern(surface)
    try:
        deleted = cache.delete_pattern(pattern)
        return deleted if deleted is not None else 0
    except Exception:
        return 0
        
def make_cache_key(surface: str, endpoint: str, **params) -> str:
    filtered = {k: v for k, v in params.items() if v is not None}
    if not filtered:
        return f"{CACHE_PREFIX}:{surface}:{endpoint}"
    param_str = "&".join(f"{k}={v}" for k, v in sorted(filtered.items()))
    return f"{CACHE_PREFIX}:{surface}:{endpoint}:{param_str}"


def make_surface_pattern(surface: str) -> str:
    return f"{CACHE_PREFIX}:{surface}:*"

def make_query_cache_key(raw_query: str) -> str:
    import hashlib
    import re
    normalised = raw_query.strip().lower()
    normalised = re.sub(r'\s+', ' ', normalised)
    normalised = normalised.rstrip('?.!')
    query_hash = hashlib.md5(normalised.encode()).hexdigest()
    return make_cache_key("chat", "query", query_hash=query_hash)