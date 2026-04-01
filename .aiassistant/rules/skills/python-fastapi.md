---
name: python-fastapi
description: >
  Best practices for FastAPI backends: async/await patterns, Pydantic validation, dependency injection,
  WebSocket handling, background tasks, error handling, and service layer architecture.
  Activate when working on any Python backend code in FastAPI — routes, services, middleware, models,
  WebSocket handlers, Pydantic schemas, or async functions. Also activate when the user asks
  "how do I structure this in Python?", "is this the right way to use FastAPI?", "async best practices",
  "Pydantic model", "dependency injection", or "background tasks".
---

# Python FastAPI Best Practices

FastAPI is powerful but easy to misuse. These patterns keep the Amandla backend
clean, safe, and easy to maintain.

---

## Part 1 — Project Structure

```
backend/
├── main.py              ← App creation, startup events, route registration ONLY
├── middleware.py        ← Rate limiting, CORS, logging middleware
├── models/              ← Pydantic request/response models (data shapes)
│   ├── __init__.py
│   └── messages.py
├── services/            ← Business logic — one file per domain
│   ├── __init__.py
│   ├── sign_maps.py     ← English → SASL mappings (single source of truth)
│   ├── whisper_service.py
│   ├── ollama_service.py
│   └── claude_service.py
└── utils/               ← Shared utilities (logging, helpers)
    └── __init__.py
```

**Rule:** `main.py` registers routes and handles WebSocket connections — but all actual logic
goes in `services/`. Routes should be thin wrappers around service calls.

---

## Part 2 — Pydantic Models (Data Validation)

Pydantic validates data automatically. Use it for ALL request/response shapes.

```python
# models/messages.py
from pydantic import BaseModel, Field, field_validator

class TranslationRequest(BaseModel):
    """Request shape for text-to-SASL translation."""
    text: str = Field(..., min_length=1, max_length=5000)
    language: str | None = Field(None, description="Source language (None = English)")
    request_id: str = Field(..., min_length=1)

    @field_validator('text')
    @classmethod
    def text_must_not_be_whitespace_only(cls, value: str) -> str:
        """Rejects text that is all whitespace."""
        if not value.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        return value.strip()

class TranslationResponse(BaseModel):
    """Response shape for text-to-SASL translation."""
    success: bool
    signs: list[str] = []
    request_id: str
    error: str | None = None  # User-friendly error message only
```

---

## Part 3 — Async/Await Patterns

FastAPI is async-first. Use `async def` for routes and any I/O operation.

```python
# ✅ Correct — async route with proper error handling
@app.post("/speech", response_model=TranscriptionResponse)
async def transcribe_speech(audio: UploadFile = File(...)):
    """
    Transcribes uploaded audio using Whisper.
    
    Args:
        audio: Audio file (MP3, WAV, M4A), max 10MB
    
    Returns:
        TranscriptionResponse with transcribed text
    """
    # Validate file size before processing
    if audio.size > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Audio file exceeds maximum size of 10MB"
        )
    
    try:
        transcription = await whisper_service.transcribe(await audio.read())
        return TranscriptionResponse(success=True, text=transcription)
    except WhisperServiceError as error:
        # Log the real error, but don't expose it to the user
        logger.error(f"Whisper transcription failed: {error}")
        raise HTTPException(
            status_code=500,
            detail="Transcription service unavailable. Please try again."
        )

# ❌ Wrong — blocking I/O in an async route freezes all other requests
@app.post("/bad-example")
async def bad_route():
    import time
    time.sleep(5)   # This blocks the entire event loop!
    return {"done": True}

# ✅ Correct — run blocking I/O in a thread pool
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()

async def run_blocking(func, *args):
    """Runs a blocking function without blocking the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)
```

---

## Part 4 — WebSocket Handler Pattern

```python
# Clean WebSocket handler structure
@app.websocket("/ws/{session_id}/{role}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, role: str):
    """
    Main WebSocket endpoint for all real-time communication.
    
    Args:
        session_id: Unique session identifier (format: amandla-[timestamp]-[hex])
        role: Client role — must be 'hearing', 'deaf', or 'rights'
    """
    # 1. Validate inputs FIRST — before accepting the connection
    if role not in VALID_ROLES:
        await websocket.close(code=4001, reason=f"Invalid role: {role}")
        return
    
    if not _is_valid_session_id(session_id):
        await websocket.close(code=4002, reason="Invalid session ID format")
        return
    
    # 2. Accept the connection
    await websocket.accept()
    _register_client(session_id, role, websocket)
    
    try:
        # 3. Message loop
        async for raw_message in websocket.iter_json():
            await _handle_message(session_id, role, raw_message, websocket)
    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session_id}/{role}")
    except Exception as error:
        logger.error(f"WebSocket error for {session_id}/{role}: {error}")
    finally:
        # 4. ALWAYS clean up — even if there's an exception
        _unregister_client(session_id, role)
        await _cleanup_session(session_id)

def _is_valid_session_id(session_id: str) -> bool:
    """Returns True if session ID matches expected format: amandla-[digits]-[hex]."""
    import re
    return bool(re.match(r'^amandla-\d+-[a-f0-9]+$', session_id))
```

---

## Part 5 — Service Layer Pattern

Services contain business logic. They don't know about HTTP or WebSocket.

```python
# services/ollama_service.py
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Constants at the top — never magic numbers
OLLAMA_TIMEOUT_SECONDS = 30
OLLAMA_MAX_RETRIES = 2

async def generate_sasl_translation(text: str) -> Optional[str]:
    """
    Calls Ollama to generate an SASL gloss translation.
    
    Args:
        text: English text to translate to SASL gloss
        
    Returns:
        SASL gloss string, or None if translation fails
    """
    config = _get_ollama_config()
    
    for attempt in range(OLLAMA_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{config['base_url']}/api/generate",
                    json={"model": config['model'], "prompt": _build_prompt(text)}
                )
                response.raise_for_status()
                return response.json()["response"]
        except httpx.TimeoutException:
            logger.warning(f"Ollama timeout on attempt {attempt + 1}/{OLLAMA_MAX_RETRIES}")
        except httpx.RequestError as error:
            logger.error(f"Ollama connection error: {error}")
            return None
    
    logger.error(f"Ollama failed after {OLLAMA_MAX_RETRIES} attempts")
    return None

def _get_ollama_config() -> dict:
    """Reads Ollama configuration from environment variables."""
    import os
    return {
        "base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        "model": os.environ.get("OLLAMA_MODEL", "amandla")
    }

def _build_prompt(text: str) -> str:
    """Builds the SASL translation prompt for Ollama."""
    return f"Translate the following English to SASL gloss notation: {text}"
```

---

## Part 6 — Environment Variables (The Right Way)

```python
# ✅ Correct — read from environment, never hardcode
import os

# At module level — read once
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8000"))

# ❌ Wrong — hardcoded
WHISPER_MODEL = "small"  # What if prod needs a different model?
```

---

## Part 7 — Logging Best Practices

```python
import logging

# Each module gets its own logger
logger = logging.getLogger(__name__)

# Log levels:
# DEBUG   — detailed dev info (don't leave in production)
# INFO    — normal operations ("session created", "transcription complete")
# WARNING — something unexpected but not broken ("Ollama slow, retrying")
# ERROR   — something broke, needs attention ("Whisper failed for session X")
# CRITICAL — app cannot continue ("Database connection lost")

# ✅ Good logging
logger.info(f"Session created: {session_id} with {len(roles)} roles")
logger.error(f"Translation failed for session {session_id}: {type(error).__name__}")

# ❌ Bad — never log sensitive data
logger.info(f"User input: {raw_user_text}")  # Could contain PII
logger.debug(f"API key used: {api_key}")     # Security violation
```

---

## Environment Notes

**In Claude Code (terminal):**
```bash
# Check for blocking I/O in async functions
grep -rn "time.sleep\|requests.get\|requests.post" backend/ --include="*.py"

# Run with auto-reload for development
uvicorn backend.main:app --reload --log-level debug

# Check types
mypy backend/ --ignore-missing-imports
```

**In Claude.ai (browser):** Always show the full function with docstring, type hints, and error handling.
Never show a partial function without error handling — it'll be copied as-is.
