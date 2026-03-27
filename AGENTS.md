# AGENTS.md — AI Agent Guide for AMANDLA Desktop

> Guidance for AI coding agents working on the AMANDLA communication bridge project
> Last Updated: March 27, 2026

---

## Project Overview

**AMANDLA** is an Electron-based sign language communication bridge serving disabled South Africans. It connects **hearing users** (speech input via Whisper) with **deaf users** (sign language visual output via 3D avatar). The architecture spans desktop (Electron + Three.js), backend (FastAPI + Ollama), and real-time communication (WebSockets).

**Critical constraint**: This is a *mono-window split-screen application* — hearing and deaf users see different interfaces in real-time via shared session state and WebSocket messages.

---

## Architecture & Data Flow

### Three Core Layers

1. **Desktop (Electron)** — `src/main.js`
   - Spawns split-screen: hearing window (0, 0) and deaf window (halfWidth, 0)
   - Both windows load HTML views with WebSocket bridge via preload.js
   - Windows communicate *only* through backend WebSocket, not IPC

2. **Backend (FastAPI)** — `../amandla/backend/main.py`
   - WebSocket endpoint: `ws://localhost:8000/ws/{sessionId}/{role}`
   - Routes speech→signs pipeline: Whisper → Ollama sign recognition → text→sign conversion
   - State: per-session shared context; no global session store
   - Runs on `http://localhost:8000`; health check endpoint: `/health`

3. **Signs Library** — `signs_library.js`
   - 100+ SASL signs from Einstein Hands SASL Dictionary
   - Exports: `sentenceToSigns(text)` → array of sign objects
   - Each sign has: `R` (right arm), `L` (left arm) with bone rotations (sh/el/wr) + `osc` (oscillation)
   - Fallback: `fingerspell(word)` for unknown words
   - Must be copied to `src/windows/hearing/signs_library.js` before use

### Critical Communication Pattern

The **preload bridge** (`src/preload/preload.js`) is the only way frontend talks to backend:
- `window.amandla.connect(sessionId, role)` — initiates WebSocket
- `window.amandla.send(payload)` — sends message (returns bool for success)
- `window.amandla.onMessage(handler)` — registers message listener
- `window.amandla.onConnectionChange(handler)` — tracks connection state

**No direct HTTP calls from frontend.** All communication is WebSocket-based, authenticated by sessionId.

---

## Startup Sequence & Critical Dependencies

### Build Order (from `AMANDLA_BLUEPRINT__2_.md`)

1. **Thursday night (setup)**:
   - Create `backend/__init__.py`, `backend/routers/__init__.py`, `backend/services/__init__.py` (empty files)
   - Create `backend/requirements.txt` with all dependencies (see *Dependencies* section)
   - Create `Modelfile` in `amandla/` root for Ollama model
   - Run `ollama create amandla -f Modelfile`

2. **Friday (main build)**:
   - Implement backend routers (sign_ws WebSocket, speech_upload multipart/form-data)
   - Implement `sentenceToSigns` integration in backend
   - Build avatar.js in Three.js (see *Avatar Section* below)

### Launch Flow

```powershell
npm start
# Internally runs:
#   concurrently:
#     - npm run backend      (cd ../amandla && uvicorn on :8000)
#     - wait-on :8000/health && electron .
```

**Critical**: Backend must respond to health check before Electron starts, or windows spawn but can't connect.

---

## Key Files & Their Roles

| File | Role | Modification Frequency |
|------|------|----------------------|
| `src/main.js` | Window setup, lifecycle | Rarely — foundational |
| `src/preload/preload.js` | WebSocket bridge | Rarely — add methods only if new IPC patterns |
| `src/windows/hearing/index.html` | Hearing UI (text input) | Frequently — UI changes |
| `src/windows/deaf/index.html` | Deaf UI (avatar container) | Frequently — avatar integration |
| `signs_library.js` | Sign database + text→signs | Rarely — add signs, fix mappings |
| `AMANDLA_FINAL_BLUEPRINT.md` | Avatar.js implementation spec | Reference only — don't edit |
| `AMANDLA_MISSING_PIECES.md` | Backend gap fixes | Reference only — follow for setup |

---

## Signs Library Integration

### How It Works

1. User (hearing) types/speaks: `"Hello, how are you?"`
2. Backend calls `sentenceToSigns("Hello, how are you?")`
3. Library splits text → normalizes words (via `WORD_MAP`) → looks up in `SIGN_LIBRARY`
4. Returns array: `[{name: 'HELLO', R: {...}, L: {...}, osc: {...}}, {name: 'HOW ARE YOU', ...}, ...]`
5. Avatar reads queue and animates each sign sequentially

### Data Structure

```javascript
// One sign object from sentenceToSigns()
{
  name: 'HELLO',
  shape: 'Hand waves away from head',
  desc: 'Move hand away from head — universal greeting',
  conf: 5,
  R: {
    sh: {x: -1.35, y: 0, z: -0.18},        // shoulder rotation (radians)
    el: {x: 0.05, y: 0, z: 0},             // elbow rotation
    wr: {x: 0, y: 0, z: 0},                // wrist rotation
    hand: {i: [...], m: [...], r: [...], p: [...], t: [...]}  // handshape (finger curls)
  },
  L: {...},  // left arm (mirror or different for bilateral signs)
  osc: {j: 'R_wr', ax: 'z', amp: 0.35, freq: 1.8}  // oscillation: joint, axis, amplitude, frequency
}
```

### Adding New Signs

Edit `signs_library.js` → `SIGN_LIBRARY` object:

```javascript
'MY_NEW_SIGN': sign(
  'MY_NEW_SIGN',
  'Brief handshape name',
  'One-line description of hand position and movement',
  5,  // confidence 1-5
  // Right arm: shoulder, elbow, wrist, handshape
  {x: -0.5, y: 0, z: -0.1}, {x: -0.5, y: 0, z: 0}, {x: 0, y: 0, z: 0}, HS.flat,
  // Left arm: (usually idle)
  IL.sh, IL.el, IL.wr, NL,
  // Oscillation: joint, axis, amplitude, frequency
  {j: 'R_wr', ax: 'z', amp: 0.3, freq: 1.5}
)
```

**Presets available**: `HS.*` (handshapes: `flat`, `fist_A`, `fist_S`, `point1`, `vhand`, `whand`, etc.) and `ARM.*` (positions: `idle_R`, `chest_R`, `chin_R`, `forward_R`, `raised_R`).

---

## Avatar Implementation (Three.js)

The avatar is the visual heart of the deaf user experience. **Critical**: It must consume data from `signs_library.js`, not custom arrays.

### Bone Structure Required

```javascript
avatarBones = {
  'R_sh': THREE.Bone(),  // right shoulder
  'R_el': THREE.Bone(),  // right elbow
  'R_wr': THREE.Bone(),  // right wrist
  'L_sh': THREE.Bone(),  // left shoulder
  'L_el': THREE.Bone(),  // left elbow
  'L_wr': THREE.Bone(),  // left wrist
  'R_hand': {           // hand fingers: i, m, r, p, t (thumb)
    'i': [mcp, pip, dip],
    'm': [mcp, pip, dip],
    // ...
  },
  'L_hand': {...}
}
```

### Animation Loop

1. Dequeue next sign from `signQueue`
2. Animate `signProgress` from 0 → 1 over `SIGN_DURATION` (0.55s typical)
3. Apply rotations to bones: `bone.rotation = interpolate(currentSign.R.sh, signProgress)`
4. Apply finger curls: `fingerBones[i][j].rotation.z = interpolate(handshape[finger][joint], progress)`
5. Apply oscillation: `bone.rotation[axis] += sign.osc.amp * sin(time * sign.osc.freq)`
6. Insert gap (0.12s) between signs
7. Loop

### File Location

Must exist at: `src/windows/deaf/avatar.js`

Referenced from: `src/windows/deaf/index.html` via `<script src="avatar.js"></script>`

**Template provided in AMANDLA_FINAL_BLUEPRINT.md** — use that exact structure.

---

## Backend Routers Pattern

### WebSocket Router

**Endpoint**: `ws://localhost:8000/ws/{sessionId}/{role}`

**Message protocol**:
```json
// Hearing → Backend (speech or text)
{"type": "speech", "audio_path": "...", "sender": "hearing", "timestamp": 1234567890}
{"type": "text", "text": "Hello", "sender": "hearing", "timestamp": 1234567890}

// Backend → Deaf (sign queue, status)
{"type": "signs", "signs": [...], "session_id": "demo"}
{"type": "status", "status": "processing", "session_id": "demo"}
```

**Per-session state** (no global state):
- Store in `sessions = {sessionId: {state, users, queue}}`
- Clean up on disconnect

### Multipart Upload Router

**Endpoint**: `POST /speech` (hearing user uploads speech audio)

Expects: `FormData` with `audio` file (WAV or MP3)

Returns: `{"signs": [...], "text": "..."}` or error

---

## Dependencies & External Services

### Python Requirements (`backend/requirements.txt`)
- `fastapi==0.115.0` — web framework
- `uvicorn[standard]==0.32.0` — ASGI server
- `python-dotenv==1.0.1` — .env loader
- `websockets==13.1` — WebSocket support
- `faster-whisper==1.1.0` — speech-to-text (local, no API key)
- `anthropic==0.40.0` — Claude API (optional, for NLP)
- `openai==1.55.0` — GPT API (optional, for intent classification)
- `pydantic==2.10.0` — data validation
- `aiofiles==24.1.0` — async file I/O

### External Services
- **Ollama** (local LLM) — runs custom `amandla` model for sign classification
  - Health check: `ollama serve` running
  - Model creation: `ollama create amandla -f Modelfile`
- **Whisper** (faster-whisper) — speech transcription (local, no API)

### Electron Deps
- `electron@^28.0.0`
- `electron-builder@^24.0.0` — packaging
- `concurrently@^8.0.0` — parallel processes
- `wait-on@^7.0.0` — health check before Electron start

---

## Project-Specific Conventions

### Naming
- **Roles**: `"hearing"` or `"deaf"` (not "speaker"/"listener" or other terms)
- **Sign names in SIGN_LIBRARY**: UPPERCASE (e.g., `'HELLO'`, `'HOW ARE YOU'`)
- **Message types**: lowercase (e.g., `type: "text"`, `type: "speech"`, `type: "signs"`)
- **Windows**: file structure mirrors role (`src/windows/hearing/`, `src/windows/deaf/`)

### Config & Env
- Ollama model name: hardcoded as `"amandla"` (not configurable per project policy)
- Port: FastAPI runs on `8000` (not configurable)
- Session ID: arbitrary string passed by client (e.g., "demo", "test123")
- Split-screen: horizontal split at `width/2` (not vertical)

### Error Handling
- **Frontend**: WebSocket errors auto-reconnect every 1000ms (see preload.js)
- **Backend**: Return HTTP 500 or WebSocket `{"type": "error", "message": "..."}` for failures
- **Avatar**: Gracefully skip malformed signs (log but don't crash)

### Testing Approach
- No automated tests (per project scope) — manual integration testing in split-screen
- Use hardcoded session ID `"demo"` for local testing
- Console logs: prefix with `[Component]` (e.g., `[Avatar]`, `[Preload]`, `[Backend]`)

---

## Common Workflows

### Adding a New Conversation Feature
1. Add message type to backend `sentenceToSigns()` or new router
2. Send WebSocket `{"type": "new_type", ...}` from one role
3. Register handler in other role's `window.amandla.onMessage()`
4. Update HTML UI if needed

### Fixing Avatar Glitches
1. Check sign data in `signs_library.js` — verify rotations are radians, not degrees
2. Check bone interpolation in `avatar.js` — ensure `signProgress` is 0..1
3. Add console logs: `console.log('[Avatar]', sign.name, sign.R.sh)` for inspection
4. Test with a single sign: manually queue `['HELLO']` and inspect rotation values

### Debugging WebSocket Issues
1. Open DevTools (F12) in Electron window
2. Monitor Network tab (won't show WebSocket fully, but shows connection events)
3. Add logs in `preload.js`: `console.log('[Preload] Send:', message)`
4. Check backend logs: `python -m uvicorn` output shows connections

---

## Known Limitations & Gotchas

1. **No global state across sessions** — each sessionId is independent. Session affinity handled by sessionId string matching.

2. **Three.js coordinates** — Y-up (not Z-up). Avatar facing camera = camera looking at (0, 0.4, 0).

3. **SIGN_LIBRARY fallback** — if word not found, `fingerspell()` auto-spells it letter-by-letter. This is intended behavior, not an error.

4. **Oscillation timing** — oscillation frequency is in Hz. Adjust `osc.freq` 1.0–3.0 for natural motion; >4.0 looks twitchy.

5. **Electron security** — contextIsolation=true, nodeIntegration=false. No `require()` in frontend code. Use preload bridge.

6. **Handshape curl ranges** — typically 0 (straight) to 1.55 (fully curled). Values outside this range may invert or cause NaN in Three.js interpolation.

---

## References

- **Full avatar spec**: See `AMANDLA_FINAL_BLUEPRINT.md` (1500+ lines, includes complete avatar.js template)
- **Backend setup**: See `AMANDLA_MISSING_PIECES.md` (critical __init__.py, requirements.txt, Modelfile)
- **Build schedule**: See `AMANDLA_BLUEPRINT__2_.md` (hourly breakdown for full implementation)
- **Signs dictionary**: `signs_library.js` (100+ SASL signs, fully documented)

---

**Last verified**: March 27




, 2026  
**Next review**: When adding new message types or significantly modifying avatar structure

