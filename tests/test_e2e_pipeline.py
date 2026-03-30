"""AMANDLA — End-to-end pipeline test (TEST-3).

Tests the full communication round-trip:
  1. Hearing sends text -> backend translates -> deaf receives 'signs'
  2. Deaf sends sign -> backend debounces -> hearing receives 'deaf_speech'
  3. Deaf sends assist_phrase -> hearing receives 'deaf_speech' directly
  4. Emergency broadcast reaches both windows

Requires the backend to be running on port 8000:
    python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

Run with:
    python tests/test_e2e_pipeline.py
    -- or --
    python -m pytest tests/test_e2e_pipeline.py -v
"""

import asyncio
import json
import sys
import os
import urllib.request

# Ensure project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import websockets
except ImportError:
    print("ERROR: pip install websockets")
    sys.exit(1)

# -- Constants ---------------------------------------------------------
BACKEND_URL = "http://localhost:8000"
WS_BASE = "ws://localhost:8000/ws"
TIMEOUT_S = 15  # generous timeout -- Ollama/rule-based may be slow
SESSION_ID = "e2e-test-pipeline"

# -- Counters ----------------------------------------------------------
PASS_COUNT = 0
FAIL_COUNT = 0


def result(name, passed, detail=""):
    """Print and tally a single test result."""
    global PASS_COUNT, FAIL_COUNT
    if passed:
        PASS_COUNT += 1
        tag = "PASS"
    else:
        FAIL_COUNT += 1
        tag = "FAIL"
    line = "  [{}] {}".format(tag, name)
    if detail:
        line += " -- " + str(detail)
    print(line)


def fetch_session_secret():
    """Fetch the session authentication token from the backend."""
    url = "{}/auth/session-secret".format(BACKEND_URL)
    with urllib.request.urlopen(url) as resp:
        data = json.loads(resp.read().decode())
    return data["session_secret"]


async def drain(ws, timeout=0.3):
    """Drain all pending messages from a WebSocket, returning them as a list."""
    messages = []
    try:
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            messages.append(json.loads(raw))
    except (asyncio.TimeoutError, Exception):
        pass
    return messages


async def recv_until(ws, msg_type, timeout=TIMEOUT_S):
    """Receive messages until one with the given type appears, or timeout.

    Args:
        ws:       The WebSocket connection.
        msg_type: The 'type' field to wait for.
        timeout:  Maximum seconds to wait.

    Returns:
        The matching message dict, or None if timeout.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            return None
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            msg = json.loads(raw)
            if msg.get("type") == msg_type:
                return msg
        except asyncio.TimeoutError:
            return None
        except Exception:
            return None


async def run_tests():
    """Execute all end-to-end pipeline tests."""
    print("")
    print("AMANDLA E2E Pipeline Test (TEST-3)")
    print("=" * 50)

    # -- Fetch session token -----------------------------------
    try:
        token = fetch_session_secret()
        print("  Token acquired (length={})".format(len(token)))
    except Exception as exc:
        print("")
        print("[FAIL] Cannot reach backend: {}".format(exc))
        print("   Start the backend first: python -m uvicorn backend.main:app --port 8000")
        return False

    ws_url_hearing = "{}/{}/hearing?token={}".format(WS_BASE, SESSION_ID, token)
    ws_url_deaf = "{}/{}/deaf?token={}".format(WS_BASE, SESSION_ID, token)

    # -- Connect BOTH windows to the same session --------------
    async with websockets.connect(ws_url_hearing) as hearing_ws, \
               websockets.connect(ws_url_deaf) as deaf_ws:

        # Both should receive a status message on connect
        hearing_status = await recv_until(hearing_ws, "status", timeout=5)
        deaf_status = await recv_until(deaf_ws, "status", timeout=5)

        result(
            "1. Hearing connects",
            hearing_status is not None and hearing_status.get("session_id") == SESSION_ID,
            "session_id={}".format(hearing_status.get("session_id") if hearing_status else "NONE"),
        )
        result(
            "2. Deaf connects to same session",
            deaf_status is not None and deaf_status.get("session_id") == SESSION_ID,
            "session_id={}".format(deaf_status.get("session_id") if deaf_status else "NONE"),
        )

        # -- TEST: Hearing text -> Deaf receives signs ---------
        print("")
        print("  Hearing -> Deaf pipeline:")
        await hearing_ws.send(json.dumps({
            "type": "text",
            "text": "hello",
            "sender": "hearing",
        }))

        # Deaf should receive 'translating' then 'signs'
        translating_msg = await recv_until(deaf_ws, "translating", timeout=TIMEOUT_S)
        result(
            "3. Deaf receives 'translating' indicator",
            translating_msg is not None,
            "type={}".format(translating_msg.get("type") if translating_msg else "TIMEOUT"),
        )

        signs_msg = await recv_until(deaf_ws, "signs", timeout=TIMEOUT_S)
        result(
            "4. Deaf receives 'signs' with SASL gloss",
            signs_msg is not None and isinstance(signs_msg.get("signs"), list),
            "signs={}".format(signs_msg.get("signs") if signs_msg else "TIMEOUT"),
        )

        # Verify HELLO is in the signs list (rule-based fallback guaranteed)
        if signs_msg:
            signs_list = signs_msg.get("signs", [])
            has_hello = "HELLO" in signs_list
            result(
                "5. Signs contain 'HELLO'",
                has_hello,
                "signs={}".format(signs_list),
            )
        else:
            result("5. Signs contain 'HELLO'", False, "No signs message received")

        # Hearing receives both 'turn' and 'sasl_ack' (order varies).
        # Collect all messages from hearing within the timeout window.
        hearing_msgs = await drain(hearing_ws, timeout=2)
        ack_msg = next((m for m in hearing_msgs if m.get("type") == "sasl_ack"), None)
        turn_msg = next((m for m in hearing_msgs if m.get("type") == "turn"), None)

        result(
            "6. Hearing receives 'sasl_ack'",
            ack_msg is not None and "sasl_gloss" in (ack_msg or {}),
            "gloss={}".format(ack_msg.get("sasl_gloss") if ack_msg else "TIMEOUT"),
        )
        result(
            "7. Turn indicator broadcast (hearing)",
            turn_msg is not None and turn_msg.get("speaker") == "hearing",
            "speaker={}".format(turn_msg.get("speaker") if turn_msg else "TIMEOUT"),
        )

        # -- TEST: Deaf sign -> Hearing receives deaf_speech ---
        print("")
        print("  Deaf -> Hearing pipeline (sign button):")

        # Drain any remaining messages from hearing_ws first
        await drain(hearing_ws, timeout=0.5)

        await deaf_ws.send(json.dumps({
            "type": "sign",
            "text": "HELP",
            "sender": "deaf",
        }))

        # Hearing should get the sign broadcast immediately
        sign_msg = await recv_until(hearing_ws, "sign", timeout=5)
        result(
            "8. Hearing receives 'sign' broadcast",
            sign_msg is not None and sign_msg.get("text") == "HELP",
            "text={}".format(sign_msg.get("text") if sign_msg else "TIMEOUT"),
        )

        # After 1.5s debounce, hearing should receive 'deaf_speech'
        deaf_speech_msg = await recv_until(hearing_ws, "deaf_speech", timeout=8)
        result(
            "9. Hearing receives 'deaf_speech' after debounce",
            deaf_speech_msg is not None and deaf_speech_msg.get("text"),
            "text={}".format(deaf_speech_msg.get("text") if deaf_speech_msg else "TIMEOUT"),
        )

        # -- TEST: Assist phrase bypass (BUG-2 fix) ------------
        print("")
        print("  Deaf -> Hearing pipeline (assist phrase):")

        await drain(hearing_ws, timeout=0.5)

        await deaf_ws.send(json.dumps({
            "type": "assist_phrase",
            "text": "I need water please",
            "sender": "deaf",
        }))

        assist_msg = await recv_until(hearing_ws, "deaf_speech", timeout=5)
        result(
            "10. Hearing receives assist phrase as 'deaf_speech'",
            assist_msg is not None and assist_msg.get("text") == "I need water please",
            "text={}".format(assist_msg.get("text") if assist_msg else "TIMEOUT"),
        )

        # Verify it was NOT run through SASL reconstruction (source=assist)
        if assist_msg:
            result(
                "11. Assist phrase has source='assist' (no reconstruction)",
                assist_msg.get("source") == "assist",
                "source={}".format(assist_msg.get("source")),
            )
        else:
            result("11. Assist phrase has source='assist'", False, "No message received")

        # -- TEST: Emergency broadcast -------------------------
        print("")
        print("  Emergency broadcast:")

        await drain(hearing_ws, timeout=0.3)
        await drain(deaf_ws, timeout=0.3)

        await deaf_ws.send(json.dumps({
            "type": "emergency",
            "sender": "deaf",
        }))

        emg_hearing = await recv_until(hearing_ws, "emergency", timeout=5)
        emg_deaf = await recv_until(deaf_ws, "emergency", timeout=5)

        result(
            "12. Hearing receives emergency",
            emg_hearing is not None and emg_hearing.get("type") == "emergency",
            "received" if emg_hearing else "TIMEOUT",
        )
        result(
            "13. Deaf receives emergency (broadcast_all includes sender)",
            emg_deaf is not None and emg_deaf.get("type") == "emergency",
            "received" if emg_deaf else "TIMEOUT",
        )

        # -- TEST: Invalid role rejection ----------------------
        print("")
        print("  Security checks:")
        try:
            bad_role_url = "{}/{}/hacker?token={}".format(WS_BASE, SESSION_ID, token)
            async with websockets.connect(bad_role_url) as bad_ws:
                # Should be closed immediately by backend
                try:
                    raw = await asyncio.wait_for(bad_ws.recv(), timeout=3)
                    result("14. Invalid role rejected", False, "Received: {}".format(raw))
                except websockets.exceptions.ConnectionClosed:
                    result("14. Invalid role rejected", True, "Connection closed by server")
        except websockets.exceptions.InvalidStatusCode:
            result("14. Invalid role rejected", True, "Connection refused by server")
        except Exception as exc:
            result("14. Invalid role rejected", True, "Rejected: {}".format(type(exc).__name__))

        # Bad token test
        try:
            bad_token_url = "{}/bad-session/hearing?token=wrong-token".format(WS_BASE)
            async with websockets.connect(bad_token_url) as bad_ws:
                try:
                    raw = await asyncio.wait_for(bad_ws.recv(), timeout=3)
                    result("15. Bad token rejected", False, "Received: {}".format(raw))
                except websockets.exceptions.ConnectionClosed:
                    result("15. Bad token rejected", True, "Connection closed by server")
        except websockets.exceptions.InvalidStatusCode:
            result("15. Bad token rejected", True, "Connection refused by server")
        except Exception as exc:
            result("15. Bad token rejected", True, "Rejected: {}".format(type(exc).__name__))

    # -- Summary -----------------------------------------------
    total = PASS_COUNT + FAIL_COUNT
    print("")
    print("=" * 50)
    print("  Results: {}/{} passed".format(PASS_COUNT, total))
    if FAIL_COUNT > 0:
        print("  WARNING: {} test(s) FAILED".format(FAIL_COUNT))
    else:
        print("  ALL TESTS PASSED")
    print("=" * 50)
    print("")
    return FAIL_COUNT == 0


# -- Pytest integration ------------------------------------------------
# `pytest tests/test_e2e_pipeline.py -v` runs the whole suite as one test.
# The test is skipped if the backend is not running.

def test_e2e_pipeline():
    """Pytest wrapper: runs the full E2E pipeline test suite.

    Skipped if backend is not reachable on localhost:8000.
    """
    import pytest
    try:
        urllib.request.urlopen("{}/health".format(BACKEND_URL), timeout=2)
    except Exception:
        pytest.skip("Backend not running on localhost:8000 -- start it first")
    ok = asyncio.run(run_tests())
    assert ok, "E2E pipeline tests failed: {} failure(s)".format(FAIL_COUNT)


if __name__ == "__main__":
    try:
        ok = asyncio.run(run_tests())
        sys.exit(0 if ok else 1)
    except Exception as exc:
        print("")
        print("[FAIL] Test suite crashed: {}".format(exc))
        print("   Is the backend running? python -m uvicorn backend.main:app --port 8000")
        sys.exit(1)

