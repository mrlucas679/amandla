const { contextBridge, ipcRenderer } = require('electron')

// ── Module-level WebSocket state ─────────────────────────────────────────────
let ws = null
let currentSessionId = null
let currentRole = null
let currentSecret = null
let messageCallback = null
let connectionCallback = null
let reconnectTimer = null

// Reconnect backoff: starts at 1.5 s, doubles each attempt, caps at 15 s
let _reconnectDelay = 1500
const _RECONNECT_MAX_MS = 15000

// ── Pending request system for promise-based WS calls ──────────────────────
// Each request gets a unique numeric ID. When the backend responds with the
// same request_id the corresponding promise is resolved.
let _requestId = 0
const _pending = new Map()
// 60 s timeout — Whisper CPU transcription can take up to 45 s on slower machines
const REQUEST_TIMEOUT_MS = 60000
// Maximum outgoing message size (1 MB) — protects against accidental giant payloads
const _MAX_SEND_BYTES = 1_000_000

/**
 * Send a payload via WebSocket and return a Promise that resolves when the
 * backend responds with a matching request_id.
 *
 * @param {Object} payload - The message object to send (must not have request_id set yet).
 * @returns {Promise<Object>} Resolves with the response data, rejects on timeout or error.
 */
function _sendRequest(payload) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    return Promise.reject(new Error('Not connected to backend'))
  }
  _requestId++
  const id = _requestId
  payload.request_id = id

  return new Promise((resolve, reject) => {
    // Auto-reject if the backend does not respond within the timeout window
    const timer = setTimeout(() => {
      _pending.delete(id)
      reject(new Error('Request timed out'))
    }, REQUEST_TIMEOUT_MS)

    _pending.set(id, { resolve, reject, timer })
    ws.send(JSON.stringify(payload))
  })
}

/**
 * Open (or reopen) a WebSocket connection to the backend for the given session
 * and role. Called automatically by the IPC handlers below, and can also be
 * called directly from page scripts.
 *
 * Includes a duplicate-connection guard: if a socket is already CONNECTING or
 * OPEN for the same session + role, the call is a no-op.
 *
 * @param {string} sessionId - The shared session identifier (from main process).
 * @param {string} role      - Either "hearing", "deaf", or "rights".
 * @param {string} secret    - Session secret token for backend authentication.
 */
function connect(sessionId, role, secret) {
  currentSessionId = sessionId
  currentRole = role
  if (secret) currentSecret = secret

  // Guard: don't open a second socket if one is already live for this session + role
  const sessionKey = sessionId + '/' + role
  if (
    ws &&
    (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN) &&
    ws._amandlaSession === sessionKey
  ) {
    console.log('[Preload] Already connected — skipping duplicate connect()')
    return
  }

  // Clean up any existing (stale) socket before creating a new one
  if (ws) {
    ws.onclose = null // prevent the onclose handler from triggering a reconnect loop
    ws.close()
  }

  const url = `ws://localhost:8000/ws/${sessionId}/${role}?token=${encodeURIComponent(currentSecret || '')}`
  console.log(`[Preload] Connecting to ${url}`)
  ws = new WebSocket(url)
  // Tag the socket so we can detect duplicates above
  ws._amandlaSession = sessionKey

  // ── Event: connection established ────────────────────────────────────────
  ws.onopen = () => {
    console.log(`[Preload] WebSocket connected: session=${sessionId} role=${role}`)
    _reconnectDelay = 1500 // reset exponential backoff on successful connect
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (connectionCallback) connectionCallback(true)
  }

  // ── Event: message received ──────────────────────────────────────────────
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)

      // If this is a response to a pending promise-based request, resolve it
      if (data.request_id && _pending.has(data.request_id)) {
        const req = _pending.get(data.request_id)
        clearTimeout(req.timer)
        _pending.delete(data.request_id)
        if (data.error) {
          req.reject(new Error(data.error))
        } else {
          req.resolve(data)
        }
        // Do NOT pass request/response messages to the broadcast handler
        return
      }

      // Normal broadcast message — forward to the registered page handler
      if (messageCallback) messageCallback(data)
    } catch (e) {
      console.error('[Preload] Message parse error:', e)
    }
  }

  // ── Event: connection closed ─────────────────────────────────────────────
  ws.onclose = () => {
    console.log(`[Preload] WebSocket closed — reconnecting in ${_reconnectDelay}ms…`)
    if (connectionCallback) connectionCallback(false)
    // Reject all in-flight requests so callers don't hang forever
    for (const [, req] of _pending) {
      clearTimeout(req.timer)
      req.reject(new Error('WebSocket disconnected'))
    }
    _pending.clear()
    // Schedule an automatic reconnect with exponential backoff
    reconnectTimer = setTimeout(() => {
      if (currentSessionId && currentRole) {
        connect(currentSessionId, currentRole, currentSecret)
      }
    }, _reconnectDelay)
    // Double the delay for the next attempt, capped at the maximum
    _reconnectDelay = Math.min(_reconnectDelay * 2, _RECONNECT_MAX_MS)
  }

  // ── Event: socket-level error ────────────────────────────────────────────
  ws.onerror = (err) => {
    console.error('[Preload] WebSocket error:', err)
  }
}

contextBridge.exposeInMainWorld('amandla', {
  // Connect to WebSocket with session ID, role, and auth secret
  connect: (sessionId, role, secret) => connect(sessionId, role, secret),

  /**
   * Send a fire-and-forget JSON message to the backend via WebSocket.
   *
   * @param {Object} message - Payload to send. Must be JSON-serialisable.
   * @returns {boolean} true if sent, false if not connected or message too large.
   */
  send: (message) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      const payload = JSON.stringify(message)
      // Reject payloads that are unreasonably large (protects bandwidth + backend)
      if (payload.length > _MAX_SEND_BYTES) {
        console.warn(`[Preload] Message too large (${payload.length} bytes) — rejected`)
        return false
      }
      ws.send(payload)
      return true
    } else {
      console.warn('[Preload] Cannot send — WebSocket not open')
      return false
    }
  },

  // Register a callback for incoming messages
  onMessage: (callback) => { messageCallback = callback },

  // Register a callback for connection state changes (true=connected, false=disconnected)
  onConnectionChange: (callback) => { connectionCallback = callback },

  // Disconnect cleanly — stops reconnect loop
  disconnect: () => {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    currentSessionId = null
    currentRole = null
    currentSecret = null
    if (ws) {
      ws.onclose = null // prevent onclose from scheduling a reconnect
      ws.close()
    }
  },

  // FEAT-6: Register a callback for global emergency shortcut (Ctrl+E)
  onEmergencyShortcut: (callback) => {
    ipcRenderer.on('emergency-trigger', () => {
      if (typeof callback === 'function') callback()
    })
  },

  // Ask main process to open RIGHTS window
  openRights: () => ipcRenderer.invoke('open-rights'),

  // Ask main process for session ID at any time
  getSessionId: () => ipcRenderer.invoke('get-session-id'),

  /**
   * Upload speech audio via WebSocket (replaces direct fetch to /speech).
   * Converts a Blob to base64, sends it, and waits for transcription result.
   *
   * @param {Blob} audioBlob - The recorded audio blob.
   * @param {string} mimeType - MIME type of the audio (e.g. "audio/webm").
   * @returns {Promise<Object>} - Resolves with { text, language, confidence }.
   */
  uploadSpeech: (audioBlob, mimeType) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return Promise.reject(new Error('Not connected to backend'))
    }
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => {
        const base64 = reader.result.split(',')[1] // strip data:...;base64, prefix
        _sendRequest({
          type: 'speech_upload',
          audio_b64: base64,
          mime_type: mimeType || 'audio/webm',
          sender: currentRole,
          timestamp: Date.now()
        }).then(resolve).catch(reject)
      }
      reader.onerror = () => reject(new Error('Failed to read audio'))
      reader.readAsDataURL(audioBlob)
    })
  },

  /**
   * Request backend status via WebSocket (replaces direct fetch to /api/status).
   *
   * @returns {Promise<Object>} - Resolves with { qwen, whisper, sessions }.
   */
  requestStatus: () => _sendRequest({ type: 'status_request' }),

  /**
   * Request rights incident analysis via WebSocket (replaces direct fetch to /rights/analyze).
   *
   * @param {string} description - The incident description.
   * @param {string} incidentType - The type of discrimination.
   * @returns {Promise<Object>} - Resolves with the analysis result.
   */
  analyzeRights: (description, incidentType) => _sendRequest({
    type: 'rights_analyze',
    description: description,
    incident_type: incidentType || 'workplace'
  }),

  /**
   * Request rights complaint letter via WebSocket (replaces direct fetch to /rights/letter).
   *
   * @param {Object} details - Letter details: description, user_name, employer_name, etc.
   * @returns {Promise<Object>} - Resolves with { letter, laws_cited }.
   */
  generateLetter: (details) => _sendRequest({
    type: 'rights_letter',
    ...(details || {})
  }),

  /**
   * Request conversation history for the current session via WebSocket.
   * FEAT-3: Retrieves stored messages from the SQLite database.
   *
   * @param {string} [sessionId] - Optional session ID override (defaults to current).
   * @param {number} [limit] - Max messages to return (default 100).
   * @returns {Promise<Object>} - Resolves with { session_id, messages: [...] }.
   */
  requestHistory: (sessionId, limit) => _sendRequest({
    type: 'history_request',
    session_id: sessionId || undefined,
    limit: limit || 100
  }),

  /**
   * List all sessions with message counts via WebSocket.
   * FEAT-3: Returns session summaries from the SQLite database.
   *
   * @returns {Promise<Object>} - Resolves with { sessions: [...] }.
   */
  listSessions: () => _sendRequest({
    type: 'history_request',
    list_sessions: true
  }),
})

// ── IPC: receive session ID, secret, and role from the main process ──────────
// These arrive once per window load (sent from main.js did-finish-load).
// We auto-connect as soon as ALL THREE values are known, regardless of which
// arrives first — this fixes the race condition where role arrives before
// session-id (or vice-versa).

ipcRenderer.on('session-id', (_event, id) => {
  currentSessionId = id
  // If secret and role were already received, we have everything — connect now
  if (currentSessionId && currentSecret && currentRole) {
    connect(currentSessionId, currentRole, currentSecret)
  }
})

ipcRenderer.on('session-secret', (_event, secret) => {
  currentSecret = secret
  // If session-id and role were already received, we have everything — connect now
  if (currentSessionId && currentSecret && currentRole) {
    connect(currentSessionId, currentRole, currentSecret)
  }
})

ipcRenderer.on('role', (_event, role) => {
  currentRole = role
  // If session-id and secret were already received, we have everything — connect now
  if (currentSessionId && currentSecret && currentRole) {
    connect(currentSessionId, currentRole, currentSecret)
  }
})
