"""Small production-safe middleware shared by web and API routes."""

import logging
import re
import time
import uuid


logger = logging.getLogger("xggaffer.requests")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestIdMiddleware:
    """Attach a safe correlation ID and emit one completion log per request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied_id = request.headers.get("X-Request-ID", "")
        request_id = (
            supplied_id
            if REQUEST_ID_PATTERN.fullmatch(supplied_id)
            else uuid.uuid4().hex
        )
        request.request_id = request_id
        started_at = time.monotonic()

        try:
            response = self.get_response(request)
        except Exception:
            logger.exception(
                "request_failed request_id=%s method=%s path=%s duration_ms=%d",
                request_id,
                request.method,
                request.path,
                round((time.monotonic() - started_at) * 1000),
            )
            raise

        response["X-Request-ID"] = request_id
        if not request.path.startswith("/health/"):
            logger.info(
                "request_completed request_id=%s method=%s path=%s status=%d duration_ms=%d",
                request_id,
                request.method,
                request.path,
                response.status_code,
                round((time.monotonic() - started_at) * 1000),
            )
        return response
