const { app, BrowserWindow, ipcMain, screen } = require('electron')
const path = require('path')

// ── ARCHITECTURE NOTE ─────────────────────────────────────────────
// AMANDLA uses two BrowserWindow instances positioned side-by-side
// to create a split-screen effect (hearing left, deaf right).
// This is intentional — NOT a single webview with split layout.
// Communication between windows goes through the backend WebSocket,
// never through Electron IPC between renderer processes.
// The preload bridge (preload.js) is the ONLY way renderers talk
// to the backend — no direct fetch/XHR from renderer code.
// ──────────────────────────────────────────────────────────────────

// Content-Security-Policy — restricts what scripts and connections are allowed
const CSP = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; connect-src 'self' ws://localhost:8000 http://localhost:8000; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self';"

let hearingWin = null
let deafWin = null
let rightsWin = null

// Generate a session ID once when the app starts
// Both windows get the same ID so they join the same WebSocket room
const SESSION_ID = 'amandla-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8)

function createWindows() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize
  const halfWidth = Math.floor(width / 2)

  // --- Window 1: Hearing person (left side) ---
  hearingWin = new BrowserWindow({
    x: 0,
    y: 0,
    width: halfWidth,
    height: height,
    title: 'AMANDLA — Hearing View',
    backgroundColor: '#0D0D0D',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload/preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    }
  })
  hearingWin.loadFile('src/windows/hearing/index.html')
  // Pass the session ID to the window once it finishes loading
  hearingWin.webContents.on('did-finish-load', () => {
    hearingWin.webContents.send('session-id', SESSION_ID)
    hearingWin.webContents.send('role', 'hearing')
  })

  // --- Window 2: Deaf / signer (right side) ---
  deafWin = new BrowserWindow({
    x: halfWidth,
    y: 0,
    width: halfWidth,
    height: height,
    title: 'AMANDLA — Signer View',
    backgroundColor: '#0D0D0D',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload/preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      experimentalFeatures: true,     // Required for SharedArrayBuffer (MediaPipe WASM threads)
      enableBlinkFeatures: 'SharedArrayBuffer',  // MediaPipe WASM multi-hand needs this
    }
  })
  deafWin.loadFile('src/windows/deaf/index.html')
  deafWin.webContents.on('did-finish-load', () => {
    deafWin.webContents.send('session-id', SESSION_ID)
    deafWin.webContents.send('role', 'deaf')
  })

  // Camera and microphone permissions — both windows
  const allowMedia = (webContents) => {
    webContents.session.setPermissionRequestHandler((wc, permission, callback) => {
      // Allow camera, microphone and generic media requests
      const allowed = ['media', 'camera', 'microphone', 'video-capture', 'audio-capture']
      callback(allowed.includes(permission))
    })
    // Also allow getUserMedia checks (Electron 20+)
    webContents.session.setPermissionCheckHandler((wc, permission) => {
      const allowed = ['media', 'camera', 'microphone', 'video-capture', 'audio-capture']
      return allowed.includes(permission)
    })
  }
  allowMedia(hearingWin.webContents)
  allowMedia(deafWin.webContents)

  // Apply Content-Security-Policy headers to all windows
  _applyCSP(hearingWin)
  _applyCSP(deafWin)
}

/**
 * Apply Content-Security-Policy headers to a BrowserWindow.
 * Restricts script sources to self and approved CDNs only.
 */
function _applyCSP(win) {
  win.webContents.session.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [CSP]
      }
    })
  })
}

// IPC: Open RIGHTS window from hearing window button
ipcMain.handle('open-rights', () => {
  if (rightsWin && !rightsWin.isDestroyed()) {
    rightsWin.focus()
    return
  }
  rightsWin = new BrowserWindow({
    width: 900,
    height: 800,
    title: 'AMANDLA — Know Your Rights',
    backgroundColor: '#0D0D0D',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload/preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    }
  })
  rightsWin.loadFile('src/windows/rights/index.html')
  // Send session ID and role to rights window so it can connect via WebSocket
  rightsWin.webContents.on('did-finish-load', () => {
    rightsWin.webContents.send('session-id', SESSION_ID)
    rightsWin.webContents.send('role', 'rights')
  })
  _applyCSP(rightsWin)
  rightsWin.on('closed', () => { rightsWin = null })
})

// IPC: Allow renderer to ask for the session ID at any time
ipcMain.handle('get-session-id', () => SESSION_ID)

app.whenReady().then(createWindows)
app.on('window-all-closed', () => app.quit())
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindows()
})
