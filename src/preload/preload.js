const { contextBridge, ipcRenderer } = require('electron')

let ws = null
let currentSessionId = null
let currentRole = null
let messageCallback = null
let connectionCallback = null
let reconnectTimer = null

// ── Pending request system for promise-based WS calls ──────────────────────
// Each request gets a unique ID. When the backend responds with the same
// request_id, the corresponding promise is resolved.
let _requestId = 0
const _pending = new Map()
const REQUEST_TIMEOUT_MS = 60000 // 60 seconds — Whisper CPU transcription can take up to 45s

/**
 * Send a payload via WebSocket and return a Promise that resolves when the
 * backend responds with a matching request_id.
 *
 * @param {Object} payload - The message object to send.
 * @returns {Promise<Object>} - Resolves with the response data, rejects on timeout or error.
 */
function _sendRequest(payload) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    return Promise.reject(new Error('Not connected to backend'))
  }
  _requestId++
  const id = _requestId
  payload.request_id = id

  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      _pending.delete(id)
      reject(new Error('Request timed out'))
    }, REQUEST_TIMEOUT_MS)

    _pending.set(id, { resolve, reject, timer })
    ws.send(JSON.stringify(payload))
  })
}

function connect(sessionId, role) {
  currentSessionId = sessionId
  currentRole = role

  if (ws) {
    ws.close()
let reconnectTimer = null
let _reconnectDelay = 1500 // starts at 1.5s, doubles each attempt, caps at 15s
const _RECONNECT_MAX_MS = 15000

// ...existing code...

  ws.onopen = () => {
    console.log(`[Preload] WebSocket connected: session=${sessionId} role=${role}`)
    if (connectionCallback) connectionCallback(true)
    _reconnectDelay = 1500 // reset backoff on successful connect
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)

      // Check if this is a response to a pending request
      if (data.request_id && _pending.has(data.request_id)) {
        const req = _pending.get(data.request_id)
        clearTimeout(req.timer)
        _pending.delete(data.request_id)
        if (data.error) {
          req.reject(new Error(data.error))
        } else {
          req.resolve(data)
        }
        return // Don't pass to messageCallback — it's a request/response, not a broadcast
      }

      // Normal broadcast message — pass to the registered handler
      if (messageCallback) messageCallback(data)
    } catch (e) {
      console.error('[Preload] Message parse error:', e)
    }
  }

  ws.onclose = () => {
    console.log('[Preload] WebSocket closed — reconnecting in 1.5s...')
    if (connectionCallback) connectionCallback(false)
    // Reject all pending requests on disconnect
    for (const [id, req] of _pending) {
      clearTimeout(req.timer)
      req.reject(new Error('WebSocket disconnected'))
    }
    _pending.clear()
    // Auto-reconnect with exponential backoff
    reconnectTimer = setTimeout(() => {
      if (currentSessionId && currentRole) {
        connect(currentSessionId, currentRole)
      }
    }, _reconnectDelay)
    // Double the delay for next attempt, cap at max
    _reconnectDelay = Math.min(_reconnectDelay * 2, _RECONNECT_MAX_MS)
  }

  ws.onerror = (err) => {
    console.error('[Preload] WebSocket error:', err)
  }
}

contextBridge.exposeInMainWorld('amandla', {
  // Connect to WebSocket with session ID and role
  connect: (sessionId, role) => connect(sessionId, role),

  // Send a message to the other window (fire-and-forget)
  send: (message) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message))
    } else {
      console.warn('[Preload] Cannot send — WebSocket not open')
    }
  },

  // Register a callback for incoming messages
  onMessage: (callback) => { messageCallback = callback },

  // Register a callback for connection state changes (true=connected, false=disconnected)
  onConnectionChange: (callback) => { connectionCallback = callback },

  // Disconnect cleanly
  disconnect: () => {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    currentSessionId = null
    currentRole = null
    if (ws) ws.close()
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
})

// Receive session ID and role pushed from main process
ipcRenderer.on('session-id', (event, id) => {
  currentSessionId = id
})
ipcRenderer.on('role', (event, role) => {
  currentRole = role
  // Auto-connect once we have both values
  if (currentSessionId && currentRole) {
    connect(currentSessionId, currentRole)
  }
})
