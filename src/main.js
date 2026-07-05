const { app, BrowserWindow, ipcMain, screen, globalShortcut, dialog } = require('electron')
const { spawn } = require('child_process')
const http = require('http')
const path = require('path')
const crypto = require('crypto')

// ── BUILD-4: Auto-update ──────────────────────────────────────────
// Uses electron-updater with GitHub Releases. In development mode
// (not packaged), autoUpdater is a no-op to avoid errors.
let autoUpdater = null
try {
  autoUpdater = require('electron-updater').autoUpdater
  autoUpdater.autoDownload = false  // prompt the user first
} catch (e) {
  // electron-updater not available in dev mode — that's fine
  console.log('[Main] Auto-updater not available (dev mode)')
}

// ── ARCHITECTURE NOTE ─────────────────────────────────────────────
// AMANDLA uses two BrowserWindow instances positioned side-by-side
// to create a split-screen effect (hearing left, deaf right).
// This is intentional — NOT a single webview with split layout.
// Communication between windows goes through the backend WebSocket,
// never through Electron IPC between renderer processes.
// The preload bridge (preload.js) is the ONLY way renderers talk
// to the backend — no direct fetch/XHR from renderer code.
// ──────────────────────────────────────────────────────────────────

// Content-Security-Policy — restricts what scripts and connections are allowed.
// style-src includes fonts.googleapis.com so Google Fonts <link> tags work.
// font-src includes fonts.gstatic.com so the actual font files can be downloaded.
// ISSUE 1 FIX: added https://cdn.jsdelivr.net to connect-src so MediaPipe
// can download its WASM binary and model files from the jsdelivr CDN at runtime.
const CSP = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; connect-src 'self' ws://localhost:8000 http://localhost:8000 https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data:; font-src 'self' https://fonts.gstatic.com;"

let hearingWin = null
let deafWin = null
let rightsWin = null

// Generate a cryptographically secure session ID once when the app starts.
// 32 random bytes = 256 bits of entropy — safe even if the backend is ever
// exposed on a network. Both windows get the same ID so they join the same
// WebSocket room. Format: 'amandla-' + 43-char URL-safe base64 token.
const SESSION_ID = 'amandla-' + crypto.randomBytes(32).toString('base64url')

// Session secret fetched from the backend at startup.
// Required by every WebSocket connection as a ?token= query parameter.
let SESSION_SECRET = null

// ── BUILD-3: Backend process management ───────────────────────────
// In packaged builds, Electron spawns the bundled backend binary.
// In dev mode, the backend is started externally by concurrently/npm.
let _backendProcess = null

// Maximum time to wait for the backend health check (milliseconds)
const BACKEND_STARTUP_TIMEOUT_MS = 30000
// Interval between health check retries (milliseconds)
const BACKEND_POLL_INTERVAL_MS = 500

/**
 * Start the bundled backend binary in packaged builds.
 * In dev mode (not packaged), this is a no-op — the backend is started
 * by `npm run backend` via concurrently.
 */
function _startBackend() {
  if (!app.isPackaged) {
    console.log('[Main] Dev mode — backend started externally via npm')
    return
  }

  const backendDir = path.join(process.resourcesPath, 'backend')
  const exeName = process.platform === 'win32' ? 'amandla-backend.exe' : 'amandla-backend'
  const exePath = path.join(backendDir, exeName)

  console.log('[Main] Starting bundled backend:', exePath)

  _backendProcess = spawn(exePath, [], {
    cwd: backendDir,
    stdio: ['ignore', 'pipe', 'pipe'],
    // Detach on non-Windows so the process can outlive the spawner briefly
    detached: process.platform !== 'win32',
  })

  _backendProcess.stdout.on('data', (data) => {
    console.log('[Backend]', data.toString().trim())
  })
  _backendProcess.stderr.on('data', (data) => {
    console.error('[Backend]', data.toString().trim())
  })
  _backendProcess.on('exit', (code) => {
    console.log('[Main] Backend process exited with code', code)
    _backendProcess = null
  })
  _backendProcess.on('error', (err) => {
    console.error('[Main] Failed to start backend:', err.message)
    _backendProcess = null
  })
}

/**
 * Poll the backend /health endpoint until it responds or timeout.
 * Used in packaged builds where we spawn the backend ourselves.
 *
 * @returns {Promise<void>} Resolves when backend is healthy, rejects on timeout.
 */
function _waitForBackend() {
  return new Promise((resolve, reject) => {
    const startTime = Date.now()

    function poll() {
      const elapsed = Date.now() - startTime
      if (elapsed > BACKEND_STARTUP_TIMEOUT_MS) {
        reject(new Error('Backend did not start within ' + (BACKEND_STARTUP_TIMEOUT_MS / 1000) + 's'))
        return
      }

      const req = http.get('http://localhost:8000/health', { timeout: 2000 }, (res) => {
        res.resume() // drain
        if (res.statusCode === 200) {
          console.log('[Main] Backend health check passed (' + elapsed + 'ms)')
          resolve()
        } else {
          setTimeout(poll, BACKEND_POLL_INTERVAL_MS)
        }
      })
      req.on('error', () => {
        setTimeout(poll, BACKEND_POLL_INTERVAL_MS)
      })
      req.on('timeout', () => {
        req.destroy()
        setTimeout(poll, BACKEND_POLL_INTERVAL_MS)
      })
    }

    poll()
  })
}

/**
 * Gracefully stop the backend process if we spawned it.
 * Sends SIGTERM first, then forces kill after 5 seconds.
 */
function _stopBackend() {
  if (!_backendProcess) return

  console.log('[Main] Stopping backend process...')
  const FORCE_KILL_TIMEOUT_MS = 5000

  try {
    if (process.platform === 'win32') {
      // Windows: taskkill is needed for clean child process termination
      spawn('taskkill', ['/pid', String(_backendProcess.pid), '/f', '/t'])
    } else {
      _backendProcess.kill('SIGTERM')
    }
  } catch (err) {
    console.error('[Main] Error stopping backend:', err.message)
  }

  // Force kill if still alive after timeout
  const forceTimer = setTimeout(() => {
    if (_backendProcess) {
      try {
        _backendProcess.kill('SIGKILL')
      } catch (e) { /* already dead */ }
    }
  }, FORCE_KILL_TIMEOUT_MS)

  _backendProcess.on('exit', () => {
    clearTimeout(forceTimer)
    _backendProcess = null
    console.log('[Main] Backend stopped')
  })
}

/**
 * Fetch the session secret from the backend's /auth/session-secret endpoint.
 * Called once after app.whenReady() and the backend health check has passed.
 *
 * @returns {Promise<string>} The session secret token string.
 */
async function fetchSessionSecret() {
  return new Promise((resolve, reject) => {
    http.get('http://localhost:8000/auth/session-secret', (res) => {
      let body = ''
      res.on('data', (chunk) => { body += chunk })
      res.on('end', () => {
        try {
          const data = JSON.parse(body)
          resolve(data.session_secret)
        } catch (err) {
          reject(new Error('Failed to parse session secret response'))
        }
      })
    }).on('error', (err) => reject(err))
  })
}

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
  // Pass the session ID and secret to the window once it finishes loading
  hearingWin.webContents.on('did-finish-load', () => {
    hearingWin.webContents.send('session-id', SESSION_ID)
    hearingWin.webContents.send('session-secret', SESSION_SECRET)
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
    deafWin.webContents.send('session-secret', SESSION_SECRET)
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
  // Send session ID, secret, and role to rights window so it can connect via WebSocket
  rightsWin.webContents.on('did-finish-load', () => {
    rightsWin.webContents.send('session-id', SESSION_ID)
    rightsWin.webContents.send('session-secret', SESSION_SECRET)
    rightsWin.webContents.send('role', 'rights')
  })
  _applyCSP(rightsWin)
  rightsWin.on('closed', () => { rightsWin = null })
})

// IPC: Allow renderer to ask for the session ID at any time
ipcMain.handle('get-session-id', () => SESSION_ID)

/**
 * Set up electron-updater event handlers for auto-update flow.
 * Shows a dialog when an update is available, downloads it on confirmation,
 * and installs + restarts when the download is complete.
 */
function _setupAutoUpdater() {
  if (!autoUpdater) return

  autoUpdater.on('update-available', (info) => {
    const version = info.version || 'new version'
    dialog.showMessageBox({
      type: 'info',
      title: 'Update Available',
      message: `AMANDLA v${version} is available. Download now?`,
      buttons: ['Download', 'Later'],
      defaultId: 0,
    }).then((result) => {
      if (result.response === 0) autoUpdater.downloadUpdate()
    })
  })

  autoUpdater.on('update-downloaded', () => {
    dialog.showMessageBox({
      type: 'info',
      title: 'Update Ready',
      message: 'Update downloaded. AMANDLA will restart to install it.',
      buttons: ['Restart Now', 'Later'],
      defaultId: 0,
    }).then((result) => {
      if (result.response === 0) autoUpdater.quitAndInstall()
    })
  })

  autoUpdater.on('error', (err) => {
    console.error('[AutoUpdater] Error checking for updates:', err.message)
  })
}

/**
 * Check if Ollama is running by hitting its /api/tags endpoint.
 * Shows a dialog if Ollama is not reachable so the user knows
 * AI features will be limited.
 *
 * @returns {Promise<void>}
 */
async function _checkOllamaRunning() {
  return new Promise((resolve) => {
    const req = http.get('http://localhost:11434/api/tags', { timeout: 3000 }, (res) => {
      // Any response means Ollama is running
      res.resume() // drain the response
      console.log('[Main] Ollama is running')
      resolve()
    })
    req.on('error', () => {
      dialog.showMessageBox({
        type: 'warning',
        title: 'Ollama Not Running',
        message: 'Ollama is not running. AI features (sign recognition, translation) will be limited.\n\nRun "ollama serve" in a terminal for full functionality.',
        buttons: ['Continue Anyway'],
        defaultId: 0,
      }).then(() => resolve())
    })
    req.on('timeout', () => {
      req.destroy()
    })
  })
}

app.whenReady().then(async () => {
  // ── BUILD-3: Start the bundled backend in packaged mode ──────────────
  // In dev mode, concurrently + wait-on handles backend startup.
  // In packaged mode, we spawn the binary ourselves and wait for health.
  if (app.isPackaged) {
    _startBackend()
    try {
      await _waitForBackend()
      console.log('[Main] Bundled backend is ready')
    } catch (err) {
      console.error('[Main] Backend startup failed:', err.message)
      dialog.showErrorBox(
        'Backend Failed to Start',
        'The AMANDLA backend did not start in time.\n\n' +
        'Please try restarting the application.\n' +
        'If the problem persists, check the logs directory.'
      )
    }
  }

  // BUILD-5: Check if Ollama is running before creating windows
  await _checkOllamaRunning()

  // Fetch the session secret from the backend (which is already running via
  // concurrently + wait-on in dev, or spawned above in packaged mode).
  // This token is required for all WebSocket connections.
  try {
    SESSION_SECRET = await fetchSessionSecret()
    console.log('[Main] Session secret acquired from backend')
  } catch (err) {
    console.error('[Main] Failed to fetch session secret — WebSocket auth will fail:', err.message)
  }
  createWindows()

  // ── FEAT-6: Global emergency shortcut ──────────────────────────────────
  // Ctrl+E (or Cmd+E on macOS) triggers emergency from any window.
  // Sends an IPC message to both hearing and deaf renderers so they show
  // the emergency overlay. The deaf window also sends a WS emergency message
  // to the backend so the hearing user is alerted.
  globalShortcut.register('CommandOrControl+E', () => {
    console.log('[Main] Emergency shortcut triggered (Ctrl+E)')
    if (hearingWin && !hearingWin.isDestroyed()) {
      hearingWin.webContents.send('emergency-trigger')
    }
    if (deafWin && !deafWin.isDestroyed()) {
      deafWin.webContents.send('emergency-trigger')
    }
  })

  // ── BUILD-4: Check for updates after windows are created ──────────────
  // Only runs in packaged builds — development mode skips this entirely.
  if (autoUpdater && app.isPackaged) {
    _setupAutoUpdater()
    // Check after a short delay so the UI has time to render
    setTimeout(() => { autoUpdater.checkForUpdates() }, 5000)
  }
})
app.on('will-quit', () => {
  // Unregister all shortcuts when the app is about to quit
  globalShortcut.unregisterAll()
  // BUILD-3: Stop the backend process if we spawned it
  _stopBackend()
})
app.on('window-all-closed', () => {
  // BUILD-3: Stop backend before quitting
  _stopBackend()
  app.quit()
})
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindows()
})
