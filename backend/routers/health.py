"""Health and status endpoints for AMANDLA backend.

Routes:
  GET /health              — simple liveness probe
  GET /auth/session-secret — returns the session authentication token
  GET /api/status          — AI service health (Ollama + Whisper)
"""

import logging
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.shared import SESSION_SECRET, sessions

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health():
    """Simple liveness check — returns 200 OK if the server is running."""
    return JSONResponse({"ok": True})


@router.get("/auth/session-secret")
async def get_session_secret():
    """Return the session secret token.

    Called once by Electron main process after the health check passes.
    Only reachable on 127.0.0.1 (localhost binding) — never exposed to the
    network. Each backend restart generates a fresh token.
    """
    return JSONResponse({"session_secret": SESSION_SECRET})


@router.get("/api/status")
async def api_status():
    """Returns health of AI services for status-dot polling."""
    try:
        qwen_alive = await _check_ollama()
        whisper_ok = _check_whisper()
        return {
            "status": "ok",
            "qwen": "alive" if qwen_alive else "dead",
            "whisper": "ready" if whisper_ok else "unavailable",
            "sessions": len(sessions)
        }
    except Exception as exc:
        logger.error("[Status] Health check failed: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": "Status check temporarily unavailable."}
        )


async def _check_ollama() -> bool:
    """Check whether the Ollama model is loaded and responding.

    Returns:
        True if the configured Ollama model is available, False otherwise.
    """
    try:
        from backend.services.ollama_pool import get_client
        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model_name = os.getenv("OLLAMA_MODEL", "amandla")
        client = get_client()
        resp = await client.get(f"{base}/api/tags", timeout=2.0)
        if resp.status_code != 200:
            return False
        tags = resp.json().get("models", [])
        return any(model_name in m.get("name", "") for m in tags)
    except Exception:
        return False


def _check_whisper() -> bool:
    """Check whether the Whisper model is already loaded (does not trigger load).

    Returns:
        True if the Whisper model is loaded in memory, False otherwise.
    """
    try:
        from backend.services import whisper_service
        return whisper_service._model is not None
    except Exception:
        return False

