# AMANDLA — Four Agent Prompts for Claude Code

> Copy-paste each prompt into a separate Claude Code terminal.
> **Phase 1**: Run Agent 1 + Agent 2 in parallel.
> **Phase 2**: Run Agent 3 + Agent 4 in parallel (after Phase 1 completes).

---

## HOW TO LAUNCH

Open four terminal windows / Claude Code sessions:

```powershell
# Terminal 1 — Agent 1: Security
cd C:\Users\Admin\amandla-desktop
claude

# Terminal 2 — Agent 2: Backend  
cd C:\Users\Admin\amandla-desktop
claude

# Terminal 3 — Agent 3: Preload (run AFTER 1+2 finish)
cd C:\Users\Admin\amandla-desktop
claude

# Terminal 4 — Agent 4: Frontend (run AFTER 1+2 finish)
cd C:\Users\Admin\amandla-desktop
claude
```

Then paste the corresponding prompt below into each session.

---

## AGENT 1 PROMPT — SECURITY

```
You are Agent 1: SECURITY. Fix ALL security vulnerabilities in the AMANDLA Electron + FastAPI desktop app. This is a sign language communication bridge for disabled South Africans.

Read CLAUDE.md and AGENTS.md first for project context.

DO EVERY TASK BELOW — NO EXCEPTIONS:

━━━ TASK 1: REMOVE HARDCODED API KEY ━━━
File: .env
Line 31 has a REAL NVIDIA API key: NVIDIA_API_KEY=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
Change it to: NVIDIA_API_KEY=
This is a CRITICAL security vulnerability.

━━━ TASK 2: CREATE .env.example ━━━
Create a new file .env.example with all the same keys from .env but with empty/placeholder values. Add comments explaining each variable. This file IS safe to commit to git.

━━━ TASK 3: FIX CORS ━━━
File: backend/main.py (around line 60)
Change: allow_origins=["*"]
To: allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"]
A wildcard CORS allows any website to call your API.

━━━ TASK 4: FIX ERROR MESSAGE LEAKS ━━━
File: backend/main.py — In the /speech endpoint (around line 209), change:
  "error": str(e)  →  "error": "Transcription failed. Please try again."
File: backend/services/whisper_service.py — Around line 183 and 191:
  Replace all str(whisper_err) and str(parakeet_err) with generic "Speech processing failed." messages.
Never expose raw Python exception text to the client.

━━━ TASK 5: ADD AUDIO FILE TYPE VALIDATION ━━━
File: backend/main.py — In the /speech endpoint, after reading audio content:
Add a check that audio.content_type starts with "audio/" or is "application/octet-stream".
If invalid, raise HTTPException(status_code=415, detail="Unsupported audio format. Please upload an audio file.")

━━━ TASK 6: ADD INPUT LENGTH VALIDATION ━━━
File: backend/main.py — Update the Pydantic models:
- AnalyseRequest.description: add Field(max_length=5000)
- LetterRequest.description: add Field(max_length=5000)
- LetterRequest.user_name: add Field(max_length=200)
- LetterRequest.employer_name: add Field(max_length=300)
Import Field from pydantic. Use named constants: MAX_DESCRIPTION_LENGTH = 5000, etc.

━━━ TASK 7: ADD INPUT SANITIZATION ━━━
File: backend/main.py — Create a helper function:
def _sanitize_user_input(text: str, max_length: int = 5000) -> str:
    """Remove control characters and truncate user input to prevent prompt injection."""
Strip control characters (except newlines), strip leading/trailing whitespace, truncate to max_length.
Call this on all user-provided text in rights_analyze() and rights_letter() before passing to AI.

━━━ TASK 8: ADD WEBSOCKET MESSAGE VALIDATION ━━━
File: backend/main.py — Create Pydantic models for each WS message type:
- TextMessage(type="text", text=str, language=Optional[str], sender=str, timestamp=int)
- SaslTextMessage(type="sasl_text", text=str, sender=str, timestamp=int)
- SignMessage(type="sign", text=str, sender=str, timestamp=int)
- LandmarkMessage(type="landmarks", landmarks=list, handedness=str, sender=str, timestamp=int)
- EmergencyMessage(type="emergency", sender=str, timestamp=int)

In websocket_endpoint, after json.loads(data), validate based on msg.get("type"):
- Wrap the validation in try/except ValidationError
- On failure: send {"type": "error", "message": "Invalid message format"} and continue
- On success: proceed with the existing handler logic

━━━ TASK 9: ADD SESSION EXPIRY ━━━
File: backend/main.py — Add a background task that cleans up stale sessions.
- Add a "last_activity" timestamp to each session dict (update it on every WS message)
- Use @app.on_event("startup") to launch an asyncio task that runs every 60 seconds
- Remove sessions where last_activity is older than 30 minutes AND no WebSocket is connected
- Also clean up _sign_buffers and _sign_tasks for expired sessions
- Use a named constant: SESSION_EXPIRY_SECONDS = 1800

━━━ TASK 10: REMOVE webSecurity: false ━━━
File: src/main.js — Remove the line "webSecurity: false" from ALL THREE BrowserWindow definitions:
- Hearing window (around line 37)
- Deaf window (around line 57)
- Rights window (around line 103)
Simply delete those lines. They disable Chromium's same-origin policy which is a major security risk.

━━━ TASK 11: ADD CONTENT SECURITY POLICY ━━━
File: src/main.js — After createWindows(), add CSP headers for all windows. Use:
const CSP = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; connect-src 'self' ws://localhost:8000 http://localhost:8000; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self';"

Apply it via session.webRequest.onHeadersReceived for each window's session.

━━━ TASK 12: ADD RATE LIMITING ━━━
Create NEW file: backend/middleware.py
Implement a simple in-memory rate limiter as FastAPI middleware:
- Track request counts per endpoint path per minute
- Limits: /speech = 10/min, /rights/analyze = 5/min, /rights/letter = 5/min
- Return HTTP 429 with message "Too many requests. Please wait a moment." when exceeded
- Use a dict with minute-granularity keys that auto-expire

Then in backend/main.py, import and add the middleware after CORS:
from backend.middleware import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)

RULES:
- Add a comment above EVERY function
- NEVER hardcode secrets
- Use named constants for all magic numbers
- All error responses must be generic — no stack traces
- Don't break existing functionality
- Don't touch files not listed above
- Prefix console logs with [Security] where relevant
```

---

## AGENT 2 PROMPT — BACKEND

```
You are Agent 2: BACKEND. Fix all backend service issues, imports, error handling, and robustness in the AMANDLA FastAPI app. This is a sign language bridge for disabled South Africans.

Read CLAUDE.md and AGENTS.md first for project context.

CRITICAL CONTEXT: Another agent (Agent 3) will update the frontend to send speech uploads and rights requests through WebSocket instead of direct HTTP. You need to add the WS message handlers for those new message types.

DO EVERY TASK BELOW — NO EXCEPTIONS:

━━━ TASK 1: SINGLE load_dotenv() CALL ━━━
File: backend/main.py — Add at the top (after the os/sys imports, before FastAPI init):
  from dotenv import load_dotenv
  load_dotenv()
This is the ONE place dotenv is loaded. Remove all other load_dotenv() calls in:
- backend/services/ollama_client.py (line ~47)
- backend/services/ollama_service.py (line ~12)
- backend/services/claude_service.py (inside _get_ollama_config)
- backend/services/whisper_service.py (line ~16)
These services are always imported after main.py runs, so env vars are already loaded.

━━━ TASK 2: MOVE LAZY IMPORTS TO TOP-LEVEL ━━━
File: backend/main.py — Move ALL function-level imports to the top of the file:
- import httpx (used in _check_ollama, _ollama_signs_to_english)
- from backend.services.whisper_service import transcribe_audio
- from backend.services.ollama_service import recognize_sign
- from backend.services.claude_service import analyse_incident, generate_rights_letter
- For sasl_transformer: wrap in try/except at module level:
    try:
        from sasl_transformer.transformer import SASLTransformer
        from sasl_transformer.models import TranslationRequest
        _SASL_AVAILABLE = True
    except ImportError as e:
        _SASL_AVAILABLE = False
        logger.warning(f"[SASL] Transformer not available: {e}")
  Then in _text_to_sasl_signs, check _SASL_AVAILABLE before using it.

━━━ TASK 3: FIX ASYNCIO IMPORT ━━━
File: backend/main.py — Line 253 has "import asyncio as _asyncio". 
Remove this. Add "import asyncio" at the top with other stdlib imports.
Find/replace all "_asyncio." with "asyncio." throughout the file.

━━━ TASK 4: CLEAN UP SIGN BUFFERS ON DISCONNECT ━━━
File: backend/main.py — In the finally block of websocket_endpoint (around line 549-553), add:
  # Cancel any pending sign-to-English reconstruction task
  pending_task = _sign_tasks.pop(sessionId, None)
  if pending_task and not pending_task.done():
      pending_task.cancel()
  _sign_buffers.pop(sessionId, None)
This prevents memory leaks when WebSocket disconnects while signs are buffered.

━━━ TASK 5: REMOVE DEAD IMPORT ━━━
File: backend/main.py — Line 583 (bottom of file):
  from backend.services.sign_maps import sentence_to_sign_names
This is imported but NEVER used in main.py. Delete this line.

━━━ TASK 6: ADD TYPE HINTS ━━━
File: backend/main.py — Add type annotations to all functions that lack them. Key ones:
- _text_to_sasl_signs(text: str) -> dict
- _check_ollama() -> bool (already has)
- _check_whisper() -> bool (already has)
- _simple_signs_to_english(signs: list[str]) -> str
- _ollama_signs_to_english(signs: list[str]) -> Optional[str]
- _signs_to_english(signs: list[str]) -> str
- _debounce_and_flush(session_id: str, session: dict) -> None
- _send_safe(ws: WebSocket, msg: dict) -> None
- _broadcast(session: dict, sender_ws: WebSocket, msg: dict) -> None
- _broadcast_all(session: dict, msg: dict) -> None

━━━ TASK 7: SHARED HTTPX CLIENT ━━━
File: backend/main.py — Create a shared httpx.AsyncClient for Ollama API calls.
At module level:
  _http_client: Optional[httpx.AsyncClient] = None
  
  async def _get_http_client() -> httpx.AsyncClient:
      """Get or create the shared HTTP client for Ollama API calls."""
      global _http_client
      if _http_client is None or _http_client.is_closed:
          _http_client = httpx.AsyncClient(timeout=10.0)
      return _http_client

Use this in _check_ollama() and _ollama_signs_to_english() instead of creating new clients.
Add cleanup in a @app.on_event("shutdown") handler.

━━━ TASK 8: ADD NEW WEBSOCKET MESSAGE TYPES ━━━
File: backend/main.py — In websocket_endpoint, add handlers for these new message types:

a) "status_request" — Any role can request status:
   if msg.get("type") == "status_request":
       qwen_alive = await _check_ollama()
       whisper_ok = _check_whisper()
       await _send_safe(websocket, {
           "type": "status_response",
           "request_id": msg.get("request_id"),
           "qwen": "alive" if qwen_alive else "dead",
           "whisper": "ready" if whisper_ok else "unavailable",
           "sessions": len(sessions)
       })
       continue

b) "speech_upload" — Hearing role sends base64-encoded audio:
   if msg.get("type") == "speech_upload" and role == "hearing":
       import base64
       audio_b64 = msg.get("audio_b64", "")
       mime_type = msg.get("mime_type", "audio/webm")
       try:
           audio_bytes = base64.b64decode(audio_b64)
           result = await transcribe_audio(audio_bytes, mime_type)
           text = result.get("text", "").strip()
           # Send transcription result back to sender
           await _send_safe(websocket, {
               "type": "speech_result",
               "request_id": msg.get("request_id"),
               "text": text,
               "language": result.get("language", "en"),
               "confidence": result.get("confidence", 0.0)
           })
           # If text was transcribed, also convert to signs and broadcast
           if text:
               sasl = await _text_to_sasl_signs(text)
               out = {"type": "signs", "signs": sasl["signs"], "text": sasl["text"], "original_english": text, "language": result.get("language"), "session_id": sessionId}
               await _broadcast(session, websocket, out)
               await _broadcast_all(session, {"type": "turn", "speaker": "hearing"})
       except Exception as e:
           logger.error(f"[WS] speech_upload error: {e}")
           await _send_safe(websocket, {"type": "speech_result", "request_id": msg.get("request_id"), "error": "Speech processing failed."})
       continue

c) "rights_analyze" — Any role (typically rights window):
   if msg.get("type") == "rights_analyze":
       description = msg.get("description", "")
       incident_type = msg.get("incident_type", "workplace")
       try:
           result = await analyse_incident(description, incident_type)
           await _send_safe(websocket, {"type": "rights_result", "request_id": msg.get("request_id"), **result})
       except Exception as e:
           logger.error(f"[WS] rights_analyze error: {e}")
           await _send_safe(websocket, {"type": "rights_result", "request_id": msg.get("request_id"), "error": "Analysis failed."})
       continue

d) "rights_letter" — Any role:
   if msg.get("type") == "rights_letter":
       try:
           result = await generate_rights_letter(
               incident_description=msg.get("description", ""),
               user_name=msg.get("user_name", "The Complainant"),
               employer_name=msg.get("employer_name", ""),
               incident_date=msg.get("incident_date", ""),
               analysis=msg.get("analysis")
           )
           await _send_safe(websocket, {"type": "rights_letter_result", "request_id": msg.get("request_id"), **result})
       except Exception as e:
           logger.error(f"[WS] rights_letter error: {e}")
           await _send_safe(websocket, {"type": "rights_letter_result", "request_id": msg.get("request_id"), "error": "Letter generation failed."})
       continue

Place these handlers BEFORE the final "broadcast everything else" catch-all at the bottom.

━━━ TASK 9: FIX SERVICE IMPORTS ━━━
File: backend/services/ollama_client.py — Move lazy imports to top:
  import httpx  (move from inside _try_ollama)
  Remove the load_dotenv() call inside _try_ollama. Read env vars at module level:
  OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
  OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "amandla")

File: backend/services/claude_service.py — Move "import httpx" to top-level (from inside _call_ollama).

━━━ TASK 10: REDUCE WHISPER TIMEOUT ━━━
File: backend/services/whisper_service.py — Change:
  WHISPER_TIMEOUT_S = 120.0  →  WHISPER_TIMEOUT_S = 45.0
120s is way too long for a real-time communication app. 45s is generous for CPU transcription.

━━━ TASK 11: ADD --reload TO PACKAGE.JSON ━━━
File: package.json — Change the "backend" script from:
  "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"
to:
  "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

━━━ TASK 12: MARK GEMINI SERVICE AS DEPRECATED ━━━
File: backend/services/gemini_service.py — Add at the very top (line 1):
  # DEPRECATED — All AI now uses local Ollama. This stub file is kept only
  # to prevent ImportError if any legacy code references it.
  # Scheduled for removal in next cleanup sprint.
Do NOT delete the file.

RULES:
- Add a comment above EVERY function you write or modify
- All error messages sent to WS clients must be generic
- Use named constants for magic numbers
- Add type hints to every function
- Don't touch src/ files (those are for Agent 3 and 4)
- Keep all existing HTTP endpoints working (they're fallbacks)
- Prefix log messages with [ComponentName]
```

---

## AGENT 3 PROMPT — PRELOAD & ARCHITECTURE

```
You are Agent 3: PRELOAD & ARCHITECTURE. Fix all communication pattern violations in the AMANDLA Electron app.

CRITICAL RULE FROM AGENTS.md: "No direct HTTP calls from frontend. All communication is WebSocket-based."

Currently the app violates this rule in 6 places where the renderer makes direct fetch() calls to the backend. You must route ALL of these through the preload bridge (window.amandla.*) via WebSocket.

Agent 2 has already added WebSocket message handlers on the backend for: status_request, speech_upload, rights_analyze, and rights_letter.

Read CLAUDE.md and AGENTS.md first for full project context.

DO EVERY TASK BELOW — NO EXCEPTIONS:

━━━ TASK 1: ADD PROMISE-BASED WS METHODS TO PRELOAD ━━━
File: src/preload/preload.js

Add a pending-request system:
- At module level, add: let _requestId = 0; const _pending = new Map();
- Create a helper: function _sendRequest(payload) that:
  1. Increments _requestId
  2. Adds request_id to the payload
  3. Creates a new Promise
  4. Stores {resolve, reject, timer} in _pending keyed by request_id
  5. Sets a 30-second timeout that rejects with "Request timed out"
  6. Sends the payload via ws.send(JSON.stringify(payload))
  7. Returns the Promise

Update the ws.onmessage handler to check BEFORE calling messageCallback:
  if (data.request_id && _pending.has(data.request_id)) {
    const req = _pending.get(data.request_id);
    clearTimeout(req.timer);
    _pending.delete(data.request_id);
    if (data.error) req.reject(new Error(data.error));
    else req.resolve(data);
    return; // Don't pass to messageCallback
  }

Add these new methods to contextBridge.exposeInMainWorld('amandla', {...}):

a) uploadSpeech: (audioBlob, mimeType) => {
     // Convert Blob to base64
     return new Promise((resolve, reject) => {
       const reader = new FileReader();
       reader.onload = () => {
         const base64 = reader.result.split(',')[1]; // strip data:...;base64, prefix
         _sendRequest({
           type: 'speech_upload',
           audio_b64: base64,
           mime_type: mimeType || 'audio/webm',
           sender: currentRole,
           timestamp: Date.now()
         }).then(resolve).catch(reject);
       };
       reader.onerror = () => reject(new Error('Failed to read audio'));
       reader.readAsDataURL(audioBlob);
     });
   }

b) requestStatus: () => _sendRequest({ type: 'status_request' })

c) analyzeRights: (description, incidentType) => _sendRequest({
     type: 'rights_analyze',
     description: description,
     incident_type: incidentType || 'workplace'
   })

d) generateLetter: (details) => _sendRequest({
     type: 'rights_letter',
     ...details
   })

Each method should check if ws is connected first. If not, return Promise.reject(new Error('Not connected to backend')).

━━━ TASK 2: FIX HEARING WINDOW — SPEECH UPLOAD ━━━
File: src/windows/hearing/index.html

Replace the uploadAudio() function. Currently it uses direct fetch:
  const resp = await fetch('http://localhost:8000/speech', { method: 'POST', body: fd })

Change to:
  async function uploadAudio(blob, mimeType) {
    transcriptEl.textContent = 'Transcribing…'
    try {
      const data = await window.amandla.uploadSpeech(blob, mimeType)
      if (data.text) {
        sendText(data.text, data.language || null)
      } else {
        transcriptEl.textContent = 'Could not transcribe — try typing'
      }
    } catch (err) {
      console.error('[Hearing] Upload error:', err)
      transcriptEl.textContent = 'Transcription failed — try typing instead'
    }
  }

━━━ TASK 3: FIX HEARING WINDOW — STATUS POLLING ━━━
File: src/windows/hearing/index.html

Replace the pollStatus() function. Currently it uses direct fetch:
  const r = await fetch('http://localhost:8000/api/status')

Change to:
  async function pollStatus() {
    try {
      const d = await window.amandla.requestStatus()
      statusDot.className = d.qwen === 'alive' ? '' : 'offline'
      statusDot.title = d.qwen === 'alive' ? 'AI online' : 'AI offline — restart Ollama'
    } catch (e) {
      statusDot.className = 'offline'
      statusDot.title = 'Backend offline'
    }
  }

━━━ TASK 4: FIX DEAF WINDOW — STATUS POLLING ━━━
File: src/windows/deaf/index.html

Same change as hearing window — replace the fetch-based pollStatus() with window.amandla.requestStatus().

━━━ TASK 5: FIX RIGHTS WINDOW — CONNECT TO WEBSOCKET ━━━
File: src/main.js — In the ipcMain.handle('open-rights') handler, after rightsWin.loadFile():
  rightsWin.webContents.on('did-finish-load', () => {
    rightsWin.webContents.send('session-id', SESSION_ID)
    rightsWin.webContents.send('role', 'rights')
  })

File: src/windows/rights/index.html — Add at the BEGINNING of the <script> section:
  // Connect to WebSocket so all API calls go through the preload bridge
  window.amandla.getSessionId().then(function (id) {
    window.amandla.connect(id || 'demo', 'rights')
  }).catch(function () {
    window.amandla.connect('demo', 'rights')
  })

━━━ TASK 6: FIX RIGHTS WINDOW — ANALYZE INCIDENT ━━━
File: src/windows/rights/index.html

Replace the analyseIncident() function:
  async function analyseIncident(description) {
    const result = await window.amandla.analyzeRights(description, getIncidentType())
    return result
  }

━━━ TASK 7: FIX RIGHTS WINDOW — GENERATE LETTER ━━━
File: src/windows/rights/index.html

Replace the generateLetter() function:
  async function generateLetter() {
    const result = await window.amandla.generateLetter({
      description: document.getElementById('incident-desc').value.trim(),
      user_name: document.getElementById('your-name').value.trim() || 'The Complainant',
      employer_name: document.getElementById('org-name').value.trim(),
      incident_date: document.getElementById('incident-date').value || todayString(),
      analysis: analysisData
    })
    return result
  }

━━━ TASK 8: FIX DEAF WINDOW — SHOW ORIGINAL ENGLISH ━━━
File: src/windows/deaf/index.html — In the message handler for msg.type === 'signs' (around line 425-445):
After the gloss display logic, add:
  // Show original English sentence below the SASL gloss
  if (msg.original_english) {
    sentenceEl.textContent = msg.original_english
    setTimeout(function () { sentenceEl.textContent = '' }, clearAfter)
  }

━━━ TASK 9: MARK UNUSED HEARING SIGNS LIBRARY ━━━
File: src/windows/hearing/signs_library.js — Add at the very top:
  // NOTE: This file is NOT used by the hearing window.
  // The hearing window does not render signs or an avatar.
  // It is a candidate for removal — confirm with the team first.
Do NOT delete the file.

RULES:
- Add JSDoc comments above every new function in preload.js
- Keep ALL existing window.amandla methods working
- The pending-promise pattern must have 30s timeout
- If WS is not connected, reject promises immediately
- Don't touch backend files (those are Agent 2's)
- Don't touch avatar files (those are Agent 4's)
- Test by tracing: every fetch() in the codebase should be gone after your changes (except CDN script loads)
```

---

## AGENT 4 PROMPT — FRONTEND & AVATAR

```
You are Agent 4: FRONTEND & AVATAR. Fix all UI bugs, user feedback, and avatar integration issues in the AMANDLA Electron app. Focus on user experience — when things go wrong, users must see CLEAR messages.

Read CLAUDE.md and AGENTS.md first for project context.

The app has two windows: Hearing (green/teal #2EA880) and Deaf (purple #8B6FD4). Error color is #FC8181.

DO EVERY TASK BELOW — NO EXCEPTIONS:

━━━ TASK 1: ADD CONNECTION ERROR BANNER — HEARING ━━━
File: src/windows/hearing/index.html

Add CSS in the <style> block:
  #conn-banner {
    display: none;
    position: fixed; top: 0; left: 0; right: 0; z-index: 9997;
    background: #FC818130; border-bottom: 2px solid #FC8181;
    padding: 10px 16px; text-align: center;
    font-size: 13px; color: #FCA5A5;
    animation: banner-in 0.3s ease;
  }
  #conn-banner.visible { display: flex; align-items: center; justify-content: center; gap: 12px; }
  #conn-banner button { background: #FC818140; border: 1px solid #FC8181; color: #fff; padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; }
  @keyframes banner-in { from { transform: translateY(-100%); } to { transform: translateY(0); } }

Add HTML after the emergency overlay:
  <div id="conn-banner">
    ⚠ Cannot connect to AMANDLA backend. Make sure the app was started with <code>npm start</code>.
    <button onclick="document.getElementById('conn-banner').classList.remove('visible')">Dismiss</button>
  </div>

Add JS: Show the banner if disconnected for more than 3 seconds:
  let _connBannerTimer = null
  // Update the existing onConnectionChange callback:
  // When connected: clear timer, hide banner
  // When disconnected: start 3-second timer, then show banner
  In the existing window.amandla.onConnectionChange handler, add:
    if (connected) {
      if (_connBannerTimer) { clearTimeout(_connBannerTimer); _connBannerTimer = null; }
      document.getElementById('conn-banner').classList.remove('visible')
    } else {
      _connBannerTimer = setTimeout(function() {
        document.getElementById('conn-banner').classList.add('visible')
      }, 3000)
    }

━━━ TASK 2: ADD CONNECTION ERROR BANNER — DEAF ━━━
File: src/windows/deaf/index.html
Same pattern as hearing window. Different text: "⚠ Waiting for connection to backend…"
Same CSS, HTML, and JS logic.

━━━ TASK 3: IMPROVE EMERGENCY OVERLAY — BOTH WINDOWS ━━━
File: src/windows/hearing/index.html AND src/windows/deaf/index.html

a) Change auto-dismiss timeout from 10000ms to 30000ms (10s → 30s).

b) Add a countdown display. In the emergency overlay HTML, add:
   <div class="emg-countdown" id="emg-countdown"></div>
   Style: font-size: 14px; color: rgba(255,255,255,0.7); margin-top: 6px;

c) Update showEmergency() to include a countdown:
   let _emgCountdown = 30
   let _emgInterval = null
   function showEmergency() {
     document.getElementById('emergency-overlay').classList.add('active')
     speakText('Emergency. Signer has triggered an emergency alert.')
     _emgCountdown = 30
     const countEl = document.getElementById('emg-countdown')
     _emgInterval = setInterval(function() {
       _emgCountdown--
       if (countEl) countEl.textContent = 'Auto-dismiss in ' + _emgCountdown + 's'
       if (_emgCountdown <= 0) hideEmergency()
     }, 1000)
   }
   function hideEmergency() {
     document.getElementById('emergency-overlay').classList.remove('active')
     if (_emgInterval) { clearInterval(_emgInterval); _emgInterval = null; }
   }

d) Add keyboard dismiss — listen for Escape key:
   document.addEventListener('keydown', function(e) {
     if (e.key === 'Escape') hideEmergency()
   })

━━━ TASK 4: CDN SCRIPT FALLBACK — DEAF WINDOW ━━━
File: src/windows/deaf/index.html

Replace the three CDN script tags (Three.js, MediaPipe hands, MediaPipe camera) with onerror handling:
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"
          onerror="handleCDNError('Three.js')"></script>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469240/hands.min.js"
          onerror="handleCDNError('MediaPipe Hands')"></script>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils@0.3.1675466862/camera_utils.min.js"
          onerror="handleCDNError('MediaPipe Camera')"></script>

Add a small inline script BEFORE these tags:
  <script>
    window._cdnErrors = []
    function handleCDNError(libName) {
      console.warn('[CDN] Failed to load:', libName)
      window._cdnErrors.push(libName)
      // Show a visible warning after all scripts have had a chance to load
      setTimeout(function() {
        if (window._cdnErrors.length > 0) {
          var panel = document.getElementById('avatar-panel')
          if (panel) {
            var warn = document.createElement('div')
            warn.style.cssText = 'position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;color:#FCA5A5;font-size:15px;padding:20px;'
            warn.innerHTML = '⚠ Could not load: ' + window._cdnErrors.join(', ') + '<br><br>Avatar will be unavailable.<br>Text-based signs will still appear below.'
            panel.appendChild(warn)
          }
        }
      }, 2000)
    }
  </script>

━━━ TASK 5: GRACEFUL SIGN ERROR HANDLING — AVATAR ━━━
File: src/windows/deaf/avatar.js

In resolveSign() (around line 308), wrap the entire body in try/catch:
  function resolveSign(item) {
    try {
      // ... existing code ...
    } catch (err) {
      console.warn('[Avatar] Skipping malformed sign:', item, err)
      return null
    }
  }

In queueSign() (around line 325), after resolveSign returns:
  if (!s && typeof signObj === 'string' && signObj.length > 1) {
    console.warn('[Avatar] Unknown sign, will fingerspell:', signObj)
  }

━━━ TASK 6: AVATAR INIT FAILURE EVENT ━━━
File: src/windows/deaf/avatar.js — In initAvatar(), where it checks typeof THREE === 'undefined':
Instead of just console.error, also:
  window._avatarFailed = true
  window.dispatchEvent(new CustomEvent('amandla:avatarFailed', { detail: { reason: 'THREE.js not loaded' } }))

File: src/windows/deaf/index.html — Listen for this event:
  window.addEventListener('amandla:avatarFailed', function(e) {
    var panel = document.getElementById('avatar-panel')
    if (panel) {
      var msg = document.createElement('div')
      msg.style.cssText = 'position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;color:#8B6FD4;font-size:18px;'
      msg.innerHTML = '🤟 SASL text mode active<br><small style="color:#888">Avatar unavailable — signs will appear as text</small>'
      panel.appendChild(msg)
    }
  })

━━━ TASK 7: DOCUMENT AVATAR DRIVER GAP ━━━
File: src/windows/deaf/avatar_driver.js — Add at the VERY TOP of the file (before the IIFE):
  /**
   * STATUS: NOT CURRENTLY INTEGRATED
   *
   * This driver maps AMANDLA sign poses to Mixamo-rigged GLB skeletons.
   * The current avatar.js uses a PROCEDURAL skeleton built with Three.js primitives.
   *
   * When the project upgrades to a GLB model (e.g. human_signing.glb),
   * this driver should be integrated into avatar.js to replace buildAvatarSkeleton().
   * Key functions to integrate:
   *   - bindBonesFromGLTF() — maps GLB bone names to AMANDLA joint names
   *   - remapPoseForMixamo() — adjusts rotation axes for Mixamo convention
   *   - applyHandshapeGLTF() — finger curl on Mixamo finger bones
   */

━━━ TASK 8: SIGN PLAYBACK FEEDBACK — DEAF ━━━
File: src/windows/deaf/index.html — In the msg.type === 'signs' handler, add:
  // Show sign count indicator
  if (Array.isArray(msg.signs) && msg.signs.length > 0) {
    var signLabel = document.getElementById('avatar-sign-label')
    if (signLabel) signLabel.textContent = 'Playing ' + msg.signs.length + ' signs…'
    // Show "Done" after all signs finish
    setTimeout(function() {
      if (signLabel) signLabel.textContent = '✓ Done'
      setTimeout(function() { if (signLabel) signLabel.textContent = '' }, 1000)
    }, clearAfter - 500)
  }

━━━ TASK 9: BETTER MIC ERROR MESSAGE ━━━
File: src/windows/hearing/index.html — In the catch block of startRecording() (around line 417):
Change:
  transcriptEl.textContent = 'Microphone access denied'
To:
  transcriptEl.textContent = '🎙 Microphone access denied — check your system settings and allow microphone access for AMANDLA'

━━━ TASK 10: KEYBOARD ACCESSIBILITY ━━━
File: src/windows/hearing/index.html AND src/windows/deaf/index.html

Add at the bottom of the <script>:
  // Keyboard: Enter dismisses startup overlay
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && overlay.style.display !== 'none') {
      startBtn.click()
    }
  })

RULES:
- Keep the existing color scheme: #2EA880 (hearing), #8B6FD4 (deaf), #FC8181 (errors)
- All visible text must be plain simple English
- Don't touch backend files or preload.js
- Add comments above every new function
- Don't add any new npm packages or CDN scripts
- Don't delete any existing code — only add to it
- Keep all existing functionality working
```

