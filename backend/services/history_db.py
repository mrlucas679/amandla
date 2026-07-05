"""
backend.services.history_db — SQLite conversation history for AMANDLA.

Stores all messages exchanged during sessions so they survive restarts.
Important for medical and legal settings where a record of what was
communicated must be kept.

Uses Python's built-in sqlite3 module — no external dependencies.
All database calls run in a background thread via asyncio.to_thread()
to avoid blocking the event loop.

Database location: data/conversations.db (relative to project root).
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Database file path — stored in the project's data/ directory
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DB_DIR = _PROJECT_ROOT / "data"
_DB_PATH = _DB_DIR / "conversations.db"

# Module-level connection (reused across calls, created lazily)
_connection: Optional[sqlite3.Connection] = None


def _get_connection() -> sqlite3.Connection:
    """Get or create the SQLite connection (thread-safe, WAL mode).

    Returns:
        sqlite3.Connection: The database connection with WAL journal mode
        enabled for better concurrent read performance.
    """
    global _connection
    if _connection is None:
        _DB_DIR.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        # WAL mode allows concurrent reads while writing
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA foreign_keys=ON")
        logger.info("[HistoryDB] Connected to %s", _DB_PATH)
    return _connection


def _init_tables() -> None:
    """Create the conversations and sessions tables if they don't already exist.

    conversations schema:
        id              — auto-incrementing primary key
        session_id      — WebSocket session identifier
        timestamp       — ISO 8601 UTC timestamp
        direction       — 'hearing_to_deaf' or 'deaf_to_hearing'
        original_text   — the original input text (English or SASL)
        sasl_gloss      — the SASL gloss representation (sign names)
        translated_text — the translated output text
        source          — how the message was created (text, speech, sign, assist)
        sign_count      — number of SASL signs in this utterance (derived from sasl_gloss)
        animation_version — signs_library.js version used to produce these signs

    sessions schema (ARCH-6):
        session_id      — primary key, matches conversations.session_id
        created_at      — ISO 8601 UTC timestamp when session was first seen
        closed_at       — ISO 8601 UTC when last role disconnected (NULL = open)
        roles_present   — comma-separated list of roles that joined (e.g. 'hearing,deaf')
        message_count   — total messages logged for this session
    """
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id        TEXT    NOT NULL,
            timestamp         TEXT    NOT NULL,
            direction         TEXT    NOT NULL,
            original_text     TEXT    DEFAULT '',
            sasl_gloss        TEXT    DEFAULT '',
            translated_text   TEXT    DEFAULT '',
            source            TEXT    DEFAULT 'text',
            sign_count        INTEGER DEFAULT 0,
            animation_version TEXT    DEFAULT 'v2'
        )
    """)

    # ARCH-6: session metadata table — enables analytics without scanning all conversations
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id    TEXT PRIMARY KEY,
            created_at    TEXT NOT NULL,
            closed_at     TEXT,
            roles_present TEXT DEFAULT '',
            message_count INTEGER DEFAULT 0
        )
    """)
    # Index on session_id for fast per-session lookups
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_session
        ON conversations (session_id)
    """)
    # Index on timestamp for chronological queries
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_timestamp
        ON conversations (timestamp)
    """)
    # Composite index: eliminates sort step in per-session history queries (ARCH-4)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_session_time
        ON conversations (session_id, timestamp DESC)
    """)

    # ── Migration: add new columns to existing databases ──────────────────────
    # SQLite does not support IF NOT EXISTS on ALTER TABLE, so we catch the error.
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(conversations)")}
    if "sign_count" not in existing_cols:
        conn.execute("ALTER TABLE conversations ADD COLUMN sign_count INTEGER DEFAULT 0")
        logger.info("[HistoryDB] Migration: added sign_count column")
    if "animation_version" not in existing_cols:
        conn.execute("ALTER TABLE conversations ADD COLUMN animation_version TEXT DEFAULT 'v2'")
        logger.info("[HistoryDB] Migration: added animation_version column")

    conn.commit()
    logger.info("[HistoryDB] Tables initialised")


def init_db() -> None:
    """Initialise the database — called once at backend startup.

    Creates the data/ directory and conversations table if they don't exist.
    Safe to call multiple times (CREATE TABLE IF NOT EXISTS).

    Raises:
        Exception: Propagated from _init_tables() so the caller (main.py lifespan)
        can fail fast instead of starting a degraded server (ARCH-9).
    """
    _init_tables()


def _sync_log_message(
    session_id: str,
    direction: str,
    original_text: str = "",
    sasl_gloss: str = "",
    translated_text: str = "",
    source: str = "text",
) -> None:
    """Insert one conversation record into the database (synchronous).

    Args:
        session_id:      WebSocket session ID.
        direction:       'hearing_to_deaf' or 'deaf_to_hearing'.
        original_text:   The original input (English text or SASL gloss typed by deaf).
        sasl_gloss:      The SASL sign names generated/sent.
        translated_text: The translated output (English sentence or SASL text).
        source:          How the message originated: 'text', 'speech', 'sign', 'assist'.

    sign_count is auto-derived from sasl_gloss word count so callers don't need
    to compute it — sasl_gloss is already the space-separated list of sign names.
    animation_version is pinned to the current signs_library.js version.
    """
    try:
        conn = _get_connection()
        now = datetime.now(timezone.utc).isoformat()
        # Count SASL signs from the gloss string (each token is one sign name)
        sign_count = len(sasl_gloss.split()) if sasl_gloss and sasl_gloss.strip() else 0
        animation_version = "v2"
        conn.execute(
            """INSERT INTO conversations
               (session_id, timestamp, direction, original_text, sasl_gloss,
                translated_text, source, sign_count, animation_version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, now, direction, original_text, sasl_gloss,
             translated_text, source, sign_count, animation_version),
        )
        # ARCH-6: keep session message_count in sync
        conn.execute(
            """INSERT OR IGNORE INTO sessions (session_id, created_at)
               VALUES (?, ?)""",
            (session_id, now),
        )
        conn.execute(
            "UPDATE sessions SET message_count = message_count + 1 WHERE session_id = ?",
            (session_id,),
        )
        conn.commit()
    except Exception as exc:
        logger.error("[HistoryDB] Failed to log message: %s", exc)


async def log_message(
    session_id: str,
    direction: str,
    original_text: str = "",
    sasl_gloss: str = "",
    translated_text: str = "",
    source: str = "text",
) -> None:
    """Insert one conversation record (async — runs in a background thread).

    Args:
        session_id:      WebSocket session ID.
        direction:       'hearing_to_deaf' or 'deaf_to_hearing'.
        original_text:   The original input text.
        sasl_gloss:      The SASL sign names.
        translated_text: The translated output text.
        source:          Origin type: 'text', 'speech', 'sign', 'assist'.
    """
    await asyncio.to_thread(
        _sync_log_message,
        session_id, direction, original_text, sasl_gloss, translated_text, source,
    )


def _sync_get_session_history(
    session_id: str, limit: int = 100
) -> List[Dict[str, Any]]:
    """Retrieve conversation history for a session (synchronous).

    Args:
        session_id: The session to look up.
        limit:      Maximum number of messages to return (newest first reversed to chronological).

    Returns:
        List of message dicts, each with: id, session_id, timestamp,
        direction, original_text, sasl_gloss, translated_text, source.
    """
    try:
        conn = _get_connection()
        cursor = conn.execute(
            """SELECT id, session_id, timestamp, direction,
                      original_text, sasl_gloss, translated_text, source,
                      sign_count, animation_version
               FROM conversations
               WHERE session_id = ?
               ORDER BY id DESC
               LIMIT ?""",
            (session_id, limit),
        )
        rows = cursor.fetchall()
        # Reverse so oldest is first (chronological order)
        return [dict(row) for row in reversed(rows)]
    except Exception as exc:
        logger.error("[HistoryDB] Failed to get session history: %s", exc)
        return []


async def get_session_history(
    session_id: str, limit: int = 100
) -> List[Dict[str, Any]]:
    """Retrieve conversation history for a session (async).

    Args:
        session_id: The session to look up.
        limit:      Maximum number of messages to return.

    Returns:
        List of message dicts in chronological order.
    """
    return await asyncio.to_thread(_sync_get_session_history, session_id, limit)


def _sync_get_all_sessions() -> List[Dict[str, Any]]:
    """List all sessions with metadata (synchronous).

    Reads from the sessions table (ARCH-6) for O(1) per row instead of
    scanning all conversations. Falls back to the conversations aggregate
    if a session was logged before the sessions table existed.

    Returns:
        List of dicts: { session_id, created_at, closed_at, roles_present,
                         message_count }.
    """
    try:
        conn = _get_connection()
        # Primary: sessions table (fast, no scan)
        cursor = conn.execute(
            """SELECT session_id, created_at, closed_at, roles_present, message_count
               FROM sessions
               ORDER BY created_at DESC
               LIMIT 50"""
        )
        rows = [dict(row) for row in cursor.fetchall()]
        if rows:
            return rows
        # Fallback: sessions table empty (pre-migration DB) — aggregate from conversations
        cursor = conn.execute(
            """SELECT session_id,
                      COUNT(*) as message_count,
                      MIN(timestamp) as created_at,
                      MAX(timestamp) as closed_at,
                      '' as roles_present
               FROM conversations
               GROUP BY session_id
               ORDER BY closed_at DESC
               LIMIT 50"""
        )
        return [dict(row) for row in cursor.fetchall()]
    except Exception as exc:
        logger.error("[HistoryDB] Failed to list sessions: %s", exc)
        return []


async def get_all_sessions() -> List[Dict[str, Any]]:
    """List all sessions with message counts (async).

    Returns:
        List of session summary dicts.
    """
    return await asyncio.to_thread(_sync_get_all_sessions)


def _sync_delete_old_messages(days: int = 90) -> int:
    """Delete conversation records older than `days` days (synchronous).

    Args:
        days: Retain messages newer than this many days. Default: 90.

    Returns:
        Number of rows deleted.
    """
    try:
        conn = _get_connection()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        cursor = conn.execute(
            "DELETE FROM conversations WHERE timestamp < ?",
            (cutoff,),
        )
        conn.commit()
        count = cursor.rowcount
        logger.info("[HistoryDB] Retention: deleted %d messages older than %d days", count, days)
        return count
    except Exception as exc:
        logger.error("[HistoryDB] Failed to delete old messages: %s", exc)
        return 0


def _sync_upsert_session(session_id: str, role: str) -> None:
    """Create or update the sessions row when a role joins (synchronous).

    On first join: inserts the row with created_at = now.
    On subsequent joins: appends the role to roles_present if not already listed.

    Args:
        session_id: The WebSocket session ID.
        role:       The role that connected ('hearing', 'deaf', 'rights').
    """
    try:
        conn = _get_connection()
        now = datetime.now(timezone.utc).isoformat()
        # Insert if not exists (first role to join)
        conn.execute(
            """INSERT OR IGNORE INTO sessions (session_id, created_at, roles_present)
               VALUES (?, ?, '')""",
            (session_id, now),
        )
        # Append role if not already in the comma-separated list
        row = conn.execute(
            "SELECT roles_present FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row:
            existing = row["roles_present"] or ""
            roles = set(r for r in existing.split(",") if r)
            roles.add(role)
            conn.execute(
                "UPDATE sessions SET roles_present = ?, closed_at = NULL WHERE session_id = ?",
                (",".join(sorted(roles)), session_id),
            )
        conn.commit()
    except Exception as exc:
        logger.warning("[HistoryDB] Failed to upsert session: %s", exc)


async def upsert_session(session_id: str, role: str) -> None:
    """Create or update the sessions row when a role joins (async).

    Args:
        session_id: The WebSocket session ID.
        role:       The role that connected.
    """
    await asyncio.to_thread(_sync_upsert_session, session_id, role)


def _sync_close_session(session_id: str) -> None:
    """Mark the session as closed when the last role disconnects (synchronous).

    Args:
        session_id: The WebSocket session ID.
    """
    try:
        conn = _get_connection()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE sessions SET closed_at = ? WHERE session_id = ?",
            (now, session_id),
        )
        conn.commit()
    except Exception as exc:
        logger.warning("[HistoryDB] Failed to close session: %s", exc)


async def close_session(session_id: str) -> None:
    """Mark the session as closed when the last role disconnects (async).

    Args:
        session_id: The WebSocket session ID.
    """
    await asyncio.to_thread(_sync_close_session, session_id)



async def delete_old_messages(days: int = 90) -> int:
    """Delete conversation records older than `days` days (async).

    Called weekly by the session reaper to prevent unbounded database growth.

    Args:
        days: Retain messages newer than this many days. Default: 90.

    Returns:
        Number of rows deleted.
    """
    return await asyncio.to_thread(_sync_delete_old_messages, days)

