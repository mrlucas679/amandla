"""WebSocket broadcast helpers for AMANDLA.

Small utility functions used by the WebSocket handler to send messages
safely to one or more connected clients.

Supports FEAT-8 (multi-user hearing): session["users"][role] may be either
a single WebSocket or a list of WebSockets. All helpers flatten both forms
transparently so the rest of the codebase never has to check.
"""

import asyncio
from typing import Any, Generator

try:
    from starlette.websockets import WebSocketState as _WSState
    _CONNECTED = _WSState.CONNECTED
except ImportError:
    _CONNECTED = None  # fallback — skip state check


def _iter_ws(session: dict) -> Generator[Any, None, None]:
    """Yield every active WebSocket connection in a session.

    Handles both single-socket and list-of-sockets per role (FEAT-8).
    Skips None entries defensively.
    """
    for role_ws in session.get("users", {}).values():
        if role_ws is None:
            continue
        if isinstance(role_ws, list):
            for ws in role_ws:
                if ws is not None and _ws_alive(ws):
                    yield ws
        else:
            if _ws_alive(role_ws):
                yield role_ws


def _ws_alive(ws) -> bool:
    """Return True if ws appears to be an open connection.

    Filters stale sockets from the hearing multi-user list (BUG-15).
    Falls back to True if state inspection is unavailable.
    """
    if _CONNECTED is None:
        return True
    try:
        return ws.client_state == _CONNECTED
    except Exception:
        return True


def get_role_ws(session: dict, role: str):
    """Return the first WebSocket for a role, or None if none connected.

    Safe for both single-socket and multi-socket roles.

    Args:
        session: The session dict.
        role:    The role name ('hearing', 'deaf', 'rights', 'interpreter').

    Returns:
        First WebSocket for the role, or None.
    """
    v = session["users"].get(role)
    if v is None:
        return None
    if isinstance(v, list):
        return v[0] if v else None
    return v


async def send_safe(ws, msg: dict) -> None:
    """Send a JSON message to a single WebSocket, swallowing errors.

    Args:
        ws:  The WebSocket connection to send to.
        msg: The JSON-serialisable dict to send.
    """
    try:
        await ws.send_json(msg)
    except Exception:
        pass


async def broadcast(session: dict, sender_ws, msg: dict) -> None:
    """Send msg to all users in session except sender (parallel).

    Handles multi-user roles (FEAT-8) — all sockets for all roles receive
    the message except the one that sent it.

    Args:
        session:   The session dict containing connected users.
        sender_ws: The WebSocket that originated the message (excluded).
        msg:       The JSON-serialisable dict to broadcast.
    """
    targets = [ws for ws in _iter_ws(session) if ws is not sender_ws]
    if targets:
        await asyncio.gather(*(send_safe(ws, msg) for ws in targets))


async def broadcast_all(session: dict, msg: dict) -> None:
    """Send msg to every user in session including sender (parallel).

    Handles multi-user roles (FEAT-8).

    Args:
        session: The session dict containing connected users.
        msg:     The JSON-serialisable dict to broadcast.
    """
    targets = list(_iter_ws(session))
    if targets:
        await asyncio.gather(*(send_safe(ws, msg) for ws in targets))

