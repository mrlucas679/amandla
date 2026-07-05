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


async def session_reaper() -> None:
    """Background loop: remove stale sessions with no active users.

    A session is considered stale when:
      - It has no connected WebSocket users (session["users"] is empty), AND
      - It has been empty for at least SESSION_EXPIRY_S seconds.

    The '_empty_since' timestamp is written to the session dict by the
    WebSocket handler's finally block when the last user disconnects.
    """
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

