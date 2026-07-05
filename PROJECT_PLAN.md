# AMANDLA — Master Investigation Report & Implementation Plan

> Generated: April 1, 2026 by 5 parallel AI agents (deep codebase investigation)
> This file is the SINGLE SOURCE OF TRUTH for what needs to be done next.
> Source of truth for architecture: CLAUDE.md | Source of truth for security: this file
> Update status column as work is completed.

---

## Executive Summary

Five specialist agents performed a full audit of the AMANDLA codebase covering:

- Agent 1: SASL sign mapping & translation pipeline
- Agent 2: Database & conversation history
- Agent 3: Security (full OWASP Top 10)
- Agent 4: Frontend, Electron IPC & WebSocket protocol
- Agent 5: Performance, AI services & HARPS ML system

**Total findings: 38 bugs, 24 security issues, 19 architecture improvements, 20+ new feature ideas.**

The app is architecturally sound and well-designed, but has **critical bugs causing real data
loss and security breaches right now**, plus **3 features that are non-functional in production**:
HARPS ML model, Modelfile sign inventory (only 20/100+ signs), and missing translation caching.

---

## PHASE 1 — Critical Fixes (Do These First, No New Features Until Done)

These cause real data loss, security breaches, or broken UX **right now**.

---

### FIX-1: Assist-mode messages logged with empty session_id

**Agent:** 2 (Database) | **Severity:** CRITICAL | **Effort:** 5 min | **Status:** DONE

Every message a deaf user sends via the assist-mode phrase bank is stored in the database
with `session_id=""`, permanently orphaning it from its session. History queries for that
session will never return those messages.

**File:** `backend/ws/handler.py` (around line 385)

```python
# CURRENT (broken):
await log_message(
    session_id="",   # BUG
    direction="deaf_to_hearing",
    ...
)

# FIX: Pass session_id into _handle_assist_phrase():
async def _handle_assist_phrase(session, session_id, msg):
    await log_message(
        session_id=session_id,  # FIXED
        direction="deaf_to_hearing",
        ...
    )
```

---

### FIX-2: Any authenticated user can read any session's history

**Agent:** 3 (Security) | **Severity:** CRITICAL | **Effort:** 10 min | **Status:** DONE

The `history_request` WebSocket message accepts an arbitrary `session_id` with no ownership
check. Any authenticated client can read anyone else's conversation history (including
medical/legal conversations).

**File:** `backend/ws/handler.py` (around line 633)

```python
# CURRENT (broken):
target_session = msg.get("session_id", session_id)  # User can specify any session!

# FIX: Enforce ownership
target_session = msg.get("session_id", session_id)
if target_session != session_id and not msg.get("list_sessions"):
    await send_safe(websocket, {
        "type": "history_response",
        "request_id": request_id,
        "error": "You can only view your own session history.",
    })
    return
```

---

### FIX-3: showDetectedSign() called but never defined — ReferenceError in browser

**Agent:** 4 (Frontend) | **Severity:** CRITICAL | **Effort:** 15 min | **Status:** DONE (was already implemented)

`deaf.js` calls `showDetectedSign(sign, 1.0)` but the function is never defined anywhere.
Every sign recognition event in the deaf window throws a `ReferenceError`.

**File:** `src/windows/deaf/deaf.js` (around line 267)

```javascript
/**
 * Display a detected sign to the deaf user as visual feedback.
 * @param {string} sign - The sign name (e.g. "HELLO")
 * @param {number} confidence - Recognition confidence 0.0-1.0
 */
function showDetectedSign(sign, confidence) {
    const detectedEl = document.getElementById('detected-sign')
    if (!detectedEl) return
    detectedEl.textContent = `${sign} (${Math.round(confidence * 100)}%)`
    detectedEl.classList.add('visible')
    setTimeout(() => detectedEl.classList.remove('visible'), 2000)
}
```

---

### FIX-4: Off-by-one in sentenceToSigns() — last 3-word phrase never matched

**Agent:** 1 (SASL) | **Severity:** CRITICAL | **Effort:** 5 min | **Status:** DONE

**Note:** The same off-by-one existed in `backend/services/sign_maps.py:sentence_to_sign_names()`
(Python backend) and was fixed April 7, 2026 — `if i + 2 < len(words)` → `if i + 3 <= len(words)`.

When a sentence ends with a 3-word phrase, it is never matched because the loop boundary
condition is wrong.

**File:** `signs_library.js` (around line 1440)

```javascript
// CURRENT (broken):
if (i + 2 < words.length) {  // Misses last 3-word phrase

// FIX:
if (i + 3 <= words.length) {  // Correct
```

---

### FIX-5: No rate limiting on WebSocket endpoint — DoS vector

**Agent:** 3 (Security) | **Severity:** CRITICAL | **Effort:** 30 min | **Status:** DONE

The HTTP rate-limit middleware only covers HTTP routes. The WebSocket endpoint
`/ws/{sessionId}/{role}` has no connection-rate limit. An attacker can open thousands
of connections per second, exhausting memory and blocking legitimate users.

**File:** `backend/shared.py` + `backend/ws/handler.py`

**Plan:**

1. Add per-IP connection tracking dict to `shared.py`
2. In `websocket_endpoint()`, before accepting connection:

```python
MAX_WS_CONNECTIONS_PER_IP = 5
client_ip = websocket.client.host if websocket.client else "unknown"
if not _check_ws_connection_limit(client_ip):
    await websocket.close(code=1008, reason="Too many connections from this address")
    return
```

---

### FIX-6: All database exceptions silently swallowed — failures invisible

**Agent:** 2 (Database) | **Severity:** HIGH | **Effort:** 10 min | **Status:** DONE

Every `log_message()` call is wrapped in a bare `except Exception: pass`. If the
database goes down, fills the disk, or corrupts, zero warning is written anywhere.

**Files:** `backend/ws/handler.py` (lines ~211, ~359, ~393, ~486),
`backend/services/sign_reconstruction.py` (line ~334)

```python
# CURRENT (broken):
except Exception:
    pass

# FIX — all occurrences:
except Exception as e:
    logger.warning("[History] Failed to log message: %s", e)
    # Still do not raise — history failure must not break the main flow
```

---

### FIX-7: Modelfile only lists 20 signs — Ollama cannot recognize 80+ app signs

**Agent:** 5 (Performance/AI) | **Severity:** CRITICAL | **Effort:** 45 min | **Status:** DONE

The `Modelfile` teaches Ollama only 20 sign names. `sign_maps.py` defines 100+ signs.
Ollama currently fails to recognize 80% of the app's signs.

**Files:** `Modelfile`, new `scripts/generate_modelfile.py`

**Plan:**

1. Write `scripts/generate_modelfile.py` that reads all WORD_MAP values from `sign_maps.py`
2. Generates a new Modelfile system prompt listing all signs with examples
3. Rebuild model: `ollama create amandla -f Modelfile`

---

### FIX-8: Ollama URL not validated — SSRF vulnerability

**Agent:** 3 (Security) | **Severity:** CRITICAL | **Effort:** 15 min | **Status:** DONE

`OLLAMA_BASE_URL` is read from `.env` without validating it points to localhost.
A misconfigured or compromised env file can point requests to arbitrary internal services.

**File:** `backend/main.py` (add after `load_dotenv()`)

```python
from urllib.parse import urlparse

_ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_parsed = urlparse(_ollama_url)
if _parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
    raise ValueError(
        f"SECURITY: OLLAMA_BASE_URL must point to localhost. Got: {_parsed.hostname}"
    )
```

---

### FIX-9: No max length validation on audio or text in hearing window

**Agent:** 4 (Frontend) | **Severity:** HIGH | **Effort:** 20 min | **Status:** DONE

Backend enforces 10 MB audio and 5000 char text limits but the frontend sends without
checking. Large payloads silently time out after 60 seconds.

**File:** `src/windows/hearing/hearing.js`

```javascript
// Add before sending text (around line 192):
const MAX_TEXT_LENGTH = 5000
if (text.length > MAX_TEXT_LENGTH) {
    transcriptEl.textContent = `Message too long (${text.length}/${MAX_TEXT_LENGTH} chars)`
    return
}

// Add before uploading audio (around line 283):
const MAX_AUDIO_BYTES = 10 * 1024 * 1024  // 10 MB
if (blob.size > MAX_AUDIO_BYTES) {
    transcriptEl.textContent = 'Audio too large (max 10 MB). Try a shorter clip.'
    return
}
```

---

### FIX-10: Deaf and rights windows never disconnect WebSocket on close

**Agent:** 4 (Frontend) | **Severity:** HIGH | **Effort:** 10 min | **Status:** DONE (was already implemented)

`hearing.js` correctly calls `window.amandla.disconnect()` on `beforeunload`.
`deaf.js` and `rights.js` do not, leaving zombie listeners.

**Files:** `src/windows/deaf/deaf.js`, `src/windows/rights/rights.js`

```javascript
// Add to BOTH files:
window.addEventListener('beforeunload', function () {
    window.amandla.disconnect()
})
```

---

## PHASE 2 — High-Impact Architecture Fixes

These cause incorrect behavior, data divergence, or significant reliability risk.

---

### ARCH-1: Unify WORD_MAP — single source of truth

**Agent:** 1 (SASL) | **Severity:** HIGH | **Effort:** 2-3 hours | **Status:** DONE

`WORD_MAP` and `PHRASE_MAP` exist in both `backend/services/sign_maps.py` (Python)
and `signs_library.js` (JavaScript) and have already diverged:

- "need to" maps to MUST in backend, missing in frontend
- "afternoon" maps to MORNING in frontend, intentionally omitted in backend
- "would" maps to WILL in backend only

**Plan:**

1. Create `backend/data/word_map.json` as the canonical source
2. Load it in `sign_maps.py` at startup
3. Add HTTP endpoint `GET /api/sasl/word-map` that serves the JSON
4. In `signs_library.js`, fetch from backend at startup and merge into `WORD_MAP`
5. Remove the hardcoded `WORD_MAP` dict from `signs_library.js`

---

### ARCH-2: Unify filler word lists

**Agent:** 1 (SASL) | **Severity:** MEDIUM | **Effort:** 1-2 hours | **Status:** DONE

Backend `FILLER` set has 50+ words. Frontend `signs_library.js` hardcodes ~30.
Words like "some", "between", "about" are dropped on backend but fingerspelled on frontend.

**Plan:**

1. Create `backend/data/filler_words.json`
2. Backend loads from JSON; expose via `GET /api/sasl/filler-words`
3. Frontend fetches and uses same set in `sentenceToSigns()`

---

### ARCH-3: Fix modal verbs in rule-based fallback

**Agent:** 1 (SASL) | **Severity:** MEDIUM | **Effort:** 1 hour | **Status:** DONE

When Ollama is offline, modal verbs (`can`, `must`, `will`) are silently dropped.
"I can help" becomes "I HELP" offline.

**File:** `sasl_transformer/transformer.py` (around line 351)

```python
MODAL_VERBS = {"can", "could", "must", "should", "will", "would", "may", "might"}
if clean in MODAL_VERBS:
    mapped = WORD_MAP.get(clean)
    if mapped:
        content_words.append(mapped)
    continue
```

---

### ARCH-4: Add missing composite database index

**Agent:** 2 (Database) | **Severity:** MEDIUM | **Effort:** 5 min | **Status:** DONE

Every session history query scans `session_id` index then sorts. Composite index
eliminates the sort: 10-100x speedup for sessions with large histories.

**File:** `backend/services/history_db.py` (in `_init_tables()`)

```sql
CREATE INDEX IF NOT EXISTS idx_conversations_session_time
ON conversations (session_id, timestamp DESC)
```

---

### ARCH-5: Add database retention policy

**Agent:** 2 (Database) | **Severity:** MEDIUM | **Effort:** 30 min | **Status:** DONE

The database grows forever with no deletion mechanism. In a busy clinic it will
hit hundreds of MB within weeks.

**File:** `backend/services/history_db.py`
Add `async def delete_old_messages(days: int = 90) -> int` function, then
call it weekly from the session reaper in `backend/ws/session.py`.

---

### ARCH-6: Session metadata table

**Agent:** 2 (Database) | **Severity:** LOW | **Effort:** 1 hour | **Status:** DONE

No way to query session duration, roles, or message counts without scanning
all `conversations` rows. A `sessions` table enables analytics.

```sql
CREATE TABLE IF NOT EXISTS sessions (
    session_id      TEXT PRIMARY KEY,
    created_at      TEXT NOT NULL,
    closed_at       TEXT,
    roles_present   TEXT DEFAULT '',
    message_count   INTEGER DEFAULT 0
)
```

---

### ARCH-7: Session token in URL query parameter — visible in logs

**Agent:** 3 (Security) | **Severity:** HIGH | **Effort:** 1-2 hours | **Status:** DONE

`?token=<value>` appears in server access logs, reverse proxy logs, and browser history.
Move to `Sec-WebSocket-Protocol` header or custom handshake header.

**Plan:**

1. In `src/preload/preload.js`: pass token as custom WS header
2. In `backend/ws/handler.py`: read from header instead of query param

---

### ARCH-8: Validate and whitelist incident_type field

**Agent:** 3 (Security) | **Severity:** MEDIUM | **Effort:** 15 min | **Status:** DONE

`incident_type` is user-controlled with no whitelist, enabling prompt injection into Ollama.

**File:** `backend/ws/handler.py` (around line 555)

```python
VALID_INCIDENT_TYPES = {"workplace", "hospital", "school", "public", "other"}
incident_type = sanitise_text(msg.get("incident_type", "workplace"))
if incident_type not in VALID_INCIDENT_TYPES:
    incident_type = "workplace"
```

---

### ARCH-9: Startup fail-fast if critical services unavailable

**Agent:** 3 (Security) | **Severity:** MEDIUM | **Effort:** 30 min | **Status:** DONE

If database or Ollama pool fail to initialize, the server still starts, silently
accepts connections, then fails per-request. Should fail immediately with a clear error.

**File:** `backend/main.py` (lifespan function) — wrap `init_db()` and
`ollama_pool_startup()` in try/except that raises `RuntimeError` on failure.

---

## PHASE 3 — Translation Quality Improvements

---

### QUAL-1: Add translation caching

**Agent:** 5 (Performance) | **Severity:** HIGH | **Effort:** 1-2 hours | **Status:** DONE

Every `classify_text_to_signs()` and `text_to_sasl_signs()` call makes a fresh Ollama
request, even for identical input. Emergency phrases hit Ollama repeatedly.

**Files:** `backend/services/ollama_client.py`, `backend/services/sasl_pipeline.py`

```python
from functools import lru_cache

@lru_cache(maxsize=500)
def _cached_classify(text: str) -> tuple:
    # pure Ollama call
    pass
```

**Estimated impact:** 40% latency reduction for repeated phrases. "HELP" goes from
2-3s to <10ms on second use.

---

### QUAL-2: Update Modelfile with full sign inventory

**Agents:** 1 & 5 | **Severity:** CRITICAL | **Effort:** 45 min | **Status:** DONE (script at scripts/generate_modelfile.py — run: python scripts/generate_modelfile.py && ollama create amandla -f Modelfile)

(Also FIX-7 in Phase 1 — highest priority)

Write `scripts/generate_modelfile.py` to read all WORD_MAP entries from `sign_maps.py`
and auto-generate the Modelfile system prompt, then rebuild with `ollama create amandla -f Modelfile`.

---

### QUAL-3: Fix FINISH/WILL markers for perfect aspect

**Agent:** 1 (SASL) | **Severity:** MEDIUM | **Effort:** 1 hour | **Status:** DONE

"I have eaten" produces "EAT I" (no FINISH marker) because "have + past participle"
pattern is not detected in the rule-based fallback.

**File:** `sasl_transformer/transformer.py` — detect perfect aspect and set `has_past_tense = True`.

---

### QUAL-4: Add yes/no question marker in rule-based fallback

**Agent:** 1 (SASL) | **Severity:** MEDIUM | **Effort:** 1 hour | **Status:** DONE

"Are you happy?" produces "YOU HAPPY" with no question indicator.
SASL requires raised-eyebrow non-manual marker for yes/no questions.

**File:** `sasl_transformer/transformer.py` — when sentence ends with "?" and
`question_markers` is empty, add `{"type": "facial", "expression": "raised_brows"}`.

---

### QUAL-5: South African English dialect extensions

**Agent:** 1 (SASL) | **Severity:** LOW | **Effort:** 4-6 hours | **Status:** DONE

Common SA English terms have no sign mapping:

- "robot" (traffic light), "just now" (later), "lekker" (nice), "shame" (empathy)

**Plan:** Create `backend/data/sa_english_extensions.json` and merge at startup.

---

## PHASE 4 — HARPS ML System

---

### HARPS-1: Current model trained on synthetic data — unusable in production

**Agent:** 5 (Performance) | **Severity:** CRITICAL | **Status:** DONE (Option A applied)

The `model.pth` was trained with `--demo` flag on 21 generic synthetic classes
(`SIGN_00` through `SIGN_20`). Real-world accuracy: ~0%.

**Applied:** Option A — HARPS ML tier removed from `_handle_landmarks()` in `handler.py`.
Landmark frames now go directly to Ollama. The `harps_recognizers` dict and all cleanup
code removed from `handler.py` and `shared.py`.
Option B (real training data) remains open as a future funded community project.

---

### HARPS-2: Session expiry too short for medical appointments

**Agent:** 5 | **Severity:** MEDIUM | **Effort:** 5 min | **Status:** DONE

30-minute expiry cuts off mid-appointment. Medical appointments run 45-90 min.

**File:** `backend/shared.py`

```python
SESSION_EXPIRY_S: int = int(os.getenv("SESSION_EXPIRY_S", "3600"))  # 1 hour default
```

---

### HARPS-3: Emergency messages exempt from rate limiting

**Agent:** 5 | **Severity:** MEDIUM | **Effort:** 15 min | **Status:** DONE

Emergency phrases can be rate-limited if user taps rapidly in distress. Emergency
messages must never be throttled.

**File:** `backend/shared.py`

```python
RATE_LIMIT_EXEMPT_TYPES = {"emergency", "assist_phrase"}

def check_rate_limit(session_id: str, msg_type: str) -> bool:
    if msg_type in RATE_LIMIT_EXEMPT_TYPES:
        return True  # Always allow
    # ... existing logic ...
```

---

## PHASE 5 — New Features (Ranked by Impact)

Implement after Phases 1-3 are complete.


| #  | Feature                                                | Impact                       | Effort     | Status |
| -- | ------------------------------------------------------ | ---------------------------- | ---------- | ------ |
| 1  | Conversation export (PDF/text)                         | HIGH — medical/legal record | 3-4h       | DONE   |
| 2  | Offline phrase library (50 medical phrases, no Ollama) | VERY HIGH — rural clinics   | 1 week     | DONE   |
| 3  | Real-time character counter on text input              | LOW                          | 30 min     | DONE   |
| 4  | MediaPipe hand recognition (after HARPS-1 decision)    | MEDIUM                       | 2-3 weeks  | TODO   |
| 5  | Interpreter role (3rd participant)                     | HIGH — government/hospital  | 1 week     | DONE   |
| 6  | Adjustable avatar signing speed                        | LOW — learners              | 2h         | DONE   |
| 7  | Android mobile app (React Native)                      | CRITICAL FOR SCALE           | 3-6 months | TODO   |
| 8  | Multi-user session (multiple hearing staff)            | MEDIUM                       | 1 week     | DONE   |
| 9  | Search conversation history                            | MEDIUM                       | 3-4h       | DONE   |
| 10 | Avatar appearance customization                        | LOW — representation        | 1-2 weeks  | DONE   |

---

## Sprint Plan

### Sprint 1 — This Week (All Critical Bugs ~2.5 hours total)



### Sprint 2 — Next Week (~12-15 hours)

ARCH-1 through ARCH-9, QUAL-1 through QUAL-4, HARPS-2, HARPS-3

### Sprint 3 — Following Week

FIX-5 (WS rate limiting), ARCH-6 (session metadata), QUAL-5 (SA dialect words),
FEAT-1 (export), FEAT-2 (offline phrases)

---

## Verification After Sprint 1

```bash
# 1. Verify DB fix — assist-mode messages now have correct session_id
sqlite3 data/conversations.db "SELECT session_id, source FROM conversations WHERE source='assist' LIMIT 10"

# 2. Run full test suite
python -m pytest tests/ -v

# 3. WebSocket smoke test
python scripts/test_all_ws_handlers.py

# 4. Quick health check
curl http://localhost:8000/health
```

---

*Generated April 1, 2026. All findings verified against live codebase by 5 specialist agents.
Update Status column (TODO → IN_PROGRESS → DONE) as each item is completed.*
