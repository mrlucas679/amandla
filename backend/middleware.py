"""
Rate-limiting middleware for AMANDLA backend.

Per-IP, per-endpoint in-memory rate limiter. Tracks request counts within
a sliding minute window and returns HTTP 429 when limits are exceeded.

Limits (per IP, per minute):
  /speech         — 10 requests
  /rights/analyze — 5 requests
  /rights/letter  — 5 requests
"""
import time
import logging
from collections import defaultdict
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# ── Named constants for rate limits ──────────────────────────────
RATE_WINDOW_SECONDS = 60
RATE_LIMITS: Dict[str, int] = {
    "/speech": 10,
    "/rights/analyze": 5,
    "/rights/letter": 5,
}

# Fallback IP used when the client address cannot be determined
# (e.g. behind a misconfigured proxy).
_UNKNOWN_IP = "unknown"


def _get_client_ip(request: Request) -> str:
    """Extract the client IP from the request.

    Checks the ``X-Forwarded-For`` header first (common behind reverse
    proxies), then falls back to ``request.client.host``.

    Args:
        request: The incoming Starlette request object.

    Returns:
        A string representing the client's IP address.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # X-Forwarded-For may contain a comma-separated list; first entry
        # is the original client IP.
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return _UNKNOWN_IP


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Per-IP, per-endpoint in-memory rate limiter middleware.

    Tracks the number of requests per (client_ip, endpoint_path) within
    a sliding minute window. Returns HTTP 429 when the limit is exceeded
    for any tracked endpoint.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialise the rate limiter with an empty request counter."""
        super().__init__(app)  # type: ignore[misc]
        # Key: (client_ip, path, minute_bucket) → Value: request count
        self._counters: Dict[Tuple[str, str, int], int] = defaultdict(int)
        self._last_cleanup = time.time()

    def _get_minute_bucket(self) -> int:
        """Return the current minute as an integer bucket for grouping requests."""
        return int(time.time() // RATE_WINDOW_SECONDS)

    def _cleanup_old_buckets(self) -> None:
        """Remove expired minute buckets to prevent memory growth."""
        now = time.time()
        # Only clean up every 60 seconds to avoid overhead
        if now - self._last_cleanup < RATE_WINDOW_SECONDS:
            return
        self._last_cleanup = now
        current_bucket = self._get_minute_bucket()
        expired_keys = [
            key for key in self._counters
            if key[2] < current_bucket
        ]
        for key in expired_keys:
            del self._counters[key]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Check if the request exceeds the per-IP rate limit for its endpoint.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            HTTP 429 response if rate limit exceeded, otherwise the normal response.
        """
        path = request.url.path
        limit = RATE_LIMITS.get(path)

        if limit is not None:
            client_ip = _get_client_ip(request)
            bucket = self._get_minute_bucket()
            counter_key = (client_ip, path, bucket)
            self._counters[counter_key] += 1

            if self._counters[counter_key] > limit:
                logger.warning(
                    "[RateLimit] IP %s exceeded %d req/min limit on %s",
                    client_ip,
                    limit,
                    path,
                )
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please wait a moment."},
                )

            # Periodic cleanup of old buckets
            self._cleanup_old_buckets()

        return await call_next(request)

