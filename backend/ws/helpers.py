"""WebSocket broadcast helpers for AMANDLA.

Small utility functions used by the WebSocket handler to send messages
safely to one or more connected clients.
"""

import asyncio


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

    Args:
        session:   The session dict containing connected users.
        sender_ws: The WebSocket that originated the message (excluded).
        msg:       The JSON-serialisable dict to broadcast.
    """
    targets = [ws for ws in session["users"].values() if ws is not sender_ws]
    if targets:
        await asyncio.gather(*(send_safe(ws, msg) for ws in targets))


async def broadcast_all(session: dict, msg: dict) -> None:
    """Send msg to every user in session including sender (parallel).

    Args:
        session: The session dict containing connected users.
        msg:     The JSON-serialisable dict to broadcast.
    """
    targets = list(session["users"].values())
    if targets:
        await asyncio.gather(*(send_safe(ws, msg) for ws in targets))

