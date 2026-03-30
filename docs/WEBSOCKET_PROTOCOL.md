# AMANDLA WebSocket Protocol Reference

> Last Updated: March 30, 2026  
> Authoritative source: `backend/ws/handler.py` + `src/preload/preload.js`

---

## Connection

### Endpoint

```
ws://localhost:8000/ws/{sessionId}/{role}?token={sessionSecret}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sessionId` | string (path) | Yes | Shared session identifier (e.g. `amandla-<base64url>`) |
| `role` | string (path) | Yes | One of: `hearing`, `deaf`, `rights` |
| `token` | string (query) | Yes | Session secret from `GET /auth/session-secret` |

### Connection lifecycle

1. Client sends `?token=<secret>` — validated with constant-time `hmac.compare_digest()`
2. If token is invalid → `close(1008, "Invalid or missing session token")`
3. If role is invalid → `close(1008, "Invalid role '<role>'")`
4. If session limit reached → `close(1013, "Too many active sessions")`
5. On success → server sends: `{ "type": "status", "status": "connected", "session_id": "..." }`

### Reconnection

The preload bridge auto-reconnects with exponential backoff:
- Initial delay: 1.5 s
- Max delay: 15 s
- Doubles each attempt, resets on successful connect

### Limits

| Limit | Value |
|-------|-------|
| Max concurrent sessions | 10 |
| Max text message length | 5,000 chars |
| Max audio upload size | 10 MB |
| Request timeout (client) | 60 s |
| Max outgoing payload (client) | 1 MB |
| Session expiry (idle) | 30 min |

---

## Message Types

All messages are JSON objects with a `type` field. Messages are divided into two categories:

- **Request/Response** — include a `request_id` field; the response echoes it back
- **Broadcast** — no `request_id`; sent to one or more session participants

---

### Request/Response Messages

These messages use `request_id` for promise resolution in the preload bridge. The client generates a unique numeric ID; the backend echoes it in the response.

---

#### `speech_upload` — Audio → Whisper → SASL signs

**Direction:** Hearing → Backend → Hearing (response) + Deaf (broadcast)  
**Rate limited:** Yes (2 s per session)  
**Sender role:** Any (typically hearing)

**Request:**
```json
{
  "type": "speech_upload",
  "audio_b64": "<base64 encoded audio>",
  "mime_type": "audio/webm",
  "sender": "hearing",
  "timestamp": 1711800000000,
  "request_id": 1
}
```

**Response (to sender):**
```json
{
  "request_id": 1,
  "text": "Hello how are you",
  "signs": ["HELLO", "HOW", "YOU"],
  "sasl_gloss": "HELLO HOW YOU",
  "language": "en",
  "confidence": 0.95
}
```

**Side effects:**
- Broadcasts `translating` to deaf window
- Broadcasts `signs` to deaf window (no `request_id`)
- Broadcasts `turn` with `speaker: "hearing"` to all

**Error response:**
```json
{
  "request_id": 1,
  "error": "Speech processing failed. Try typing instead."
}
```

---

#### `status_request` — AI service health check

**Direction:** Any → Backend → Same client  
**Rate limited:** No

**Request:**
```json
{
  "type": "status_request",
  "request_id": 2
}
```

**Response:**
```json
{
  "request_id": 2,
  "status": "ok",
  "qwen": "alive",
  "whisper": "ready",
  "sessions": 1
}
```

| Field | Values | Meaning |
|-------|--------|---------|
| `qwen` | `"alive"` / `"dead"` | Whether Ollama is reachable |
| `whisper` | `"ready"` / `"unavailable"` | Whether Whisper model is loaded |
| `sessions` | number | Count of active WebSocket sessions |

---

#### `rights_analyze` — Incident → Rights analysis

**Direction:** Rights → Backend → Rights  
**Rate limited:** Yes (30 s per session)

**Request:**
```json
{
  "type": "rights_analyze",
  "description": "My employer refused to provide a sign language interpreter...",
  "incident_type": "workplace",
  "request_id": 3
}
```

**Response:**
```json
{
  "request_id": 3,
  "analysis": "...",
  "laws_violated": ["Employment Equity Act", "..."],
  "recommendations": ["..."]
}
```

**Validation error:**
```json
{
  "request_id": 3,
  "error": "Missing required field: description"
}
```

---

#### `rights_letter` — Details → Formal complaint letter

**Direction:** Rights → Backend → Rights  
**Rate limited:** Yes (45 s per session)

**Request:**
```json
{
  "type": "rights_letter",
  "description": "My employer refused...",
  "user_name": "John Doe",
  "employer_name": "Acme Corp",
  "incident_date": "2026-03-15",
  "analysis": { "...from rights_analyze response..." },
  "request_id": 4
}
```

**Required fields:** `description`, `employer_name`, `incident_date`  
**Optional fields:** `user_name` (defaults to "The Complainant"), `analysis`

**Response:**
```json
{
  "request_id": 4,
  "letter": "Dear Sir/Madam...",
  "laws_cited": ["Employment Equity Act 55 of 1998", "..."]
}
```

**Validation error:**
```json
{
  "request_id": 4,
  "error": "Missing required fields: employer_name, incident_date"
}
```

---

### Broadcast Messages (Fire-and-Forget)

These messages do **not** use `request_id`. They are sent via `window.amandla.send()` and received via `window.amandla.onMessage()`.

---

#### `text` / `speech_text` — Hearing user typed or spoke

**Direction:** Hearing → Backend → Deaf (as `signs`) + All (as `turn`)  
**Sender role:** `hearing`

```json
{
  "type": "text",
  "text": "Hello how are you",
  "language": "en",
  "sender": "hearing",
  "timestamp": 1711800000000
}
```

**Backend actions:**
1. Sends `translating` to deaf window
2. Runs SASL pipeline: `text_to_sasl_signs(text)`
3. Broadcasts `signs` to deaf window (see below)
4. Broadcasts `turn` with `speaker: "hearing"` to all
5. Sends `sasl_ack` back to hearing window

> `speech_text` is a synonym for `text` — both are handled identically.

---

#### `signs` — SASL sign sequence for the avatar

**Direction:** Backend → Deaf (broadcast, excludes sender)  
**Generated by:** `_handle_text()` and `_handle_speech_upload()`

```json
{
  "type": "signs",
  "signs": ["HELLO", "HOW", "YOU"],
  "text": "HELLO HOW YOU",
  "original_english": "Hello, how are you?",
  "language": "en",
  "session_id": "amandla-abc123"
}
```

The deaf window calls `window.avatarPlaySigns(msg.signs, msg.text)` to animate.

---

#### `sasl_ack` — SASL translation acknowledgement

**Direction:** Backend → Hearing (sender only)  
**Generated by:** `_handle_text()`

```json
{
  "type": "sasl_ack",
  "sasl_gloss": "HELLO HOW YOU",
  "original_english": "Hello how are you"
}
```

Lets the hearing user see what the deaf person received.

---

#### `translating` — Translation in progress indicator

**Direction:** Backend → Deaf  
**Generated by:** `_handle_text()` and `_handle_speech_upload()`

```json
{
  "type": "translating",
  "session_id": "amandla-abc123"
}
```

Deaf window shows a loading indicator while the SASL pipeline runs.

---

#### `sign` — Deaf quick-sign button press

**Direction:** Deaf → Backend → Hearing (broadcast)  
**Sender role:** `deaf`

```json
{
  "type": "sign",
  "text": "HELLO",
  "sender": "deaf",
  "timestamp": 1711800000000
}
```

**Backend actions:**
1. Buffers the sign name in `sign_buffers[session_id]`
2. Starts/restarts a 1.5 s debounce timer
3. When timer fires → `signs_to_english(buffered_signs)` → sends `deaf_speech`
4. Broadcasts the `sign` message to hearing window (for real-time indicator)
5. Broadcasts `turn` with `speaker: "deaf"` to all

---

#### `sasl_text` — Deaf user typed SASL gloss

**Direction:** Deaf → Backend → Hearing (as `deaf_speech`)  
**Sender role:** `deaf`

```json
{
  "type": "sasl_text",
  "text": "HELLO HOW YOU",
  "sender": "deaf"
}
```

**Backend actions:**
1. Forwards `sasl_text` to hearing window (real-time indicator)
2. Splits with `split_sasl_gloss()` (longest-match for multi-word signs)
3. Runs `signs_to_english()` with 6 s timeout → falls back to `simple_signs_to_english()`
4. Sends `deaf_speech` to hearing window

---

#### `assist_phrase` — Assist-mode English phrase

**Direction:** Deaf → Backend → Hearing (as `deaf_speech`)  
**Sender role:** `deaf`

```json
{
  "type": "assist_phrase",
  "text": "I need help please",
  "sender": "deaf"
}
```

**Backend actions:**
1. Forwards directly to hearing as `deaf_speech` (no SASL reconstruction needed)
2. Response includes `"source": "assist"` field

---

#### `deaf_speech` — Reconstructed English from deaf signs

**Direction:** Backend → Hearing  
**Generated by:** `_handle_sasl_text()`, `_handle_assist_phrase()`, debounce flush

```json
{
  "type": "deaf_speech",
  "text": "Hello, how are you?",
  "signs": ["HELLO", "HOW", "YOU"],
  "sasl_original": "HELLO HOW YOU"
}
```

Or from assist mode:
```json
{
  "type": "deaf_speech",
  "text": "I need help please",
  "source": "assist"
}
```

The hearing window speaks this aloud via TTS.

---

#### `landmarks` — MediaPipe hand landmarks

**Direction:** Deaf → Backend  
**Sender role:** `deaf`

```json
{
  "type": "landmarks",
  "landmarks": [ [0.5, 0.3, 0.1], ... ],
  "handedness": "Right"
}
```

**Backend actions:**
1. Passes to `ollama_service.recognize_sign()`
2. If confidence ≥ 0.5: buffers sign name, echoes `sign` back to deaf window
3. Signs are flushed via the same debounce mechanism as quick-sign buttons

---

#### `emergency` — Emergency alert

**Direction:** Any → Backend → All (broadcast_all, including sender)

```json
{
  "type": "emergency",
  "sender": "deaf",
  "timestamp": 1711800000000
}
```

Broadcasts to ALL users in the session (hearing + deaf + rights). Both windows show a full-screen overlay. The hearing window also speaks an alert via TTS.

A global keyboard shortcut (`Ctrl+E` / `Cmd+E`) can trigger emergency from any window.

---

#### `turn` — Turn indicator

**Direction:** Backend → All (broadcast_all)

```json
{
  "type": "turn",
  "speaker": "hearing"
}
```

| `speaker` value | Meaning |
|-----------------|---------|
| `"hearing"` | Hearing user is speaking |
| `"deaf"` | Deaf user is signing |

Auto-resets in the UI after 12 seconds.

---

## Error Response Format

For request/response messages, errors are returned as:

```json
{
  "request_id": <original_id>,
  "error": "Human-readable error message"
}
```

Error messages are always generic — raw Python exceptions are never exposed.

---

## Rate Limiting

Heavy AI operations are rate-limited per session:

| Message Type | Cooldown |
|-------------|----------|
| `speech_upload` | 2 s |
| `rights_analyze` | 30 s |
| `rights_letter` | 45 s |

If a call arrives during cooldown:
```json
{
  "request_id": <id>,
  "error": "Too many requests — please wait a moment before trying again."
}
```

HTTP endpoints are additionally rate-limited per IP per endpoint via `backend/middleware.py`.

---

## Authentication Flow

1. Backend generates `SESSION_SECRET` at startup (`secrets.token_urlsafe(32)`)
2. Electron main fetches it: `GET /auth/session-secret` → `{ "session_secret": "..." }`
3. Main process sends secret to each window via IPC
4. Every WebSocket connection includes `?token=<secret>` in the URL
5. Backend validates with `hmac.compare_digest()` (constant-time)

---

## Preload Bridge API

The renderer accesses the WebSocket through `window.amandla`:

| Method | Returns | Description |
|--------|---------|-------------|
| `connect(sessionId, role, secret)` | void | Open WebSocket connection |
| `send(message)` | boolean | Fire-and-forget JSON message |
| `onMessage(callback)` | void | Register broadcast message handler |
| `onConnectionChange(callback)` | void | Register connection state handler |
| `disconnect()` | void | Close connection, stop reconnection |
| `uploadSpeech(blob, mimeType)` | Promise | Upload audio → transcription result |
| `requestStatus()` | Promise | Get AI service health |
| `analyzeRights(description, type)` | Promise | Rights incident analysis |
| `generateLetter(details)` | Promise | Formal complaint letter |
| `openRights()` | Promise | Open the Know Your Rights window |
| `getSessionId()` | Promise | Get session ID from main process |
| `onEmergencyShortcut(callback)` | void | Register global emergency handler |

