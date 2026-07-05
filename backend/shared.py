"""Shared constants, utilities, and in-memory state for the AMANDLA backend.

Every module that needs session state, sanitisation, or security tokens
imports from here. This avoids circular imports between routers, WS
handlers, and service modules.

NOTE: This module must be imported AFTER load_dotenv() has been called
in backend/main.py — it does not call load_dotenv() itself.
"""

import hmac
import logging
import re
import secrets
import time as _time
import unicodedata
from typing import Any, Dict

logger = logging.getLogger(__name__)

# ── Session authentication token ──────────────────────────────────────────────
# Generated once at startup. Electron main process reads this via /auth/session-secret
# and passes it to each window via IPC. Every WebSocket connection must include
# ?token=<this value> or it is rejected immediately. Uses constant-time
# comparison to prevent timing side-channels.
SESSION_SECRET: str = secrets.token_urlsafe(32)

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
SESSION_EXPIRY_S: int = 1800  # 30 minutes

# ── Sign reconstruction buffers ───────────────────────────────────────────────
# Per-session: accumulate signs from deaf user, then reconstruct to English.
sign_buffers: Dict[str, list] = {}          # sessionId → [sign_names]
sign_tasks: Dict[str, Any] = {}             # sessionId → asyncio.Task

# ── Per-session HARPS sign recognisers ────────────────────────────────────
# Each deaf WebSocket session gets its own HARPSSignRecognizer instance
# so landmark frames are buffered independently per session.
harps_recognizers: Dict[str, Any] = {}      # sessionId → HARPSSignRecognizer

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

    Args:
        session_id: The WebSocket session identifier.
        msg_type:   The WebSocket message type being throttled.

    Returns:
        True  — call is allowed (cooldown has elapsed or this is the first call).
        False — call is denied (still inside the cooldown window).
    """
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

