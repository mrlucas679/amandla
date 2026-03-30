/**
 * deaf.js — JavaScript for the AMANDLA Deaf window.
 *
 * Handles: startup overlay, WebSocket connection, incoming sign messages,
 * avatar initialisation, SASL text input, quick-sign buttons, category tabs,
 * turn indicator, emergency overlay, MediaPipe camera, status polling,
 * mode toggle, and assist-mode phrase sending.
 */

// ── DOM REFS ──────────────────────────────────────────────
const overlay       = document.getElementById('startup-overlay')
const startBtn      = document.getElementById('start-btn')
const connStatus    = document.getElementById('conn-status')
const statusDot     = document.getElementById('status-dot')
const sentenceEl    = document.getElementById('sentence-display')
const glossEl       = document.getElementById('gloss-display')
const turnEl        = document.getElementById('turn-indicator')
const offlineBanner = document.getElementById('offline-banner')
const offlineDismiss = document.getElementById('offline-dismiss')

// Track whether user dismissed the banner this poll cycle
let offlineDismissed = false
offlineDismiss.addEventListener('click', function () {
  offlineBanner.classList.remove('visible')
  offlineDismissed = true
})
const saslInput     = document.getElementById('sasl-input')
const saslSendBtn   = document.getElementById('sasl-send-btn')
const saslStatus    = document.getElementById('sasl-send-status')
const signProgressEl = document.getElementById('sign-progress')
const replayBtn      = document.getElementById('replay-btn')

// UX-3: Store last sign sequence for replay
let lastSigns = null
let lastSignText = ''

replayBtn.addEventListener('click', function () {
  if (lastSigns && window.avatarPlaySigns) {
    window.avatarPlaySigns(lastSigns, lastSignText)
  }
})

// ── STARTUP ───────────────────────────────────────────────
startBtn.addEventListener('click', function () {
  overlay.style.display = 'none'
  try {
    const u = new SpeechSynthesisUtterance(' ')
    u.volume = 0
    window.speechSynthesis.speak(u)
  } catch (e) { /* ignore */ }
  saslInput.focus()
})

// ── AVATAR INIT ───────────────────────────────────────────

/** Initialise the Three.js avatar once the library and module are loaded. */
function tryInitAvatar() {
  if (typeof THREE !== 'undefined' && window.AmandlaAvatar) {
    window.AmandlaAvatar.initAvatar('avatar-canvas')
    // UX-2: Wire sign progress callback to show "Signing 2 of 5"
    window.AmandlaAvatar.onSignProgress(function (current, total) {
      if (total > 1) {
        signProgressEl.textContent = 'Signing ' + current + ' of ' + total
        signProgressEl.classList.add('visible')
      }
      // Hide when the last sign starts (will clear after hold+gap)
      if (current >= total) {
        setTimeout(function () { signProgressEl.classList.remove('visible') }, 1200)
      }
    })
  }
}
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', tryInitAvatar)
} else {
  tryInitAvatar()
}

// ── CONNECTION ────────────────────────────────────────────
window.amandla.getSessionId().then(function (id) {
  window.amandla.connect(id || 'demo', 'deaf')
}).catch(function () {
  window.amandla.connect('demo', 'deaf')
})

// Track WebSocket connection state — checked before every send
let wsConnected = false
let statusPollingStarted = false
window.amandla.onConnectionChange(function (connected) {
  wsConnected = connected
  connStatus.textContent = connected ? 'connected' : 'disconnected'
  connStatus.className   = connected ? 'connected' : ''
  // Show/hide connection error banner
  const banner = document.getElementById('conn-banner')
  if (banner) banner.classList.toggle('visible', !connected)
  // Start status polling only after first successful connection
  if (connected && !statusPollingStarted) {
    statusPollingStarted = true
    pollStatus()
    setInterval(pollStatus, 30000)
  }
})

// ── INCOMING MESSAGES ─────────────────────────────────────
window.amandla.onMessage(function (msg) {
  if (!msg) return

  // ── HEARING → DEAF: Hearing person's text is being translated to SASL.
  // Show a "translating…" indicator so the deaf user knows something is coming.
  if (msg.type === 'translating') {
    glossEl.textContent = '…'
    sentenceEl.textContent = 'Hearing person is speaking — translating…'
    return
  }

  // ── HEARING → DEAF: Signs + SASL gloss arrive from the hearing person's speech/text.
  // This is the main display path for the deaf user.
  if (msg.type === 'signs') {
    const signCount = Array.isArray(msg.signs) ? msg.signs.length : 1
    const clearAfter = (signCount * 700) + 1200

    // Show SASL gloss (what signs will be performed — deaf user's language)
    if (msg.text) {
      glossEl.textContent = msg.text
      setTimeout(function () { glossEl.textContent = '' }, clearAfter)
    }

    // Show the original English below the gloss.
    // This lets the deaf user also see what was SAID in English
    // (helpful for context and for when a sign may be ambiguous).
    if (msg.original_english) {
      sentenceEl.textContent = '"' + msg.original_english + '"'
      setTimeout(function () { sentenceEl.textContent = '' }, clearAfter + 500)
    } else {
      sentenceEl.textContent = ''
    }

    if (msg.language) setDetectedLanguage(msg.language)

    // Drive the avatar with the sign sequence using the documented public API
    if (Array.isArray(msg.signs) && msg.signs.length > 0) {
      // UX-3: Store for replay
      lastSigns = msg.signs.slice()
      lastSignText = msg.text || msg.signs.join(' ')
      replayBtn.classList.add('visible')

      if (window.avatarPlaySigns) {
        window.avatarPlaySigns(msg.signs, msg.text || msg.signs.join(' '))
      } else {
        glossEl.textContent = msg.text || msg.signs.join(' ')
      }
    }
    return
  }

  // Turn indicator broadcast
  if (msg.type === 'turn') {
    setTurnIndicator(msg.speaker)
    return
  }

  if (msg.type === 'emergency') {
    showEmergency()
    return
  }
})

// ── TURN INDICATOR ────────────────────────────────────────
// Auto-resets after 12 seconds — long enough for Whisper + SASL translation
const TURN_RESET_MS = 12000

/**
 * Update the turn indicator to show who is currently communicating.
 * @param {string} speaker - 'hearing', 'deaf', or anything else to reset.
 */
function setTurnIndicator(speaker) {
  if (speaker === 'hearing') {
    turnEl.textContent = '🎙 Hearing person is speaking'
    turnEl.className = 'hearing'
  } else if (speaker === 'deaf') {
    turnEl.textContent = '🤟 Signer is signing'
    turnEl.className = 'deaf'
  } else {
    turnEl.textContent = 'Waiting…'
    turnEl.className = ''
  }
  clearTimeout(window._turnTimer)
  window._turnTimer = setTimeout(function () {
    turnEl.textContent = 'Waiting…'
    turnEl.className = ''
  }, TURN_RESET_MS)
}

// ── SASL TEXT INPUT → HEARING ─────────────────────────────

/** Send the SASL text input to the backend for English reconstruction. */
function sendSaslText() {
  const text = saslInput.value.trim()
  if (!text) return
  if (!wsConnected) {
    saslStatus.textContent = '⚠ Not connected — is the backend running? (npm start)'
    return
  }
  window.amandla.send({
    type:      'sasl_text',
    text:      text,
    sender:    'deaf',
    timestamp: Date.now()
  })
  saslStatus.textContent = 'Sent — translating to English for the hearing person…'
  const SASL_STATUS_CLEAR_MS = 3000
  setTimeout(function () { saslStatus.textContent = '' }, SASL_STATUS_CLEAR_MS)
  saslInput.value = ''
  saslInput.focus()
}

saslSendBtn.addEventListener('click', sendSaslText)
saslInput.addEventListener('keypress', function (e) {
  if (e.key === 'Enter') sendSaslText()
})

// ── QUICK-SIGN CATEGORY BUTTONS ───────────────────────────
const CATEGORIES = {
  'MEDICAL':   ['DOCTOR', 'NURSE', 'HOSPITAL', 'SICK', 'PAIN', 'AMBULANCE', 'MEDICINE', 'HURT', 'EMERGENCY'],
  'GREETINGS': ['HELLO', 'GOODBYE', 'PLEASE', 'THANK YOU', 'SORRY', 'YES', 'NO'],
  'EMOTIONS':  ['HAPPY', 'SAD', 'ANGRY', 'SCARED', 'LOVE', 'TIRED', 'HUNGRY', 'THIRSTY'],
  'ACTIONS':   ['HELP', 'WAIT', 'STOP', 'REPEAT', 'COME', 'GO', 'LISTEN', 'UNDERSTAND'],
  'RIGHTS':    ['RIGHTS', 'LAW', 'EQUAL', 'FREE'],
}

const toolbar    = document.getElementById('quick-signs')
const catBar     = document.getElementById('category-tabs')
let activeCat    = null

/**
 * Render a category's quick-sign buttons into the toolbar.
 * @param {string} category - The category key from CATEGORIES.
 */
function renderCategory(category) {
  activeCat = category
  catBar.querySelectorAll('.cat-tab').forEach(function (t) {
    t.classList.toggle('active', t.dataset.cat === category)
  })
  const signs = CATEGORIES[category] || []
  while (toolbar.firstChild) toolbar.removeChild(toolbar.firstChild)
  signs.forEach(function (sign) {
    const btn = document.createElement('button')
    btn.className = 'qs-btn' + (sign === 'EMERGENCY' ? ' emergency' : '')
    btn.textContent = sign
    btn.setAttribute('aria-label', 'Send sign: ' + sign)
    btn.addEventListener('click', function () {
      if (sign === 'EMERGENCY') {
        // Emergency is always allowed — show overlay regardless of connection
        if (wsConnected) window.amandla.send({ type: 'emergency', sender: 'deaf', timestamp: Date.now() })
        showEmergency()
        return
      }
      if (!wsConnected) return  // silently ignore — banner already shows "disconnected"
      window.amandla.send({ type: 'sign', text: sign, sender: 'deaf', timestamp: Date.now() })
      if (window.AmandlaAvatar) window.AmandlaAvatar.playSignNow(sign)
      showDetectedSign(sign, 1.0)
      btn.classList.add('sent')
      const SENT_FLASH_MS = 800
      setTimeout(function () { btn.classList.remove('sent') }, SENT_FLASH_MS)
    })
    toolbar.appendChild(btn)
  })
}

// Build category tab buttons
Object.keys(CATEGORIES).forEach(function (cat) {
  const tab = document.createElement('button')
  tab.className = 'cat-tab'
  tab.dataset.cat = cat
  tab.textContent = cat
  tab.setAttribute('role', 'tab')
  tab.addEventListener('click', function () { renderCategory(cat) })
  catBar.appendChild(tab)
})
renderCategory('MEDICAL')

// ── QUICK-SIGN VALIDATION ──────────────────────────────────
// Log warnings for any category sign name not found in the signs library.
// This catches silent failures where a button would do nothing on click.
;(function validateQuickSigns() {
  var lib = (window.AMANDLA_SIGNS && window.AMANDLA_SIGNS.SIGN_LIBRARY) || {}
  var missing = []
  Object.keys(CATEGORIES).forEach(function (cat) {
    CATEGORIES[cat].forEach(function (sign) {
      if (sign === 'EMERGENCY') return  // EMERGENCY triggers overlay, not avatar
      if (!lib[sign]) missing.push(cat + '/' + sign)
    })
  })
  if (missing.length > 0) {
    console.warn('[QuickSigns] Signs not found in SIGN_LIBRARY:', missing.join(', '))
  } else {
    console.log('[QuickSigns] All category signs validated against SIGN_LIBRARY ✓')
  }
})()

// ── EMERGENCY ─────────────────────────────────────────────
let _emgInterval = null
// Auto-dismiss after 30 seconds — longer for deaf users who rely on visual alerts
const EMERGENCY_DISMISS_SECONDS = 30

/** Show the full-screen emergency overlay with countdown auto-dismiss. */
function showEmergency() {
  document.getElementById('emergency-overlay').classList.add('active')
  let remaining = EMERGENCY_DISMISS_SECONDS
  const cdEl = document.getElementById('emg-countdown')
  if (cdEl) cdEl.textContent = 'Auto-dismiss in ' + remaining + 's'
  clearInterval(_emgInterval)
  _emgInterval = setInterval(function () {
    remaining--
    if (cdEl) cdEl.textContent = remaining > 0 ? 'Auto-dismiss in ' + remaining + 's' : ''
    if (remaining <= 0) { hideEmergency(); clearInterval(_emgInterval) }
  }, 1000)
}

/** Hide the emergency overlay and stop the countdown. */
function hideEmergency() {
  document.getElementById('emergency-overlay').classList.remove('active')
  clearInterval(_emgInterval)
  const cdEl = document.getElementById('emg-countdown')
  if (cdEl) cdEl.textContent = ''
}
window.hideEmergency = hideEmergency

// FEAT-6: Global emergency shortcut (Ctrl+E) — triggered from main process
// Deaf window also sends the WS emergency broadcast so hearing user is alerted
window.amandla.onEmergencyShortcut(function () {
  if (wsConnected) {
    window.amandla.send({ type: 'emergency', sender: 'deaf', timestamp: Date.now() })
  }
  showEmergency()
})

// ── SIGN DETECTION FEEDBACK ───────────────────────────────

/**
 * Briefly show a detected sign name on screen with colour feedback.
 * @param {string} signName - The name of the detected sign.
 * @param {number} confidence - Detection confidence (0–1).
 */
function showDetectedSign(signName, confidence) {
  const el = document.getElementById('detected-sign')
  if (!el) return
  el.textContent = signName
  el.style.opacity = '1'
  const HIGH_CONFIDENCE_THRESHOLD = 0.75
  el.style.color = confidence > HIGH_CONFIDENCE_THRESHOLD ? '#2EA880' : '#ECC94B'
  clearTimeout(el._hideTimer)
  const SIGN_DISPLAY_MS = 2000
  el._hideTimer = setTimeout(function () { el.style.opacity = '0' }, SIGN_DISPLAY_MS)
}

// ── MULTI-LANGUAGE TTS ────────────────────────────────────
const SA_LANGUAGES = {
  'en':  { tts: 'en-ZA',  label: 'English'    },
  'zu':  { tts: 'zu-ZA',  label: 'isiZulu'    },
  'xh':  { tts: 'xh-ZA',  label: 'isiXhosa'   },
  'af':  { tts: 'af-ZA',  label: 'Afrikaans'  },
  'st':  { tts: 'st-ZA',  label: 'Sesotho'    },
  'tn':  { tts: 'tn-ZA',  label: 'Setswana'   },
  'nso': { tts: 'nso-ZA', label: 'Sepedi'     },
  'ts':  { tts: 'ts-ZA',  label: 'Xitsonga'   },
  've':  { tts: 've-ZA',  label: 'Tshivenda'  },
  'nr':  { tts: 'nr-ZA',  label: 'isiNdebele' },
  'ss':  { tts: 'ss-ZA',  label: 'siSwati'    },
}

let currentTTSLang = 'en-ZA'

/**
 * Update the TTS language based on Whisper's detected language code.
 * @param {string} code - Two-letter ISO language code from Whisper.
 */
function setDetectedLanguage(code) {
  const entry = code && SA_LANGUAGES[code]
  if (entry) currentTTSLang = entry.tts
}

/**
 * Find the best available TTS voice for a given language tag.
 * @param {string} lang - BCP 47 language tag (e.g. 'en-ZA').
 * @returns {SpeechSynthesisVoice|null} The best matching voice.
 */
function getBestVoice(lang) {
  const voices = window.speechSynthesis.getVoices()
  return voices.find(function (v) { return v.lang === lang })
      || voices.find(function (v) { return v.lang.startsWith(lang.split('-')[0]) })
      || voices.find(function (v) { return v.lang.startsWith('en') })
      || (voices[0] || null)
}

/**
 * Speak text aloud using the Web Speech API.
 * @param {string} text - The text to speak.
 * @param {string} [lang] - Optional language override.
 */
function speakText(text, lang) {
  const useLang = lang || currentTTSLang
  if (window.speechSynthesis.paused) window.speechSynthesis.resume()
  if (window.speechSynthesis.speaking) window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(text)
  const voice = getBestVoice(useLang)
  if (voice) u.voice = voice
  u.rate = 0.95
  window.speechSynthesis.speak(u)
}

// ── STATUS POLLING (via WebSocket preload bridge) ───────
// Polling is started in onConnectionChange after first WS connection

/**
 * Poll the backend for AI service health status.
 * Updates the status dot and offline banner accordingly.
 */
async function pollStatus() {
  try {
    const d = await window.amandla.requestStatus()
    const ollamaOk = d.qwen === 'alive'
    const whisperOk = d.whisper === 'ready'
    const allOk = ollamaOk && whisperOk
    statusDot.className = allOk ? '' : 'offline'
    statusDot.title     = 'AI: ' + (ollamaOk ? 'online' : 'offline')
                        + ' | Speech: ' + (whisperOk ? 'ready' : 'unavailable')

    // UX-1: Show/hide offline banner when AI is degraded
    if (!ollamaOk && !offlineDismissed) {
      offlineBanner.classList.add('visible')
    } else if (ollamaOk) {
      offlineBanner.classList.remove('visible')
      offlineDismissed = false  // Reset dismiss so it re-shows if AI drops again
    }
  } catch (e) {
    statusDot.className = 'offline'
    statusDot.title     = 'Backend offline'
    // Backend itself is down — show the banner (more serious than just Ollama)
    if (!offlineDismissed) {
      offlineBanner.classList.add('visible')
    }
  }
}

// ── MODE TOGGLE ───────────────────────────────────────────
const modeToggleBtn = document.getElementById('modeToggleBtn')
if (modeToggleBtn && window.ModeController) {
  modeToggleBtn.addEventListener('click', function () {
    window.ModeController.toggle()
  })
  window.ModeController.onChange(function (mode) {
    modeToggleBtn.textContent = mode === 'sign' ? 'Assist Mode' : 'Sign Mode'
  })
}

// ── ASSIST MODE → SEND PHRASE VIA WS ──────────────────────
// BUG-2 fix: Assist phrases are already natural English — send as
// 'assist_phrase' so the backend forwards them directly to hearing
// instead of running SASL→English reconstruction on them.
window.addEventListener('amandla:assistPhrase', function (e) {
  const phrase = e.detail && e.detail.phrase
  if (!phrase) return
  window.amandla.send({
    type:      'assist_phrase',
    text:      phrase,
    sender:    'deaf',
    timestamp: Date.now()
  })
})

// ── MEDIAPIPE CAMERA SIGN RECOGNITION ─────────────────────
const cameraContainer = document.getElementById('camera-container')
const cameraVideo     = document.getElementById('camera-video')
const cameraToggle    = document.getElementById('camera-toggle')
let mpHands       = null
let mpCamera      = null
let cameraActive  = false
let lastLandmarkSend = 0
const LANDMARK_THROTTLE_MS = 500  // send landmarks at most every 500ms

/** Initialise the MediaPipe Hands model for sign recognition. */
function initMediaPipe() {
  if (typeof Hands === 'undefined') {
    console.warn('[MediaPipe] Hands library not loaded')
    return
  }
  mpHands = new Hands({
    locateFile: function (file) {
      return 'https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469240/' + file
    }
  })
  mpHands.setOptions({
    maxNumHands: 2,
    modelComplexity: 1,
    minDetectionConfidence: 0.6,
    minTrackingConfidence: 0.5
  })
  mpHands.onResults(onHandResults)
  console.log('[MediaPipe] Hands initialised')
}

/**
 * Process hand detection results from MediaPipe and send landmarks to backend.
 * @param {Object} results - MediaPipe Hands results object.
 */
function onHandResults(results) {
  if (!results.multiHandLandmarks || results.multiHandLandmarks.length === 0) return
  const now = Date.now()
  if (now - lastLandmarkSend < LANDMARK_THROTTLE_MS) return
  lastLandmarkSend = now

  // Send landmarks for the first detected hand
  const landmarks = results.multiHandLandmarks[0].map(function (pt) {
    return { x: pt.x, y: pt.y, z: pt.z }
  })
  const handedness = (results.multiHandedness && results.multiHandedness[0])
    ? results.multiHandedness[0].label
    : 'Right'

  window.amandla.send({
    type:       'landmarks',
    landmarks:  landmarks,
    handedness: handedness,
    sender:     'deaf',
    timestamp:  now
  })
}

/** Start the user-facing camera and connect it to MediaPipe Hands. */
async function startCamera() {
  if (cameraActive) return
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: 320, height: 240 } })
    cameraVideo.srcObject = stream
    cameraContainer.classList.remove('hidden')
    cameraActive = true

    if (!mpHands) initMediaPipe()

    if (mpHands && typeof Camera !== 'undefined') {
      mpCamera = new Camera(cameraVideo, {
        onFrame: async function () {
          if (mpHands) await mpHands.send({ image: cameraVideo })
        },
        width: 320,
        height: 240
      })
      mpCamera.start()
      console.log('[MediaPipe] Camera started')
    }
  } catch (err) {
    console.error('[MediaPipe] Camera error:', err)
  }
}

/** Stop the camera stream and hide the preview. */
function stopCamera() {
  if (!cameraActive) return
  if (mpCamera) { try { mpCamera.stop() } catch(e) { /* ignore */ } }
  const stream = cameraVideo.srcObject
  if (stream) stream.getTracks().forEach(function (t) { t.stop() })
  cameraVideo.srcObject = null
  cameraContainer.classList.add('hidden')
  cameraActive = false
  console.log('[MediaPipe] Camera stopped')
}

if (cameraToggle) {
  cameraToggle.addEventListener('click', function () {
    if (cameraActive) stopCamera()
    else startCamera()
  })
}

// ── CLEANUP ON CLOSE ─────────────────────────────────────
// Stop the camera stream and disconnect cleanly when the window is closed
// so the backend session is torn down immediately rather than waiting for
// the WebSocket timeout.
window.addEventListener('beforeunload', function () {
  stopCamera()
  window.amandla.disconnect()
})

