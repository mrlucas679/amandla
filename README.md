# AMANDLA — Sign Language Communication Bridge

> A real-time sign language communication bridge for disabled South Africans.  
> Electron desktop app with FastAPI backend, Three.js avatar, Whisper speech-to-text, and Ollama AI.

---

## What AMANDLA Does

Two side-by-side windows share one WebSocket session:

- **Left (Hearing)** — type or speak in any of South Africa's 11 official languages
- **Right (Deaf)** — a 3D avatar signs the translation in South African Sign Language (SASL)

The deaf user can reply via quick-sign buttons, SASL text input, or camera-based sign recognition. Their signs are reconstructed into natural English and spoken aloud on the hearing side via TTS.

A third **Know Your Rights** window helps deaf users document workplace discrimination incidents, analyse which laws were violated, and generate formal complaint letters.

---

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| [Node.js](https://nodejs.org/) | 18+ | Electron runtime |
| [Python](https://python.org/) | 3.10+ | FastAPI backend |
| [Ollama](https://ollama.com/) | Latest | Local AI for sign recognition + translation |
| [ffmpeg](https://ffmpeg.org/) | Latest | Audio processing for Whisper |

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/amandla-desktop.git
cd amandla-desktop

# 2. Install Node.js dependencies
npm install

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Create the Ollama AMANDLA model
ollama create amandla -f Modelfile

# 5. Create your .env file (copy the example or create manually)
# See "Environment Variables" section below for required values
```

---

## How to Start

```bash
# Step 1 — Start Ollama (must be running first)
ollama serve

# Step 2 — Start everything
npm start
```

`npm start` launches the FastAPI backend on port 8000, waits for the health check, then opens the split-screen Electron app. Both windows auto-connect via WebSocket.

---

## Architecture

```
Electron Main (src/main.js)
  └─ Creates two BrowserWindows: hearing (left) + deaf (right)
  └─ Generates SESSION_ID once; passes to both windows via IPC
  └─ Fetches SESSION_SECRET from backend for WebSocket authentication

Preload Bridge (src/preload/preload.js)
  └─ The ONLY way renderers talk to the backend
  └─ Exposes window.amandla.{ connect, send, onMessage, uploadSpeech, ... }
  └─ All backend calls go through WebSocket — zero direct fetch() from renderers

Backend (backend/main.py → routers/ + ws/ + services/)
  └─ WS  /ws/{sessionId}/{role}   ← all real-time communication
  └─ GET  /health                  ← liveness probe
  └─ GET  /api/status              ← AI service health
  └─ POST /speech                  ← direct API testing only
  └─ POST /rights/analyze          ← direct API testing only
  └─ POST /rights/letter           ← direct API testing only

Signs Library (signs_library.js — root)
  └─ 100+ SASL signs from Einstein Hands SASL Dictionary
  └─ Loaded by deaf window as window.AMANDLA_SIGNS

Avatar (src/windows/deaf/avatar.js)
  └─ Three.js skeleton with TransitionEngine
  └─ Public API: window.avatarPlaySigns(signs, text)
```

### Communication Flow

```
Hearing types/speaks
  → window.amandla.send({type:'text'})
  → WebSocket → backend SASL pipeline
  → broadcast {type:'signs'} to deaf window
  → avatar animates the signs

Deaf taps button / signs on camera
  → window.amandla.send({type:'sign'})
  → WebSocket → backend buffers (1.5s debounce)
  → signs_to_english() reconstruction
  → {type:'deaf_speech'} to hearing window → TTS speaks it aloud
```

---

## Project Structure

```
src/
  main.js                          — Electron entry: two windows, session ID, CSP
  preload/preload.js               — WebSocket bridge (only renderer ↔ backend path)
  windows/
    hearing/                       — index.html + hearing.css + hearing.js
    deaf/                          — index.html + deaf.css + deaf.js + avatar.js
    rights/                        — index.html + rights.css + rights.js

backend/
  main.py                          — FastAPI app, router registration, lifespan
  shared.py                        — Shared state, constants, auth, sanitisation
  middleware.py                    — Per-IP per-endpoint HTTP rate limiting
  routers/                         — health.py, speech.py, rights.py
  ws/                              — handler.py, helpers.py, session.py
  services/
    sasl_pipeline.py               — English → SASL signs (3-tier fallback)
    sign_reconstruction.py         — SASL signs → English sentences
    sign_maps.py                   — English→SASL word/phrase mappings (SINGLE SOURCE OF TRUTH)
    whisper_service.py             — Speech-to-text (faster-whisper + ffmpeg)
    ollama_service.py              — Sign recognition via Ollama
    ollama_client.py               — Text → sign names via Ollama
    ollama_pool.py                 — Shared httpx connection pool for Ollama
    claude_service.py              — Rights analysis + letter generation
    nvidia_service.py              — NVIDIA NIM fallback (optional)
    harps_recognizer.py            — HARPS ML sign recogniser
    mediapipe_bridge.py            — MediaPipe landmarks → HARPS arrays
    sign_buffer.py                 — Sliding-window frame accumulator

sasl_transformer/                  — Full SASL grammar transformer module
signs_library.js                   — 100+ SASL signs with bone data (deaf window only)
Modelfile                          — Ollama amandla model definition
```

---

## Environment Variables (`.env`)

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

## Running Tests

```bash
# Unit tests — sign map lookups (49 tests)
python -m pytest tests/test_sign_maps.py -v

# End-to-end pipeline tests (requires backend running)
python tests/test_e2e_pipeline.py

# WebSocket handler tests (requires backend running)
python scripts/test_all_ws_handlers.py

# Quick health check
curl http://localhost:8000/health
```

---

## Documentation

| File | Purpose |
|------|---------|
| **`CLAUDE.md`** | ⭐ Single source of truth — architecture, constraints, rules |
| **`AGENTS.md`** | AI agent coding conventions and full file map |
| `PROJECT_PLAN.md` | Self-contained project plan: status, open items, next steps |
| **`PRODUCTION_READINESS.md`** | Audit of all issues, fixes, and remaining work |
| `AMANDLA_FINAL_BLUEPRINT.md` | Avatar and Three.js implementation spec |
| `AMANDLA_MISSING_PIECES.md` | Backend integration blueprint |
| `SASL_Transformer_README.md` | SASL grammar transformer documentation |
| `docs/WEBSOCKET_PROTOCOL.md` | WebSocket message type reference |

> Files in the `archive/` directory are historical snapshots — do not follow their instructions.

---

## Key Constraints

- **Electron security**: `contextIsolation: true`, `nodeIntegration: false` — always
- **No direct fetch from renderers** — use `window.amandla.*` preload bridge only
- **CORS must be `["*"]`** — Electron is not a browser origin
- **`.env` loaded once** in `backend/main.py` — never in service files
- **`sign_maps.py`** is the single source of truth for English→SASL word mappings
- **Modal verbs** (`will`, `must`, `can`) map to SASL signs — never put in FILLER

---

## How to Contribute

1. Read `CLAUDE.md` first (the single source of truth)
2. Read `AGENTS.md` for coding conventions
3. Check `PRODUCTION_READINESS.md` for open issues
4. Follow the plan-first, implement-second approach
5. Never commit `.env`, `node_modules/`, or `__pycache__/`

---

## License

This project is developed for the South African deaf community. License TBD.

---

*Last Updated: March 30, 2026*
