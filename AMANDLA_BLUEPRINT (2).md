# AMANDLA — Complete Hackathon Blueprint
> Isazi AI for Accessibility Hackathon · March 27–29, 2026  
> Knightsbridge Office Park, 33 Sloane Street, Rivonia, Johannesburg  
> Build time: ~45 hours · Prize pool: R52,500  
> Last updated: March 21, 2026

---

## HOW TO USE THIS DOCUMENT

This is not a reference document. This is your **build script**.  
You open it on one screen. You open JetBrains on the other screen.  
You follow it line by line from Friday 8pm to Sunday 1pm.  
Every section tells you exactly what to build, in what order, with what code.  
When you are stuck, you paste the relevant section into Claude inside JetBrains and say: *"Build this."*

Do not skip ahead. Do not build features out of order.  
The order exists because each piece depends on the previous one.

---

## PART 1 — WHO YOU ARE AND WHAT YOU ARE BUILDING

### The product in one sentence
AMANDLA is the wheelchair for communication — it gives disabled South Africans the ability to have real conversations with anyone, without a third person in between.

### The problem you are solving
In South Africa, a deaf person in a hospital, classroom, or job interview always needs a third person — an interpreter — just to have a conversation. That interpreter is not always available. That dependency is the real disability. AMANDLA removes the third person.

### The tagline
**"Amandla Awethu — Power to the People"**

### What AMANDLA does
- A deaf person signs. AMANDLA speaks for them.
- A hearing person speaks. AMANDLA converts speech to large text for the deaf person.
- A blind person listens. Every message is read aloud automatically.
- No interpreter. No dependency. No exclusion.

### What you are NOT building at the hackathon
- BUILD mode (dataset collection) — removed from scope
- COMPETE mode (skills assessment) — removed from scope
- CONSULT mode (accessibility auditing) — removed from scope
- These exist in old documents. Ignore them completely.

---

## PART 2 — THE COMPLETE TECH STACK

### Plain English version
| Layer | What it is | What it does |
|---|---|---|
| **Frontend** | Electron + HTML + CSS + JavaScript | The two desktop windows the user sees |
| **Backend** | Python + FastAPI | The brain — speech, AI, hand tracking |
| **Real-time link** | WebSockets | Instant communication between windows and backend |
| **Speech to text** | Faster-Whisper (local) | Converts hearing person's speech to text |
| **STT backup** | NVIDIA Parakeet via NIM API | Faster, more accurate — activates if Whisper struggles |
| **Local AI** | Qwen2.5:3b via Ollama | Sign recognition, language tasks, free, offline |
| **AI backup** | NVIDIA NIM (free credits) | Activates if Qwen times out |
| **Legal AI** | Claude API (Anthropic) | Only for RIGHTS mode — writes formal complaint letters |
| **Hand tracking** | MediaPipe WASM | Runs in Electron, tracks hand landmarks from camera |
| **Avatar** | Three.js | 3D humanoid with fully articulated fingers — signs for deaf user |
| **Text to speech** | Web Speech API (browser built-in) | Reads messages aloud for blind users, free, no install |

### Why JavaScript not TypeScript
TypeScript enforces strict rules that cause errors blocking your app from running until fixed. At 2am during a hackathon this wastes time. Plain JavaScript runs even when messy. Post-hackathon, convert to TypeScript for production.

### Why Electron not a browser
- Opens as a proper desktop app — no browser bar, no URL, taskbar icon
- Judges see a native desktop application
- All HTML/CSS/Three.js work transfers without changes
- Multi-window support built in (critical for two-screen demo)
- Used by VS Code, Slack, Discord, Figma — not a toy framework

### The full architecture diagram
```
┌─────────────────────────────────────────────────────────┐
│                    ELECTRON APP                          │
│                                                         │
│  ┌──────────────────┐     ┌──────────────────────────┐  │
│  │  Window 1        │     │  Window 2                │  │
│  │  HEARING VIEW    │     │  DEAF / SIGNER VIEW      │  │
│  │                  │     │                          │  │
│  │  • Microphone    │     │  • Camera feed           │  │
│  │  • Waveform      │     │  • MediaPipe skeleton    │  │
│  │  • Three.js      │     │  • Large text display    │  │
│  │    avatar signs  │     │  • Quick-sign buttons    │  │
│  │  • Transcript    │     │  • Sign input field      │  │
│  │  • TTS readout   │     │  • Emergency button      │  │
│  └────────┬─────────┘     └────────────┬─────────────┘  │
│           │                            │                 │
│           └──────────┬─────────────────┘                 │
│                      │ WebSocket                         │
└──────────────────────┼──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                PYTHON FASTAPI BACKEND                    │
│                                                         │
│  /ws/session     — WebSocket session manager            │
│  /api/transcribe — Whisper → Parakeet fallback          │
│  /api/tts        — Text to speech trigger               │
│  /api/rights     — Claude API legal letter              │
│                                                         │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  Whisper   │  │  Qwen/Ollama │  │  MediaPipe      │  │
│  │  (local)   │  │  (local)     │  │  (hand tracking)│  │
│  └─────┬──────┘  └──────┬───────┘  └────────┬────────┘  │
│        │                │                   │            │
│  ┌─────▼──────┐  ┌──────▼───────┐           │            │
│  │  Parakeet  │  │  NVIDIA NIM  │           │            │
│  │  (backup)  │  │  (backup)    │           │            │
│  └────────────┘  └──────────────┘           │            │
└─────────────────────────────────────────────────────────┘
```

---

## PART 3 — BEFORE FRIDAY: SETUP EVERYTHING

> Do all of this on Thursday night. It takes about 60 minutes.  
> If something fails Thursday, you have time to fix it.  
> If it fails Friday night, your build time is gone.

### 3.1 — Check what is already installed

Open your terminal (PowerShell or Command Prompt on Windows) and run each command:


```powershell
# Check Python
python --version
# Expected: Python 3.13.x

# Check Ollama
ollama --version
# Expected: ollama version 0.18.0

# Check if amandla model exists
ollama list
# Expected: amandla model in the list

# Check Node.js
node --version
# If not installed, go to nodejs.org and install LTS version
# Expected: v20.x.x or higher

# Check npm
npm --version
# Expected: 10.x.x or higher

# Check git
git --version
# Expected: git version 2.x.x
```

If Node.js is not installed — go to `https://nodejs.org` → download → install → restart terminal → check again.

### 3.2 — Create the project folder structure

```powershell
# Navigate to where you want the project
cd C:\Users\Admin

# Create the Electron app folder (separate from existing amandla/ Python folder)
mkdir amandla-desktop
cd amandla-desktop

# Initialise npm project
npm init -y
```

### 3.3 — Install Electron and frontend dependencies

```powershell
# Install Electron
npm install --save-dev electron

# Install electron-builder (for packaging later)
npm install --save-dev electron-builder

# Install concurrently (runs Python + Electron together)
npm install --save-dev concurrently

# Install wait-on (waits for Python backend to start before Electron)
npm install --save-dev wait-on
```

### 3.4 — Create the folder structure

Create these folders and files manually or run:

```powershell
mkdir src
mkdir src\windows
mkdir src\windows\hearing
mkdir src\windows\deaf
mkdir src\windows\rights
mkdir src\preload
mkdir assets
mkdir assets\icons

# Create placeholder files
echo. > src\main.js
echo. > src\preload\preload.js
echo. > src\windows\hearing\index.html
echo. > src\windows\deaf\index.html
echo. > src\windows\rights\index.html
```

Final structure:
```
amandla-desktop/
├── package.json
├── src/
│   ├── main.js                 ← Electron main process (controls windows)
│   ├── preload/
│   │   └── preload.js          ← Bridge between Electron and web pages
│   └── windows/
│       ├── hearing/
│       │   └── index.html      ← Hearing person's screen
│       ├── deaf/
│       │   └── in


dex.html      ← Deaf/signer's screen
│       └── rights/
│           └── index.html      ← RIGHTS mode screen
├── assets/
│   └── icons/                  ← App icon files
└── node_modules/
```

### 3.5 — Configure package.json

Open `package.json` and replace the entire contents with:

```json
{
  "name": "amandla",
  "version": "1.0.0",
  "description": "AMANDLA — Communication bridge for disabled South Africans",
  "main": "src/main.js",
  "scripts": {
    "start": "concurrently \"npm run backend\" \"wait-on http://localhost:8000/health && electron .\"",
    "electron": "electron .",
    "backend": "cd ../amandla && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload",
    "dev": "electron . --inspect",
    "build": "electron-builder"
  },
  "devDependencies": {
    "electron": "^28.0.0",
    "electron-builder": "^24.0.0",
    "concurrently": "^8.0.0",
    "wait-on": "^7.0.0"
  },
  "build": {
    "appId": "co.za.amandla",
    "productName": "AMANDLA",
    "directories": {
      "output": "dist"
    },
    "win": {
      "target": "nsis",
      "icon": "assets/icons/icon.ico"
    }
  }
}
```

### 3.6 — Test that Electron opens

Paste this minimal code into `src/main.js`:

```javascript
const { app, BrowserWindow } = require('electron')

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    title: 'AMANDLA',
    backgroundColor: '#0D0D0D',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  })
  win.loadFile('src/windows/hearing/index.html')
}

app.whenReady().then(createWindow)
app.on('window-all-closed', () => app.quit())
```

Paste this into `src/windows/hearing/index.html`:

```html
<!DOCTYPE html>
<html>
<head><title>AMANDLA</title></head>
<body style="background:#0D0D0D;color:#F5F0E8;font-family:sans-serif;
  display:flex;align-items:center;justify-content:center;height:100vh;margin:0;">
  <h1 style="font-size:64px;letter-spacing:-2px;">AMAN<span style="color:#2EA880;">DLA</span></h1>
</body>
</html>
```

Run it:
```powershell
npx electron .
```

A black window should open with the AMANDLA logo. If this works, your Electron setup is correct. Close it and move on.

### 3.7 — Install Claude in JetBrains

This is how you get Claude inside your IDE so you can generate code without leaving the editor.

**Option A — Claude AI Plugin (recommended)**

1. Open any JetBrains IDE (PyCharm or WebStorm)
2. Go to: `File` → `Settings` → `Plugins`
3. Click `Marketplace` tab
4. Search: `Claude`
5. Install: **"Claude AI"** or **"Anthropic Claude"** plugin
6. Restart the IDE
7. After restart: `File` → `Settings` → `Tools` → `Claude AI`
8. Paste your Anthropic API key: `sk-ant-...`
9. Save

Claude now appears as a panel on the right side of your IDE. You can highlight code and ask Claude to explain or fix it. You can open a chat and describe what you want to build.

**Option B — JetBrains AI Assistant with Claude**

1. Go to: `File` → `Settings` → `Tools` → `AI Assistant`
2. Click `AI Provider`
3. Select `Anthropic Claude`
4. Paste your API key
5. Select model: `claude-sonnet-4-6`

This gives you inline code completion powered by Claude everywhere in your editor.

**How to use Claude in JetBrains during the hackathon:**

Every time you need to build a feature, open the Claude panel and write a prompt like:

> *"I am building AMANDLA, an accessibility desktop app. I need you to write the FastAPI WebSocket endpoint that handles real-time session management between two Electron windows. The endpoint lives in `backend/routers/sign_ws.py`. Use Python 3.13, FastAPI, and WebSockets. Here is my existing main.py: [paste main.py]. Build the complete file."*

The more context you give, the better the output. Always paste the relevant existing files.

### 3.8 — Get NVIDIA free API key (5 minutes)

1. Go to `https://build.nvidia.com`
2. Click `Sign Up`
3. Create account with your Gmail
4. Go to `API Keys` section
5. Generate a new key — starts with `nvapi-`
6. Copy and save it somewhere safe

You now have 1,000 free inference credits. You will not use these during normal operation — only if your local Qwen AI stops responding.

### 3.9 — Create your .env file

In your `amandla/` Python folder (not the Electron folder), create a file called `.env`:

```
# Anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here

# NVIDIA NIM (backup tier — activates if Qwen fails)
NVIDIA_API_KEY=nvapi-your-key-here
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_ENABLED=false

# Whisper
WHISPER_MODEL=small
WHISPER_DEVICE=cpu

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=amandla

# App
APP_ENV=development
BACKEND_PORT=8000
```

`NVIDIA_ENABLED=false` means NVIDIA is off by default. If Qwen dies during the demo, you change this to `true` and restart. One line change. Thirty seconds.

### 3.10 — Thursday night checklist

Before you sleep on Thursday, confirm every item:

- [ ] `node --version` returns v20+
- [ ] `npx electron .` opens a black window with AMANDLA text
- [ ] `ollama run amandla "say hello"` responds
- [ ] `cd amandla && python -m uvicorn backend.main:app` starts without errors
- [ ] Claude plugin is visible in JetBrains sidebar
- [ ] NVIDIA API key saved in `.env`
- [ ] Anthropic API key saved in `.env`
- [ ] GitHub repo exists and last commit pushed

If all ten are checked — you walk into Friday completely ready.

---

## PART 4 — FRIDAY NIGHT: HOURS 1–6 (8pm – 2am)

> **Goal: Two Electron windows talking to each other through WebSockets.**  
> Nothing else. Not the avatar. Not the speech recognition. Just connection.  
> If you finish this before 2am, you are ahead of schedule.

### What "done" looks like at 2am
- You type text in Window 1 (Hearing view) and it appears in Window 2 (Deaf view) instantly
- The WebSocket connection survives if you close and reopen a window
- The Python backend is running and `/health` returns `{"status": "ok"}`

### Hour 1–2: FastAPI backend skeleton

Open JetBrains. Open `amandla/backend/main.py`. Tell Claude:

> *"Write a complete FastAPI main.py with: a /health endpoint returning {status: ok}, CORS configured for localhost, WebSocket router mounted at /ws, and uvicorn startup. Include all imports."*

The file should look like this when done:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from backend.routers import sign_ws

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("AMANDLA backend starting...")
    yield
    print("AMANDLA backend shutting down...")

app = FastAPI(title="AMANDLA API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sign_ws.router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "AMANDLA"}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
```

Test it:
```powershell
cd C:\Users\Admin\amandla
python -m uvicorn backend.main:app --reload
```

Open browser → `http://localhost:8000/health` → should return `{"status":"ok","service":"AMANDLA"}`

### Hour 2–3: WebSocket session manager

Create `amandla/backend/routers/sign_ws.py`. Tell Claude:

> *"Write a FastAPI WebSocket router that manages real-time sessions between two clients (hearing and deaf). Each session has a session_id. Both clients join the same session. When one client sends a message, it is broadcast to the other client immediately. Message format is JSON with fields: type, text, sender, timestamp. Include session creation, joining, disconnection handling, and broadcast."*

Key things this file must handle:
- `POST /api/session/create` — creates a new session, returns `session_id`
- `GET /ws/{session_id}/{role}` — WebSocket endpoint, role is `hearing` or `deaf`
- When a message arrives from `hearing`, broadcast to `deaf` and vice versa
- When a client disconnects, notify the other client
- Store active sessions in a dictionary in memory (no database needed for hackathon)

Test it with two browser tabs open to a simple HTML test page that connects via WebSocket.

### Hour 3–4: Electron main process — two windows

Open `amandla-desktop/src/main.js`. Tell Claude:

> *"Write the complete Electron main.js that: creates two BrowserWindow objects side by side on screen, Window 1 loads hearing/index.html, Window 2 loads deaf/index.html, both windows have no menu bar, dark background #0D0D0D, and the app quits when all windows are closed. Windows should be positioned so they sit side by side on a 1920x1080 screen. Include IPC handlers for sending messages between windows via the main process."*

The two-window positioning:
```javascript
// Window 1 — left half
const hearingWin = new BrowserWindow({
  x: 0, y: 0,
  width: Math.floor(screen.width / 2),
  height: screen.height,
  // ...
})

// Window 2 — right half  
const deafWin = new BrowserWindow({
  x: Math.floor(screen.width / 2), y: 0,
  width: Math.floor(screen.width / 2),
  height: screen.height,
  // ...
})
```

### Hour 4–5: Preload script and WebSocket connection in frontend

Create `amandla-desktop/src/preload/preload.js`. Tell Claude:

> *"Write an Electron preload script that safely exposes WebSocket functionality to the renderer process using contextBridge. Expose: connect(sessionId, role), send(message), onMessage(callback), onConnectionChange(callback), disconnect(). The WebSocket connects to ws://localhost:8000/ws/{sessionId}/{role}."*

Then in both `hearing/index.html` and `deaf/index.html`, add the WebSocket connection logic that uses the preload bridge.

### Hour 5–6: Verify two windows talking

Build a minimal test UI in both windows:
- Hearing window: text input + send button
- Deaf window: large text display showing received messages

Type in the hearing window. Text appears in the deaf window. This is your proof of concept. If this works at 2am — sleep. The hardest technical piece is done.

**What to tell Claude if the WebSocket fails:**
> *"My Electron app cannot connect to the FastAPI WebSocket. The error is: [paste error]. My Electron preload is: [paste file]. My FastAPI WebSocket router is: [paste file]. Debug this."*

---

## PART 5 — SATURDAY MORNING: HOURS 7–12 (9am – 3pm)

> **Goal: Full hearing → deaf pipeline working.**  
> Hearing person speaks → Whisper transcribes → text appears in deaf window → avatar signs it.

### Hour 7–8: Wire up Whisper STT

Open `amandla/backend/services/whisper_service.py`. Tell Claude:

> *"Write a complete whisper_service.py using faster-whisper library. It should: load the small model on startup, expose an async function transcribe_audio(audio_bytes) that returns {text, language, confidence}, handle errors gracefully, and log timing. The function will be called from a FastAPI endpoint."*

Add a new endpoint to `sign_ws.py`:

```python
@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    result = await whisper_service.transcribe_audio(audio_bytes)
    return result
```

In the Electron hearing window, add microphone recording:
- Press and hold mic button → records audio
- Release → sends audio blob to `/api/transcribe`
- Receives text → sends text via WebSocket to deaf window
- Text appears large in deaf window

Tell Claude to write the browser-side audio recording code:

> *"Write JavaScript for an Electron renderer that: records from microphone using MediaRecorder API, sends the audio blob to http://localhost:8000/api/transcribe via fetch POST, receives the transcription text, and sends it via the existing WebSocket connection. Include start/stop recording on button press/release."*

### Hour 8–9: NVIDIA Parakeet backup for STT

Open `amandla/backend/services/whisper_service.py`. Add the fallback:

> *"Add a fallback to my whisper_service.py: if Whisper transcription takes more than 3 seconds or throws an error, fall back to NVIDIA Parakeet via the NIM API. NVIDIA_API_KEY and NVIDIA_BASE_URL come from environment variables. NVIDIA_ENABLED must be true in .env for this to activate. The NIM API is OpenAI-compatible."*

The fallback logic in plain terms:
```
try:
    result = whisper.transcribe(audio)      # try local first
    if took > 3 seconds: raise TimeoutError
    return result
except:
    if NVIDIA_ENABLED:
        return nvidia_parakeet.transcribe(audio)   # backup
    raise   # if both fail, raise error
```

### Hour 9–10: Three.js avatar integration into Electron

Copy the avatar HTML code into `src/windows/hearing/avatar.js` as a module.

The avatar needs to respond to incoming sign commands. Tell Claude:

> *"Integrate the Three.js SASL avatar into the AMANDLA Electron hearing window. The avatar should: initialise on page load, expose a function playSign(signName) that animates the correct handshape, respond to WebSocket messages of type 'sign' by calling playSign with the sign name, and respond to messages of type 'speech_text' by displaying the text below the avatar."*

The avatar signs what the DEAF person sent. So when the deaf person taps HELP:
1. Deaf window sends WebSocket message: `{type: "sign", text: "HELP", sender: "deaf"}`
2. Hearing window receives it
3. Hearing window calls `playSign("HELP")` on the avatar
4. Avatar animates the HELP handshape
5. Hearing window also plays TTS: "HELP"

### Hour 10–11: Auto-TTS for blind users

In the deaf window, every message that arrives should be read aloud automatically. This requires zero backend work — it is one line of JavaScript:

```javascript
function speakText(text) {
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'en-ZA'
  utterance.rate = 0.95
  utterance.pitch = 1.0
  window.speechSynthesis.cancel()  // stop any current speech
  window.speechSynthesis.speak(utterance)
}

// Call this every time a new message arrives
socket.onMessage(msg => {
  displayMessage(msg)
  speakText(msg.text)  // auto-read for blind users
})
```

### Hour 11–12: Quick-sign buttons

In the deaf window, add 10 buttons. Each button:
1. Sends a WebSocket message to the hearing window: `{type: "sign", text: "HELP", sender: "deaf"}`
2. The hearing window's avatar plays that sign
3. The hearing window's TTS speaks the word aloud

```javascript
const QUICK_SIGNS = ['HELP','YES','NO','PLEASE','THANK YOU','WATER','PAIN','WAIT','REPEAT','UNDERSTAND']

QUICK_SIGNS.forEach(sign => {
  const btn = document.createElement('button')
  btn.textContent = sign
  btn.addEventListener('click', () => {
    window.amandla.send({
      type: 'sign',
      text: sign,
      sender: 'deaf',
      timestamp: Date.now()
    })
  })
  quickSignsContainer.appendChild(btn)
})
```

---

## PART 6 — SATURDAY AFTERNOON: HOURS 13–16 (3pm – 7pm)

> **Goal: Polish, MediaPipe camera tracking, emergency alert, full demo rehearsal.**

### Hour 13: MediaPipe hand tracking overlay

In the deaf window, the camera feed should show with the hand skeleton overlaid — this is the visual proof that AI is working.

Tell Claude:

> *"Write JavaScript for an Electron renderer window that: accesses the webcam using getUserMedia, displays the live video feed, loads MediaPipe Hands WASM from CDN, runs hand landmark detection on each frame, draws the hand skeleton landmarks on a canvas overlay positioned exactly over the video, uses purple (#8B6FD4) for left hand and teal (#2EA880) for right hand, and updates at 30fps."*

MediaPipe CDN for Electron (add to the HTML head):
```html
<script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>
```

**Risk:** Electron may block camera access. If it does, add to your `BrowserWindow` config:
```javascript
webPreferences: {
  // ...existing preferences...
}
// AND add this flag when launching:
// app.commandLine.appendSwitch('use-fake-ui-for-media-stream') // DEV ONLY
```

And in your deaf window HTML, request camera permissions explicitly:
```javascript
navigator.mediaDevices.getUserMedia({video: true, audio: false})
  .then(stream => { /* attach to video element */ })
  .catch(err => console.error('Camera error:', err))
```

### Hour 14: Emergency alert button

This is one of the most powerful demo moments. Both windows go full-screen red simultaneously.

In the deaf window HTML, add:
```html
<button id="emergency-btn" style="background:rgba(229,62,62,0.15);border:1px solid rgba(229,62,62,0.4);
  color:#FC8181;font-size:14px;font-weight:700;padding:10px 20px;border-radius:8px;cursor:pointer;">
  🚨 EMERGENCY
</button>
```

When pressed:
```javascript
document.getElementById('emergency-btn').addEventListener('click', () => {
  // Send emergency signal to other window via WebSocket
  window.amandla.send({ type: 'emergency', sender: 'deaf', timestamp: Date.now() })
  // Trigger locally too
  showEmergencyOverlay()
})

function showEmergencyOverlay() {
  const overlay = document.getElementById('emergency-overlay')
  overlay.style.display = 'flex'
  // Auto-dismiss after 10 seconds unless manually dismissed
  setTimeout(() => overlay.style.display = 'none', 10000)
}
```

The emergency overlay HTML (add inside body of both windows):
```html
<div id="emergency-overlay" style="display:none;position:fixed;inset:0;z-index:9999;
  background:rgba(229,62,62,0.95);flex-direction:column;align-items:center;
  justify-content:center;gap:20px;text-align:center;padding:40px;
  animation:pulse 1s ease-in-out infinite;">
  <div style="font-size:72px;">🚨</div>
  <div style="font-family:'Playfair Display',serif;font-size:52px;font-weight:900;
    color:#fff;letter-spacing:-2px;">EMERGENCY</div>
  <div style="font-size:20px;color:rgba(255,255,255,0.85);">
    Help has been alerted
  </div>
  <button onclick="document.getElementById('emergency-overlay').style.display='none'"
    style="background:rgba(255,255,255,0.2);border:2px solid rgba(255,255,255,0.4);
    color:#fff;font-size:15px;font-weight:700;padding:14px 36px;border-radius:12px;cursor:pointer;">
    Dismiss
  </button>
</div>
```

In the hearing window, listen for emergency WebSocket messages and trigger the same overlay.

### Hour 15: Turn indicator

At the top of both windows, show who is currently communicating.

```javascript
function setTurnIndicator(speaker) {
  const indicator = document.getElementById('turn-indicator')
  if(speaker === 'hearing') {
    indicator.textContent = '🎙 Hearing person is speaking'
    indicator.style.color = '#2EA880'
  } else if(speaker === 'deaf') {
    indicator.textContent = '🤟 Signer is signing'
    indicator.style.color = '#8B6FD4'
  } else {
    indicator.textContent = 'Waiting...'
    indicator.style.color = '#6B5C48'
  }
}
```

### Hour 16: Full demo rehearsal

Stop building. Sit down and run the demo script from start to finish.

**Demo flow (practice this until smooth):**

1. Launch the app — two windows appear side by side
2. On hearing window: tap microphone button, say "Good morning, how are you feeling today?"
3. Watch text appear in deaf window in large font
4. On deaf window: tap quick-sign "THANK YOU"
5. Watch avatar in hearing window sign "THANK YOU"
6. Hear TTS say "THANK YOU" from hearing window
7. On deaf window: tap "EMERGENCY" button
8. Both windows go full-screen red
9. Dismiss

Time yourself. If any step fails, fix it before moving to RIGHTS mode.

---

## PART 7 — SATURDAY EVENING: HOURS 17–20 (7pm – 11pm)

> **Goal: RIGHTS mode — only build this if the bridge is stable.**  
> If the bridge demo is not smooth by 7pm, skip RIGHTS mode and keep polishing.

### The RIGHTS / ENFORCE mode

User describes a discrimination incident by voice or text. Claude API reads it. Maps it to SA disability law. Generates a formal complaint letter in 90 seconds. PDF download.

### Hour 17: RIGHTS backend endpoint

Open `amandla/backend/routers/rights.py`. Tell Claude:

> *"Write a FastAPI endpoint POST /api/rights/generate that: accepts a JSON body with fields {incident_description, user_name, employer_name, incident_date}, calls the Anthropic Claude API using the anthropic Python SDK, passes the incident details plus pre-loaded SA law text, prompts Claude to extract facts and map them to Employment Equity Act s.6, Promotion of Equality Act s.7, Constitution s.9(3), and Labour Relations Act s.191, returns a formal complaint letter as a string, and handles API errors. The Anthropic API key comes from environment variable ANTHROPIC_API_KEY."*

The Claude prompt for the legal letter:

```python
LEGAL_PROMPT = """
You are a South African disability rights legal assistant.

A disabled person has experienced discrimination. Your job is to:
1. Extract the key facts from their description
2. Identify which SA laws were violated
3. Write a formal complaint letter they can send to their employer or the CCMA

Relevant laws:
- Employment Equity Act s.6: Prohibits unfair discrimination based on disability
- Promotion of Equality and Prevention of Unfair Discrimination Act s.7: Broader discrimination prohibition
- Constitution s.9(3): Right to equality, prohibits discrimination on grounds of disability
- Labour Relations Act s.191: Unfair dismissal and unfair labour practice procedures

Incident description: {incident_description}
Complainant name: {user_name}
Respondent (employer): {employer_name}
Date of incident: {incident_date}

Write a formal complaint letter. Be specific, cite the exact laws violated with section numbers.
Format as a proper legal letter with date, addresses, reference number, and signature block.
"""
```

### Hour 18: RIGHTS frontend window

Open `src/windows/rights/index.html`. This is a 3-step flow:

**Step 1 — Incident input:**
- Voice recording button (sends audio to `/api/transcribe`)
- OR text area for typing
- Submit button

**Step 2 — AI analysis display:**
- Animated loading state while Claude processes
- Display the identified laws with severity badges

**Step 3 — Letter output:**
- Full letter in an editable text area
- Copy button
- Download as PDF button (use browser print dialog or jsPDF library)

Tell Claude to build each step as a function that shows/hides sections.

### Hour 19: PDF download

Add jsPDF to your rights window:
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
```

```javascript
function downloadLetter(letterText) {
  const { jsPDF } = window.jspdf
  const doc = new jsPDF()
  
  doc.setFontSize(12)
  const lines = doc.splitTextToSize(letterText, 180)
  doc.text(lines, 15, 20)
  doc.save('AMANDLA_complaint_letter.pdf')
}
```

### Hour 20: Connect RIGHTS window to main app

Add a button in the hearing window that opens the RIGHTS window:

```javascript
// In main.js — IPC handler
ipcMain.handle('open-rights', () => {
  const rightsWin = new BrowserWindow({
    width: 900, height: 800,
    title: 'AMANDLA — Know Your Rights',
    backgroundColor: '#0D0D0D',
    webPreferences: {
      preload: path.join(__dirname, 'preload/preload.js'),
      contextIsolation: true
    }
  })
  rightsWin.loadFile('src/windows/rights/index.html')
})
```

---

## PART 8 — SUNDAY MORNING: HOURS 21–27 (9am – 1pm)

> **Goal: Fix everything broken. Record the video. Submit.**

### Hour 21–22: Bug fixing session

Go through every demo step and note what breaks. Common issues and fixes:

| Problem | Likely cause | Fix |
|---|---|---|
| WebSocket disconnects | Backend restarting | Add reconnection logic in preload.js |
| Avatar doesn't animate | Three.js not loaded | Check CDN URL, check CSP in Electron |
| Camera not working | Electron permissions | Add `--use-fake-ui-for-media-stream` flag |
| Whisper too slow | CPU overloaded | Switch to tiny model for demo: `WHISPER_MODEL=tiny` |
| Text not appearing large enough | CSS not applied | Set `font-size: min(5vw, 48px)` on transcript element |
| TTS not speaking | Browser autoplay policy | User must interact with window first — add a "tap to start" screen |
| Emergency overlay not showing on other window | WebSocket message type mismatch | Log messages in both windows, check type field |

### Hour 23–24: Demo polish checklist

Go through each item and fix anything that looks wrong:

- [ ] AMANDLA logo visible in top bar of both windows
- [ ] Dark theme consistent across both windows (#0D0D0D background)
- [ ] Large text in deaf window is readable from 1 metre away (minimum 42px)
- [ ] Turn indicator updates correctly when each person communicates
- [ ] Quick-sign buttons have the correct icons
- [ ] Avatar animates a different pose for each of the 10 signs
- [ ] Emergency overlay covers the full window on both screens
- [ ] Backend starts automatically when Electron launches
- [ ] Session ID is generated and shared correctly between windows
- [ ] App title bar shows "AMANDLA" not "Electron"

### Hour 25: Record the demo video

**Requirements from submission docs:**
- 2–10 minutes long (aim for 3–4)
- Must show working app end-to-end
- Record in a quiet room
- Zoom in so text is readable
- Speak while showing screen

**Script (3 minutes 30 seconds):**

*[0:00 – 0:30] — Opening*
"In South Africa, a deaf person in a hospital, a school, a job interview — always needs a third person to translate. That third person is not always available. That dependency is the real disability. AMANDLA removes the third person."

*[0:30 – 1:30] — Hearing to Deaf demo*
"I open AMANDLA. Two windows appear — one for the hearing person, one for the person who signs."
[Open app — two windows appear]
"The hearing person speaks."
[Tap microphone, say: "Good morning, how are you feeling today?"]
[Show text appearing large in deaf window]
"Instantly. No interpreter. The conversation happens."

*[1:30 – 2:30] — Deaf to Hearing demo*
"Now the deaf person responds."
[Tap THANK YOU quick-sign button on deaf window]
[Show avatar in hearing window animating THANK YOU]
[Point to TTS audio playing]
"The deaf person has a voice. Without speaking. Watch the hand."
[Zoom into avatar — show the W-hand for WATER]
[Zoom into MediaPipe skeleton on camera]
"Real-time AI. Running on a laptop."

*[2:30 – 2:50] — Emergency*
[Tap EMERGENCY button]
[Both windows go red]
"In an emergency — one tap. Both people know."
[Dismiss]

*[2:50 – 3:30] — Closing*
"AMANDLA also gives disabled South Africans access to justice."
[Show RIGHTS mode briefly — voice input, letter generating]
"Employment Equity Act. Promotion of Equality Act. Constitution Section 9. Formal complaint letter in 90 seconds."
"AMANDLA. The wheelchair for communication."
"Amandla Awethu — Power to the People."

**How to record:**
1. Use OBS Studio (free) or Windows built-in Game Bar (Win+G)
2. Record full screen
3. Speak clearly — the microphone on your laptop is fine
4. Do one practice run before recording
5. Keep the recording — do not re-record multiple times in the demo environment, use your first good take

### Hour 26: Submit

**Submission link:** `https://forms.gle/gQhx6aiiJgbsRD8g7`

**What to submit:**
- Demo video (3–4 minutes)
- Project name: AMANDLA
- Description: 2–3 paragraphs about what it does and how
- GitHub repo link
- Team member names

**GitHub — push before submitting:**
```powershell
git add .
git commit -m "AMANDLA hackathon submission — Isazi AI Accessibility 2026"
git push origin main
```

### Hour 27: Done

You are done. Walk away from the laptop.

---

## PART 9 — WHAT COULD GO WRONG (AND THE FIX)

### Risk 1 — Python backend crashes and won't restart
**Symptoms:** Electron window opens but shows connection error. WebSocket fails.  
**Fix:** Open a separate terminal, navigate to `amandla/`, run `python -m uvicorn backend.main:app --reload`. Do not rely on Electron auto-starting the backend for the demo — run it manually in a terminal so you can see error messages.

### Risk 2 — Qwen/Ollama stops responding
**Symptoms:** Sign recognition fails, AI responses stop.  
**Fix:** Open terminal → `ollama serve` → wait for it to restart → `ollama run amandla "test"`. If it takes more than 30 seconds: open `.env` → set `NVIDIA_ENABLED=true` → restart backend. NVIDIA NIM takes over.

### Risk 3 — Whisper is too slow for real-time demo
**Symptoms:** You speak, but text appears 5+ seconds later. Awkward pause in demo.  
**Fix A:** In `.env` change `WHISPER_MODEL=tiny` (faster, slightly less accurate).  
**Fix B:** Set `NVIDIA_ENABLED=true` (uses Parakeet instead — faster and more accurate).

### Risk 4 — Three.js avatar doesn't appear
**Symptoms:** Blank space where avatar should be.  
**Likely cause:** Electron's Content Security Policy blocking Three.js CDN.  
**Fix:** Add this to your `main.js` BrowserWindow config:
```javascript
webPreferences: {
  webSecurity: false  // DEV ONLY — remove before production
}
```
Or add the Three.js CDN to your CSP whitelist in the window's meta tag.

### Risk 5 — Camera access denied in Electron
**Symptoms:** MediaPipe skeleton doesn't appear, camera shows black.  
**Fix:** Add to the start of `main.js`:
```javascript
app.commandLine.appendSwitch('use-fake-ui-for-media-stream')  // forces permission grant
```
For real camera access in packaged app, add to BrowserWindow:
```javascript
webPreferences: {
  // ...
}
// After window creation:
win.webContents.session.setPermissionRequestHandler((webContents, permission, callback) => {
  if (permission === 'media') callback(true)
  else callback(false)
})
```

### Risk 6 — WebSocket drops connection during demo
**Symptoms:** Text stops appearing, no response to button presses.  
**Fix:** Add auto-reconnect in your preload.js:
```javascript
function connect(sessionId, role) {
  ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}/${role}`)
  ws.onclose = () => {
    setTimeout(() => connect(sessionId, role), 1000)  // reconnect after 1 second
  }
}
```

### Risk 7 — App won't launch on the demo laptop (if using a different machine)
**Fix:** Demo from your own laptop always. Never demo from a borrowed machine. If forced to — install Node.js, Python, Ollama, clone repo, run `npm install`, `pip install -r requirements.txt`, `ollama pull qwen2.5:3b`. This takes about 20 minutes.

### Risk 8 — The venue WiFi is slow and NVIDIA NIM fails
**Symptoms:** Backend fallback to NVIDIA fails because API calls time out.  
**Fix:** Set `NVIDIA_ENABLED=false`. Demo with Whisper local only. It is slower but it works offline. The core bridge (hearing→deaf text, deaf→hearing TTS) works entirely locally. The only internet-dependent feature is the RIGHTS mode Claude API.

---

## PART 10 — WHAT TO SAY TO THE JUDGES

### The 30-second pitch (memorise this)
"In South Africa, a deaf person at a hospital, at school, in a job interview — always needs a third person to translate. That third person is not always available. AMANDLA removes the third person. A deaf person signs — AMANDLA speaks for them. A hearing person speaks — AMANDLA shows it in large text. Both people talk. No interpreter needed. It's the wheelchair for communication."

### When judges ask hard questions

**"Why won't people just use Google Translate?"**  
Google Translate cannot translate South African Sign Language. SASL is not a written language — it is a spatial, gestural language. You cannot type it. You cannot search it. AMANDLA works inside the live conversation, in real time, in the room where it is happening.

**"What's your business model?"**  
Disabled people use it free. Institutions pay. Every company with 50+ employees in South Africa is legally required by the Employment Equity Act to be accessible. AMANDLA is cheaper than hiring a full-time interpreter, cheaper than a CCMA fine, and cheaper than a discrimination lawsuit. Schools, hospitals, courts, and corporates are the paying customers. The users pay nothing.

**"How do you train the sign language model without data?"**  
For the hackathon, Qwen handles sign recognition via hand landmark analysis from MediaPipe — it works well enough to demonstrate. Every real conversation on AMANDLA passively builds a South African Sign Language training dataset. The product builds the dataset it needs to improve itself.

**"SASL is different from ASL — how do you handle that?"**  
AMANDLA's architecture is language-agnostic. The MediaPipe landmark system captures hand geometry — the same technology works for any sign language. Post-hackathon, we collect SASL data through the communication bridge itself and train a SASL-specific recognition model. The data collection happens while the app is being used by real deaf South Africans.

**"Is this accessible to the people who need it?"**  
Every screen auto-reads for blind users using the browser's built-in text-to-speech. Sign language recognition requires no typing for deaf users. All 11 South African languages are supported through Whisper and Qwen. The interface was designed specifically so that a person's disability determines how they interact — not how the app was designed.

**"What makes this different from existing tools?"**  
Name one tool that does all of these in real time, for South African users, in South African Sign Language, for free. There isn't one. The closest thing is a human interpreter who costs R450 per hour and is not available at 3am in a hospital emergency room. AMANDLA is.

---

## PART 11 — THE BUSINESS CASE (FOR JUDGING)

### Who pays
Disabled people never pay. Institutions pay.

| Customer | Why they pay | How much |
|---|---|---|
| Government hospitals | Legal obligation to communicate with deaf patients | Per-location license |
| Schools | Every school has deaf learners with no SASL support | Per-learner annual license |
| Courts | Constitutional right to fair hearing requires accessibility | Per-court license |
| Corporates 50+ employees | Employment Equity Act compliance | Per-seat annual license |
| SASSA offices | Millions of disabled grant recipients | Government contract |
| Call centres | Voice accessibility for deaf callers | Per-agent seat license |

### The data flywheel (post-hackathon)
Every conversation on AMANDLA passively contributes to the first South African Sign Language AI corpus. Users contribute without knowing it. The dataset becomes the world's first SASL training dataset. This has independent academic and commercial value.

### South Africa's disability numbers
- 7.7 million disabled South Africans
- 600,000+ deaf or hard-of-hearing
- 90% disabled unemployment rate
- Zero existing real-time SASL AI translation tools

---

## PART 12 — QUICK REFERENCE COMMANDS

### Start everything
```powershell
# Terminal 1 — Python backend
cd C:\Users\Admin\amandla
python -m uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Electron app
cd C:\Users\Admin\amandla-desktop
npx electron .
```

### If Ollama stops working
```powershell
ollama serve
ollama run amandla "test"
```

### If backend crashes and you don't know why
```powershell
cd C:\Users\Admin\amandla
python -m uvicorn backend.main:app --reload --log-level debug
```

### Enable NVIDIA backup
Open `amandla/.env` → change `NVIDIA_ENABLED=false` to `NVIDIA_ENABLED=true` → restart backend

### Push to GitHub
```powershell
cd C:\Users\Admin\amandla
git add .
git commit -m "update"
git push
```

### Check if backend is running
Open browser → `http://localhost:8000/health` → should return `{"status":"ok"}`

---

## PART 13 — FILES YOU WILL BUILD AT THE HACKATHON

This is the complete list. Every file. Build them in this order.

### Python backend files
| File | When | What it does |
|---|---|---|
| `backend/main.py` | Hour 1 | FastAPI app setup, CORS, router mounting |
| `backend/routers/sign_ws.py` | Hour 2 | WebSocket session manager, message broadcast |
| `backend/services/whisper_service.py` | Hour 7 | Speech-to-text with Parakeet fallback |
| `backend/services/nvidia_service.py` | Hour 8 | NVIDIA NIM API calls |
| `backend/routers/rights.py` | Hour 17 | Claude API legal letter endpoint |
| `backend/services/claude_service.py` | Hour 17 | Claude API wrapper |

### Electron frontend files
| File | When | What it does |
|---|---|---|
| `src/main.js` | Hour 3 | Creates both windows, manages IPC |
| `src/preload/preload.js` | Hour 4 | WebSocket bridge, secure API access |
| `src/windows/hearing/index.html` | Hour 4–5 | Hearing person's UI |
| `src/windows/hearing/avatar.js` | Hour 9 | Three.js SASL avatar |
| `src/windows/deaf/index.html` | Hour 4–5 | Deaf person's UI with camera |
| `src/windows/deaf/mediapipe.js` | Hour 13 | Hand tracking overlay |
| `src/windows/rights/index.html` | Hour 18 | RIGHTS mode 3-step UI |

### Config files (set up Thursday)
| File | Location | Purpose |
|---|---|---|
| `.env` | `amandla/` | All API keys and feature flags |
| `package.json` | `amandla-desktop/` | Electron dependencies and scripts |
| `requirements.txt` | `amandla/backend/` | Python packages |

---

## PART 14 — HACKATHON LOGISTICS

- **Venue:** Knightsbridge Office Park, 33 Sloane Street, Rivonia, Johannesburg
- **Friday:** Arrive 4:30pm sharp. Kickoff 5pm. Build starts ~8pm after team formation.
- **Saturday:** 9am–10pm
- **Sunday:** 9am–5pm. Submission deadline 5pm.
- **Submission link:** `https://forms.gle/gQhx6aiiJgbsRD8g7`
- **Discord:** `https://discord.gg/kApnE3pv`
- **Facilitator:** Faeeza Lok — faeeza@isaziconsulting.co.za
- **Challenge area to select:** Hearing & Speech
- **Bring:** Laptop, charger, ID or student card, phone (as reference screen)
- **Provided:** Meals, WiFi, screens
- **Team size:** 1–3 people (formed Friday night)

---

## PART 15 — MASTER CLAUDE PROMPTS FOR THE HACKATHON

Copy these prompts into JetBrains Claude panel when you need them. Replace `[PASTE FILE]` with the actual file contents.

**Prompt for any new file:**
> "I am building AMANDLA — a real-time communication bridge for deaf and hearing South Africans. It is a desktop app built with Electron (frontend) and Python FastAPI (backend). I need you to build [FILE NAME]. Here is what it must do: [DESCRIBE FEATURE]. Here are the existing related files for context: [PASTE FILES]. Build the complete file with no placeholders. Use plain JavaScript for frontend files and Python 3.13 for backend files."

**Prompt when something is broken:**
> "This code in AMANDLA is broken. The error is: [PASTE ERROR]. The file is: [PASTE FILE]. The related files are: [PASTE FILES]. Diagnose the problem and give me the fixed complete file."

**Prompt for UI/styling:**
> "I need to style the [WINDOW NAME] window of AMANDLA. The app uses a dark theme with background #0D0D0D, teal accent #2EA880, purple accent #8B6FD4, and body font DM Sans. The Playfair Display font is used for headings. Here is the current HTML: [PASTE FILE]. Make it look polished, professional, and accessible. Large text for deaf users (minimum 42px for transcript). Return the complete updated HTML."

**Prompt for WebSocket debugging:**
> "My Electron app's WebSocket connection to FastAPI is failing. Electron preload: [PASTE]. FastAPI router: [PASTE]. Error message: [PASTE]. Fix it."

**Prompt for the avatar:**
> "I have a Three.js SASL avatar. I need it to: [DESCRIBE WHAT YOU NEED]. Here is the current avatar code: [PASTE avatar.js]. Return the complete updated file."

---

*AMANDLA — Power to the People*  
*Built for the Isazi AI for Accessibility Hackathon, March 2026*  
*"Your disability does not have to remove you from the conversation."*
