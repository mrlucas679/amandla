# AMANDLA — Production Readiness Audit
> **Generated**: March 30, 2026  
> **Scope**: Full read of every source file in the codebase  
> **Purpose**: Document EVERY issue, gap, improvement, and task needed to ship AMANDLA as a real product  
> **Status**: 35 of 37 issues FIXED — Phases 1–6 complete, 2 build items remaining

---

## How to Use This Document

Each issue has:
- **Severity** — CRITICAL / HIGH / MEDIUM / LOW / ENHANCEMENT
- **Category** — Security, Bugs, UX, Architecture, Performance, Testing, Build, Accessibility
- **What is wrong** — exact description
- **Where it is** — file(s) + line reference
- **Fix plan** — exactly what to change
- **Effort** — estimated time

Issues are grouped by category and ordered by severity within each group.

---

## TABLE OF CONTENTS

1. [Security Vulnerabilities](#1-security-vulnerabilities)
2. [Remaining Bugs (from INVESTIGATION_AND_PLAN.md)](#2-remaining-bugs)
3. [UX / Accessibility Gaps](#3-ux--accessibility-gaps)
4. [Architecture & Code Quality](#4-architecture--code-quality)
5. [Performance](#5-performance)
6. [Testing](#6-testing)
7. [Build / Packaging / Distribution](#7-build--packaging--distribution)
8. [Documentation & Onboarding](#8-documentation--onboarding)
9. [Feature Completeness](#9-feature-completeness)
10. [Implementation Order](#10-implementation-order)

---

## 1. SECURITY VULNERABILITIES

---

### SEC-1 — ~~`python-multipart` has 3 known HIGH-severity CVEs~~ ✅ FIXED

**Severity:** CRITICAL  
**Category:** Security — Dependency CVE  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
`requirements.txt` pinned `python-multipart==0.0.6` with 3 HIGH-severity CVEs (CVE-2024-24762, CVE-2024-53981, CVE-2026-24486).

**What was done:**  
Upgraded to `python-multipart>=0.0.22` in root `requirements.txt`. Deleted `backend/requirements.txt` (consolidated per ARCH-4).

---

### SEC-2 — ~~Electron 28.0.0 has 2 known CVEs (heap buffer overflow + ASAR bypass)~~ ✅ FIXED

**Severity:** HIGH  
**Category:** Security — Dependency CVE  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
`package.json` pinned `electron@^28.0.0` with CVE-2024-46993 and CVE-2025-55305.

**What was done:**  
Upgraded to `electron@^35.7.5` and `electron-builder@^25.0.0` in `package.json`.

---

### SEC-3 — ~~No input sanitisation on WebSocket text messages~~ ✅ FIXED

**Severity:** HIGH  
**Category:** Security — Input Validation  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
WebSocket text fields were never sanitised for control characters, null bytes, or XSS payloads. Rights window used `innerHTML` in several places.

**What was done:**  
1. Added `sanitise_text()` in `backend/shared.py` — strips C0/C1 control chars, normalises Unicode (NFC), truncates to max length.
2. All 12 user-text extraction points in `backend/ws/handler.py` now call `sanitise_text()`.
3. `rights.js` replaced `innerHTML` with DOM API calls (`createElement`, `textContent`).

---

### SEC-4 — ~~No authentication or session validation on WebSocket connections~~ ✅ FIXED

**Severity:** MEDIUM  
**Category:** Security — Access Control  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
Anyone who knew the session ID could connect. Session IDs had only ~16M possibilities per second. Backend bound to `0.0.0.0`.

**What was done:**  
1. `SESSION_SECRET` generated with `secrets.token_urlsafe(32)` (256-bit entropy) in `backend/shared.py`.
2. Electron main fetches it via `GET /auth/session-secret` and passes to windows via IPC.
3. Every WS connection requires `?token=<secret>` — validated with `hmac.compare_digest()`.
4. `BACKEND_HOST` changed to `127.0.0.1` in `.env` and `package.json` — localhost-only by default.
5. `MAX_CONCURRENT_SESSIONS=10` caps total sessions.

---

### SEC-5 — ~~`_ollama_signs_to_english` has indentation bug creating dead code~~ ✅ FIXED

**Severity:** HIGH  
**Category:** Security / Bug — Backend  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
The Ollama HTTP call in the old monolithic `main.py` had an indentation error where the POST call and status check were at different levels inside `async with`.

**What was done:**  
Code was refactored into `backend/services/sign_reconstruction.py` with correct indentation. Now uses `ollama_pool.get_client()` (shared connection pool) instead of creating a new `httpx.AsyncClient` per call.

---

### SEC-6 — ~~Rate limiter tracks by session ID only, not per-IP~~ ✅ FIXED

**Severity:** LOW  
**Category:** Security — Abuse Prevention  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
HTTP rate limiter was global (not per-IP). No cap on concurrent sessions.

**What was done:**  
1. `backend/middleware.py` now tracks per-IP per-endpoint with minute buckets and `X-Forwarded-For` support.
2. `MAX_CONCURRENT_SESSIONS=10` in `backend/shared.py` caps total concurrent WS sessions.

---

## 2. REMAINING BUGS (from INVESTIGATION_AND_PLAN.md)

These are the issues from the original investigation that have NOT yet been fixed:

---

### BUG-1 — ~~`sasl_text` backend handler splits multi-word signs on whitespace (ISSUE 3)~~ ✅ FIXED

**Severity:** CRITICAL  
**Category:** Bug — Backend  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
The `sasl_text` handler split typed SASL input with `.split()`, breaking multi-word signs like `"THANK YOU"` into individual words.

**What was done:**  
Added `split_sasl_gloss()` in `backend/services/sign_reconstruction.py` — performs longest-match against known multi-word signs before whitespace fallback. Handler in `backend/ws/handler.py` now calls `split_sasl_gloss()` instead of `.split()`.

---

### BUG-2 — ~~AssistMode phrases routed through wrong backend pipeline (ISSUE 4)~~ ✅ FIXED

**Severity:** HIGH  
**Category:** Bug — Backend  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
`mode_controller.js` dispatched assist-mode English phrases as `sasl_text` messages. Backend treated them as SASL gloss and ran reconstruction — wrong pipeline.

**What was done:**  
1. `src/windows/deaf/deaf.js` now sends `assist_phrase` type (not `sasl_text`).
2. `backend/ws/handler.py` has `_handle_assist_phrase()` that forwards text directly to hearing as `deaf_speech` (no SASL reconstruction).

---

### BUG-3 — ~~`_ollama_signs_to_english` indentation error (SEC-5 above)~~ ✅ FIXED

Already documented in SEC-5. Cross-reference only.

---

## 3. UX / ACCESSIBILITY GAPS

---

### UX-1 — ~~No offline indicator — user has no idea when Ollama is down~~ ✅ FIXED

**Severity:** HIGH  
**Category:** UX  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
When Ollama was not running, the app silently fell back to rule-based translation with no visible indicator.

**What was done:**  
Added a persistent dismissible yellow banner (`offline-banner`) to both `hearing.js` and `deaf.js`. Shows when `qwen !== 'alive'`, re-shows on each poll if still offline, resets dismiss state when AI comes back online.

---

### UX-2 — ~~No visual feedback when avatar is processing a sign queue~~ ✅ FIXED

**Severity:** MEDIUM  
**Category:** UX  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
No progress indicator when avatar was animating through multiple signs.

**What was done:**  
Added `window.AmandlaAvatar.onSignProgress(callback)` in `avatar.js` — fires `callback(currentIndex, totalCount)` each time a sign starts. Wired in `deaf.js` to update a progress indicator.

---

### UX-3 — ~~Deaf user cannot replay the last sign sequence~~ ✅ FIXED

**Severity:** MEDIUM  
**Category:** UX  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
Once signs were played, there was no way to replay them.

**What was done:**  
`deaf.js` stores `lastSigns`/`lastText` and shows a `replay-btn` ("↻ Replay") that calls `window.avatarPlaySigns(lastSigns, lastText)`.

---

### UX-4 — ~~Rights window has no connection status indicator~~ ✅ FIXED

**Severity:** MEDIUM  
**Category:** UX  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
Rights window had no status dot or connection banner.

**What was done:**  
Added `rights-status-dot` element in `rights.js` with green/red connection indicator.

---

### UX-5 — ~~No loading state for SASL translation in hearing window~~ ✅ FIXED

**Severity:** LOW  
**Category:** UX  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
After Send, no "translating…" indicator while waiting for `sasl_ack`.

**What was done:**  
`hearing.js` now shows `⏳ Translating to SASL…` in the transcript area immediately after `sendText()`. Replaced when `sasl_ack` arrives.

---

### UX-6 — ~~Hearing window startup overlay blocks mic button even after connection~~ ✅ FIXED

**Severity:** LOW  
**Category:** UX  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
First `pollStatus()` disabled the mic button because Whisper wasn't loaded yet, confusing the user.

**What was done:**  
Added `isFirstPoll` flag in `hearing.js`. On first poll, if Whisper isn't ready, shows a tooltip warning but leaves the mic button enabled. Subsequent polls enforce the disable normally.

---

### UX-7 — ~~Emergency overlay has no sound alert for hearing window on some systems~~ ✅ FIXED

**Severity:** LOW  
**Category:** UX / Accessibility  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
TTS might be unavailable; no visual alert for emergencies.

**What was done:**  
Added `@keyframes emg-border-flash` in `hearing.css` and `emg-flash` body class in `hearing.js` — flashes the window border red 5 times on emergency, providing a visual cue even if TTS fails.

---

### UX-8 — ~~`rights/index.html` — `loading-msg` and `loading-msg-2` use duplicated show/hide logic (ISSUE 14 from plan)~~ ✅ FIXED

**Severity:** LOW  
**Category:** Code Quality  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
Two separate loading spinner elements with duplicate `style.display` manipulation.

**What was done:**  
Extracted `showLoading(panelNumber, visible)` helper in `rights.js` — single function controls both spinners.

---

## 4. ARCHITECTURE & CODE QUALITY

---

### ARCH-1 — ~~All UI in monolithic HTML files (700–850 lines each)~~ ✅ FIXED

**Severity:** MEDIUM  
**Category:** Architecture  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
`hearing/index.html` (709 lines), `deaf/index.html` (954 lines), and `rights/index.html` (684 lines) each contained ALL CSS, HTML, and JavaScript in a single file. This made them hard to maintain, test, and diff.

**What was done:**  
Extracted CSS and JS into separate files. Each `index.html` is now a clean HTML shell:
- `hearing/index.html` (63 lines) + `hearing.css` + `hearing.js`
- `deaf/index.html` (89 lines) + `deaf.css` + `deaf.js`
- `rights/index.html` (120 lines) + `rights.css` + `rights.js`

CSP already allows `script-src 'self'` and `style-src 'self'` — no changes needed to `main.js`.
`CLAUDE.md` and `AGENTS.md` file maps updated to reflect the new structure.

---

### ARCH-2 — ~~`backend/main.py` is 1087 lines — too large for a single file~~ ✅ FIXED

**Severity:** MEDIUM  
**Category:** Architecture  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
Monolithic `main.py` contained routes, WS handler, SASL pipeline, sign reconstruction, rate limiting, session management, and broadcast helpers.

**What was done:**  
Split into focused modules — `backend/main.py` is now 133 lines (app creation + lifespan + router registration only):
- `backend/routers/health.py` — GET /health, /auth/session-secret, /api/status
- `backend/routers/speech.py` — POST /speech
- `backend/routers/rights.py` — POST /rights/analyze, /rights/letter
- `backend/ws/handler.py` — WebSocket message dispatcher
- `backend/ws/helpers.py` — send_safe(), broadcast(), broadcast_all()
- `backend/ws/session.py` — Session reaper background task
- `backend/services/sasl_pipeline.py` — text → SASL signs
- `backend/services/sign_reconstruction.py` — signs → English
- `backend/shared.py` — shared state, constants, auth, sanitisation, rate limiting

---

### ARCH-3 — ~~`mode_controller.js` exports via `module.exports` (Node.js) — invalid in Electron renderer~~ ✅ FIXED

**Severity:** LOW  
**Category:** Architecture  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
Dead `module.exports` block unreachable with `nodeIntegration: false`.

**What was done:**  
Removed the `module.exports` block. Only `window.ModeController` and `window.AssistEngine` assignments remain.

---

### ARCH-4 — ~~Two separate `requirements.txt` files with divergent content~~ ✅ FIXED

**Severity:** LOW  
**Category:** Architecture  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
Root and `backend/requirements.txt` had overlapping but divergent dependencies.

**What was done:**  
Consolidated into one root `requirements.txt`. Deleted `backend/requirements.txt`.

---

### ARCH-5 — ~~`signs_library_v2.js` exists alongside `signs_library.js` — confusing~~ ✅ FIXED

**Severity:** LOW  
**Category:** Code Cleanliness  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
`signs_library_v2.js` in root was never loaded — stale duplicate.

**What was done:**  
Deleted `signs_library_v2.js`.

---

## 5. PERFORMANCE

---

### PERF-1 — ~~Whisper model loads synchronously on first speech upload (15–45s stall)~~ ✅ FIXED

**Severity:** HIGH  
**Category:** Performance  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
`whisper_service.get_model()` lazy-loaded on first call, blocking the executor thread for 15–45s.

**What was done:**  
Pre-load Whisper in the lifespan handler via `loop.run_in_executor(None, whisper_service.get_model)` in `backend/main.py` — runs in a background thread so the event loop is never blocked.

---

### PERF-2 — ~~CDN scripts block deaf window initial render~~ ✅ FIXED

**Severity:** MEDIUM  
**Category:** Performance  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
Three.js loaded from CDN; MediaPipe scripts blocked render synchronously.

**What was done:**  
1. Bundled `three.min.js` locally in `assets/js/` — loaded from filesystem (`../../../assets/js/three.min.js`).
2. MediaPipe scripts now have `async` attribute so they don't block rendering.

---

### PERF-3 — `signs_library.js` is 1599 lines loaded on every deaf window open

**Severity:** LOW  
**Category:** Performance  

**What is wrong:**  
The entire sign library (134 signs × transition engine × helper functions) is loaded as a single blocking script. On slow machines this adds 100–200ms to initial load.

**Fix plan (low priority):**  
No action needed now. If performance becomes an issue, the library could be split into a lazy-loaded module for signs not in the "top 30" most used.

**Effort:** N/A (deferred)

---

### PERF-4 — ~~Ollama API calls have no connection pooling~~ ✅ FIXED

**Severity:** LOW  
**Category:** Performance  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
Every Ollama call created a new `httpx.AsyncClient` — fresh TCP handshake each time.

**What was done:**  
Created `backend/services/ollama_pool.py` — shared `httpx.AsyncClient` with keep-alive pooling (10 keep-alive / 20 max connections). Started in lifespan handler, closed on shutdown. All Ollama callers (`sign_reconstruction.py`, `ollama_service.py`, `ollama_client.py`, `claude_service.py`) import `get_client()` from the pool.

---

## 6. TESTING

---

### TEST-1 — ~~No automated tests for WebSocket message handlers~~ ✅ FIXED

**Severity:** HIGH  
**Category:** Testing  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
The WebSocket handler in `main.py` is the core of the app (600+ lines) and had ZERO automated tests. `scripts/ws_test.py` existed but was a manual smoke test only.

**What was done:**  
Created `scripts/test_all_ws_handlers.py` — an end-to-end WebSocket handler test suite covering:
- WS connection establishment + status message
- `status_request` handler with `request_id` round-trip
- `rights_analyze` handler (valid + missing-field validation)
- `rights_letter` validation (missing fields)
- `emergency` broadcast
- `text` → `signs` pipeline (turn indicator)
- `sasl_text` handler
- Second session connects independently (session isolation)

Run with: `python scripts/test_all_ws_handlers.py` (requires backend running on port 8000).

---

### TEST-2 — ~~No tests for `sign_maps.py` sentence_to_sign_names~~ ✅ FIXED

**Severity:** MEDIUM  
**Category:** Testing  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
`sign_maps.py` is the single source of truth for word→sign mappings and had no automated tests.

**What was done:**  
Created `tests/test_sign_maps.py` with 49 pytest tests across 10 test classes:
- Edge cases (empty, None, whitespace)
- Single word lookups (direct WORD_MAP hits, synonyms, case insensitivity)
- Phrase matching (2-word and 3-word PHRASE_MAP lookups)
- FILLER word dropping (articles, aux verbs, all-filler sentences)
- Modal verbs NOT in FILLER (will, must, can, should, could, finish, already)
- Stemming (`stem()` suffix stripping for -er, -ing, etc.)
- Fingerspelling (unknown words letter-by-letter, digits skipped)
- Punctuation stripping
- Full sentence integration
- Data integrity (no modals in FILLER, correct value types)

Run with: `python -m pytest tests/test_sign_maps.py -v`

---

### TEST-3 — ~~No end-to-end test that validates the full pipeline~~ ✅ FIXED

**Severity:** MEDIUM  
**Category:** Testing  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
No test validated the full round-trip: hearing types → backend translates → deaf receives signs → deaf taps button → hearing receives speech.

**What was done:**  
Created `tests/test_e2e_pipeline.py` with 15 end-to-end tests covering:
- Hearing + deaf connect to same session with token auth
- Hearing text → deaf receives 'translating' + 'signs' with correct SASL gloss (HELLO)
- Hearing receives 'sasl_ack' + 'turn' indicator
- Deaf sign button → hearing receives broadcast + 'deaf_speech' after 1.5s debounce
- Assist phrase bypass (BUG-2) — forwarded directly, source='assist'
- Emergency broadcast reaches both windows (broadcast_all)
- Invalid role rejection (WS close code 1008)
- Bad token rejection (WS close code 1008)

Run with: `python tests/test_e2e_pipeline.py` or `python -m pytest tests/test_e2e_pipeline.py -v`
(Requires backend running on port 8000.)

---

### TEST-4 — ~~`test_transformer.py` uses `/tmp` path (fails on Windows)~~ ✅ FIXED

**Severity:** LOW  
**Category:** Testing  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
`tests/test_transformer.py` used hardcoded `/tmp/test_sign_library.json` — fails on Windows.

**What was done:**  
Replaced both `/tmp` paths with `os.path.join(tempfile.gettempdir(), ...)` — works on all platforms. Added `import tempfile`.

---

## 7. BUILD / PACKAGING / DISTRIBUTION

---

### BUILD-1 — ~~No electron-builder configuration for macOS or Linux~~ ✅ FIXED

**Severity:** HIGH  
**Category:** Build  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
`package.json` only defined a `win` build target. No `mac` or `linux` targets existed.

**What was done:**  
Added `mac` (dmg target, `public.app-category.healthcare`) and `linux` (AppImage + deb targets, `Accessibility` category) build configurations to `package.json`.

---

### BUILD-2 — No app icon files exist

**Severity:** MEDIUM  
**Category:** Build  

**What is wrong:**  
`package.json` references `assets/icons/icon.ico` but the `assets/icons/` directory may not contain the actual icon files (`.ico`, `.icns`, `.png` at multiple sizes). Without proper icons, the packaged app uses Electron's default icon.

**Where it is:**  
`assets/icons/` directory

**Fix plan:**  
Create AMANDLA logo icon in all required formats:
- `icon.ico` (256×256, multi-size for Windows)
- `icon.icns` (macOS)
- `icon.png` (512×512 for Linux)

**Effort:** 1 hr (design + export)

---

### BUILD-3 — Python backend is not bundled — user must install Python + pip dependencies

**Severity:** HIGH  
**Category:** Build / Distribution  

**What is wrong:**  
The current `npm start` command expects Python, pip, and all dependencies to be pre-installed. This is a huge barrier for non-technical users. A real product needs either:
- A bundled Python runtime (PyInstaller / cx_Freeze)
- A Docker container for the backend
- Or a pre-built binary of the backend

**Fix plan (recommended):**  
Use **PyInstaller** to bundle the FastAPI backend into a single executable:
```bash
pyinstaller --onefile --name amandla-backend backend/main.py
```
Update `package.json` to launch the bundled binary instead of `python -m uvicorn`.

**Effort:** 4 hr (bundling + testing + platform-specific builds)

---

### BUILD-4 — ~~No auto-update mechanism~~ ✅ FIXED

**Severity:** MEDIUM  
**Category:** Build / Distribution  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
No mechanism for the app to check for updates or auto-update itself.

**What was done:**  
1. Installed `electron-updater@^6.8.3` as a dependency in `package.json`.
2. `src/main.js` imports `autoUpdater`, sets `autoDownload: false`, and registers event handlers for `update-available` (shows download dialog), `update-downloaded` (shows restart dialog), and `error` (logs to console).
3. `_setupAutoUpdater()` is called after windows are created, but only in packaged builds (`app.isPackaged`).
4. Update check runs after a 5 s delay so the UI has time to render.

---

### BUILD-5 — ~~`npm start` requires `ollama serve` to be running — no startup check~~ ✅ FIXED

**Severity:** MEDIUM  
**Category:** Build / UX  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
If Ollama was not running, the app started but all AI features silently degraded with no startup warning.

**What was done:**  
Added `_checkOllamaRunning()` in `src/main.js` — checks `http://localhost:11434/api/tags` on startup. If unreachable, shows a dialog: "Ollama is not running. AI features will be limited." with a "Continue Anyway" button. Runs before window creation with a 3 s timeout.

---

### BUILD-6 — ~~No `.gitignore` visible — risk of committing `node_modules`, `.env`, build artifacts~~ ✅ FIXED

**Severity:** LOW  
**Category:** Build  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
No `.gitignore` existed — risk of committing secrets, `node_modules`, build artefacts.

**What was done:**  
Created comprehensive `.gitignore` (52 lines) covering: `.env`, `__pycache__/`, `node_modules/`, `dist/`, `logs/`, `.venv/`, editor metadata, OS artefacts, and temp files.

---

## 8. DOCUMENTATION & ONBOARDING

---

### DOC-1 — ~~README.md may be outdated~~ ✅ FIXED

**Severity:** MEDIUM  
**Category:** Documentation  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
README.md was 337 lines of stale content referencing deleted files, outdated architecture, and incorrect setup steps.

**What was done:**  
Rewrote README.md from scratch with: what AMANDLA does, prerequisites table, installation steps, how to start, current architecture diagram, full project structure, environment variables, test commands, current documentation table, key constraints, and contribution guide.

---

### DOC-2 — ~~10 stale `ARCHIVED` doc files still in the root directory~~ ✅ FIXED

**Severity:** LOW  
**Category:** Documentation  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
CLAUDE.md §10 listed 10+ stale doc files in the root that confused both humans and AI agents.

**What was done:**  
Created `archive/` directory and moved all 12 stale docs into it: APPLICATION_STARTED.md, FINAL_STATUS_REPORT.md, OPERATIONAL_STATUS.md, SETUP_COMPLETE.md, SETUP_VERIFICATION.md, WHAT_WAS_COMPLETED.md, PROJECT_SETUP_SUMMARY.md, START_HERE.md, NEXT_STEPS.md, AGENT_TASKS.md, AGENT_PROMPTS.md, AMANDLA_BLUEPRINT (2).md.

---

### DOC-3 — ~~No API documentation for WebSocket message format~~ ✅ FIXED

**Severity:** MEDIUM  
**Category:** Documentation  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
The WebSocket protocol (15+ message types, request/response pairs, broadcasts) was only documented in scattered code comments.

**What was done:**  
Created `docs/WEBSOCKET_PROTOCOL.md` — comprehensive reference covering: connection lifecycle and authentication, all 12 message types with direction/fields/examples, request/response vs broadcast classification, rate limiting rules, error response format, and preload bridge API table.

---

## 9. FEATURE COMPLETENESS

---

### FEAT-1 — ~~Camera sign recognition via MediaPipe + Ollama is unreliable~~ ✅ FIXED (Phase 2)

**Severity:** HIGH  
**Category:** Feature Quality  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
Even with the feature extraction fix (Issue 5 from the original plan), using an LLM (Ollama 3B) to classify hand gestures from computed features is fundamentally imprecise. The model has no real training data for SASL hand configurations. It's guessing from textual descriptions of finger states.

**What was done:**  
Phase 2 implemented: `_handle_landmarks()` in `backend/ws/handler.py` now tries HARPS ML classifier first (per-session `HARPSSignRecognizer` with frame buffering), falls back to Ollama only if HARPS model is unavailable. HARPS recognizer instances are stored in `backend/shared.py` → `harps_recognizers` dict and cleaned up on session disconnect. Training script (`scripts/gen_harps_from_library.py`) generates training data from `signs_library.js` via forward kinematics — no video data needed.

---

### FEAT-2 — ~~Avatar only uses a procedural Three.js skeleton — no realistic model~~ ✅ FIXED

**Severity:** MEDIUM  
**Category:** Feature Quality  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
The avatar is a geometric stick figure. While functional, it looks clinical and doesn't convey the nuance of real sign language (facial expressions, body posture, non-manual markers). A `human_signing.fbx` file exists in the deaf window directory but is never used.

**What was done:**  
1. Copied `human_signing.glb` to `assets/models/avatar.glb` (33 MB).
2. Bundled `GLTFLoader.js` (r128, matching Three.js) at `assets/js/GLTFLoader.js`.
3. Added `avatar_driver.js` script tag to `deaf/index.html` (loads before `avatar.js`).
4. Added `tryLoadGLBModel()` in `avatar.js` — loads GLB via `THREE.GLTFLoader`, binds bones via `AvatarDriver.bindBonesFromGLTF()`, hides procedural skeleton on success.
5. Updated `applyPoseDirect()` to branch: GLB mode uses `AvatarDriver.remapPoseForMixamo()` + `applyHandshapeGLTF()` + `updateTwistBones()`; procedural mode uses direct Euler sets.
6. Graceful fallback: if GLB fails to load (missing file, wrong rig), procedural skeleton remains active.

---

### FEAT-3 — ~~No conversation history or session persistence~~ ✅ FIXED

**Severity:** MEDIUM  
**Category:** Feature  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
All conversations are lost when the app restarts (in-memory sessions). In a medical setting, having a record of what was communicated is important for both legal and clinical reasons.

**What was done:**  
1. Created `backend/services/history_db.py` — SQLite database (`data/conversations.db`) with `conversations` table. Schema: `id, session_id, timestamp, direction, original_text, sasl_gloss, translated_text, source`. Uses Python stdlib `sqlite3` + `asyncio.to_thread()` — no new dependencies.
2. Database initialised at startup via `init_db()` in `backend/main.py` lifespan handler.
3. Added `log_message()` calls to four handler points in `backend/ws/handler.py`: `_handle_text`, `_handle_speech_upload`, `_handle_sasl_text`, `_handle_assist_phrase`.
4. Added `_handle_history_request()` WebSocket handler + dispatch entry for `history_request` message type.
5. Added `requestHistory()` and `listSessions()` to `src/preload/preload.js` bridge.
6. Added "📋 History" button in hearing window topbar (`hearing/index.html`) with modal overlay showing chronological message history, styled in `hearing.css`.


---

### FEAT-4 — ~~No print/export of conversation transcript~~ ✅ FIXED

**Severity:** LOW  
**Category:** Feature  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
The hearing window had a message log but no way to export or print it.

**What was done:**  
Added a "🖨 Print" button (`print-btn`) in the hearing window toolbar. `hearing.js` handles click → checks for messages → calls `window.print()`. `hearing.css` has `@media print` rules that hide everything except the message log for a clean printout.

---

### FEAT-5 — ~~No multilingual SASL support — only English → SASL~~ ✅ FIXED

**Severity:** LOW  
**Category:** Feature  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
SASL is language-agnostic (it's a visual language), but the text→SASL pipeline assumed English input. South Africa has 11 official languages. Whisper can transcribe isiZulu, isiXhosa, Afrikaans etc., but the SASL transformer only had English grammar rules.

**What was done:**  
1. Added `_translate_to_english()` in `sasl_pipeline.py` — calls Ollama (shared pool) to translate non-English text to English before entering the SASL pipeline.
2. Updated `text_to_sasl_signs()` signature with optional `language` parameter — English input bypasses translation entirely (no double-translation).
3. Added `SA_LANGUAGE_LABELS` dict covering all 11 official SA languages for human-readable prompts.
4. Added `TRANSLATION_SYSTEM_PROMPT`, `TRANSLATION_TIMEOUT_S`, `TRANSLATION_TEMPERATURE` named constants.
5. Added `TRANSLATION_OLLAMA_MODEL` env var (defaults to `OLLAMA_MODEL`) for optional override with a general-purpose model.
6. Wired `language` through `_handle_text` and `_handle_speech_upload` in `handler.py`.
7. `sasl_ack` and `signs` broadcasts now include `source_language` and `original_input` metadata.
8. Hearing window UI shows "✓ Translated from {language} → SASL: ..." for non-English input.
9. Changed `WHISPER_LANGUAGE=` to empty (auto-detect) in `.env` and `.env.example`.
10. Graceful fallback: if Ollama translation fails, original text passes through unchanged.

---

### FEAT-6 — ~~No keyboard shortcut for emergency~~ ✅ FIXED

**Severity:** LOW  
**Category:** Accessibility  
**Status:** COMPLETED — March 30, 2026

**What was wrong:**  
The emergency button was a small on-screen button in the deaf window's quick-signs category.

**What was done:**  
Registered `CommandOrControl+E` global shortcut in `src/main.js` using Electron's `globalShortcut` API. Sends `emergency-trigger` IPC to both hearing and deaf windows. Preload bridge exposes `window.amandla.onEmergencyShortcut()` listener. Both windows show the emergency overlay on trigger.

---

## 10. IMPLEMENTATION ORDER

Implement in this order to get maximum value with minimum risk:

### PHASE 1 — ~~Critical Security + Bugs (Day 1)~~ ✅ COMPLETE

| # | Issue | Files Changed | Status |
|---|-------|---------------|--------|
| 1 | ~~SEC-1: Upgrade python-multipart~~ | `requirements.txt` | ✅ Done |
| 2 | ~~SEC-5: Fix indentation bug~~ | `backend/services/sign_reconstruction.py` | ✅ Done |
| 3 | ~~BUG-1: Fix multi-word sign splitting~~ | `backend/services/sign_reconstruction.py`, `backend/ws/handler.py` | ✅ Done |
| 4 | ~~BUG-2: Add `assist_phrase` handler~~ | `deaf/deaf.js`, `backend/ws/handler.py` | ✅ Done |
| 5 | ~~SEC-3: Sanitise WebSocket text + audit innerHTML~~ | `backend/shared.py`, `backend/ws/handler.py`, `rights/rights.js` | ✅ Done |

**Phase 1 total: ~1.5 hours**

### PHASE 2 — ~~High-Priority UX + Performance (Day 1–2)~~ ✅ COMPLETE

| # | Issue | Files Changed | Status |
|---|-------|---------------|--------|
| 6 | ~~SEC-2: Upgrade Electron~~ | `package.json` | ✅ Done |
| 7 | ~~UX-1: Add "AI offline" persistent banner~~ | `hearing/hearing.js`, `deaf/deaf.js` | ✅ Done |
| 8 | ~~PERF-1: Pre-load Whisper at startup~~ | `backend/main.py` | ✅ Done |
| 9 | ~~UX-5: Show "translating…" in hearing window~~ | `hearing/hearing.js` | ✅ Done |
| 10 | ~~UX-6: Don't disable mic on first poll~~ | `hearing/hearing.js` | ✅ Done |
| 11 | ~~PERF-2: Bundle Three.js locally~~ | `deaf/index.html`, `assets/js/` | ✅ Done |

**Phase 2 total: ~1.5 hours**

### PHASE 3 — ~~Testing (Day 2–3)~~ ✅ COMPLETE

| # | Issue | Files Changed | Status |
|---|-------|---------------|--------|
| 12 | ~~TEST-4: Fix Windows temp path~~ | `tests/test_transformer.py` | ✅ Done |
| 13 | ~~TEST-2: Add sign_maps tests~~ | `tests/test_sign_maps.py` | ✅ Done |
| 14 | ~~TEST-1: Add WebSocket handler tests~~ | `scripts/test_all_ws_handlers.py` | ✅ Done |
| 15 | ~~TEST-3: Add E2E pipeline test~~ | `tests/test_e2e_pipeline.py` | ✅ Done |

### PHASE 4 — ~~Build & Distribution (Day 3–4)~~ ✅ COMPLETE (except BUILD-2/3)

| # | Issue | Files Changed | Status |
|---|-------|---------------|--------|
| 16 | ~~BUILD-6: Create .gitignore~~ | `.gitignore` | ✅ Done |
| 17 | ~~BUILD-1: Add mac/linux build targets~~ | `package.json` | ✅ Done |
| 18 | BUILD-2: Create app icons | `assets/icons/` | Open |
| 19 | ~~BUILD-5: Add Ollama startup check~~ | `src/main.js` | ✅ Done |
| 20 | BUILD-3: Bundle Python backend | `pyinstaller` config, `package.json` | Open |

**Phase 4 total: ~6 hours**

### PHASE 5 — ~~Architecture & Polish (Day 4–5)~~ ✅ COMPLETE

| # | Issue | Files Changed | Status |
|---|-------|---------------|--------|
| 21 | ~~ARCH-1: Extract CSS/JS from HTML~~ | All 3 windows | ✅ Done |
| 22 | ~~ARCH-2: Split main.py into modules~~ | `backend/` | ✅ Done |
| 23 | ~~ARCH-4: Consolidate requirements.txt~~ | `requirements.txt` | ✅ Done |
| 24 | ~~ARCH-5: Delete stale signs_library_v2.js~~ | Root | ✅ Done |
| 25 | ~~DOC-2: Archive stale docs~~ | Root → `archive/` | ✅ Done |
| 26 | ~~DOC-1: Rewrite README.md~~ | `README.md` | ✅ Done |
| 27 | ~~DOC-3: Write WebSocket protocol doc~~ | `docs/WEBSOCKET_PROTOCOL.md` (new) | ✅ Done |

**Phase 5 total: ~7 hours**

### PHASE 6 — Feature Enhancements (Week 2)

| # | Issue | Files Changed | Status |
|---|-------|---------------|--------|
| 28 | ~~UX-3: Add replay button~~ | `deaf/deaf.js` | ✅ Done |
| 29 | ~~UX-4: Rights window status indicator~~ | `rights/rights.js` | ✅ Done |
| 30 | ~~FEAT-6: Global emergency shortcut~~ | `src/main.js`, `preload.js` | ✅ Done |
| 31 | ~~PERF-4: Ollama connection pooling~~ | `backend/services/ollama_pool.py` | ✅ Done |
| 32 | ~~SEC-4: Bind backend to localhost~~ | `.env`, `backend/shared.py`, `package.json` | ✅ Done |
| 33 | ~~FEAT-4: Print transcript~~ | `hearing/hearing.js`, `hearing/hearing.css` | ✅ Done |
| 34 | ~~FEAT-2: GLB avatar model~~ | `deaf/avatar_driver.js`, `deaf/avatar.js`, `deaf/index.html` | ✅ Done |
| 35 | ~~FEAT-1 P2: HARPS sign classifier~~ | `backend/ws/handler.py`, `backend/shared.py` | ✅ Done |
| 36 | ~~FEAT-3: Conversation history (SQLite)~~ | `backend/services/history_db.py`, `handler.py`, `hearing.js` | ✅ Done |
| 37 | ~~BUILD-4: Auto-update~~ | `src/main.js`, `package.json` | ✅ Done |

**Phase 6 total: ~20 hours**

---

## TOTAL ESTIMATED EFFORT

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Critical Security + Bugs | ✅ COMPLETE |
| 2 | High-Priority UX + Performance | ✅ COMPLETE |
| 3 | Testing | ✅ COMPLETE |
| 4 | Build & Distribution | 3/5 done — BUILD-2 (icons) + BUILD-3 (pyinstaller) remain |
| 5 | Architecture & Polish | ✅ COMPLETE |
| 6 | Feature Enhancements | ✅ COMPLETE |
| **TOTAL REMAINING** | | **~2 items (~5 hr) — BUILD-2 + BUILD-3 only** |

---

## WHAT WAS ALREADY FIXED (for reference)

These issues from `INVESTIGATION_AND_PLAN.md` have already been implemented:

| Issue # | Description | Status |
|---------|------------|--------|
| 1 | CSP `connect-src` for MediaPipe | ✅ Fixed |
| 2 | Ollama `system` prompt override | ✅ Fixed |
| 5 | Landmark feature extraction | ✅ Fixed |
| 6 | Remove `speakText` from deaf emergency | ✅ Fixed |
| 7 | Per-type rate limit intervals | ✅ Fixed |
| 8 | Status dot reflects Whisper + Ollama | ✅ Fixed |
| 9 | Turn indicator 12s reset | ✅ Fixed |
| 10 | Remove dead avatar_driver.js load | ✅ Fixed |
| 11 | conn-banner consistency | ✅ Fixed |
| 12 | Use window.avatarPlaySigns API | ✅ Fixed |
| 13 | Emergency auto-dismiss 30s | ✅ Fixed |
| 14 | Quick-sign validation at startup | ✅ Fixed (renamed to startup console check) |

---

## WHAT IS NOT A BUG (Confirmed Correct)

These were investigated and confirmed to be working correctly:

- `translate_with_rules` public method — correct delegation pattern ✓
- `sentenceToSigns` with individual strings — works via `SIGN_LIBRARY[upper]` lookup ✓
- Duplicate WebSocket connection guard — preload's session-key guard is correct ✓
- Rights window CSP — `_applyCSP(rightsWin)` IS called ✓
- `sasl_ack` for text messages — sent correctly ✓
- ModeController init race — script loading order is correct ✓
- `_sign_buffers` race condition — cancel+recreate pattern is safe ✓
- CORS `["*"]` — required for Electron (not a browser origin) ✓
- Single `load_dotenv()` in main.py — correct pattern ✓
- In-memory sessions — intentional (restart clears, this is fine for desktop) ✓

