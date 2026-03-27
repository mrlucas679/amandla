# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AMANDLA is a real-time sign language communication bridge for disabled South Africans. It is a hybrid **Electron + FastAPI** desktop application with two synchronized windows: a hearing user's input window and a deaf user's display window.

## Commands

### Starting the App
```bash
npm start                  # Starts backend + waits for health check + launches Electron
```

### Running Services Individually
```bash
npm run backend            # FastAPI backend only (uvicorn, hot-reload, port 8000)
npm run electron           # Electron frontend only
npm run dev                # Electron with Node inspector attached
```

### Building
```bash
npm run build              # electron-builder → dist/ (NSIS installer for Windows)
```

### Backend Only (alternative)
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Testing Scripts
```bash
python scripts/ws_test.py           # WebSocket connection smoke test
python scripts/post_speech_test.py  # Speech endpoint smoke test
```

### External Services Required
```bash
ollama serve               # Must be running on port 11434 before starting the app
```

### Health Check
```bash
curl http://localhost:8000/health
```

## Architecture

### Three-Layer Structure

```
Electron Main Process (src/main.js)
  └─ Creates split-screen BrowserWindow (hearing left, deaf right)
  └─ Generates SESSION_ID, dispatches via IPC to both windows

Preload Bridge (src/preload/preload.js)
  └─ Exposes window.amandla.{connect, send, onMessage, onConnectionChange}
  └─ Manages WebSocket lifecycle — NOT direct HTTP from frontend

Backend (backend/main.py — FastAPI)
  └─ WS /ws/{sessionId}/{role}  ← Main communication channel
  └─ POST /speech               ← Audio upload (Whisper transcription)
  └─ GET /health
  └─ Services: whisper_service.py (STT), ollama_service.py (sign lookup)
```

### Communication Flow

1. Hearing window captures text or audio
2. Frontend sends via `window.amandla.send({type: 'text', text: '...'})` — goes through WebSocket only
3. Backend receives, calls `sentence_to_sign_names(text)` → returns array of sign names
4. Backend broadcasts sign array to deaf window in same session
5. Deaf window calls `window.avatarPlaySigns(signs, text)` to animate

### Session Management

- Session ID format: `'amandla-' + Date.now() + '-' + randomHex`
- Backend stores per-session state: `sessions[sessionId] = {users: {role: ws}, queue: []}`
- Both windows auto-connect to `ws://localhost:8000/ws/{sessionId}/{hearing|deaf}` on load

### Signs Library

Sign data lives in `signs_library.js` (root) and is imported by both windows. Each sign entry:
```javascript
{
  name: 'HELLO',
  shape: '...',   // human description
  R: { sh, el, wr, hand: {i, m, r, p, t} },  // right arm joint rotations
  L: { ... },     // left arm
  osc: { j, ax, amp, freq }  // oscillation for animated signs
}
```
The avatar in `src/windows/deaf/avatar.js` is a placeholder — Three.js animation is the main unimplemented piece.

### Key Constraints (from AGENTS.md)

- **Mono-window split-screen**: Both views live in one Electron `BrowserWindow`, never separate windows
- **WebSocket-only frontend**: No direct `fetch`/XHR from renderer to backend — all communication through the preload `window.amandla` API
- **Backend is stateful per session**: Session dictionary is in-memory; restart clears all sessions

## Environment

Configuration via `.env` at project root:
```
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
OLLAMA_MODEL=amandla          # Custom model defined in Modelfile (based on qwen2.5:3b)
OLLAMA_BASE_URL=http://localhost:11434
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
ANTHROPIC_API_KEY=            # Optional
OPENAI_API_KEY=               # Optional
```

The Ollama model (`amandla`) is defined in `Modelfile` and must be created once with `ollama create amandla -f Modelfile`.