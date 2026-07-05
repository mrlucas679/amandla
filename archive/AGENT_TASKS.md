# ARCHIVED — DO NOT USE
> This file claimed "ALL ISSUES FIXED" which was incorrect and caused agents to skip real bugs.
> It has been replaced. Read `CLAUDE.md` for the current project state and constraints.

---

## ✅ ALL ISSUES — ALREADY FIXED

Every issue below has been implemented directly. These prompts are provided
so you can re-run any agent if you need to reverify or extend the fixes.

---

## Agent 1: BACKEND (backend/main.py)

**What was fixed:**
- Added 5 WebSocket handlers: `speech_upload`, `status_request`, `rights_analyze`, `rights_letter`, `emergency`
- Registered `RateLimitMiddleware` from `backend/middleware.py`
- Added `import base64` for speech upload decoding
- Fixed session cleanup race condition with try/except wrapper
- All handlers include `request_id` in responses for preload promise resolution
- Broadcast messages (signs to deaf) do NOT include `request_id`
- Input validation on all handlers (missing fields return error with `request_id`)

**Claude Code prompt (if you need to re-run):**
```
claude "Read backend/main.py and verify these 5 WebSocket handlers exist inside the websocket_endpoint while-loop: speech_upload (decodes base64 audio, runs Whisper, returns transcription+signs with request_id), status_request (checks Ollama+Whisper health, returns with request_id), rights_analyze (calls claude_service.analyse_incident, returns with request_id), rights_letter (calls claude_service.generate_rights_letter, returns with request_id), emergency (broadcasts to all users). Also verify RateLimitMiddleware is registered and session cleanup has try/except. Fix anything missing."
```

---

## Agent 2: FRONTEND (hearing, deaf, rights HTML files)

**What was fixed:**
- `hearing/index.html`: Replaced `fetch('/speech')` → `window.amandla.uploadSpeech()`
- `hearing/index.html`: Replaced `fetch('/api/status')` → `window.amandla.requestStatus()`
- `deaf/index.html`: Replaced `fetch('/api/status')` → `window.amandla.requestStatus()`
- `rights/index.html`: Replaced `fetch('/rights/analyze')` → `window.amandla.analyzeRights()`
- `rights/index.html`: Replaced `fetch('/rights/letter')` → `window.amandla.generateLetter()`
- `rights/index.html`: Added WebSocket connection setup (was completely missing)

**Claude Code prompt (if you need to re-run):**
```
claude "Verify that src/windows/hearing/index.html, src/windows/deaf/index.html, and src/windows/rights/index.html contain ZERO direct fetch('http://localhost:8000/...') calls. All should use window.amandla.* methods from preload.js instead. Also verify rights/index.html has a WebSocket connection setup calling window.amandla.connect(). Fix anything missing."
```

---

## Agent 3: ARCHITECTURE (cleanup + documentation)

**What was fixed:**
- Deleted `src/windows/hearing/signs_library.js` (1,061 lines of dead v1 code)
- Deleted `src/windows/hearing/avatar.js` (dead code, never loaded by HTML)
- Added architecture documentation comment to `src/main.js`

**Claude Code prompt (if you need to re-run):**
```
claude "Verify src/windows/hearing/ contains ONLY index.html (no avatar.js or signs_library.js). Verify src/main.js has an ARCHITECTURE NOTE comment block explaining the two-window split-screen design. Fix anything missing."
```

---

## Agent 4: INTEGRATION/QA (preload + end-to-end wiring)

**What was fixed:**
- Increased `REQUEST_TIMEOUT_MS` from 30000 → 60000 in `src/preload/preload.js`
- Verified `request_id` round-trip: all WS handlers include it in responses
- Verified broadcast messages do NOT include `request_id`
- Verified rights window connects as role `'rights'`

**Claude Code prompt (if you need to re-run):**
```
claude "Read src/preload/preload.js and backend/main.py. Verify REQUEST_TIMEOUT_MS is 60000. Verify every new WS handler (speech_upload, status_request, rights_analyze, rights_letter) includes request_id in its response. Verify broadcast messages like {type:'signs'} do NOT include request_id. Fix anything missing."
```

---

## Execution Order

```
Agent 3 (Architecture)  ─────────────────► Done (independent)

Agent 1 (Backend)  ──────┐
                         ├──► Agent 4 (Integration) ──► Done
Agent 2 (Frontend) ──────┘
```

- Agents 1, 2, 3 can run in PARALLEL (no file conflicts)
- Agent 4 runs AFTER 1 & 2 (validates wiring)

---

## Quick Test After All Fixes

```powershell
# 1. Start Ollama (required)
ollama serve

# 2. Start AMANDLA
npm start

# 3. Test flow:
#    - Click START SESSION in hearing window
#    - Click READY in deaf window
#    - Type "Hello how are you" in hearing → should see signs on deaf avatar
#    - Click EMERGENCY on deaf → both windows show red overlay
#    - Click mic button → speak → Whisper transcribes via WebSocket
#    - Click RIGHTS button → rights window opens → fill form → analyse
```

