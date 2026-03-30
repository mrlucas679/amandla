# CLAUDE.md — AMANDLA Project: Authoritative State Document

> **Last updated**: March 30, 2026
> This is the SINGLE SOURCE OF TRUTH for AI coding agents working on AMANDLA.
> When this file conflicts with ANY other file, THIS FILE WINS.

---

## 1. What AMANDLA Is

A hybrid **Electron + FastAPI** desktop application — a real-time sign language
communication bridge for disabled South Africans.

Two side-by-side windows share one WebSocket session:
- **Left (Hearing)**: text / speech input
- **Right (Deaf)**: 3D avatar signs the translation back

---

## 2. How to Start the App

```bash
# Prerequisite — must be running first:
ollama serve

# Start everything:
npm start
```

`npm start` runs the FastAPI backend on port 8000, waits for the health check,
then launches Electron. Both windows auto-connect via WebSocket.

---

## 3. Project Architecture (READ THIS BEFORE TOUCHING ANY FILE)

```
Electron Main (src/main.js)
  └─ Creates two BrowserWindows: hearing (left) + deaf (right)
  └─ Generates SESSION_ID once; sends it to both windows via IPC
  └─ Session ID format: 'amandla-' + Date.now() + '-' + randomHex

Preload Bridge (src/preload/preload.js)
  └─ The ONLY way renderers talk to the backend
  └─ Exposes window.amandla.{ connect, send, onMessage, onConnectionChange,
       uploadSpeech, requestStatus, analyzeRights, generateLetter, openRights,
       requestHistory, listSessions }
  └─ All backend calls go through WebSocket — zero direct fetch() from renderers

Backend (backend/main.py — FastAPI)
  └─ WS  /ws/{sessionId}/{role}     ← all real-time communication
  └─ POST /speech                   ← kept for direct API testing only
  └─ GET  /health                   ← liveness probe
  └─ GET  /api/status               ← AI service health
  └─ POST /rights/analyze           ← kept for direct API testing only
  └─ POST /rights/letter            ← kept for direct API testing only
  └─ Services: whisper_service, ollama_service, claude_service, sign_maps

Signs Library (signs_library.js — root)
  └─ 100+ SASL signs from Einstein Hands SASL Dictionary
  └─ Loaded by deaf window as window.AMANDLA_SIGNS
  └─ sentenceToSigns(text) → array of sign objects
  └─ fingerspell(word) → letter-by-letter fallback
  └─ Word mappings live in backend/services/sign_maps.py (backend side)

Avatar (src/windows/deaf/avatar.js)
  └─ Three.js skeleton — reads from window.AMANDLA_SIGNS
  └─ State machine: idle → transitioning → holding → gap → idle
  └─ Public API: window.avatarPlaySigns(signs, text)
```

### Communication Flow (Hearing → Deaf)
1. Hearing user types or speaks (in any of SA's 11 official languages)
2. `window.amandla.send({type:'text', text:'...', language:'af'})` → WebSocket → backend
3. Backend: if language ≠ English → `_translate_to_english(text)` via Ollama (FEAT-5)
4. Backend: `text_to_sasl_signs(text)` → SASL transformer → sign names array
5. Backend broadcasts `{type:'signs', signs:[...]}` to deaf window
6. Deaf window calls `window.avatarPlaySigns(signs, text)` to animate

### Communication Flow (Deaf → Hearing)
1. Deaf user taps quick-sign button or MediaPipe detects a sign
2. `window.amandla.send({type:'sign', text:'HELLO'})` → WebSocket → backend
3. Backend buffers signs; after 1.5s silence → `_signs_to_english(signs)`
4. Backend sends `{type:'deaf_speech', text:'Hello.'}` to hearing window
5. Hearing window speaks the text aloud via TTS

---

## 4. ⛔ DO NOT RECREATE — Intentionally Deleted Files

These files were **deliberately removed**. Do NOT recreate them. Ever.

| File | Why deleted |
|------|-------------|
| `src/windows/hearing/signs_library.js` | Dead code — signs library is loaded only by the deaf window, not the hearing window |
| `src/windows/hearing/avatar.js` | Dead code — avatar lives only in the deaf window |

If you see these mentioned in any other doc file, ignore it — those docs are stale.

---

## 5. ⛔ DO NOT ADD BACK — Intentionally Removed Code

| What | Where it was | Why removed |
|------|-------------|-------------|
| `load_dotenv()` calls | `ollama_service.py`, `nvidia_service.py`, inside `claude_service._get_ollama_config()` | `backend/main.py` calls `load_dotenv()` once at startup before any service is imported — calling it again in services is redundant |
| `"error": str(e)` in HTTP responses | `/speech` endpoint in `main.py` | Exposes raw Python exception details to clients — security risk |
| `allow_origins=["http://localhost:8000"]` | `main.py` CORS config | **This breaks Electron** — Electron renderers do not originate from localhost; CORS must stay `["*"]` for desktop apps |

---

## 6. Key Constraints (Non-Negotiable)

### Electron
- `contextIsolation: true`, `nodeIntegration: false` — always
- No `require()` in renderer code — use the preload bridge only
- CORS on FastAPI **must** be `allow_origins=["*"]` — Electron is not a browser origin
- CSP allows `https://fonts.googleapis.com` (style-src) and `https://fonts.gstatic.com` (font-src)

### WebSocket
- Session roles are exactly: `"hearing"`, `"deaf"`, `"rights"`
- Message types (lowercase): `text`, `speech_upload`, `signs`, `sign`, `translating`,
  `deaf_speech`, `sasl_text`, `assist_phrase`, `landmarks`, `emergency`, `status_request`,
  `rights_analyze`, `rights_letter`, `history_request`, `history_response`, `sasl_ack`, `turn`
- All request/response pairs include a `request_id` field for promise resolution in preload.js
- Broadcast messages (`signs`, `deaf_speech`, `turn`) do NOT include `request_id`

### Backend
- `.env` is loaded ONCE in `backend/main.py` via `load_dotenv()` — never again in services
- Session state is in-memory (`sessions` dict) — restart clears it, this is intentional
- `_sign_buffers` and `_sign_tasks` are cleaned up in the WebSocket `finally` block
- A session reaper background task removes empty sessions after 30 minutes
- Maximum audio upload: 10 MB
- Maximum text message: 5000 chars

### Signs / SASL
- `sign_maps.py` is the SINGLE SOURCE OF TRUTH for English → SASL word mappings
- Modal verbs (`will`, `must`, `can`, etc.) map to SASL signs — they are NOT in FILLER
- `FINISH`/`WILL` aspect markers are critical SASL grammar — never drop them
- `FILLER` only contains words with zero SASL equivalent (articles, prepositions, etc.)
- Non-English input is pre-translated to English via Ollama before the SASL pipeline (FEAT-5)
- English input (`language=None` or `language='en'`) bypasses translation — no double-translation

---

## 7. Environment Variables (`.env`)

```
WHISPER_MODEL=small          # tiny|base|small|medium|large
WHISPER_DEVICE=cpu           # cpu|cuda
WHISPER_LANGUAGE=            # empty = auto-detect (recommended for multilingual)
OLLAMA_MODEL=amandla         # must be created: ollama create amandla -f Modelfile
OLLAMA_BASE_URL=http://localhost:11434
TRANSLATION_OLLAMA_MODEL=    # optional — defaults to OLLAMA_MODEL if not set
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
NVIDIA_ENABLED=false         # set true only if you have an NVIDIA API key
NVIDIA_API_KEY=              # get from build.nvidia.com
ANTHROPIC_API_KEY=           # optional cloud AI
OPENAI_API_KEY=              # optional cloud AI
```

---

## 8. Running the Tests

```bash
python scripts/ws_test.py             # WebSocket smoke test
python scripts/post_speech_test.py    # Speech endpoint test
curl http://localhost:8000/health     # Quick health check
```

---

## 9. File Map — What Each File Does

| File | Purpose | Edit frequency |
|------|---------|----------------|
| `src/main.js` | Electron window creation, session ID, CSP | Rarely |
| `src/preload/preload.js` | WebSocket bridge, IPC, promise-based requests | Rarely |
| `src/windows/hearing/index.html` | Hearing UI — HTML shell | Occasionally |
| `src/windows/hearing/hearing.css` | Hearing window styles | Occasionally |
| `src/windows/hearing/hearing.js` | Hearing window logic — text input, mic, TTS | Often |
| `src/windows/deaf/index.html` | Deaf UI — HTML shell | Occasionally |
| `src/windows/deaf/deaf.css` | Deaf window styles | Occasionally |
| `src/windows/deaf/deaf.js` | Deaf window logic — avatar, sign buttons, camera | Often |
| `src/windows/deaf/avatar.js` | Three.js avatar engine v2 | Occasionally |
| `src/windows/rights/index.html` | Rights UI — HTML shell | Occasionally |
| `src/windows/rights/rights.css` | Rights window styles | Occasionally |
| `src/windows/rights/rights.js` | Rights window logic — wizard, PDF, API calls | Often |
| `signs_library.js` | 100+ SASL sign objects + sentenceToSigns() | Rarely |
| `backend/main.py` | FastAPI app, WebSocket handler, all routes | Often |
| `backend/middleware.py` | Rate limiting middleware | Rarely |
| `backend/services/sign_maps.py` | English → SASL word/phrase mappings | Often |
| `backend/services/whisper_service.py` | Speech-to-text (faster-whisper + ffmpeg) | Rarely |
| `backend/services/ollama_service.py` | Sign recognition via Ollama | Rarely |
| `backend/services/claude_service.py` | Rights analysis + letter generation | Rarely |
| `backend/services/nvidia_service.py` | NVIDIA NIM fallback (optional) | Rarely |
| `backend/services/ollama_client.py` | Classify text → sign names via Ollama | Rarely |
| `sasl_transformer/transformer.py` | Full SASL grammar transformer | Occasionally |
| `Modelfile` | Ollama amandla model definition | Once |

---

## 10. Stale Docs — Ignore These

The following files still exist but contain **outdated information**. Their first
line says "ARCHIVED". Do not follow their instructions:

- `APPLICATION_STARTED.md` — March 24 snapshot
- `FINAL_STATUS_REPORT.md` — March 24 snapshot
- `OPERATIONAL_STATUS.md` — March 24 snapshot
- `SETUP_COMPLETE.md` — references deleted files
- `SETUP_VERIFICATION.md` — references deleted files
- `WHAT_WAS_COMPLETED.md` — duplicate of above
- `PROJECT_SETUP_SUMMARY.md` — duplicate of above
- `START_HERE.md` — pointed to stale docs
- `NEXT_STEPS.md` — outdated roadmap
- `AGENT_TASKS.md` — incorrectly said "all fixed"
- `AGENT_PROMPTS.md` — contained wrong CORS fix that breaks Electron
- `AMANDLA_BLUEPRINT (2).md` — original hackathon script, superseded

