---
name: testing-strategy
description: >
  Guides writing tests for Python FastAPI backends, JavaScript Electron frontends, WebSocket handlers,
  and sign language/avatar logic. Activate when the user asks "how do I test this?", "write tests for X",
  "set up testing", "what tests do I need?", "TDD", "unit test", "integration test", "test coverage",
  or when code is written and has NO tests — always suggest tests after new functionality is built.
  Also activate when a bug is found — good tests prevent it from coming back.
---

# Testing Strategy Skill

Tests are your safety net. They catch bugs before users do, make refactoring safe,
and document what the code is supposed to do. For Amandla — which serves disabled users —
a crash or wrong translation is not just annoying, it fails the people who depend on it.

---

## The Testing Pyramid

```
         ▲ E2E Tests (few, slow, but catch real user flows)
        ▲▲▲
       ▲▲▲▲▲ Integration Tests (moderate, test components together)
      ▲▲▲▲▲▲▲
     ▲▲▲▲▲▲▲▲▲ Unit Tests (many, fast, test one thing at a time)
```

Start with unit tests, add integration tests for critical paths, and E2E tests for the most
important user journeys.

---

## Part 1 — Python Backend Testing (pytest)

### Setup
```bash
pip install pytest pytest-asyncio httpx pytest-cov --break-system-packages
```

Create `tests/` directory:
```
tests/
├── __init__.py
├── conftest.py          ← shared fixtures
├── unit/
│   ├── test_sign_maps.py
│   ├── test_sasl_transformer.py
│   └── test_ollama_service.py
└── integration/
    ├── test_websocket.py
    └── test_speech_endpoint.py
```

### conftest.py Pattern
```python
# conftest.py — shared test fixtures for the whole test suite
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.fixture
def client():
    """Provides a synchronous test client for simple HTTP endpoint tests."""
    return TestClient(app)

@pytest.fixture
async def async_client():
    """Provides an async test client for async endpoint tests."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

@pytest.fixture
def sample_session_id():
    """Returns a valid Amandla session ID for testing."""
    return "amandla-1234567890-abc123"
```

### Unit Test Pattern
```python
# test_sasl_transformer.py
import pytest
from sasl_transformer.transformer import SASLTransformer

class TestSASLTransformer:
    """Tests for the SASL grammar transformer."""

    def test_english_to_sasl_basic_sentence(self):
        """Basic sentence should be converted to SASL word order (SOV)."""
        transformer = SASLTransformer()
        result = transformer.transform("I am going to the store")
        assert "STORE" in result
        assert "GO" in result

    def test_modal_verbs_preserved(self):
        """Modal verbs must NOT be treated as filler — they are SASL signs."""
        transformer = SASLTransformer()
        result = transformer.transform("I must go")
        assert "MUST" in result

    def test_empty_input_returns_empty(self):
        """Empty input should return empty list, not crash."""
        transformer = SASLTransformer()
        result = transformer.transform("")
        assert result == [] or result == ""

    def test_finish_marker_preserved(self):
        """FINISH aspect marker must survive transformation."""
        transformer = SASLTransformer()
        result = transformer.transform("I ate already")
        assert "FINISH" in result
```

### WebSocket Integration Test Pattern
```python
# test_websocket.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app

def test_websocket_hearing_role_connects():
    """Hearing role should connect successfully to a valid session."""
    client = TestClient(app)
    session_id = "amandla-test-abc123"
    
    with client.websocket_connect(f"/ws/{session_id}/hearing") as ws:
        ws.send_json({"type": "text", "text": "hello", "request_id": "req-1"})
        data = ws.receive_json()
        assert data["type"] in ["translating", "signs", "error"]

def test_invalid_role_rejected():
    """Unknown WebSocket role should not be accepted."""
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/test-session/unknown_role") as ws:
            pass

def test_oversized_text_message_rejected():
    """Text messages over 5000 characters must be rejected."""
    client = TestClient(app)
    with client.websocket_connect("/ws/amandla-test-abc/hearing") as ws:
        ws.send_json({"type": "text", "text": "x" * 5001, "request_id": "req-1"})
        data = ws.receive_json()
        assert data["type"] == "error"
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=backend --cov=sasl_transformer --cov-report=html

# Run only fast unit tests
pytest tests/unit/

# Run a specific test
pytest tests/unit/test_sasl_transformer.py::TestSASLTransformer::test_modal_verbs_preserved -v
```

---

## Part 2 — JavaScript Frontend Testing (Jest / Vitest)

### Setup for Electron/Browser JS
```bash
npm install --save-dev jest @testing-library/dom
# or for Vite-based projects:
npm install --save-dev vitest
```

### Unit Test Pattern (Signs Library)
```javascript
// tests/signs_library.test.js

import { sentenceToSigns, fingerspell } from '../signs_library.js';

describe('sentenceToSigns', () => {
  test('returns array of sign objects for known words', () => {
    const signs = sentenceToSigns('hello world');
    expect(Array.isArray(signs)).toBe(true);
    expect(signs.length).toBeGreaterThan(0);
  });

  test('fingerspells unknown words letter by letter', () => {
    const signs = sentenceToSigns('xyzabc');
    // Unknown word should result in fingerspelled letters
    expect(signs.every(s => s.type === 'fingerspell' || s.type === 'sign')).toBe(true);
  });

  test('empty string returns empty array without crashing', () => {
    const signs = sentenceToSigns('');
    expect(signs).toEqual([]);
  });

  test('preserves FINISH marker in past tense', () => {
    const signs = sentenceToSigns('I ate');
    const hasFinish = signs.some(s => s.name === 'FINISH' || s.gloss === 'FINISH');
    expect(hasFinish).toBe(true);
  });
});

describe('fingerspell', () => {
  test('converts each letter to a sign', () => {
    const signs = fingerspell('ABC');
    expect(signs.length).toBe(3);
  });

  test('handles lowercase input', () => {
    const signs = fingerspell('abc');
    expect(signs.length).toBe(3);
  });
});
```

---

## Part 3 — What to Test First (Priority Order)

For Amandla specifically, test these first — highest risk of failure, highest user impact:

1. **SASL Transformer** — Wrong translations = wrong communication for deaf users
2. **WebSocket message routing** — Messages going to the wrong window is critical
3. **Sign maps** — Modal verbs not being treated as filler
4. **Input validation** — Oversized messages, invalid session IDs, unknown roles
5. **Error handling** — Backend crashes should not crash the Electron app
6. **Fingerspelling fallback** — When a word isn't in the library, fallback must work

---

## Part 4 — Test Quality Rules

Good tests follow **FIRST**:
- **Fast** — Unit tests run in milliseconds. If a test takes >1 second, it's probably doing too much.
- **Independent** — Tests don't depend on each other. Each test sets up its own state.
- **Repeatable** — Same result every time, no matter when or where they run.
- **Self-validating** — Clear pass/fail. No manual inspection needed.
- **Timely** — Written at the same time as the code, not months later.

Bad test smells:
- `time.sleep()` in tests (use mocks instead)
- Tests that only work on your machine
- Tests that always pass (testing nothing real)
- Giant test functions that test 10 things at once

---

## Part 5 — Mocking External Services

In tests, you don't want to actually call Ollama, Claude API, or Whisper. Mock them:

```python
# Mocking the Ollama service in tests
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_text_processing_calls_ollama(async_client):
    """Backend should call Ollama to process SASL translation."""
    with patch('backend.services.ollama_service.generate', new_callable=AsyncMock) as mock_ollama:
        mock_ollama.return_value = "HELLO WORLD"
        
        # Test the endpoint
        response = await async_client.post('/speech', json={'text': 'hello world'})
        
        assert mock_ollama.called
        assert response.status_code == 200
```

---

## Environment Notes

**In Claude Code (terminal):**
```bash
# Python tests
pytest --tb=short -v

# JavaScript tests  
npm test

# Coverage with HTML report
pytest --cov=. --cov-report=html && open htmlcov/index.html
```

**In Claude.ai (browser):** Show test code and tell the user to create the files.
Ask "what part of the code feels most risky — let's test that first."
