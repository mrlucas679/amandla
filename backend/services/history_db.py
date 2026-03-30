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
from datetime import datetime, timezone
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
    """Create the conversations table if it doesn't already exist.

    Schema:
        id              — auto-incrementing primary key
        session_id      — WebSocket session identifier
        timestamp       — ISO 8601 UTC timestamp
        direction       — 'hearing_to_deaf' or 'deaf_to_hearing'
        original_text   — the original input text (English or SASL)
        sasl_gloss      — the SASL gloss representation (sign names)
        translated_text — the translated output text
        source          — how the message was created (text, speech, sign, assist)
    """
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      TEXT    NOT NULL,
            timestamp       TEXT    NOT NULL,
            direction       TEXT    NOT NULL,
            original_text   TEXT    DEFAULT '',
            sasl_gloss      TEXT    DEFAULT '',
            translated_text TEXT    DEFAULT '',
            source          TEXT    DEFAULT 'text'
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
    conn.commit()
    logger.info("[HistoryDB] Tables initialised")


def init_db() -> None:
    """Initialise the database — called once at backend startup.

    Creates the data/ directory and conversations table if they don't exist.
    Safe to call multiple times (CREATE TABLE IF NOT EXISTS).
    """
    try:
        _init_tables()
    except Exception as exc:
        logger.error("[HistoryDB] Failed to initialise database: %s", exc)


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
    """
    try:
        conn = _get_connection()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO conversations
               (session_id, timestamp, direction, original_text, sasl_gloss, translated_text, source)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, now, direction, original_text, sasl_gloss, translated_text, source),
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
                      original_text, sasl_gloss, translated_text, source
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
    """List all sessions with message counts (synchronous).

    Returns:
        List of dicts: { session_id, message_count, first_message, last_message }.
    """
    try:
        conn = _get_connection()
        cursor = conn.execute(
            """SELECT session_id,
                      COUNT(*) as message_count,
                      MIN(timestamp) as first_message,
                      MAX(timestamp) as last_message
               FROM conversations
               GROUP BY session_id
               ORDER BY last_message DESC
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

