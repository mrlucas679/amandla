---
name: debugging
description: >
  Systematic debugging for Python FastAPI backends, JavaScript Electron frontends, WebSocket
  connections, and avatar/Three.js issues. Activate when the user says "it's broken", "I'm getting
  an error", "it's not working", "why is this failing?", "exception", "crash", "undefined",
  "null", "404", "500", "WebSocket disconnecting", "avatar not moving", "Electron won't start",
  or pastes an error message or stack trace. Never guess at bugs — debug methodically.
---

# Debugging Skill

Never guess at bugs. A guess that fixes the symptom leaves the real problem hiding.
Systematic debugging finds the root cause the first time.

---

## The Debugging Process (Always Follow This Order)

```
1. REPRODUCE — Can you make it happen consistently?
2. ISOLATE — Where exactly does it break?
3. UNDERSTAND — Why does it break there?
4. FIX — What's the minimal change that solves the root cause?
5. VERIFY — Is it actually fixed? Did the fix break anything else?
```

---

## Part 1 — Reading Error Messages

When the user shares an error, read it from the **bottom up**:
- The bottom line tells you WHAT went wrong
- The middle lines show WHERE it happened (the call stack)
- The top line shows WHEN it was triggered (the entry point)

### Python Stack Traces
```
Traceback (most recent call last):   ← START HERE
  File "backend/main.py", line 45, in handle_websocket   ← entry point
    result = await process_message(data)                   ← chain
  File "backend/services/sign_maps.py", line 12, in translate
    return SIGN_MAP[word]                                  ← WHERE it broke
KeyError: 'xyzunknown'               ← WHAT went wrong (this is the real problem)
```

**Read as:** "When handle_websocket called process_message, which called translate,
it tried to look up 'xyzunknown' in a dictionary that doesn't have that key."

**Root cause:** Missing `KeyError` handling in `translate()` — it needs a `.get()` or try/except.

### JavaScript Errors
```
TypeError: Cannot read properties of undefined (reading 'signs')
    at processMessage (deaf.js:87:32)    ← WHERE
    at WebSocket.onmessage (deaf.js:45:5) ← triggered by
```

**Read as:** Something at `deaf.js:87` tried to access `.signs` on something that was `undefined`.

**Debug step:** Add `console.log('data:', data)` just before line 87 to see what `data` actually is.

---

## Part 2 — Python/FastAPI Debugging

### Add Strategic Logging
```python
import logging
logger = logging.getLogger(__name__)

async def process_message(session_id: str, message: dict):
    """Processes incoming WebSocket messages."""
    # Log what we received — helps diagnose wrong message types
    logger.debug(f"[{session_id}] Processing message type: {message.get('type')}")
    logger.debug(f"[{session_id}] Message keys: {list(message.keys())}")
    
    # ... rest of function
```

### Check Health Endpoints
```bash
# Is the backend actually running?
curl http://localhost:8000/health

# What services are up?
curl http://localhost:8000/api/status
```

### Common Amandla Backend Issues

| Error | Likely Cause | Fix |
|-------|-------------|-----|
| `ConnectionRefusedError` to Ollama | `ollama serve` not running | Run `ollama serve` first |
| `KeyError` in sign_maps | Word not in dictionary | Add `.get(word, None)` with fallback |
| `422 Unprocessable Entity` | Request body doesn't match Pydantic model | Check request format matches schema |
| WebSocket disconnects immediately | Session ID invalid or role wrong | Validate session format in main.js |
| `load_dotenv()` called twice | Service calling it redundantly | Remove from service files, only in main.py |

### Run with Debug Logging
```bash
# Start backend with verbose logging
PYTHONPATH=. python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

---

## Part 3 — JavaScript / Electron Debugging

### Browser DevTools in Electron
In `main.js`, open DevTools for debugging:
```javascript
// Add to BrowserWindow creation during development
win.webContents.openDevTools();
```

Or press `Ctrl+Shift+I` (Windows/Linux) or `Cmd+Option+I` (Mac) in the running app.

### Common Amandla Frontend Issues

| Symptom | Likely Cause | Debug Step |
|---------|-------------|------------|
| `window.amandla is undefined` | Preload script not loaded or contextBridge error | Check `preload.js` path in `main.js` |
| WebSocket won't connect | Backend not running, wrong port | `curl http://localhost:8000/health` |
| Avatar doesn't move | `window.avatarPlaySigns` not found | Check `avatar.js` is loaded in deaf/index.html |
| Signs load but animation is wrong | Wrong bone name in sign definition | `console.log` the sign object before animating |
| Messages not routing to deaf window | Session ID mismatch between windows | Log session ID in both windows |

### Debugging the IPC / Preload Bridge
```javascript
// In hearing.js or deaf.js — temporarily add:
console.log('amandla bridge:', window.amandla);
console.log('available methods:', Object.keys(window.amandla || {}));

// In preload.js — log what's being sent:
contextBridge.exposeInMainWorld('amandla', {
  send: (data) => {
    console.log('[preload] Sending:', data);  // Temporary debug line
    return ipcRenderer.invoke('amandla-send', data);
  }
});
```

### WebSocket Message Debugging
```javascript
// In hearing.js or deaf.js — add this to see all incoming messages:
window.amandla.onMessage((message) => {
  console.log('[DEBUG] Received message:', JSON.stringify(message, null, 2));
  // ... rest of handler
});
```

---

## Part 4 — Avatar / Three.js Debugging

### Avatar Not Appearing
```javascript
// Check if the Three.js scene is rendering:
console.log('Scene children:', scene.children.length);
console.log('Camera position:', camera.position);
console.log('Renderer size:', renderer.getSize(new THREE.Vector2()));

// Check if the GLB model loaded:
loader.load(modelUrl, (gltf) => {
    console.log('Model loaded:', gltf);
    console.log('Bones:', gltf.scene.children);
});
```

### Animation Not Playing
```javascript
// Check if the sign exists in the library:
console.log('Sign for HELLO:', window.AMANDLA_SIGNS?.HELLO);
console.log('All available signs:', Object.keys(window.AMANDLA_SIGNS || {}));

// Check animation state:
console.log('Avatar state:', window.avatarState);
```

---

## Part 5 — The Rubber Duck Method

When stuck, explain the problem out loud (or in writing) as if explaining to someone who knows nothing:

1. "The code should do X"
2. "Instead it does Y"
3. "I think it's because Z"
4. "But I checked Z and..."

Often, articulating the problem reveals the solution. This works.

---

## Part 6 — When You Find the Bug

Before fixing:
1. **Write a test that reproduces the bug** — then fix the bug until the test passes
2. **Understand why the bug existed** — was it a missing check? Wrong assumption? Off-by-one?
3. **Ask: can this happen anywhere else?** — same pattern might be in other places

After fixing:
1. Verify the original problem is gone
2. Run all existing tests to check nothing new broke
3. Write a comment explaining what was happening

---

## Environment Notes

**In Claude Code (terminal):**
```bash
# Python: run with pdb debugger
python -m pdb backend/main.py

# Python: add breakpoint in code
import pdb; pdb.set_trace()  # execution pauses here

# Check what's on each port
netstat -an | grep 8000   # Windows
lsof -i :8000             # Mac/Linux
```

**In Claude.ai (browser):** Walk through the error message together. Ask the user to share:
- The full error message with stack trace
- The code around the line number mentioned
- What they expected vs what actually happened
