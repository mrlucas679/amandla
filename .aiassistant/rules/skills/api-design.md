---
name: api-design
description: >
  Guides the design of REST APIs, WebSocket message protocols, and backend endpoint contracts.
  Activate when the user asks to "add a new endpoint", "design an API", "add a WebSocket message type",
  "how should I structure this request/response", "what should the API look like", "new route", "new message type",
  "design the data flow", or when a new feature requires frontend↔backend communication.
  Also activate when reviewing existing endpoints that feel inconsistent or unclear.
---

# API Design Skill

Good API design means the frontend and backend can evolve independently, bugs are easier to find,
and new developers understand the contract immediately. Design the API before writing the implementation.

---

## Core Principle: Design the Contract First

Before writing any code, define:
1. What data goes IN (request shape)
2. What data comes OUT (response shape)
3. What can go wrong (error cases)
4. Who calls it and when

Write this as a simple spec — one paragraph or a JSON example. Get agreement on the contract,
then implement it. Changing an API after it's in use is painful.

---

## Part 1 — REST Endpoint Design

### Naming Conventions
```
GET    /resource          → list all
GET    /resource/{id}     → get one
POST   /resource          → create
PUT    /resource/{id}     → replace
PATCH  /resource/{id}     → partial update
DELETE /resource/{id}     → delete
```

For Amandla backend (FastAPI):
```
POST /speech              → upload audio for transcription
GET  /health              → liveness check
GET  /api/status          → AI service health
POST /rights/analyze      → analyze rights document
POST /rights/letter       → generate rights letter
```

### Request/Response Shape
Always use consistent shapes. For Amandla:

```python
# Request — always validate with Pydantic
from pydantic import BaseModel, Field

class TextRequest(BaseModel):
    """Request shape for text translation endpoint."""
    text: str = Field(..., min_length=1, max_length=5000, description="Text to translate to SASL")
    language: str | None = Field(None, description="Source language code (None = English)")
    request_id: str = Field(..., description="Client-generated ID for request/response matching")

# Response — always include success indicator
class TranslationResponse(BaseModel):
    """Response shape for text translation."""
    success: bool
    signs: list[str]
    original_text: str
    request_id: str  # Echo back the request_id for promise resolution
    error: str | None = None  # Only set if success=False
```

### HTTP Status Codes — Use Them Correctly
```
200 OK              → Request succeeded, here's the data
201 Created         → New resource created successfully
400 Bad Request     → Client sent invalid data (validation failed)
401 Unauthorized    → Not authenticated
403 Forbidden       → Authenticated but not allowed
404 Not Found       → Resource doesn't exist
422 Unprocessable   → Data format is right but content is invalid
429 Too Many Req    → Rate limit hit
500 Server Error    → Something broke on the server (never expose details)
```

### Error Response Shape
Never return raw Python exceptions. Always return structured errors:
```python
# ❌ Bad — exposes internal details
{"error": "KeyError: 'word_not_found' in sign_maps.py line 45"}

# ✅ Good — user-friendly, no internal leak
{"success": False, "error": "Translation failed. Please try again.", "error_code": "TRANSLATION_ERROR"}
```

---

## Part 2 — WebSocket Message Protocol

For Amandla, all real-time communication goes through WebSocket. The protocol must be consistent.

### Message Shape Contract
Every message MUST have a `type` field. That's how both sides know how to handle it.

```typescript
// Base message shape (all messages follow this)
interface BaseMessage {
  type: string;           // REQUIRED — determines how to handle this message
  request_id?: string;    // REQUIRED for request/response pairs, ABSENT for broadcasts
}

// Example: Hearing → Backend (request)
interface TextMessage extends BaseMessage {
  type: 'text';
  text: string;
  language: string | null;
  request_id: string;  // Present — backend echoes this back
}

// Example: Backend → Deaf (broadcast)
interface SignsMessage extends BaseMessage {
  type: 'signs';
  signs: string[];
  original_text: string;
  // No request_id — this is a broadcast, not a response to a specific request
}
```

### Amandla WebSocket Message Registry
When adding a new message type, document it here:

| Type | Direction | Has request_id? | Payload |
|------|-----------|-----------------|---------|
| `text` | Hearing → Backend | Yes | `{text, language}` |
| `speech_upload` | Hearing → Backend | Yes | `{audio_data, format}` |
| `signs` | Backend → Deaf | No (broadcast) | `{signs[], original_text}` |
| `translating` | Backend → Hearing | Yes (echo) | `{status}` |
| `deaf_speech` | Backend → Hearing | No (broadcast) | `{text}` |
| `sasl_text` | Backend → Deaf | No | `{gloss}` |
| `emergency` | Any → Backend | Yes | `{phrase}` |
| `status_request` | Any → Backend | Yes | `{}` |

### Adding a New Message Type — Checklist
Before adding any new message type:
- [ ] Does it fit an existing type? (Extend it instead of adding a new one)
- [ ] Is the direction clear? (Who sends it, who receives it?)
- [ ] Is `request_id` correct? (Requests get one, broadcasts don't)
- [ ] Is the payload documented in the registry above?
- [ ] Is it validated in `backend/main.py` before processing?
- [ ] Is it handled in the relevant renderer (`hearing.js`, `deaf.js`, `rights.js`)?

---

## Part 3 — API Versioning

If the API might change after users are using it, version from the start:
```
/api/v1/translate      ← current
/api/v2/translate      ← future (keep v1 working during migration)
```

For Amandla (desktop app where you control the version), versioning is less critical.
But for any web-facing API: **version it from day one**.

---

## Part 4 — Input Validation Rules

Every API endpoint must validate inputs BEFORE processing:

```python
# FastAPI + Pydantic does this automatically, but double-check:
class MessageHandler:
    
    MAX_TEXT_LENGTH = 5000
    MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10 MB
    VALID_ROLES = {"hearing", "deaf", "rights"}
    VALID_MESSAGE_TYPES = {"text", "speech_upload", "signs", "sign", ...}
    
    @staticmethod
    def validate_message(message: dict) -> tuple[bool, str | None]:
        """
        Validates an incoming WebSocket message.
        Returns (is_valid, error_message).
        """
        if "type" not in message:
            return False, "Message missing required 'type' field"
        
        if message["type"] not in MessageHandler.VALID_MESSAGE_TYPES:
            return False, f"Unknown message type: {message['type']}"
        
        if message.get("type") == "text":
            text = message.get("text", "")
            if len(text) > MessageHandler.MAX_TEXT_LENGTH:
                return False, f"Text exceeds maximum length of {MessageHandler.MAX_TEXT_LENGTH}"
        
        return True, None
```

---

## Part 5 — Documentation (OpenAPI / Swagger)

FastAPI generates Swagger docs automatically. Make them useful:

```python
@app.post(
    "/speech",
    response_model=TranscriptionResponse,
    summary="Transcribe audio to text",
    description="""
    Accepts audio file upload and returns transcription using Whisper.
    Supports MP3, WAV, M4A formats. Maximum file size: 10MB.
    Transcription language is auto-detected unless specified in .env.
    """,
    responses={
        200: {"description": "Transcription successful"},
        400: {"description": "Invalid audio format or file too large"},
        500: {"description": "Transcription service unavailable"}
    }
)
```

View the auto-generated docs at: `http://localhost:8000/docs`

---

## Environment Notes

**In Claude Code (terminal):**
```bash
# View current API docs
open http://localhost:8000/docs

# Test endpoints directly
curl -X POST http://localhost:8000/speech \
  -H "Content-Type: application/json" \
  -d '{"text": "hello world"}'
```

**In Claude.ai (browser):** Design the message/endpoint shape in writing first.
Show as JSON examples before writing any Python/JS code.
