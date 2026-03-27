const { contextBridge, ipcRenderer } = require('electron')

let ws = null
let currentSessionId = null
let currentRole = null
let messageCallback = null
let connectionCallback = null
let reconnectTimer = null

function connect(sessionId, role) {
  currentSessionId = sessionId
  currentRole = role

  if (ws) {
    ws.close()
  }

  ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}/${role}`)

  ws.onopen = () => {
    console.log(`[AMANDLA] WebSocket connected: session=${sessionId} role=${role}`)
    if (connectionCallback) connectionCallback(true)
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (messageCallback) messageCallback(data)
    } catch (e) {
      console.error('[AMANDLA] Message parse error:', e)
    }
  }

  ws.onclose = () => {
    console.log('[AMANDLA] WebSocket closed — reconnecting in 1.5s...')
    if (connectionCallback) connectionCallback(false)
    // Auto-reconnect with backoff
    reconnectTimer = setTimeout(() => {
      if (currentSessionId && currentRole) {
        connect(currentSessionId, currentRole)
      }
    }, 1500)
  }

  ws.onerror = (err) => {
    console.error('[AMANDLA] WebSocket error:', err)
  }
}

contextBridge.exposeInMainWorld('amandla', {
  // Connect to WebSocket with session ID and role
  connect: (sessionId, role) => connect(sessionId, role),

  // Send a message to the other window
  send: (message) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message))
    } else {
      console.warn('[AMANDLA] Cannot send — WebSocket not open')
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
