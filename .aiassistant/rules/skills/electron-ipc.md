---
name: electron-ipc
description: >
  Secure Electron IPC patterns: contextBridge, preload scripts, BrowserWindow configuration,
  renderer-to-main communication, and Electron security hardening. Activate when working on
  any Electron main process (main.js), preload scripts, renderer JavaScript (hearing.js, deaf.js,
  rights.js), or when adding any new communication between frontend and backend in the Amandla app.
  Also activate when asked "how do I call the backend from the renderer?", "IPC", "contextBridge",
  "preload", "nodeIntegration", "contextIsolation", or when the app can't communicate between windows.
---

# Electron IPC & Security Patterns

Electron security is not optional. The app runs with OS-level permissions.
A security mistake here is not just a web bug — it can give attackers control of the user's entire machine.

---

## The Golden Rule

**Renderers (hearing.js, deaf.js, rights.js) must NEVER talk to:**
- The filesystem directly
- The network directly
- Node.js APIs

**All communication goes through the preload bridge: `window.amandla.*`**

This is not a style preference — it's a security requirement.

---

## Part 1 — BrowserWindow Configuration (main.js)

Every `BrowserWindow` must have these exact settings:

```javascript
/**
 * Creates a new BrowserWindow with secure defaults.
 * contextIsolation and nodeIntegration settings are non-negotiable security requirements.
 *
 * @param {object} options - Window options (width, height, etc.)
 * @returns {BrowserWindow} Configured window instance
 */
function createSecureWindow(options) {
    return new BrowserWindow({
        ...options,
        webPreferences: {
            // REQUIRED — Never change these
            contextIsolation: true,        // Isolates renderer from Node.js
            nodeIntegration: false,        // Renderer has no Node.js access
            nodeIntegrationInWorker: false,
            nodeIntegrationInSubFrames: false,
            webviewTag: false,             // Disable <webview> — security risk

            // Preload script is the ONLY bridge
            preload: path.join(__dirname, 'preload/preload.js'),

            // Content Security Policy — restrict what the page can load
            // Set in main.js using session.defaultSession.webRequest.onHeadersReceived
        }
    });
}
```

### Content Security Policy
```javascript
// In main.js — set CSP for all windows
const { session } = require('electron');

session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
        responseHeaders: {
            ...details.responseHeaders,
            'Content-Security-Policy': [
                "default-src 'self';" +
                "script-src 'self';" +
                "style-src 'self' https://fonts.googleapis.com;" +
                "font-src 'self' https://fonts.gstatic.com;" +
                "connect-src 'self' ws://localhost:8000;" +
                "img-src 'self' data:;"
            ]
        }
    });
});
```

---

## Part 2 — The Preload Bridge Pattern (preload.js)

The preload script is the ONLY file that can use Node.js APIs. It creates a safe,
controlled bridge between the secure renderer world and the backend.

```javascript
// preload/preload.js
const { contextBridge, ipcRenderer } = require('electron');

/**
 * Exposes a safe, limited API to renderer processes.
 * Only expose what renderers actually need — nothing more.
 */
contextBridge.exposeInMainWorld('amandla', {
    
    /**
     * Connects this window to the backend WebSocket session.
     * @param {string} sessionId - The session ID from the main process
     * @param {string} role - Window role: 'hearing', 'deaf', or 'rights'
     */
    connect: (sessionId, role) => {
        // Validate inputs before passing to main process
        if (!sessionId || typeof sessionId !== 'string') {
            throw new Error('Invalid session ID');
        }
        if (!['hearing', 'deaf', 'rights'].includes(role)) {
            throw new Error(`Invalid role: ${role}`);
        }
        ipcRenderer.invoke('amandla-connect', { sessionId, role });
    },

    /**
     * Sends a message to the backend via WebSocket.
     * @param {object} message - Message object with required 'type' field
     * @returns {Promise<object>} Response from backend
     */
    send: (message) => {
        if (!message?.type) {
            throw new Error('Message must have a type field');
        }
        return ipcRenderer.invoke('amandla-send', message);
    },

    /**
     * Registers a callback for incoming backend messages.
     * @param {function} callback - Called with each message object
     */
    onMessage: (callback) => {
        if (typeof callback !== 'function') {
            throw new Error('onMessage requires a function');
        }
        ipcRenderer.on('amandla-message', (event, message) => callback(message));
    },

    /**
     * Removes the message listener (important for cleanup).
     */
    offMessage: () => {
        ipcRenderer.removeAllListeners('amandla-message');
    }
});

/**
 * One-time setup: receive the session ID from the main process.
 * The main process generates the session ID and sends it here via IPC.
 */
ipcRenderer.once('session-id', (event, sessionId) => {
    // Store for use in connect()
    window._amandlaSessionId = sessionId;
});
```

---

## Part 3 — Main Process IPC Handlers (main.js)

```javascript
// In main.js — handle IPC calls from preload
const { ipcMain } = require('electron');

/**
 * Handles connection requests from renderer windows.
 * Connects them to the backend WebSocket session.
 */
ipcMain.handle('amandla-connect', async (event, { sessionId, role }) => {
    try {
        // The main process manages the WebSocket connection
        await connectToBackend(sessionId, role, event.sender);
        return { success: true };
    } catch (error) {
        // Log real error, return safe message to renderer
        console.error('Connection failed:', error);
        return { success: false, error: 'Could not connect to communication service' };
    }
});

/**
 * Handles messages from renderer and forwards to backend.
 */
ipcMain.handle('amandla-send', async (event, message) => {
    try {
        const response = await sendToBackend(message);
        return response;
    } catch (error) {
        console.error('Send failed:', error);
        return { success: false, error: 'Message could not be sent' };
    }
});

/**
 * Sends a message to a specific renderer window.
 * Called when the backend sends data that needs to go to a window.
 *
 * @param {BrowserWindow} win - Target window
 * @param {object} message - Message to send
 */
function sendToRenderer(win, message) {
    if (win && !win.isDestroyed()) {
        win.webContents.send('amandla-message', message);
    }
}
```

---

## Part 4 — How Renderers Use the Bridge

```javascript
// In hearing.js, deaf.js, or rights.js

// ✅ Correct — use the bridge
window.amandla.send({ type: 'text', text: inputText, request_id: generateId() });

window.amandla.onMessage((message) => {
    if (message.type === 'signs') {
        window.avatarPlaySigns(message.signs, message.original_text);
    }
});

// ❌ Wrong — never do this in renderers
fetch('http://localhost:8000/speech', { ... });  // Direct fetch bypasses the bridge
require('fs').readFileSync('/etc/passwd');        // Node access — BLOCKED by contextIsolation
const ws = new WebSocket('ws://...');            // Direct WebSocket — bypasses session management
```

---

## Part 5 — Session ID Flow

The main process generates the session ID once and sends it to all windows:

```javascript
// main.js — generate session ID once
const sessionId = `amandla-${Date.now()}-${crypto.randomBytes(4).toString('hex')}`;

// When each window is ready, send the session ID via IPC
hearingWindow.webContents.once('did-finish-load', () => {
    hearingWindow.webContents.send('session-id', sessionId);
});

deafWindow.webContents.once('did-finish-load', () => {
    deafWindow.webContents.send('session-id', sessionId);
});
```

---

## Part 6 — Common IPC Bugs and Fixes

| Bug | Cause | Fix |
|-----|-------|-----|
| `window.amandla is undefined` | Preload script not found | Check `preload` path in webPreferences |
| Messages not received | Listener not registered | Call `window.amandla.onMessage()` before connecting |
| Session ID undefined in renderer | `session-id` IPC event not handled | Add `ipcRenderer.once('session-id', ...)` in preload |
| `ipcRenderer is not defined` | Using ipcRenderer in renderer (not preload) | Move IPC code to preload.js only |
| Memory leak — listener accumulates | Never removing old listeners | Call `window.amandla.offMessage()` on cleanup |

---

## Environment Notes

**In Claude Code (terminal):**
```bash
# Check Electron security settings
grep -rn "nodeIntegration\|contextIsolation" src/main.js

# Check for direct fetch() calls in renderers (security violation)
grep -rn "fetch(" src/windows/ --include="*.js"

# Check for require() in renderers (security violation)  
grep -rn "require(" src/windows/ --include="*.js" | grep -v "//.*require"
```

**In Claude.ai (browser):** Show the full preload bridge pattern when adding any new capability.
Never add a new `window.amandla.*` method without reviewing: is this safe? Does it validate inputs?
