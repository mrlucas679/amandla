"""Shared constants, utilities, and in-memory state for the AMANDLA backend.

Every module that needs session state, sanitisation, or security tokens
imports from here. This avoids circular imports between routers, WS
handlers, and service modules.

NOTE: This module must be imported AFTER load_dotenv() has been called
in backend/main.py — it does not call load_dotenv() itself.
"""

import hmac
import logging
import os
import re
import secrets
import time as _time
import unicodedata
from typing import Any, Dict, Set

logger = logging.getLogger(__name__)

# ── Session authentication token ──────────────────────────────────────────────
# Persisted to data/session.secret so uvicorn --reload doesn't change the secret
# between the worker that served /auth/session-secret and the worker that handles
# the WebSocket connection. Electron fetches the secret once at startup via IPC.
_SECRET_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "session.secret")

def _load_or_create_secret() -> str:
    try:
        with open(_SECRET_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        pass
    secret = secrets.token_urlsafe(32)
    os.makedirs(os.path.dirname(_SECRET_FILE), exist_ok=True)
    with open(_SECRET_FILE, "w") as f:
        f.write(secret)
    return secret

SESSION_SECRET: str = _load_or_create_secret()

# ── Upload / message size limits ──────────────────────────────────────────────
MAX_AUDIO_BYTES: int = 10 * 1024 * 1024       # 10 MB upload cap for audio files
MAX_TEXT_LENGTH: int = 5000                     # 5000 char limit for WS text messages

# ── Session management ────────────────────────────────────────────────────────
# In-memory session store: { sessionId: { "users": { role: ws }, "queue": [] } }
sessions: Dict[str, Dict[str, Any]] = {}

# Maximum number of concurrent WebSocket sessions allowed at once.
# Prevents abuse by creating unlimited sessions to bypass per-session rate limits.
MAX_CONCURRENT_SESSIONS: int = 10

# Sessions idle for longer than this (in seconds) are cleaned up by the reaper task.
# Override via SESSION_EXPIRY_S env var — medical appointments can run 45-90 min.
SESSION_EXPIRY_S: int = int(os.getenv("SESSION_EXPIRY_S", "3600"))  # 1 hour default

# ── Sign reconstruction buffers ───────────────────────────────────────────────
# Per-session: accumulate signs from deaf user, then reconstruct to English.
sign_buffers: Dict[str, list] = {}          # sessionId → [sign_names]
sign_tasks: Dict[str, Any] = {}             # sessionId → asyncio.Task

# ── Per-IP WebSocket connection limiting (FIX-5) ─────────────────────────────
# Tracks active WebSocket connections per client IP to prevent DoS via
# connection flooding. An attacker opening thousands of connections per second
# would exhaust memory and block legitimate users.

# Maximum concurrent WebSocket connections allowed from a single IP address.
MAX_WS_CONNECTIONS_PER_IP: int = int(os.getenv("MAX_WS_CONNECTIONS_PER_IP", "5"))

# Active connection count per IP: { ip_address: count }
_ws_connections_per_ip: Dict[str, int] = {}


def acquire_ws_connection(client_ip: str) -> bool:
    """Check and register a new WebSocket connection from client_ip.

    Returns True if the connection is allowed (count incremented),
    False if the per-IP limit has been reached.

    Thread-safe for single-threaded asyncio event loop use.
    """
    current = _ws_connections_per_ip.get(client_ip, 0)
    if current >= MAX_WS_CONNECTIONS_PER_IP:
        return False
    _ws_connections_per_ip[client_ip] = current + 1
    return True


def release_ws_connection(client_ip: str) -> None:
    """Decrement the connection count for client_ip on disconnect."""
    current = _ws_connections_per_ip.get(client_ip, 0)
    if current <= 1:
        _ws_connections_per_ip.pop(client_ip, None)
    else:
        _ws_connections_per_ip[client_ip] = current - 1


# ── Per-session rate limiting for heavy AI operations ─────────────────────────
# Tracks the last call timestamp per session + message type.
last_heavy_call: Dict[str, Dict[str, float]] = {}

# Per-type rate limit intervals (seconds between allowed calls per session).
HEAVY_CALL_INTERVALS: Dict[str, float] = {
    "speech_upload":  2.0,    # Whisper responds in a few seconds
    "rights_analyze": 30.0,   # Ollama takes 10–30s
    "rights_letter":  45.0,   # Ollama takes 10–30s
}
HEAVY_CALL_INTERVAL_DEFAULT: float = 2.0  # Fallback for unlisted types

# Message types that are ALWAYS allowed — never rate-limited (HARPS-3)
# Emergency and assist phrases must reach the hearing user instantly.
RATE_LIMIT_EXEMPT_TYPES: set = {"emergency", "assist_phrase"}

# ── Text sanitisation ─────────────────────────────────────────────────────────
# Precompiled regex: matches C0/C1 control characters EXCEPT tab (\t), newline (\n),
# and carriage return (\r) which are legitimate whitespace in user text.
_CONTROL_CHAR_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]')


def sanitise_text(raw: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """Strip control characters and null bytes from user-supplied text.

    Args:
        raw: The raw string to sanitise — may come from any WebSocket field.
        max_length: Maximum allowed character count (truncated, not rejected).

    Returns:
        A cleaned string safe for display, logging, and downstream processing.
        Contains only printable Unicode plus tab/newline/CR whitespace.
    """
    if not isinstance(raw, str):
        raw = str(raw)
    # Truncate to max length first to limit regex work
    text = raw[:max_length]
    # Strip C0/C1 control characters (keeps \t \n \r)
    text = _CONTROL_CHAR_RE.sub('', text)
    # Normalise Unicode to NFC to collapse equivalent codepoints
    text = unicodedata.normalize('NFC', text)
    return text


def check_rate_limit(session_id: str, msg_type: str) -> bool:
    """Return True if the call is allowed, False if it is being rate-limited.

    Enforces a per-session, per-message-type cooldown window for heavy AI
    operations. Runs in constant time and requires no external dependencies.

    Emergency and assist_phrase messages are always allowed — they must never
    be throttled (HARPS-3).

    Args:
        session_id: The WebSocket session identifier.
        msg_type:   The WebSocket message type being throttled.

    Returns:
        True  — call is allowed (cooldown has elapsed or this is the first call).
        False — call is denied (still inside the cooldown window).
    """
    if msg_type in RATE_LIMIT_EXEMPT_TYPES:
        return True  # Emergency / assist phrases are never throttled

    now = _time.monotonic()
    session_calls = last_heavy_call.setdefault(session_id, {})
    last = session_calls.get(msg_type, 0.0)
    interval = HEAVY_CALL_INTERVALS.get(msg_type, HEAVY_CALL_INTERVAL_DEFAULT)
    if (now - last) < interval:
        return False
    session_calls[msg_type] = now
    return True


def verify_session_token(token: str) -> bool:
    """Constant-time comparison of a client-provided token against the session secret.

    Args:
        token: The token string from the WebSocket query parameter.

    Returns:
        True if the token matches SESSION_SECRET, False otherwise.
    """
    return hmac.compare_digest(token, SESSION_SECRET)

