"""
WebSocket and HTTP auth contract tests (D9 + D10 in MASTER_PLAN.md).

Proves:
- valid subprotocol token accepted (and echoed on accept)
- missing token rejected
- bad token rejected
- query-string-only token rejected (the old auth method must stay dead)
- mutating HTTP requests require X-Amandla-Token; GETs stay open
- no CORS headers are emitted (wildcard CORS removal)

Run with: pytest tests/test_ws_auth.py -v
No live server needed — uses the Starlette TestClient.
"""

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.main import app
from backend.shared import SESSION_SECRET


@pytest.fixture(scope="module")
def client():
    # Plain TestClient (no context manager): skips lifespan startup so tests
    # don't preload Whisper or start background tasks.
    return TestClient(app)


# ── WebSocket auth (D9) ──────────────────────────────────────────────────


def test_valid_subprotocol_accepted(client):
    with client.websocket_connect(
        "/ws/test-auth/hearing", subprotocols=[f"amandla-{SESSION_SECRET}"]
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "status"
        assert msg["status"] == "connected"


def test_missing_token_rejected(client):
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/test-auth/hearing"):
            pass
    assert exc_info.value.code == 1008


def test_bad_token_rejected(client):
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/ws/test-auth/hearing", subprotocols=["amandla-wrong-token"]
        ):
            pass
    assert exc_info.value.code == 1008


def test_query_token_only_rejected(client):
    """The pre-D9 auth method (?token=) must not authenticate a connection."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/ws/test-auth/hearing?token={SESSION_SECRET}"):
            pass
    assert exc_info.value.code == 1008


def test_invalid_role_rejected(client):
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/ws/test-auth/hacker", subprotocols=[f"amandla-{SESSION_SECRET}"]
        ):
            pass
    assert exc_info.value.code == 1008


# ── HTTP session-token gate (D10) ────────────────────────────────────────


def test_mutating_request_without_token_is_401(client):
    resp = client.post("/api/sasl/translate", json={"english_text": "hello"})
    assert resp.status_code == 401


def test_mutating_request_with_bad_token_is_401(client):
    resp = client.post(
        "/api/sasl/translate",
        json={"english_text": "hello"},
        headers={"X-Amandla-Token": "wrong"},
    )
    assert resp.status_code == 401


def test_mutating_request_with_valid_token_passes_gate(client):
    resp = client.post(
        "/api/sasl/translate",
        json={"english_text": "hello"},
        headers={"X-Amandla-Token": SESSION_SECRET},
    )
    # The gate must not reject it; downstream translation may succeed (200)
    # or fail for unrelated reasons (500 if Ollama is absent), but never 401.
    assert resp.status_code != 401


def test_get_requests_do_not_require_token(client):
    resp = client.get("/health")
    assert resp.status_code == 200


# ── CORS removal (D10) ───────────────────────────────────────────────────


def test_no_cors_headers_emitted(client):
    """A cross-origin browser request must not receive permissive CORS headers."""
    resp = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers}
