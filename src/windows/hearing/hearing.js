/**
 * hearing.js — JavaScript for the AMANDLA Hearing window.
 *
 * Handles: startup overlay, message log, WebSocket connection,
 * incoming message routing, text/speech input, TTS output,
 * turn indicator, emergency overlay, and status polling.
 */

// ── DOM REFS ──────────────────────────────────────────────
const overlay      = document.getElementById('startup-overlay')
const startBtn     = document.getElementById('start-btn')
const connStatus   = document.getElementById('conn-status')
const statusDot    = document.getElementById('status-dot')
const rightsBtn       = document.getElementById('rights-btn')
const interpreterBtn  = document.getElementById('interpreter-btn')
const micBtn       = document.getElementById('mic-btn')
const recTimer     = document.getElementById('rec-timer')
const textInput    = document.getElementById('text-input')
const sendBtn      = document.getElementById('send-btn')
const transcriptEl = document.getElementById('transcript-text')
const turnEl       = document.getElementById('turn-indicator')
const offlineBanner = document.getElementById('offline-banner')
const offlineDismiss = document.getElementById('offline-dismiss')

// Track whether user dismissed the banner this poll cycle
let offlineDismissed = false
offlineDismiss.addEventListener('click', function () {
  offlineBanner.classList.remove('visible')
  offlineDismissed = true
})

// ── STARTUP ───────────────────────────────────────────────
startBtn.addEventListener('click', function () {
  overlay.style.display = 'none'
  try {
    const u = new SpeechSynthesisUtterance(' ')
    u.volume = 0
    window.speechSynthesis.speak(u)
  } catch (e) { /* ignore */ }
  micBtn.disabled = false
  textInput.focus()
})

// ── MESSAGE LOG ───────────────────────────────────────────
const msgLog = document.getElementById('message-log')

/**
 * Append a chat bubble to the message log.
 * @param {string} text - The message text to display.
 * @param {string} direction - 'out' for sent, 'in' for received.
 * @param {string} [meta] - Optional metadata line below the message.
 */
function addMessage(text, direction, meta) {
  const item = document.createElement('div')
  item.className = 'msg-item ' + (direction === 'out' ? 'msg-out' : 'msg-in-deaf')
  item.textContent = text
  if (meta) {
    const m = document.createElement('div')
    m.className = 'msg-meta'
    m.textContent = meta
    item.appendChild(m)
  }
  msgLog.appendChild(item)
  msgLog.scrollTop = msgLog.scrollHeight
  // Keep log from growing too long
  const MAX_LOG_ITEMS = 60
  while (msgLog.children.length > MAX_LOG_ITEMS) msgLog.removeChild(msgLog.firstChild)
}

// ── CONNECTION ────────────────────────────────────────────
window.amandla.getSessionId().then(function (id) {
  window.amandla.connect(id || 'demo', 'hearing')
}).catch(function () {
  window.amandla.connect('demo', 'hearing')
})

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

  // ── HEARING → DEAF acknowledgement: backend sends back the SASL gloss
  // that was actually delivered to the deaf person's screen.
  // This lets the hearing user see "what the deaf person saw" for transparency.
  // FEAT-5: If a non-English source language was detected, show the translation chain.
  if (msg.type === 'sasl_ack' && msg.sasl_gloss) {
    var ackText = '✓ Sent as SASL: ' + msg.sasl_gloss
    if (msg.source_language && msg.source_language !== 'en') {
      var langEntry = SA_LANGUAGES[msg.source_language]
      var langLabel = langEntry ? langEntry.label : msg.source_language
      ackText = '✓ Translated from ' + langLabel + ' → SASL: ' + msg.sasl_gloss
    }
    transcriptEl.textContent = ackText
    return
  }

  // ── DEAF → HEARING: Deaf user tapped a quick-sign or MediaPipe recognised a sign.
  // Show indicator while the debounce buffer waits for more signs before
  // reconstructing to English — the deaf_speech message arrives after ~1.5 s.
  if (msg.type === 'sign' && msg.sender === 'deaf') {
    const signName = msg.text || ''
    transcriptEl.textContent = '🤟 Signing: ' + signName + ' — translating…'
    return
  }

  // ── DEAF → HEARING: Deaf user typed SASL text — show indicator while translating.
  if (msg.type === 'sasl_text' && msg.sender === 'deaf') {
    transcriptEl.textContent = '🤟 Signer typed: ' + (msg.text || '') + ' — translating…'
    return
  }

  // Signs echoed back from our own speech — no avatar on this side
  if (msg.type === 'signs') return

  // ── DEAF → HEARING final result: reconstructed natural English from SASL signs.
  // This is the main path for the hearing user to understand the deaf person.
  if (msg.type === 'deaf_speech' && msg.text) {
    addMessage('🤟 ' + msg.text, 'in', 'via signs')
    transcriptEl.textContent = '🤟 ' + msg.text
    speakText(msg.text)
    return
  }

  // Turn indicator
  if (msg.type === 'turn') {
    setTurnIndicator(msg.speaker)
    return
  }

  if (msg.type === 'emergency') {
    showEmergency()
  }
})

// ── TURN INDICATOR ────────────────────────────────────────
// Auto-resets after 12 seconds — long enough for Whisper transcription
const TURN_RESET_MS = 12000

/**
 * Update the turn indicator to show who is currently communicating.
 * @param {string} speaker - 'hearing', 'deaf', or anything else to reset.
 */
function setTurnIndicator(speaker) {
  if (speaker === 'hearing') {
    turnEl.textContent = '🎙 You are speaking'
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

// ── SEND TEXT ─────────────────────────────────────────────

/**
 * Send a text message to the backend via WebSocket.
 * @param {string} text - The message text to send.
 * @param {string} [detectedLang] - Optional Whisper-detected language code.
 */
// Maximum text message length enforced by the backend
const MAX_TEXT_LENGTH = 5000

// ── LANGUAGE SELECTOR ────────────────────────────────────
const langSelect = document.getElementById('lang-select')

/** Return the currently selected language code, or null for auto-detect. */
function getSelectedLanguage() {
  return (langSelect && langSelect.value) ? langSelect.value : null
}

// When user manually picks a language, update the badge immediately
if (langSelect) {
  langSelect.addEventListener('change', function () {
    const code = langSelect.value
    if (code && SA_LANGUAGES[code]) {
      const badge = document.getElementById('lang-badge')
      if (badge) badge.textContent = SA_LANGUAGES[code].label
    } else {
      const badge = document.getElementById('lang-badge')
      if (badge) badge.textContent = ''
    }
  })
}

function sendText(text, detectedLang) {
  if (!text) return
  if (!wsConnected) {
    transcriptEl.textContent = '⚠ Not connected — is the backend running? (npm start)'
    return
  }
  if (text.length > MAX_TEXT_LENGTH) {
    transcriptEl.textContent = `Message too long (${text.length}/${MAX_TEXT_LENGTH} chars)`
    return
  }
  // Manual language selection takes precedence over Whisper-detected language
  const lang = getSelectedLanguage() || detectedLang || null
  transcriptEl.textContent = '🎙 ' + text
  if (lang) setDetectedLanguage(lang)
  addMessage(text, 'out')
  window.amandla.send({
    type:      'text',
    text:      text,
    language:  lang,
    sender:    'hearing',
    timestamp: Date.now()
  })
  setTurnIndicator('hearing')
  // UX-5: Show translating indicator immediately — replaced when sasl_ack arrives
  transcriptEl.textContent = '⏳ Translating to SASL…'
}

sendBtn.addEventListener('click', function () {
  const t = textInput.value.trim()
  if (!t) return
  textInput.value = ''
  updateCharCounter(0)
  if (speechAssistMode) {
    sendSpeechAssist(t)
  } else {
    sendText(t)
  }
})
textInput.addEventListener('keypress', function (e) {
  if (e.key === 'Enter') sendBtn.click()
})

// ── FEAT-3: REAL-TIME CHARACTER COUNTER ───────────────────
const charCounter = document.getElementById('char-counter')

function updateCharCounter(len) {
  if (!charCounter) return
  charCounter.textContent = len + ' / ' + MAX_TEXT_LENGTH
  charCounter.className = len > MAX_TEXT_LENGTH * 0.9 ? 'warn' : ''
}

textInput.addEventListener('input', function () {
  updateCharCounter(textInput.value.length)
})

// ── MICROPHONE RECORDING ──────────────────────────────────
let mediaRecorder = null
let audioChunks   = []
let recInterval   = null
let recSeconds    = 0
let isRecording   = false
const MAX_RECORD_SECONDS = 30

/**
 * Toggle microphone recording on/off.
 * When stopped, the audio blob is uploaded via the preload bridge.
 */
async function startRecording() {
  if (isRecording) return stopRecording()
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')
        ? 'audio/ogg;codecs=opus'
        : 'audio/mp4'

    mediaRecorder = new MediaRecorder(stream, { mimeType })
    audioChunks = []

    mediaRecorder.ondataavailable = function (e) {
      if (e.data.size > 0) audioChunks.push(e.data)
    }
    mediaRecorder.onstop = async function () {
      const blob = new Blob(audioChunks, { type: mimeType })
      stream.getTracks().forEach(function (t) { t.stop() })
      await uploadAudio(blob, mimeType)
    }

    mediaRecorder.start()
    isRecording = true
    micBtn.classList.add('recording')
    micBtn.textContent = '⏹'
    recSeconds = 0
    recTimer.textContent = '0:00'
    recInterval = setInterval(function () {
      recSeconds++
      const m = Math.floor(recSeconds / 60)
      const s = recSeconds % 60
      recTimer.textContent = m + ':' + String(s).padStart(2, '0')
      if (recSeconds >= MAX_RECORD_SECONDS) stopRecording()
    }, 1000)
  } catch (err) {
    console.error('[Hearing] Mic error:', err)
    transcriptEl.textContent = 'Microphone access denied'
  }
}

/** Stop the current recording session and reset the UI. */
function stopRecording() {
  if (!isRecording || !mediaRecorder) return
  mediaRecorder.stop()
  isRecording = false
  micBtn.classList.remove('recording')
  micBtn.textContent = '🎙'
  clearInterval(recInterval)
  recTimer.textContent = ''
}

// Maximum audio size enforced by the backend (10 MB)
const MAX_AUDIO_BYTES = 10 * 1024 * 1024

/**
 * Upload recorded audio to the backend for Whisper transcription.
 * @param {Blob} blob - The recorded audio blob.
 * @param {string} mimeType - The MIME type of the audio.
 */
async function uploadAudio(blob, mimeType) {
  if (blob.size > MAX_AUDIO_BYTES) {
    transcriptEl.textContent = 'Audio too large (max 10 MB). Try a shorter clip.'
    return
  }
  // Upload speech audio via WebSocket preload bridge (no direct HTTP fetch)
  transcriptEl.textContent = 'Transcribing…'

  // On slow machines Whisper takes 15–45 s to load on first use.
  // After 3 s without a result, show a friendlier message so the user
  // knows the app hasn't frozen.
  const SLOW_LOAD_DELAY_MS = 3000
  let whisperLoadTimer = setTimeout(function () {
    transcriptEl.textContent = 'Loading speech model (first time only — please wait)…'
  }, SLOW_LOAD_DELAY_MS)

  try {
    const data = await window.amandla.uploadSpeech(blob, mimeType, getSelectedLanguage())
    clearTimeout(whisperLoadTimer) // result arrived — cancel the slow-load message
    if (data.text) {
      // The speech_upload handler on the backend already ran the full
      // SASL pipeline AND broadcast the signs to the deaf window.
      // Do NOT call sendText() here — that would send a second {type:'text'}
      // message, causing the backend to run the pipeline again and broadcast
      // signs to the deaf window a SECOND time (double-signing bug).
      // Instead we update the UI directly without re-triggering the backend.
      addMessage(data.text, 'out')
      transcriptEl.textContent = '🎙 ' + data.text
      if (data.language) setDetectedLanguage(data.language)
      setTurnIndicator('hearing')
      // Show the SASL gloss that was delivered to the deaf person
      // FEAT-5: Include source language info when non-English speech was translated
      if (data.sasl_gloss) {
        if (data.source_language && data.source_language !== 'en') {
          var langEntry = SA_LANGUAGES[data.source_language]
          var langLabel = langEntry ? langEntry.label : data.source_language
          transcriptEl.textContent = '✓ Translated from ' + langLabel + ' → SASL: ' + data.sasl_gloss
        } else {
          transcriptEl.textContent = '✓ Sent as SASL: ' + data.sasl_gloss
        }
      }
    } else {
      transcriptEl.textContent = 'Could not transcribe — try typing'
    }
  } catch (err) {
    clearTimeout(whisperLoadTimer)
    console.error('[Hearing] Upload error:', err)
    transcriptEl.textContent = 'Transcription failed — try typing instead'
  }
}

micBtn.addEventListener('click', startRecording)

// ── RIGHTS WINDOW ─────────────────────────────────────────
rightsBtn.addEventListener('click', function () { window.amandla.openRights() })

// ── INTERPRETER WINDOW (FEAT-5) ───────────────────────────
if (interpreterBtn) {
  interpreterBtn.addEventListener('click', function () { window.amandla.openInterpreter() })
}

// ── SPEECH ASSIST MODE ────────────────────────────────────
// For hearing users who have speech impediments or articulation difficulties.
// When ON: text is sent to AI for correction, displayed here ONLY — NOT sent
// to the deaf window. Helps the speech-impaired person be understood by other
// hearing people around them.
let speechAssistMode = false

const speechAssistBtn    = document.getElementById('speech-assist-btn')
const speechAssistBanner = document.getElementById('speech-assist-banner')
const speechAssistOff    = document.getElementById('speech-assist-off')

function setSpeechAssistMode(on) {
  speechAssistMode = on
  if (speechAssistBtn) speechAssistBtn.classList.toggle('active', on)
  if (speechAssistBanner) speechAssistBanner.style.display = on ? 'flex' : 'none'
}

if (speechAssistBtn) {
  speechAssistBtn.addEventListener('click', function () {
    setSpeechAssistMode(!speechAssistMode)
  })
}
if (speechAssistOff) {
  speechAssistOff.addEventListener('click', function () { setSpeechAssistMode(false) })
}

/**
 * Run the hearing user's text through AI speech correction, then display
 * the result in the message log. Does NOT send anything to the deaf window.
 * Falls back to displaying the original text if the correction fails.
 *
 * @param {string} rawText - The garbled or incomplete input from the user.
 */
async function sendSpeechAssist(rawText) {
  if (!wsConnected) {
    transcriptEl.textContent = '⚠ Not connected — is the backend running?'
    return
  }
  if (rawText.length > MAX_TEXT_LENGTH) {
    transcriptEl.textContent = `Message too long (${rawText.length}/${MAX_TEXT_LENGTH} chars)`
    return
  }

  transcriptEl.textContent = '🗣 Correcting speech…'

  try {
    const result = await window.amandla.correctSpeech(rawText)
    const corrected = result.corrected || rawText

    // Build a message bubble that shows both what was said and what it meant
    const item = document.createElement('div')
    item.className = 'msg-item msg-out'

    const correctedEl = document.createElement('div')
    correctedEl.className = 'msg-assist-corrected'
    correctedEl.textContent = corrected
    item.appendChild(correctedEl)

    if (corrected !== rawText) {
      const originalEl = document.createElement('div')
      originalEl.className = 'msg-assist-original'
      originalEl.textContent = 'You said: "' + rawText + '"'
      item.appendChild(originalEl)
    }

    const metaEl = document.createElement('div')
    metaEl.className = 'msg-meta'
    metaEl.textContent = result.fallback ? 'Speech Assist (no AI — showing original)' : 'Speech Assist'
    item.appendChild(metaEl)

    msgLog.appendChild(item)
    msgLog.scrollTop = msgLog.scrollHeight
    const MAX_LOG_ITEMS = 60
    while (msgLog.children.length > MAX_LOG_ITEMS) msgLog.removeChild(msgLog.firstChild)

    transcriptEl.textContent = '🗣 ' + corrected
  } catch (err) {
    // Show the original text anyway so the user isn't left hanging
    addMessage(rawText, 'out', 'Speech Assist (correction failed)')
    transcriptEl.textContent = '⚠ Correction failed — showing original'
  }
}

// ── FEAT-4: PRINT TRANSCRIPT ──────────────────────────────
// Opens the browser's print dialog showing only the message log
// (styled by @media print rules in hearing.css).
const printBtn = document.getElementById('print-btn')
if (printBtn) {
  printBtn.addEventListener('click', function () {
    if (msgLog.children.length === 0) {
      transcriptEl.textContent = 'No messages to print'
      return
    }
    window.print()
  })
}

// ── EMERGENCY ─────────────────────────────────────────────
let _emgInterval = null
// Auto-dismiss after 30 seconds — gives time to read and react
const EMERGENCY_DISMISS_SECONDS = 30

/** Show the full-screen emergency overlay with countdown auto-dismiss. */
function showEmergency() {
  document.getElementById('emergency-overlay').classList.add('active')
  speakText('Emergency. Signer has triggered an emergency alert.')
  // UX-7: Flash the entire window border red as a visual cue
  document.body.classList.remove('emg-flash')
  void document.body.offsetWidth  // force reflow to restart animation
  document.body.classList.add('emg-flash')
  // Countdown timer — auto-dismiss after EMERGENCY_DISMISS_SECONDS
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
  document.body.classList.remove('emg-flash')
  clearInterval(_emgInterval)
  const cdEl = document.getElementById('emg-countdown')
  if (cdEl) cdEl.textContent = ''
}
window.hideEmergency = hideEmergency

// FEAT-6: Global emergency shortcut (Ctrl+E) — triggered from main process
window.amandla.onEmergencyShortcut(function () {
  showEmergency()
})

// ── MULTI-LANGUAGE TTS (Gap 15) ───────────────────────────
// All 11 official South African languages.
// Whisper auto-detects the spoken language; TTS switches to match.
// Not all languages have TTS voice packs on every machine — Whisper
// transcribes them all; TTS falls back to any English voice if needed.
const SA_LANGUAGES = {
  'en':  { tts: 'en-ZA',  label: 'English',    whisper: 'en'  },
  'zu':  { tts: 'zu-ZA',  label: 'isiZulu',    whisper: 'zu'  },
  'xh':  { tts: 'xh-ZA',  label: 'isiXhosa',   whisper: 'xh'  },
  'af':  { tts: 'af-ZA',  label: 'Afrikaans',   whisper: 'af'  },
  'st':  { tts: 'st-ZA',  label: 'Sesotho',    whisper: 'st'  },
  'tn':  { tts: 'tn-ZA',  label: 'Setswana',   whisper: 'tn'  },
  'nso': { tts: 'nso-ZA', label: 'Sepedi',     whisper: null  },
  'ts':  { tts: 'ts-ZA',  label: 'Xitsonga',   whisper: null  },
  've':  { tts: 've-ZA',  label: 'Tshivenda',  whisper: null  },
  'nr':  { tts: 'nr-ZA',  label: 'isiNdebele', whisper: null  },
  'ss':  { tts: 'ss-ZA',  label: 'siSwati',    whisper: null  },
}

// Persists across calls — updated when Whisper returns a language code
let currentTTSLang = 'en-ZA'

/**
 * Update the TTS language based on Whisper's detected language code.
 * @param {string} whisperLangCode - Two-letter ISO language code from Whisper.
 */
function setDetectedLanguage(whisperLangCode) {
  if (!whisperLangCode) return
  const entry = SA_LANGUAGES[whisperLangCode]
  if (entry) {
    currentTTSLang = entry.tts
    const badge = document.getElementById('lang-badge')
    if (badge) badge.textContent = entry.label
  }
}

/**
 * Find the best available TTS voice for a given language tag.
 * Falls back to any English voice, then the first available voice.
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
 * Speak text aloud using the Web Speech API with the current TTS language.
 * @param {string} text - The text to speak.
 * @param {string} [lang] - Optional language override for this utterance.
 */
function speakText(text, lang) {
  // lang arg overrides currentTTSLang only for this call
  const useLang = lang || currentTTSLang
  if (window.speechSynthesis.paused) window.speechSynthesis.resume()
  if (window.speechSynthesis.speaking) window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(text)
  const voice = getBestVoice(useLang)
  if (voice) u.voice = voice
  u.rate = 0.95
  window.speechSynthesis.speak(u)
}

// ── CLEANUP ON CLOSE ─────────────────────────────────────
// Disconnect cleanly when the window is closed so the backend session is
// torn down immediately rather than waiting for the WebSocket timeout.
window.addEventListener('beforeunload', function () {
  window.amandla.disconnect()
})

// ── STATUS POLLING (via WebSocket preload bridge) ───────
// Polling is started in onConnectionChange after first WS connection
let isFirstPoll = true  // UX-6: skip mic disable on first poll (Whisper lazy-loads)

/**
 * Poll the backend for AI service health status.
 * Updates the status dot, mic button, and offline banner accordingly.
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

    // UX-6: On first poll, Whisper may not be loaded yet (it lazy-loads on
    // first use). Show a tooltip warning but leave the mic button enabled
    // so the user isn't confused after just clicking START SESSION.
    if (isFirstPoll) {
      isFirstPoll = false
      if (!whisperOk) {
        micBtn.title = 'Speech will load on first use — click to start'
      }
    } else {
      micBtn.disabled = !whisperOk
      micBtn.title    = whisperOk ? 'Click to record' : 'Speech recognition unavailable — type instead'
    }

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

// ── FEAT-3: CONVERSATION HISTORY ──────────────────────────
// Shows a modal overlay with stored conversation history from SQLite.
const historyBtn     = document.getElementById('history-btn')
const historyOverlay = document.getElementById('history-overlay')
const historyClose   = document.getElementById('history-close')
const historyList    = document.getElementById('history-list')

// ── FEAT-1: EXPORT — last-loaded messages stored here for export ──
// Populated by loadAndShowHistory() so exportHistory() doesn't need
// a second network round-trip.
var _lastHistoryMessages = []

if (historyBtn) {
  historyBtn.addEventListener('click', loadAndShowHistory)
}
if (historyClose) {
  historyClose.addEventListener('click', function () {
    historyOverlay.style.display = 'none'
  })
}
// Close on background click
if (historyOverlay) {
  historyOverlay.addEventListener('click', function (e) {
    if (e.target === historyOverlay) historyOverlay.style.display = 'none'
  })
}

// ── FEAT-9: HISTORY SEARCH ────────────────────────────────
var historySearch = document.getElementById('history-search')
var historySearchCount = document.getElementById('history-search-count')

if (historySearch) {
  historySearch.addEventListener('input', function () {
    renderHistoryMessages(_lastHistoryMessages)
  })
}

/**
 * Render a (possibly filtered) list of messages into the history list.
 * Also updates the search result count badge.
 * @param {Array} messages - All loaded messages (unfiltered).
 */
function renderHistoryMessages(messages) {
  if (!historyList) return
  historyList.innerHTML = ''

  // FEAT-9: Apply search filter
  var query = historySearch ? historySearch.value.trim().toLowerCase() : ''
  var filtered = query
    ? messages.filter(function (m) {
        var haystack = [m.original_text, m.translated_text, m.sasl_gloss]
          .filter(Boolean).join(' ').toLowerCase()
        return haystack.indexOf(query) !== -1
      })
    : messages

  // Update result count badge
  if (historySearchCount) {
    historySearchCount.textContent = query
      ? filtered.length + ' of ' + messages.length
      : ''
  }

  if (filtered.length === 0) {
    var emptyEl = document.createElement('p')
    emptyEl.className = 'history-empty'
    emptyEl.textContent = query ? 'No messages match your search.' : 'No conversation history yet.'
    historyList.appendChild(emptyEl)
    return
  }

  filtered.forEach(function (msg) {
    var msgEl = document.createElement('div')
    msgEl.className = 'history-msg ' + (msg.direction || 'hearing-to-deaf')

    // Direction label
    var dirEl = document.createElement('div')
    dirEl.className = 'history-direction'
    dirEl.textContent = msg.direction === 'deaf_to_hearing'
      ? '🤟 Deaf → Hearing'
      : '🎙 Hearing → Deaf'
    msgEl.appendChild(dirEl)

    // Main text content
    var textEl = document.createElement('div')
    textEl.className = 'history-text'
    textEl.textContent = msg.original_text || msg.translated_text || '(empty)'
    msgEl.appendChild(textEl)

    // SASL gloss if available
    if (msg.sasl_gloss) {
      var glossEl = document.createElement('div')
      glossEl.className = 'history-meta'
      glossEl.textContent = 'SASL: ' + msg.sasl_gloss
      msgEl.appendChild(glossEl)
    }

    // Translated text if different from original
    if (msg.translated_text && msg.translated_text !== msg.original_text) {
      var transEl = document.createElement('div')
      transEl.className = 'history-meta'
      transEl.textContent = '→ ' + msg.translated_text
      msgEl.appendChild(transEl)
    }

    // Timestamp + source
    var metaEl = document.createElement('div')
    metaEl.className = 'history-meta'
    var timeStr = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''
    var sourceStr = msg.source ? ' via ' + msg.source : ''
    metaEl.textContent = timeStr + sourceStr
    msgEl.appendChild(metaEl)

    historyList.appendChild(msgEl)
  })

  historyList.scrollTop = historyList.scrollHeight
}

/**
 * Fetch conversation history from the backend and render it in the overlay.
 * Uses the preload bridge's requestHistory() method (WebSocket-based).
 */
async function loadAndShowHistory() {
  if (!historyOverlay || !historyList) return
  historyOverlay.style.display = 'flex'
  // Clear search when opening
  if (historySearch) historySearch.value = ''
  if (historySearchCount) historySearchCount.textContent = ''
  historyList.innerHTML = ''

  // Show loading indicator
  var loadingEl = document.createElement('p')
  loadingEl.className = 'history-empty'
  loadingEl.textContent = 'Loading history…'
  historyList.appendChild(loadingEl)

  try {
    var data = await window.amandla.requestHistory()

    var messages = data.messages || []

    // FEAT-1: Store for export buttons
    _lastHistoryMessages = messages
    var footerEl = document.getElementById('history-footer')
    if (footerEl) footerEl.style.display = messages.length > 0 ? 'flex' : 'none'

    renderHistoryMessages(messages)

    // Focus the search box so the user can immediately start typing
    if (historySearch && messages.length > 0) historySearch.focus()
  } catch (err) {
    _lastHistoryMessages = []
    var footerErrEl = document.getElementById('history-footer')
    if (footerErrEl) footerErrEl.style.display = 'none'
    historyList.innerHTML = ''
    var errEl = document.createElement('p')
    errEl.className = 'history-empty'
    errEl.textContent = 'Failed to load history — ' + (err.message || 'try again later')
    historyList.appendChild(errEl)
  }
}

// ── FEAT-1: CONVERSATION EXPORT ───────────────────────────

/**
 * Format conversation messages as a plain-text record.
 * @param {Array} messages - Message objects from the history DB.
 * @returns {string} UTF-8 text content ready to save as .txt
 */
function formatAsText(messages) {
  var now = new Date()
  var header = [
    'AMANDLA — Communication Record',
    '================================',
    'Date:     ' + now.toLocaleDateString('en-ZA', { year: 'numeric', month: 'long', day: 'numeric' }),
    'Exported: ' + now.toLocaleString(),
    '',
    'This record was generated by AMANDLA, an assistive communication',
    'application for deaf and hard-of-hearing South Africans.',
    'It may be used as a communication record for medical or legal purposes.',
    '================================',
    '',
  ].join('\n')

  var body = messages.map(function (msg) {
    var time = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''
    var direction = msg.direction === 'deaf_to_hearing' ? 'DEAF → HEARING' : 'HEARING → DEAF'
    var source = msg.source ? ' [' + msg.source + ']' : ''
    var text = msg.original_text || msg.translated_text || '(empty)'
    var lines = [time + '  ' + direction + source, '  ' + text]
    if (msg.sasl_gloss) lines.push('  SASL: ' + msg.sasl_gloss)
    return lines.join('\n')
  }).join('\n\n')

  return header + body + '\n\n---\nGenerated by AMANDLA\n'
}

/**
 * Format conversation messages as a styled HTML document for PDF export.
 * @param {Array} messages - Message objects from the history DB.
 * @returns {string} Self-contained HTML string.
 */
function formatAsHtml(messages) {
  var now = new Date()
  var dateStr = now.toLocaleDateString('en-ZA', { year: 'numeric', month: 'long', day: 'numeric' })
  var timeStr = now.toLocaleString()

  function esc(s) { return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') }

  var rows = messages.map(function (msg) {
    var time = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''
    var isH2D = msg.direction !== 'deaf_to_hearing'
    var dirLabel = isH2D ? '🎙 Hearing &rarr; Deaf' : '🤟 Deaf &rarr; Hearing'
    var rowClass = isH2D ? 'h2d' : 'd2h'
    var text = esc(msg.original_text || msg.translated_text || '(empty)')
    var glossRow = msg.sasl_gloss
      ? '<div class="gloss">SASL gloss: ' + esc(msg.sasl_gloss) + '</div>'
      : ''
    var sourceLabel = msg.source ? ' &middot; ' + esc(msg.source) : ''
    return '<div class="msg ' + rowClass + '">'
      + '<div class="dir">' + dirLabel + '</div>'
      + '<div class="text">' + text + '</div>'
      + glossRow
      + '<div class="meta">' + time + sourceLabel + '</div>'
      + '</div>'
  }).join('\n')

  return '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
    + '<meta charset="utf-8">\n'
    + '<title>AMANDLA — Communication Record</title>\n'
    + '<style>\n'
    + 'body{font-family:Arial,Helvetica,sans-serif;max-width:740px;margin:0 auto;padding:32px 36px;color:#222;background:#fff;}\n'
    + '.hdr{border-bottom:3px solid #2EA880;padding-bottom:16px;margin-bottom:28px;}\n'
    + '.hdr h1{font-size:24px;color:#2EA880;letter-spacing:2px;margin:0 0 6px;}\n'
    + '.hdr .meta{font-size:12px;color:#555;margin:3px 0;}\n'
    + '.hdr .note{font-size:11px;color:#888;margin-top:10px;font-style:italic;line-height:1.5;}\n'
    + '.msg{padding:10px 14px;border-radius:6px;margin-bottom:10px;page-break-inside:avoid;}\n'
    + '.h2d{background:#edfaf4;border-left:4px solid #2EA880;}\n'
    + '.d2h{background:#f0ecfb;border-left:4px solid #8B6FD4;}\n'
    + '.dir{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#888;margin-bottom:5px;}\n'
    + '.h2d .dir{color:#2EA880;} .d2h .dir{color:#8B6FD4;}\n'
    + '.text{font-size:14px;color:#111;line-height:1.5;}\n'
    + '.gloss{font-size:11px;color:#555;margin-top:4px;font-style:italic;}\n'
    + '.meta{font-size:10px;color:#999;margin-top:5px;}\n'
    + '.ftr{margin-top:36px;border-top:1px solid #ddd;padding-top:12px;font-size:11px;color:#aaa;text-align:center;}\n'
    + '@media print{body{padding:16px;} .msg{-webkit-print-color-adjust:exact;print-color-adjust:exact;}}\n'
    + '</style>\n</head>\n<body>\n'
    + '<div class="hdr">\n'
    + '<h1>AMANDLA</h1>\n'
    + '<p class="meta"><strong>Communication Record</strong></p>\n'
    + '<p class="meta">Date: ' + dateStr + '</p>\n'
    + '<p class="meta">Exported: ' + timeStr + '</p>\n'
    + '<p class="note">This record was generated by AMANDLA, an assistive communication '
    + 'application for deaf and hard-of-hearing South Africans. '
    + 'It may be used as a communication record for medical or legal purposes.</p>\n'
    + '</div>\n'
    + rows + '\n'
    + '<div class="ftr">Generated by AMANDLA &middot; '
    + messages.length + ' message' + (messages.length !== 1 ? 's' : '')
    + ' &middot; ' + dateStr + '</div>\n'
    + '</body>\n</html>'
}

/**
 * Trigger a file export of the conversation history.
 * @param {'txt'|'pdf'} format - The export format.
 */
async function exportHistory(format) {
  if (!_lastHistoryMessages || _lastHistoryMessages.length === 0) {
    transcriptEl.textContent = 'No messages to export — open History first'
    return
  }
  var dateTag = new Date().toISOString().slice(0, 10)
  var ext = format === 'pdf' ? 'pdf' : 'txt'
  var defaultName = 'AMANDLA-session-' + dateTag + '.' + ext
  var content = format === 'pdf'
    ? formatAsHtml(_lastHistoryMessages)
    : formatAsText(_lastHistoryMessages)

  try {
    var result = await window.amandla.exportConversation(format, content, defaultName)
    if (result && result.success) {
      historyOverlay.style.display = 'none'
      transcriptEl.textContent = 'Saved: ' + (result.path || defaultName)
    } else if (result && result.error) {
      transcriptEl.textContent = 'Export failed: ' + result.error
    }
    // If canceled (result.success === false, no error) — do nothing
  } catch (err) {
    transcriptEl.textContent = 'Export error: ' + (err.message || 'unknown error')
  }
}

// Wire up export buttons
var exportTxtBtn = document.getElementById('export-txt-btn')
var exportPdfBtn = document.getElementById('export-pdf-btn')
if (exportTxtBtn) exportTxtBtn.addEventListener('click', function () { exportHistory('txt') })
if (exportPdfBtn) exportPdfBtn.addEventListener('click', function () { exportHistory('pdf') })
