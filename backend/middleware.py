"""
Rate-limiting middleware for AMANDLA backend.

Simple in-memory rate limiter that tracks request counts per endpoint
path per minute. Returns HTTP 429 when limits are exceeded.

Limits:
  /speech         — 10 requests per minute
  /rights/analyze — 5 requests per minute
  /rights/letter  — 5 requests per minute
"""
import time
import logging
from collections import defaultdict
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# ── Named constants for rate limits ──────────────────────────────
RATE_WINDOW_SECONDS = 60
RATE_LIMITS: Dict[str, int] = {
    "/speech": 10,
    "/rights/analyze": 5,
    "/rights/letter": 5,
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory rate limiter middleware.

    Tracks the number of requests per endpoint path within a
    sliding minute window. Returns HTTP 429 when the limit is
    exceeded for any tracked endpoint.
    """

    def __init__(self, app):
        """Initialise the rate limiter with an empty request counter."""
        super().__init__(app)
        # Key: (path, minute_bucket) → Value: request count
        self._counters: Dict[Tuple[str, int], int] = defaultdict(int)
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
            if key[1] < current_bucket
        ]
        for key in expired_keys:
            del self._counters[key]

    async def dispatch(self, request: Request, call_next):
        """
        Check if the request exceeds the rate limit for its endpoint.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            HTTP 429 response if rate limit exceeded, otherwise the normal response.
        """
        path = request.url.path
        limit = RATE_LIMITS.get(path)

        if limit is not None:
            bucket = self._get_minute_bucket()
            counter_key = (path, bucket)
            self._counters[counter_key] += 1

            if self._counters[counter_key] > limit:
                logger.warning(
                    "[RateLimit] %s exceeded %d req/min limit on %s",
                    request.client.host if request.client else "unknown",
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

