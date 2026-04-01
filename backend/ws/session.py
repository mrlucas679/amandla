"""Session lifecycle management for AMANDLA WebSocket sessions.

Contains the background session reaper that cleans up idle sessions.
All session state lives in backend.shared — this module just manages it.
"""

import asyncio
import logging
import time as _time

from backend.shared import (
    sessions,
    sign_buffers,
    sign_tasks,
    SESSION_EXPIRY_S,
)

logger = logging.getLogger(__name__)

# Interval between reaper sweeps (seconds). 10 minutes is sufficient —
# sessions stay around for SESSION_EXPIRY_S (30 min) after last disconnect.
_REAPER_SWEEP_INTERVAL_S: int = 600

# How often to run the retention sweep — delete messages older than 90 days.
_RETENTION_SWEEP_INTERVAL_S: int = 7 * 24 * 3600  # 7 days

# Timestamp of the last retention sweep (monotonic clock)
_last_retention_sweep: float = 0.0


async def session_reaper() -> None:
    """Background loop: remove stale sessions with no active users.

    A session is considered stale when:
      - It has no connected WebSocket users (session["users"] is empty), AND
      - It has been empty for at least SESSION_EXPIRY_S seconds.

    The '_empty_since' timestamp is written to the session dict by the
    WebSocket handler's finally block when the last user disconnects.
    """
    global _last_retention_sweep
    while True:
        await asyncio.sleep(_REAPER_SWEEP_INTERVAL_S)
        now = _time.monotonic()
        stale_ids = [
            sid
            for sid, sess in list(sessions.items())
            if not sess.get("users")
            and (now - sess.get("_empty_since", now)) > SESSION_EXPIRY_S
        ]
        for sid in stale_ids:
            sessions.pop(sid, None)
            sign_buffers.pop(sid, None)
            task = sign_tasks.pop(sid, None)
            if task and not task.done():
                task.cancel()
            logger.info("[Reaper] Session '%s' expired and removed", sid)

        # Weekly: purge conversation messages older than 90 days (ARCH-5)
        if (now - _last_retention_sweep) >= _RETENTION_SWEEP_INTERVAL_S:
            try:
                from backend.services.history_db import delete_old_messages
                deleted = await delete_old_messages(days=90)
                logger.info("[Reaper] Retention sweep: deleted %d messages older than 90 days", deleted)
            except Exception as _ret_err:
                logger.warning("[Reaper] Retention sweep failed: %s", _ret_err)
            _last_retention_sweep = now

