"""AMANDLA backend — FastAPI server

Provides:
- GET  /health              — liveness check
- GET  /api/status          — AI service health (Ollama + Whisper)
- POST /speech              — audio upload → Whisper transcription → SASL signs
- POST /rights/analyze      — incident description → rights analysis (Ollama)
- POST /rights/letter       — full details → formal complaint letter (Ollama)
- POST /api/sasl/translate  — English text → SASL gloss + tokens
- GET  /api/sasl/health     — SASL transformer health
- WS   /ws/{sessionId}/{role} — main real-time communication channel

This module is the entry point: it loads environment variables, sets up
logging, creates the FastAPI app, and registers all routers.
All business logic lives in backend/routers/, backend/ws/, and backend/services/.
"""
import sys
import os
import asyncio
import logging
import logging.handlers

# Ensure project root is in sys.path regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env ONCE at startup — all modules can use os.getenv() after this
from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware

# ── Logging: console + rotating file ────────────────────────────────────────
_log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(_log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            os.path.join(_log_dir, "amandla.log"),
            maxBytes=5 * 1024 * 1024,  # 5 MB per file
            backupCount=3,
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """FastAPI lifespan handler — starts background tasks on startup.

    Replaces the deprecated @app.on_event('startup') pattern (removed in
    FastAPI 0.93+). Tasks:
    1. Session reaper — cleans up stale sessions every 30 min
    2. Whisper pre-load — loads the model in a thread so first speech upload is fast
    3. Ollama connection pool — shared httpx client for all Ollama calls
    """
    from backend.ws.session import session_reaper
    from backend.services import whisper_service
    from backend.services.ollama_pool import startup as ollama_pool_startup, shutdown as ollama_pool_shutdown
    from backend.services.history_db import init_db

    # FEAT-3: Initialise SQLite conversation history database
    init_db()

    asyncio.create_task(session_reaper())

    # PERF-1: Pre-load Whisper model in a background thread so first
    # speech upload doesn't stall the event loop for 15-45 seconds.
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, whisper_service.get_model)

    # PERF-4: Start the shared Ollama httpx connection pool
    await ollama_pool_startup()

    yield  # server runs here

    # Shutdown: close the shared Ollama connection pool
    await ollama_pool_shutdown()


# ── App creation ─────────────────────────────────────────────────────────────
app = FastAPI(title="AMANDLA Backend", lifespan=_lifespan)

# ── SASL transformer routes ────────────────────────────────────────
try:
    from sasl_transformer.routes import router as sasl_router
    app.include_router(sasl_router, prefix="/api/sasl")
    logger.info("SASL transformer routes registered at /api/sasl/*")
except Exception as _e:
    logger.error("SASL transformer routes not loaded: %s", _e, exc_info=True)

# ── Health, speech, and rights routes ──────────────────────────────
from backend.routers.health import router as health_router
from backend.routers.speech import router as speech_router
from backend.routers.rights import router as rights_router

app.include_router(health_router)
app.include_router(speech_router)
app.include_router(rights_router)

# ── CORS — must stay ["*"] for Electron desktop apps ──────────────
app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting middleware — prevents abuse of AI endpoints ─────
try:
    from backend.middleware import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)
    logger.info("Rate limit middleware registered")
except Exception as _mw_err:
    logger.warning("Rate limit middleware not loaded: %s", _mw_err)


# ── WebSocket endpoint (delegates to backend.ws.handler) ─────────
@app.websocket("/ws/{sessionId}/{role}")
async def ws_endpoint(
    websocket: WebSocket,
    sessionId: str,
    role: str,
    token: str = Query(default=""),
):
    """WebSocket entry point — delegates to the handler module."""
    from backend.ws.handler import websocket_endpoint
    await websocket_endpoint(websocket, sessionId, role, token)
