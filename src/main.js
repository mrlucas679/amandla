const { app, BrowserWindow, ipcMain, screen } = require('electron')
const path = require('path')

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
      webSecurity: false,  // Allow CDN scripts (Three.js) — dev only
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
      webSecurity: false,  // Allow CDN scripts (Three.js) — dev only
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
      if (permission === 'media') callback(true)
      else callback(false)
    })
  }
  allowMedia(hearingWin.webContents)
  allowMedia(deafWin.webContents)
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
      webSecurity: false,  // Allow CDN scripts (jsPDF) — dev only
    }
  })
  rightsWin.loadFile('src/windows/rights/index.html')
  rightsWin.on('closed', () => { rightsWin = null })
})

// IPC: Allow renderer to ask for the session ID at any time
ipcMain.handle('get-session-id', () => SESSION_ID)

app.whenReady().then(createWindows)
app.on('window-all-closed', () => app.quit())
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindows()
})
