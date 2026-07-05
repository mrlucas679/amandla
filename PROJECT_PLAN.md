# HOW FARAMANDLA — Self-Contained Project Plan

> **Date**: March 30, 2026
> **Status**: 34 of 37 production-readiness issues COMPLETE — 3 open items remain
> **Source of truth**: `CLAUDE.md` (architecture) · `PRODUCTION_READINESS.md` (full audit)

---

## 1. What AMANDLA Is

A real-time **sign language communication bridge** for disabled South Africans.
Hybrid **Electron + FastAPI** desktop app — two side-by-side windows share one
WebSocket session:


| Window      | Position  | Purpose                                                           |
| ----------- | --------- | ----------------------------------------------------------------- |
| **Hearing** | Left      | Type or speak → translated to SASL signs                         |
| **Deaf**    | Right     | 3D avatar animates signs; reply via buttons, text, or camera      |
| **Rights**  | On demand | Document discrimination, analyse laws, generate complaint letters |

---

## 2. Current State — What Is Done

### ✅ Core Features (all working)


| Feature                        | Implementation                                                      |
| ------------------------------ | ------------------------------------------------------------------- |
| English → SASL translation    | `sasl_pipeline.py` (3-tier: transformer → Ollama → rule-based)    |
| Avatar sign animation          | `avatar.js` (Three.js skeleton) + `signs_library.js` (134 signs)    |
| GLB avatar model               | `avatar_driver.js` + `assets/models/avatar.glb` (graceful fallback) |
| Speech-to-text                 | `whisper_service.py` (faster-whisper, pre-loaded at startup)        |
| Deaf → Hearing reconstruction | `sign_reconstruction.py` (1.5s debounce → Ollama → rule-based)    |
| Quick-sign buttons             | Deaf window button grid → buffer → reconstruct → TTS             |
| SASL text input                | Deaf types SASL gloss →`split_sasl_gloss()` → English             |
| Assist mode                    | Pre-formed English phrases bypass SASL reconstruction               |
| Camera sign recognition        | MediaPipe landmarks → HARPS ML (Tier 1) → Ollama (Tier 2)         |
| Know Your Rights               | Wizard →`rights_analyze` → `rights_letter` → print-ready         |
| Conversation history           | SQLite (`data/conversations.db`) — survives restarts               |
| Print/export transcript        | Hearing window "🖨 Print" button with`@media print` CSS             |
| Emergency alert                | `Ctrl+E` global shortcut → both windows + TTS + visual flash       |
| Replay signs                   | Deaf window "↻ Replay" button replays last sign sequence           |

### ✅ Infrastructure (all working)


| Area                | Implementation                                                      |
| ------------------- | ------------------------------------------------------------------- |
| WebSocket auth      | `SESSION_SECRET` (256-bit) + `hmac.compare_digest()`                |
| Input sanitisation  | `sanitise_text()` on all 12 user-text extraction points             |
| Rate limiting       | Per-session per-type for heavy AI ops + per-IP HTTP middleware      |
| Session management  | In-memory + 30-min reaper + max 10 concurrent sessions              |
| Connection pooling  | `ollama_pool.py` — shared `httpx.AsyncClient` for all Ollama calls |
| Auto-updater        | `electron-updater` (packaged builds only)                           |
| Ollama health check | Startup dialog if Ollama not running                                |
| CSP                 | Locked down: self + approved CDNs (fonts, MediaPipe, Three.js)      |

### ✅ Code Quality (all done)


| Area              | What was done                                                         |
| ----------------- | --------------------------------------------------------------------- |
| Monolith split    | `main.py` (1087→133 lines) → routers/ + ws/ + services/ + shared.py |
| HTML extraction   | All 3 windows: HTML shells + separate`.css` + `.js` files             |
| Dependency audit  | python-multipart ≥0.0.22, Electron ≥35.7.5 (CVEs resolved)          |
| Test suite        | 49 unit tests + 15 E2E tests + WS handler smoke test                  |
| Documentation     | README, CLAUDE.md, AGENTS.md, WEBSOCKET_PROTOCOL.md, QUICKSTART       |
| Stale doc cleanup | 12 archived docs moved to`archive/` directory                         |

---

## 3. What Remains — Open Items

Only **3 items** are not yet implemented. Listed by priority:

---

### 🔴 BUILD-3 — Bundle Python Backend for Distribution

**Priority**: HIGH — blocks shipping to non-technical users
**Effort**: 4–6 hours
**Category**: Build / Distribution

**Problem**: `npm start` requires Python 3.10+, pip, and all dependencies pre-installed.
Non-technical deaf users cannot be expected to install a Python toolchain.

**Plan**:

1. Use **PyInstaller** to bundle the FastAPI backend into a single executable:
   ```bash
   pip install pyinstaller
   pyinstaller --onefile --name amandla-backend \
     --hidden-import backend.routers.health \
     --hidden-import backend.routers.speech \
     --hidden-import backend.routers.rights \
     --hidden-import backend.ws.handler \
     --hidden-import backend.ws.helpers \
     --hidden-import backend.ws.session \
     --hidden-import backend.services.sasl_pipeline \
     --hidden-import backend.services.sign_reconstruction \
     --hidden-import backend.services.sign_maps \
     --hidden-import backend.services.whisper_service \
     --hidden-import backend.services.ollama_service \
     --hidden-import backend.services.ollama_client \
     --hidden-import backend.services.ollama_pool \
     --hidden-import backend.services.history_db \
     --hidden-import backend.services.claude_service \
     --hidden-import backend.services.harps_recognizer \
     --hidden-import sasl_transformer.routes \
     --hidden-import sasl_transformer.transformer \
     backend/main.py
   ```
2. Update `package.json` `"backend"` script to launch the binary instead of `python -m uvicorn`
3. Include the binary in the electron-builder `extraResources` config
4. Test on Windows, macOS, and Linux

**Files to change**:

- `package.json` — update `scripts.backend`, add `extraResources` to `build` config
- New: `amandla-backend.spec` (PyInstaller spec file)
- New: `scripts/build_backend.py` or `scripts/build_backend.bat` — automation

**Dependencies**: PyInstaller (`pip install pyinstaller`)

**Acceptance criteria**:

- [ ]  `npm start` works WITHOUT Python installed on the user's machine
- [ ]  Backend health check passes (`/health` → `{"ok": true}`)
- [ ]  WebSocket connections work with the bundled binary
- [ ]  Whisper model loads correctly from the bundled binary
- [ ]  `data/conversations.db` is created in the right location

---

### 🟡 BUILD-2 — Create App Icons

**Priority**: MEDIUM — cosmetic but required for professional distribution
**Effort**: 1 hour
**Category**: Build / Branding

**Problem**: `package.json` references `assets/icons/icon.ico` but `assets/icons/` is empty.
Packaged builds use Electron's default icon.

**Plan**:

1. Design AMANDLA logo (hands + bridge motif, accessible colour palette)
2. Export in required formats:
   - `assets/icons/icon.ico` — 256×256 multi-size (Windows)
   - `assets/icons/icon.icns` — multi-size (macOS)
   - `assets/icons/icon.png` — 512×512 (Linux)
3. Optional: `assets/icons/tray.png` — 16×16 / 32×32 for system tray

**Files to create**:

- `assets/icons/icon.ico`
- `assets/icons/icon.icns`
- `assets/icons/icon.png`

**Acceptance criteria**:

- [ ]  `npm run build` produces an installer with the custom icon
- [ ]  Icon is visible in the taskbar, title bar, and dock

---

### 🟢 FEAT-5 — Multilingual Input (Non-English → SASL)

**Priority**: LOW — enhancement, not blocking launch
**Effort**: 4 hours
**Category**: Feature

**Problem**: SASL is language-agnostic, but the text→SASL pipeline assumes English.
South Africa has 11 official languages. Whisper transcribes isiZulu, isiXhosa, Afrikaans
etc., but the SASL transformer only has English grammar rules.

**Plan**:

1. Whisper already auto-detects the spoken language — this works today
2. Add a pre-translation step in `sasl_pipeline.py`:
   - If detected language ≠ English → call Ollama with a translation system prompt
   - Translate to English first, then run normal SASL pipeline
3. Add a multilingual system prompt constant in `sasl_pipeline.py`
4. Pass the detected language through the WebSocket response for UI display

**Files to change**:

- `backend/services/sasl_pipeline.py` — add language detection + Ollama translation step
- `backend/ws/handler.py` — pass `language` field through to broadcasts

**Acceptance criteria**:

- [ ]  Afrikaans speech input produces correct SASL signs
- [ ]  Language detected is shown in the hearing window transcript
- [ ]  English input is NOT double-translated (bypass optimization)

---

## 4. Tech Stack


| Layer            | Technology                            | Version                     |
| ---------------- | ------------------------------------- | --------------------------- |
| Desktop shell    | Electron                              | ≥35.7.5                    |
| Frontend         | Vanilla JS + Three.js                 | Three.js r128 (bundled)     |
| Backend          | FastAPI + Uvicorn                     | FastAPI 0.115, Uvicorn 0.32 |
| AI (local)       | Ollama (`amandla` model)              | Latest                      |
| Speech-to-text   | faster-whisper                        | 1.1.0                       |
| Sign recognition | HARPS ML classifier + Ollama fallback | PyTorch ≥2.0               |
| Database         | SQLite (stdlib)                       | `data/conversations.db`     |
| Build tool       | electron-builder                      | ≥25.0.0                    |
| Auto-update      | electron-updater                      | Packaged builds only        |

---

## 5. Project Structure

```
src/
  main.js                          — Electron: 2 windows, session ID, CSP, auto-updater
  preload/preload.js               — WebSocket bridge (ONLY renderer↔backend path)
  windows/
    hearing/                       — index.html + hearing.css + hearing.js
    deaf/                          — index.html + deaf.css + deaf.js + avatar.js
                                     + avatar_driver.js + mode_controller.js
    rights/                        — index.html + rights.css + rights.js

backend/
  main.py                          — FastAPI app, router registration, lifespan startup
  shared.py                        — Shared state, constants, auth, sanitisation, rate limits
  middleware.py                    — Per-IP HTTP rate limiting
  routers/                         — health.py, speech.py, rights.py
  ws/                              — handler.py (dispatch), helpers.py, session.py (reaper)
  services/
    sasl_pipeline.py               — English → SASL signs (3-tier fallback)
    sign_reconstruction.py         — SASL signs → English sentences
    sign_maps.py                   — English→SASL word mappings (SINGLE SOURCE OF TRUTH)
    whisper_service.py             — Speech-to-text
    ollama_service.py              — Sign recognition via Ollama
    ollama_client.py               — Text → sign names via Ollama
    ollama_pool.py                 — Shared httpx connection pool (PERF-4)
    claude_service.py              — Rights analysis + letter generation
    nvidia_service.py              — NVIDIA NIM fallback (optional)
    harps_recognizer.py            — HARPS ML sign classifier
    mediapipe_bridge.py            — MediaPipe landmarks → HARPS arrays
    sign_buffer.py                 — Sliding-window frame accumulator
    history_db.py                  — SQLite conversation history
    gemini_service.py              — DEPRECATED stub (ImportError prevention)

sasl_transformer/                  — SASL grammar transformer module (7 files)
signs_library.js                   — 134 SASL signs with bone data (deaf window only)
data/                              — sign_library.json + conversations.db (auto-created)
assets/
  js/                              — three.min.js + GLTFLoader.js (bundled)
  models/                          — avatar.glb (33 MB GLB model)
  icons/                           — (empty — BUILD-2)
tests/                             — test_sign_maps.py, test_e2e_pipeline.py, test_transformer.py
scripts/                           — ws_test, syntax_check, train_harps, gen_harps, etc.
docs/                              — WEBSOCKET_PROTOCOL.md
archive/                           — 12 stale docs (do NOT follow)
```

---

## 6. How to Start

```bash
# Terminal 1 — Start Ollama (must be running first)
ollama serve

# Terminal 2 — Start everything
cd C:\Users\Admin\amandla-desktop
npm start
```

`npm start` runs FastAPI on port 8000, waits for the health check, then launches Electron.

### First-Time Setup

```bash
npm install                         # Node dependencies
pip install -r requirements.txt     # Python dependencies
ollama create amandla -f Modelfile  # Create Ollama model
copy .env.example .env              # Create env config
```

---

## 7. Running Tests

```bash
# Unit tests — sign map lookups (49 tests)
python -m pytest tests/test_sign_maps.py -v

# SASL transformer unit tests
python -m pytest tests/test_transformer.py -v

# End-to-end pipeline tests (requires backend running)
python tests/test_e2e_pipeline.py

# WebSocket handler smoke test (requires backend running)
python scripts/test_all_ws_handlers.py

# Python syntax check for all backend files
python scripts/syntax_check.py

# Quick health check
curl http://localhost:8000/health
```

---

## 8. Environment Variables (`.env`)

```env
WHISPER_MODEL=small          # tiny|base|small|medium|large
WHISPER_DEVICE=cpu           # cpu|cuda
WHISPER_LANGUAGE=            # empty = auto-detect (recommended)
OLLAMA_MODEL=amandla         # must be created: ollama create amandla -f Modelfile
OLLAMA_BASE_URL=http://localhost:11434
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
NVIDIA_ENABLED=false         # set true only if you have an NVIDIA API key
NVIDIA_API_KEY=              # get from build.nvidia.com
ANTHROPIC_API_KEY=           # optional cloud AI
OPENAI_API_KEY=              # optional cloud AI
```

---

## 9. Architecture — Data Flows

### Hearing → Deaf (text/speech to sign animation)

```
User types or speaks
  → window.amandla.send({type:'text', text:'Hello'})
  → WebSocket → backend/ws/handler.py → _handle_text()
  → sasl_pipeline.text_to_sasl_signs('Hello')
      Tier 1: sasl_transformer (grammar rules + Ollama LLM)
      Tier 2: ollama_client (direct LLM classification)
      Tier 3: sign_maps.sentence_to_sign_names() (rule-based)
  → broadcast {type:'signs', signs:['HELLO']} to deaf window
  → deaf.js receives → window.avatarPlaySigns(['HELLO'])
  → avatar.js animates skeleton using signs_library.js bone data
  → history_db.log_message() (async, never blocks)
```

### Deaf → Hearing (signs to speech)

```
Deaf taps quick-sign button or camera detects sign
  → window.amandla.send({type:'sign', text:'HELLO'})
  → WebSocket → backend/ws/handler.py → _handle_sign()
  → Buffers sign name in sign_buffers[session_id]
  → After 1.5s silence: sign_reconstruction.debounce_and_flush()
      Tier 1: signs_to_english() via Ollama (6s timeout)
      Tier 2: simple_signs_to_english() rule-based fallback
  → send {type:'deaf_speech', text:'Hello.'} to hearing window
  → hearing.js → SpeechSynthesis TTS reads aloud
  → history_db.log_message() (async)
```

### WebSocket Authentication

```
Backend startup → SESSION_SECRET = secrets.token_urlsafe(32)
Electron main   → GET /auth/session-secret → receives token
Each window     → ws://localhost:8000/ws/{session}/{role}?token={secret}
Backend         → hmac.compare_digest(token, SESSION_SECRET)
                  ✓ accept | ✗ close(1008)
```

### Backend Lifespan Startup Order

```
1. init_db()                  — SQLite conversations table
2. session_reaper()           — background task (30-min cleanup)
3. whisper_service.get_model() — pre-load in background thread
4. ollama_pool.startup()      — shared httpx connection pool
```

---

## 10. Key Constraints (Non-Negotiable)


| Rule                                               | Why                                                       |
| -------------------------------------------------- | --------------------------------------------------------- |
| `contextIsolation: true`, `nodeIntegration: false` | Electron security model                                   |
| No`require()` in renderers                         | Use`window.amandla.*` preload bridge only                 |
| CORS`allow_origins=["*"]`                          | Electron is not a browser origin — restricting breaks it |
| `.env` loaded once in `backend/main.py`            | Never call`load_dotenv()` in service files                |
| `sign_maps.py` is SINGLE SOURCE OF TRUTH           | All word→sign mappings live here                         |
| Modal verbs NOT in FILLER set                      | `will`, `must`, `can` map to SASL signs                   |
| Error responses must be generic                    | Never expose`str(e)` or stack traces                      |
| All user text through`sanitise_text()`             | Strips control chars, normalises Unicode, truncates       |
| History logging must never break main flow         | Wrapped in try/except pass                                |

---

## 11. WebSocket Message Types (18 total)

### Request/Response (include `request_id`)


| Type              | Direction                       | Rate limited | Purpose                     |
| ----------------- | ------------------------------- | ------------ | --------------------------- |
| `speech_upload`   | Any → Backend → Sender + Deaf | 2s           | Audio → Whisper → SASL    |
| `status_request`  | Any → Backend → Sender        | No           | AI service health check     |
| `rights_analyze`  | Rights → Backend → Rights     | 30s          | Incident → legal analysis  |
| `rights_letter`   | Rights → Backend → Rights     | 45s          | Details → complaint letter |
| `history_request` | Any → Backend → Sender        | No           | Get conversation history    |

### Broadcast (no `request_id`)


| Type                   | Direction                  | Purpose                         |
| ---------------------- | -------------------------- | ------------------------------- |
| `text` / `speech_text` | Hearing → Backend → Deaf | Typed/spoken text → SASL signs |
| `signs`                | Backend → Deaf            | SASL sign array for avatar      |
| `sasl_ack`             | Backend → Hearing         | Translation acknowledgement     |
| `translating`          | Backend → Deaf            | Loading indicator               |
| `sign`                 | Deaf → Backend → Hearing | Quick-sign button press         |
| `sasl_text`            | Deaf → Backend → Hearing | Typed SASL gloss                |
| `assist_phrase`        | Deaf → Backend → Hearing | Pre-formed English phrase       |
| `deaf_speech`          | Backend → Hearing         | Reconstructed English for TTS   |
| `landmarks`            | Deaf → Backend            | MediaPipe hand data             |
| `emergency`            | Any → Backend → All      | Emergency alert                 |
| `turn`                 | Backend → All             | Turn indicator (hearing/deaf)   |
| `history_response`     | Backend → Sender          | Conversation history data       |

---

## 12. Completed Phases (for reference)


| Phase | Focus                          | Issues                                  | Status                           |
| ----- | ------------------------------ | --------------------------------------- | -------------------------------- |
| 1     | Critical Security + Bugs       | SEC-1, SEC-5, BUG-1, BUG-2, SEC-3       | ✅ COMPLETE                      |
| 2     | High-Priority UX + Performance | SEC-2, UX-1, PERF-1, UX-5, UX-6, PERF-2 | ✅ COMPLETE                      |
| 3     | Testing                        | TEST-1 through TEST-4                   | ✅ COMPLETE                      |
| 4     | Build & Distribution           | BUILD-1, BUILD-4, BUILD-5, BUILD-6      | ⚠️ 4/6 (BUILD-2, BUILD-3 open) |
| 5     | Architecture & Polish          | ARCH-1–5, DOC-1–3                     | ✅ COMPLETE                      |
| 6     | Feature Enhancements           | FEAT-1–4, FEAT-6 + 6 more              | ✅ COMPLETE                      |

**Total**: 34/37 issues resolved. 3 remaining (BUILD-2, BUILD-3, FEAT-5).

---

## 13. Recommended Next Steps (in order)

```
1. BUILD-3 — Bundle Python backend (PyInstaller)     [4-6 hr]  ← SHIP BLOCKER
2. BUILD-2 — Create app icons                        [1 hr]    ← SHIP BLOCKER
3. FEAT-5  — Multilingual input (non-English → SASL) [4 hr]    ← Enhancement
```

After these three items, AMANDLA is shippable as a v1.0 desktop application.

---

## 14. Document Map


| Document                     | Purpose                                                               |
| ---------------------------- | --------------------------------------------------------------------- |
| **`CLAUDE.md`**              | ⭐ Single source of truth — architecture, constraints, deleted files |
| **`AGENTS.md`**              | AI agent coding conventions, file roles, debugging tips               |
| `PROJECT_PLAN.md`            | This file — self-contained project plan                              |
| `PRODUCTION_READINESS.md`    | Full 37-item audit with fix details                                   |
| `INVESTIGATION_AND_PLAN.md`  | Original bug investigation (all issues resolved)                      |
| `docs/WEBSOCKET_PROTOCOL.md` | WebSocket message type reference with examples                        |
| `AMANDLA_FINAL_BLUEPRINT.md` | Avatar and Three.js implementation spec                               |
| `AMANDLA_MISSING_PIECES.md`  | Backend integration blueprint                                         |
| `SASL_Transformer_README.md` | SASL grammar transformer documentation                                |
| `QUICKSTART.md`              | Quick start guide for developers                                      |
| `README.md`                  | Public-facing project README                                          |

---

*Generated March 30, 2026 from full codebase analysis.*
