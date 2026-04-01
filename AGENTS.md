# AGENTS.md — AI Agent Coding Guide for AMANDLA

> Last Updated: March 30, 2026
> **Read `CLAUDE.md` first** — it is the single source of truth and overrides this file.

---

## ⛔ STOP — READ THESE RULES BEFORE TOUCHING ANY FILE

These rules exist because the same mistakes keep happening in every session:

| ❌ DO NOT | ✅ CORRECT STATE |
|-----------|----------------|
| Create `src/windows/hearing/signs_library.js` | **Deleted on purpose.** Hearing window does NOT need signs. |
| Create `src/windows/hearing/avatar.js` | **Deleted on purpose.** Avatar lives only in the deaf window. |
| Add `load_dotenv()` to any service file | `backend/main.py` loads `.env` once at startup — never in services. |
| Change CORS to `["http://localhost:8000"]` | **Breaks Electron.** CORS must stay `["*"]` for desktop apps. |
| Put `"error": str(e)` in any HTTP response | Exposes Python internals to the client — use a generic message. |
| Follow instructions from any `ARCHIVED` file | Those docs are stale. Ignore them entirely. |

---

## Project Overview

**AMANDLA** is a split-screen Electron + FastAPI desktop app that bridges hearing
and deaf South Africans in real time. Two browser windows share one WebSocket session:
- **Left (Hearing)** — speech/text input
- **Right (Deaf)** — 3D avatar signs the translation

---

## Architecture

```
src/main.js                          — Electron entry: creates two windows, fetches session secret
src/preload/preload.js               — ONLY communication bridge between renderers and backend
src/windows/hearing/                 — index.html + hearing.css + hearing.js
src/windows/deaf/                    — index.html + deaf.css + deaf.js + avatar.js
                                       + avatar_driver.js + mode_controller.js
src/windows/rights/                  — index.html + rights.css + rights.js
signs_library.js (ROOT)              — 100+ SASL signs, loaded by DEAF window only

backend/main.py                      — FastAPI app creation, router registration, WS delegation
backend/shared.py                    — Shared state, constants, auth, sanitisation, rate limiting
backend/routers/health.py            — GET /health, /auth/session-secret, /api/status
backend/routers/speech.py            — POST /speech (deprecated — use WS speech_upload)
backend/routers/rights.py            — POST /rights/analyze, /rights/letter (deprecated — use WS)
backend/ws/handler.py                — WebSocket message dispatcher (all WS message types)
backend/ws/helpers.py                — send_safe(), broadcast(), broadcast_all()
backend/ws/session.py                — Session reaper background task
backend/services/sasl_pipeline.py    — HEARING→DEAF: English → SASL signs (3-tier fallback)
backend/services/sign_reconstruction.py — DEAF→HEARING: signs → English sentences
backend/services/sign_maps.py        — English→SASL word mappings (single source of truth)
backend/services/harps_recognizer.py — HARPS ML sign recogniser (replaces Ollama for landmarks)
backend/services/mediapipe_bridge.py — MediaPipe landmarks → HARPS numpy arrays
backend/services/sign_buffer.py      — Sliding-window frame accumulator for HARPS
backend/services/ollama_pool.py      — Shared httpx connection pool for all Ollama calls (PERF-4)
backend/services/history_db.py       — SQLite conversation history (data/conversations.db)
backend/services/gemini_service.py   — DEPRECATED stub (kept to prevent ImportError)
backend/services/                    — whisper, ollama, claude, nvidia services
backend/harps/                       — HARPS ML framework (datasets, transforms, models, train)
backend/harps_model/                 — Trained model checkpoint (model.pth, meta.json, scaler.json)
sasl_transformer/                    — SASL grammar transformer module
data/                                — sign_library.json + conversations.db (auto-created)
```

### HTTP routes (in addition to WebSocket)

```
GET  /health                  — liveness probe
GET  /auth/session-secret     — session authentication token (localhost only)
GET  /api/status              — AI service health (Ollama + Whisper)
POST /speech                  — audio upload (deprecated — use WS speech_upload)
POST /rights/analyze          — rights analysis (deprecated — use WS rights_analyze)
POST /rights/letter           — letter generation (deprecated — use WS rights_letter)
POST /api/sasl/translate      — English → SASL gloss (sasl_transformer)
GET  /api/sasl/health         — SASL transformer health
GET  /api/sasl/library/stats  — sign library statistics
POST /api/sasl/cache/clear    — clear translation cache (localhost only)
```

### How a hearing message reaches the deaf avatar

```
Hearing types/speaks
  → window.amandla.send({type:'text'})
  → WebSocket → backend/main.py
  → _text_to_sasl_signs(text)        [SASL grammar transformer]
  → broadcast {type:'signs', signs:[...]} to deaf window
  → window.avatarPlaySigns(signs)    [avatar.js + signs_library.js]
```

### How a deaf sign reaches the hearing user

```
Deaf taps button or MediaPipe detects sign
  → window.amandla.send({type:'sign', text:'HELLO'})
  → WebSocket → backend buffers signs (1.5s debounce)
  → _signs_to_english(signs)         [Ollama → rule-based fallback]
  → {type:'deaf_speech', text:'Hello.'} to hearing window
  → SpeechSynthesis TTS reads it aloud
```

---

## Key Constraints

### Electron
- `contextIsolation: true`, `nodeIntegration: false` — never change these
- **No `require()` in any renderer** — use `window.amandla.*` from the preload bridge
- CORS must stay `allow_origins=["*"]` — Electron doesn't originate from localhost
- CSP must include `fonts.googleapis.com` (style-src) and `fonts.gstatic.com` (font-src)
- CSP must include `cdn.jsdelivr.net` (script-src + connect-src) for MediaPipe WASM
- Global emergency shortcut: `Ctrl+E` (or `Cmd+E` on macOS) triggers emergency overlay in both windows
- Auto-updater (`electron-updater`) runs only in packaged builds — no-op in dev mode
- Startup checks for Ollama availability; shows warning dialog if not running

### WebSocket message types
Valid types (all lowercase): `text`, `speech_text`, `speech_upload`, `signs`, `sign`,
`translating`, `deaf_speech`, `sasl_text`, `assist_phrase`, `landmarks`, `emergency`,
`status_request`, `rights_analyze`, `rights_letter`, `history_request`, `history_response`,
`sasl_ack`, `turn`

- Request/response messages **must** include `request_id`
- Broadcast messages (`signs`, `deaf_speech`, `turn`) must **not** include `request_id`
- `speech_text` is a synonym for `text` (both handled identically from hearing role)
- `assist_phrase` is pre-formed English from assist mode — no SASL reconstruction needed
- `history_request` can retrieve per-session messages or list all sessions (set `list_sessions: true`)

### WebSocket authentication
- Backend generates a `SESSION_SECRET` at startup (`backend/shared.py`)
- Electron main fetches it via `GET /auth/session-secret` before creating windows
- Every WebSocket connection **must** include `?token=<secret>` query parameter
- Token is validated with constant-time `hmac.compare_digest` — never use `==`

### Backend rules
- `.env` loaded once in `backend/main.py` — **never** call `load_dotenv()` in service files
- Error responses must use generic text — never `str(e)` or raw exception details
- Session state is in-memory (`backend/shared.py` → `sessions` dict) — intentional, restart clears it
- Max audio upload: 10 MB · Max text message: 5000 chars
- All user text must pass through `sanitise_text()` from `backend/shared.py` before processing
- Max 10 concurrent WebSocket sessions (`MAX_CONCURRENT_SESSIONS` in `shared.py`)
- Heavy AI operations (`speech_upload`, `rights_analyze`, `rights_letter`) are per-session rate-limited via `check_rate_limit()` in `shared.py`
- Lifespan startup order: `init_db()` → session reaper task → Whisper pre-load → Ollama pool start
- Conversation history is persisted in SQLite (`data/conversations.db`) — survives restarts
- All WS text/speech/sign handlers log to history via `history_db.log_message()` — failures are silently caught (must never break main flow)

### SASL / Signs
- `backend/services/sign_maps.py` — single source of truth for word→sign mappings
- `FILLER` set — only words with **zero** SASL equivalent (articles, prepositions)
- Modal verbs (`will`, `must`, `can`) map to SASL signs — **never put in FILLER**
- `FINISH` and `WILL` are critical SASL grammar markers — never drop them

---

## File Roles (full list)

| File | Purpose | Change frequency |
|------|---------|-----------------|
| `src/main.js` | Window creation, session ID, CSP, fetch session secret | Rarely |
| `src/preload/preload.js` | WebSocket bridge, all IPC, promise-based requests | Rarely |
| `src/windows/hearing/index.html` | Hearing UI: HTML shell | Occasionally |
| `src/windows/hearing/hearing.css` | Hearing window styles | Occasionally |
| `src/windows/hearing/hearing.js` | Hearing window logic: text, mic, TTS | Often |
| `src/windows/deaf/index.html` | Deaf UI: HTML shell | Occasionally |
| `src/windows/deaf/deaf.css` | Deaf window styles | Occasionally |
| `src/windows/deaf/deaf.js` | Deaf window logic: avatar, sign buttons, camera, mode toggle | Often |
| `src/windows/deaf/avatar.js` | Three.js avatar v2 (TransitionEngine) | Occasionally |
| `src/windows/deaf/avatar_driver.js` | Mixamo GLB bone driver (R1: actively used when GLB loads) | Rarely |
| `src/windows/deaf/mode_controller.js` | Sign mode ↔ assist mode toggle | Occasionally |
| `src/windows/rights/index.html` | Rights UI: HTML shell | Occasionally |
| `src/windows/rights/rights.css` | Rights window styles | Occasionally |
| `src/windows/rights/rights.js` | Rights window logic: wizard, PDF, API calls | Often |
| `signs_library.js` | 100+ SASL sign objects + sentenceToSigns() | Rarely |
| `backend/main.py` | FastAPI app creation, router registration, WS delegation | Rarely |
| `backend/shared.py` | Shared state, constants, auth token, sanitisation, rate limiting | Occasionally |
| `backend/middleware.py` | Per-IP per-endpoint HTTP rate limiting | Rarely |
| `backend/routers/health.py` | GET /health, /auth/session-secret, /api/status | Rarely |
| `backend/routers/speech.py` | POST /speech (deprecated — kept for testing) | Rarely |
| `backend/routers/rights.py` | POST /rights/analyze, /rights/letter (deprecated — kept for testing) | Rarely |
| `backend/ws/handler.py` | WebSocket message dispatcher — all WS message types | Often |
| `backend/ws/helpers.py` | send_safe(), broadcast(), broadcast_all() | Rarely |
| `backend/ws/session.py` | Session reaper background task | Rarely |
| `backend/services/sasl_pipeline.py` | HEARING→DEAF: English → SASL signs (3-tier fallback) | Occasionally |
| `backend/services/sign_reconstruction.py` | DEAF→HEARING: signs → English sentences | Occasionally |
| `backend/services/sign_maps.py` | English→SASL mappings (single source of truth) | Often |
| `backend/services/harps_recognizer.py` | HARPS ML sign recogniser (replaces Ollama for landmarks) | Occasionally |
| `backend/services/mediapipe_bridge.py` | MediaPipe landmarks → HARPS numpy arrays | Rarely |
| `backend/services/sign_buffer.py` | Sliding-window frame accumulator for HARPS | Rarely |
| `backend/services/ollama_pool.py` | Shared httpx connection pool for all Ollama calls (PERF-4) | Rarely |
| `backend/services/history_db.py` | SQLite conversation history (data/conversations.db) | Rarely |
| `backend/services/gemini_service.py` | DEPRECATED stub — kept to prevent ImportError | Never |
| `backend/services/whisper_service.py` | Speech-to-text (faster-whisper + ffmpeg) | Rarely |
| `backend/services/ollama_service.py` | Sign recognition via Ollama | Rarely |
| `backend/services/ollama_client.py` | Text → sign names via Ollama | Rarely |
| `backend/services/claude_service.py` | Rights analysis + letter generation via Ollama | Rarely |
| `backend/services/nvidia_service.py` | NVIDIA NIM fallback (optional) | Rarely |
| `backend/harps/` | HARPS ML framework: datasets, transforms, models, train | Rarely |
| `backend/harps_model/` | Trained checkpoint: model.pth, meta.json, scaler.json | Rarely |
| `sasl_transformer/transformer.py` | SASL grammar transformer | Occasionally |
| `sasl_transformer/routes.py` | FastAPI routes for `/api/sasl/*` endpoints | Rarely |
| `sasl_transformer/config.py` | Transformer settings (Ollama model, cache, etc.) | Rarely |
| `sasl_transformer/grammar_rules.py` | SASL grammar reordering rules | Occasionally |
| `sasl_transformer/models.py` | Pydantic request/response models | Rarely |
| `sasl_transformer/sign_library.py` | Sign library loader for transformer | Rarely |
| `sasl_transformer/websocket_handler.py` | WS handler class for real-time SASL translation | Rarely |
| `data/sign_library.json` | Sign library data (JSON) | Rarely |
| `data/conversations.db` | SQLite conversation history (auto-created) | Never (auto) |
| `docs/WEBSOCKET_PROTOCOL.md` | Full WebSocket message type reference | Occasionally |
| `tests/test_sign_maps.py` | Unit tests for sign map lookups (49 tests) | Occasionally |
| `tests/test_e2e_pipeline.py` | End-to-end pipeline tests (requires backend) | Occasionally |
| `tests/test_transformer.py` | SASL transformer unit tests | Occasionally |
| `scripts/test_all_ws_handlers.py` | End-to-end WebSocket handler test | Rarely |
| `scripts/train_harps.py` | Train HARPS model (WLASL or synthetic demo) | Rarely |
| `scripts/gen_harps_from_library.py` | Generate HARPS training data from signs_library.js | Rarely |
| `scripts/syntax_check.py` | Python syntax check for all backend files | Rarely |
| `Modelfile` | Ollama amandla model definition | Once |

---

## Adding a New Sign

Edit `signs_library.js` → `SIGN_LIBRARY` object. Pattern:

```javascript
'MY_SIGN': sign(
  'MY_SIGN', 'handshape name', 'one-line description', 5,
  {x:-0.5,y:0,z:-0.1}, {x:-0.5,y:0,z:0}, {x:0,y:0,z:0}, HS.flat,  // right arm
  IL.sh, IL.el, IL.wr, NL,                                           // left arm (idle)
  {j:'R_wr', ax:'z', amp:0.3, freq:1.5}                             // oscillation
)
```

Then add the English word mapping in `backend/services/sign_maps.py` → `WORD_MAP`.

---

## Adding a New WebSocket Message Type

1. Add handler function in `backend/ws/handler.py` (e.g. `async def _handle_foo(...)`)
2. Add dispatch entry in `websocket_endpoint()`'s `while True:` loop
3. Include `request_id` in the response if it's a request/response pair
4. Add the send method in `src/preload/preload.js` if renderer needs to call it
5. Handle the incoming message in the relevant window's `window.amandla.onMessage()`

---

## Common Debugging

| Problem | Where to look |
|---------|--------------|
| Avatar not animating | `signs_library.js` — check sign name matches exactly (UPPERCASE) |
| Signs dropped from translation | `sign_maps.py` FILLER set — word may be wrongly listed there |
| WebSocket not connecting | Backend not started / Ollama not running / bad session token |
| Google Fonts blocked | CSP in `src/main.js` — must include `fonts.googleapis.com` |
| MediaPipe WASM blocked | CSP in `src/main.js` — must include `cdn.jsdelivr.net` |
| Frontend fetch calls backend directly | Forbidden — use `window.amandla.*` preload methods only |
| Conversation history missing | Check `data/conversations.db` exists; `history_db.init_db()` runs at startup |
| Ollama calls slow / timing out | Check `ollama_pool.py` startup ran; `ollama serve` must be running |

---

## Running Tests

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

---

## Skill Library — Use These at Every Opportunity

All 16 skills live in `.aiassistant/rules/skills/`. Each skill is a full markdown guide
to read when the trigger conditions are met. Load the skill file, follow its process, then continue.

> **Rule**: When a task matches a skill's trigger, READ that skill file before writing any code or advice.

### Trigger Map

| Skill | File | Activate when… |
|-------|------|----------------|
| **amandla-code-standards** | `amandla-code-standards.md` | Writing, reviewing, or planning ANY code for Amandla. Mentions of avatar, signs, WebSocket, hearing/deaf/rights window, FastAPI, Electron. **Always active.** |
| **security-audit** | `security-audit.md` | "is this secure?", "check for vulnerabilities", "security check", "before I deploy", "production ready", reviewing auth/error-handling/env-var usage, WebSocket or Electron security config |
| **code-review** | `code-review.md` | "review this", "does this look good?", "check my code", "is this clean?", "refactor this", "is this production ready?", pasting code for feedback |
| **git-workflow** | `git-workflow.md` | Commits, branching, PRs, merge conflicts, GitHub Actions, CI/CD, "what commit message?", "how do I push?", "protect main" |
| **api-design** | `api-design.md` | New endpoint, new WebSocket message type, "design an API", "how should I structure this request/response", "new route", designing frontend↔backend data flow |
| **debugging** | `debugging.md` | "it's broken", "I'm getting an error", "not working", "why is it failing?", "exception", "crash", "undefined", "null", "404", "500", "WebSocket disconnecting", "avatar not moving", stack trace pasted |
| **documentation** | `documentation.md` | "write docs", "document this", "update README", "add comments", "write a docstring", "update CHANGELOG", "explain the architecture", after completing a major feature |
| **electron-ipc** | `electron-ipc.md` | Working on `src/main.js`, `src/preload/preload.js`, any renderer JS, adding new hearing↔backend or deaf↔backend communication, "how do I call the backend from the renderer?", new IPC channel |
| **performance-optimization** | `performance-optimization.md` | "it's slow", "avatar lags", "app is freezing", "high CPU", "memory leak", "optimize this", animation stutters, WebSocket latency issues |
| **product-planning** | `product-planning.md` | "I have an idea", "let's build X", "new feature", "PRD", "what should we build next?", "MVP", "user story", vague concept that needs shaping before coding |
| **project-bootstrap** | `project-bootstrap.md` | "start a new project", "scaffold this", "create a new app", setting up structure/config from scratch |
| **python-fastapi** | `python-fastapi.md` | Any Python backend code: routes, services, middleware, WebSocket handlers, Pydantic models, async functions. "Is this the right way to use FastAPI?" |
| **refactoring** | `refactoring.md` | "clean this up", "this is messy", "there's duplication", "this function is too long", "technical debt", file >200 lines, function >30 lines |
| **skill-manager** | `skill-manager.md` | "what skills do we have?", "do we need a new skill?", unfamiliar technology, starting a project where existing skills may not cover all needs |
| **testing-strategy** | `testing-strategy.md` | "how do I test this?", "write tests for X", "TDD", "unit test", "integration test", after new functionality is built (proactively suggest tests), when a bug is found |
| **ui-ux-design** | `ui-ux-design.md` | "redesign this", "improve the UI", "fix the UX", "accessibility", "make it intuitive", "design the layout", "color scheme", any new UI component or window |

### How to Use a Skill

1. Identify which skill(s) apply to the current task
2. Read the skill file: `.aiassistant/rules/skills/<skill-name>.md`
3. Follow the skill's process and checklist exactly
4. Multiple skills can apply at once — e.g. adding a new endpoint triggers `api-design` + `python-fastapi` + `amandla-code-standards`

### Skills Always Active Together
- `amandla-code-standards` applies to **every** task without exception
- `security-audit` quick-checks apply whenever writing backend or frontend code
- `git-workflow` reminders apply whenever code is finished and ready to commit

---

## Stale Docs — Ignore These

All archived docs have been moved to the `archive/` directory. Their first line says
"ARCHIVED". Do not follow their instructions — they reference deleted files and
contain outdated fixes (e.g. wrong CORS configuration that breaks Electron).

---

## References (current, valid files only)

- `CLAUDE.md` — authoritative state: what exists, what was deleted, what must not change
- `PROJECT_PLAN.md` — self-contained project plan: what's done, what remains, next steps
- `AMANDLA_FINAL_BLUEPRINT.md` — complete avatar.js and Three.js implementation spec
- `AMANDLA_MISSING_PIECES.md` — backend integration blueprint and gap fixes
- `SASL_Transformer_README.md` — SASL grammar transformer documentation
- `PRODUCTION_READINESS.md` — audit of all issues, fixes, and remaining work
- `docs/WEBSOCKET_PROTOCOL.md` — full WebSocket message type reference with examples
- `signs_library.js` — 100+ SASL signs with full bone data

---

## 🤖 AI Coding Rules (apply to EVERY task — no exceptions)

These rules apply on top of all AMANDLA-specific rules above.

### Planning (Most Important)
- **Plan before code** — always present a plan first: list files to create/change,
  functions to write, and approach to take. Wait for approval before writing code.
- This is non-negotiable: Plan first, implement second.

### Security (Highest Priority)
- NEVER hardcode secrets, API keys, passwords, tokens, or credentials in code
- ALWAYS use environment variables (`.env`) for any configuration values
- Follow OWASP Top 10 security best practices at all times
- Validate and sanitize ALL user inputs before processing
- Always implement proper error handling that does NOT expose internal system
  details to users — never return `str(e)` or raw stack traces to clients
- Flag any code written that could be a security vulnerability

### Code Quality
- Write clean, readable code following Clean Code principles
- Follow DRY — never duplicate code
- Follow SOLID — each function/class does ONE thing
- Follow KISS — never over-engineer
- Use descriptive, meaningful names for ALL variables, functions, and files
- Never use vague names like `x`, `temp`, `foo`, `data`, or `val`
- Never write a function longer than 20–30 lines — break it into smaller functions
- Never use magic numbers — always use named constants or environment variables

### Comments
- Add a comment above every function: what it does, what parameters it takes,
  what it returns
- Add inline comments for any logic that is not immediately obvious
- Comments must be written in plain English that a beginner can understand

### Before Deleting Any Code
- ALWAYS ask before removing existing code
- Show exactly what will be deleted and why
- Wait for explicit confirmation

### Third-Party Libraries
- NEVER add a library without explaining: what it does, why it's needed, whether
  a simpler built-in alternative exists, and any known security issues
- Wait for approval before adding it

### Error Handling
- NEVER skip try/catch (Python: try/except) blocks
- Always handle errors gracefully — show user-friendly messages, not raw dumps
- Log errors properly for debugging
- Never swallow errors silently (empty catch blocks are forbidden)

### After Finishing Any Task
- Give a plain English summary of exactly what was built
- List all files created or changed
- List any follow-up tasks (tests, `.env` updates, etc.)
- Flag areas that could be improved in a future iteration

### Common Mistakes to Always Avoid
- No hardcoded data replacing real calls
- No pushing directly to `main`/`master`
- No committing `node_modules`, `.env`, or build folders
- No functions that do more than one thing
- No unused variables or imports left in code
- No magic numbers without named constants
- No ignored exceptions (empty catch blocks)
- Always test edge cases, not just the happy path

