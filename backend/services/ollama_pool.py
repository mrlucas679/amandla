"""Shared httpx connection pool for all Ollama API calls.

PERF-4: Every Ollama call previously created a new httpx.AsyncClient,
which means a fresh TCP handshake on every request.  This module provides
a single long-lived client with keep-alive pooling so connections are reused.

Usage:
    from backend.services.ollama_pool import get_client
    client = get_client()
    resp = await client.post(url, json=payload)

The pool is started in the FastAPI lifespan handler (backend/main.py)
and shut down cleanly when the server stops.
"""
import logging
import httpx

logger = logging.getLogger(__name__)

# Module-level client — initialised by startup(), closed by shutdown()
_client: httpx.AsyncClient | None = None

# Default timeout for Ollama requests (individual callers can override per-request)
_DEFAULT_TIMEOUT = httpx.Timeout(timeout=30.0, connect=5.0)

# Connection pool limits — max 10 keep-alive connections, 20 total
_POOL_LIMITS = httpx.Limits(max_keepalive_connections=10, max_connections=20)


async def startup() -> None:
    """Create the shared httpx.AsyncClient. Called once during app lifespan startup."""
    global _client
    _client = httpx.AsyncClient(
        timeout=_DEFAULT_TIMEOUT,
        limits=_POOL_LIMITS,
    )
    logger.info("[OllamaPool] Shared connection pool started")


async def shutdown() -> None:
    """Close the shared httpx.AsyncClient. Called during app lifespan shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
        logger.info("[OllamaPool] Shared connection pool closed")


def get_client() -> httpx.AsyncClient:
    """Return the shared httpx.AsyncClient for Ollama API calls.

    Falls back to creating a one-shot client if the pool was never started
    (e.g. during tests). Callers can override timeout per-request via
    httpx's request-level timeout parameter.

    Returns:
        httpx.AsyncClient instance with connection pooling enabled.
    """
    if _client is not None:
        return _client

    # Fallback for tests or scripts that don't run the full lifespan
    logger.warning("[OllamaPool] Pool not started — creating ephemeral client")
    return httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT, limits=_POOL_LIMITS)

