"""
AMANDLA — End-to-end WebSocket handler test.
Tests all 5 new WS handlers added in the March 29 fix.

Usage:
    1. Start backend: python -m uvicorn backend.main:app --port 8000
    2. Run this:      python scripts/test_all_ws_handlers.py
"""
import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("ERROR: pip install websockets")
    sys.exit(1)

WS_URI = "ws://localhost:8000/ws/test-handlers/hearing"
TIMEOUT_SECONDS = 10
PASS_COUNT = 0
FAIL_COUNT = 0


def result(name, passed, detail=""):
    """Print a test result line and update counters."""
    global PASS_COUNT, FAIL_COUNT
    icon = "✅" if passed else "❌"
    if passed:
        PASS_COUNT += 1
    else:
        FAIL_COUNT += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  {icon} {name}{suffix}")


async def run_tests():
    """Connect to WS and test each new handler."""
    print("\n=== AMANDLA WebSocket Handler Tests ===\n")

    async with websockets.connect(WS_URI) as ws:
        # 1. Connection test — expect status message
        raw = await asyncio.wait_for(ws.recv(), timeout=TIMEOUT_SECONDS)
        msg = json.loads(raw)
        result(
            "WS Connection",
            msg.get("type") == "status" and msg.get("status") == "connected",
            f"session_id={msg.get('session_id')}",
        )

        # 2. status_request — test request_id round-trip
        await ws.send(json.dumps({"type": "status_request", "request_id": 42}))
        raw = await asyncio.wait_for(ws.recv(), timeout=TIMEOUT_SECONDS)
        resp = json.loads(raw)
        result(
            "status_request handler",
            resp.get("request_id") == 42 and "qwen" in resp,
            f"qwen={resp.get('qwen')}, whisper={resp.get('whisper')}",
        )

        # 3. rights_analyze — with valid description
        await ws.send(json.dumps({
            "type": "rights_analyze",
            "request_id": 43,
            "description": "I was denied access to a building because I use a wheelchair.",
            "incident_type": "public access",
        }))
        raw = await asyncio.wait_for(ws.recv(), timeout=30)
        resp = json.loads(raw)
        result(
            "rights_analyze handler",
            resp.get("request_id") == 43 and "error" not in resp,
            f"keys={list(resp.keys())}",
        )

        # 4. rights_analyze — missing description (validation test)
        await ws.send(json.dumps({
            "type": "rights_analyze",
            "request_id": 44,
        }))
        raw = await asyncio.wait_for(ws.recv(), timeout=TIMEOUT_SECONDS)
        resp = json.loads(raw)
        result(
            "rights_analyze validation",
            resp.get("request_id") == 44 and "error" in resp,
            f"error={resp.get('error', 'none')}",
        )

        # 5. rights_letter — missing fields (validation test)
        await ws.send(json.dumps({
            "type": "rights_letter",
            "request_id": 45,
            "description": "Test",
        }))
        raw = await asyncio.wait_for(ws.recv(), timeout=TIMEOUT_SECONDS)
        resp = json.loads(raw)
        result(
            "rights_letter validation",
            resp.get("request_id") == 45 and "error" in resp,
            f"error={resp.get('error', 'none')}",
        )

        # 6. emergency — broadcast test (we get it back as sender)
        await ws.send(json.dumps({
            "type": "emergency",
            "sender": "hearing",
        }))
        raw = await asyncio.wait_for(ws.recv(), timeout=TIMEOUT_SECONDS)
        resp = json.loads(raw)
        result(
            "emergency broadcast",
            resp.get("type") == "emergency",
            f"received back as broadcast",
        )

        # 7. text → signs pipeline (no deaf connected, so turn msg comes back)
        await ws.send(json.dumps({
            "type": "text",
            "text": "hello",
            "sender": "hearing",
        }))
        raw = await asyncio.wait_for(ws.recv(), timeout=TIMEOUT_SECONDS)
        resp = json.loads(raw)
        result(
            "text → signs pipeline",
            resp.get("type") == "turn" and resp.get("speaker") == "hearing",
            f"type={resp.get('type')}",
        )

        # 8. sasl_text message — deaf typed a reply (no hearing connected)
        # Expect a turn broadcast back to the same window since it's the only user.
        await ws.send(json.dumps({
            "type": "sasl_text",
            "text": "HELP DOCTOR",
            "sender": "deaf",  # Note: we're sending as hearing WS but simulating deaf content
            "timestamp": 0,
        }))
        # We expect a turn indicator back (broadcast_all includes sender)
        raw = await asyncio.wait_for(ws.recv(), timeout=TIMEOUT_SECONDS)
        resp = json.loads(raw)
        result(
            "sasl_text handler (no error)",
            resp.get("type") in ("turn", "sasl_text", "deaf_speech"),
            f"type={resp.get('type')}",
        )

        # 9. Duplicate connect guard — send connect message with different session,
        # verify the old session still responds correctly (backend is stateless per session).
        # Open a SECOND connection to verify the backend handles it gracefully.
        async with websockets.connect("ws://localhost:8000/ws/test-dup-guard/hearing") as ws2:
            raw2 = await asyncio.wait_for(ws2.recv(), timeout=TIMEOUT_SECONDS)
            resp2 = json.loads(raw2)
            result(
                "Second session connects independently",
                resp2.get("type") == "status" and resp2.get("session_id") == "test-dup-guard",
                f"session_id={resp2.get('session_id')}",
            )

    # Summary
    total = PASS_COUNT + FAIL_COUNT
    print(f"\n{'='*42}")
    print(f"  Results: {PASS_COUNT}/{total} passed")
    if FAIL_COUNT > 0:
        print(f"  ⚠ {FAIL_COUNT} test(s) FAILED")
    else:
        print(f"  🎉 ALL TESTS PASSED")
    print(f"{'='*42}\n")
    return FAIL_COUNT == 0


if __name__ == "__main__":
    try:
        ok = asyncio.run(run_tests())
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        print("   Is the backend running? (python -m uvicorn backend.main:app --port 8000)")
        sys.exit(1)

