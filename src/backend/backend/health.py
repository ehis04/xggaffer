"""Minimal process and dependency health checks for deployment platforms."""

from django.core.cache import cache
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@never_cache
@require_GET
def live(request):
    return JsonResponse({"status": "ok"})


@never_cache
@require_GET
def ready(request):
    checks = {"database": False, "cache": False}

    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            checks["database"] = cursor.fetchone() == (1,)
    except Exception:
        pass

    try:
        cache_key = "xggaffer:health:ready"
        cache.set(cache_key, "ok", timeout=10)
        checks["cache"] = cache.get(cache_key) == "ok"
        cache.delete(cache_key)
    except Exception:
        pass

    is_ready = all(checks.values())
    return JsonResponse(
        {"status": "ok" if is_ready else "unavailable", "checks": checks},
        status=200 if is_ready else 503,
    )
