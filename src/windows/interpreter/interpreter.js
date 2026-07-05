/**
 * interpreter.js — AMANDLA Interpreter View (FEAT-5)
 *
 * Read-only window showing the full conversation in real time.
 * Observers see both hearing (blue, left) and deaf (purple, right) messages.
 * No send capability — the interpreter can only watch.
 */

const connStatus  = document.getElementById('conn-status')
const statusDot   = document.getElementById('status-dot')
const turnEl      = document.getElementById('turn-indicator')
const transcriptList = document.getElementById('transcript-list')
const emptyHint   = document.getElementById('transcript-empty')
const msgCountEl  = document.getElementById('msg-count')

let msgCount = 0

// ── Connection state ────────────────────────────────────────────
window.amandla.onConnectionChange(function (connected) {
  if (connected) {
    connStatus.textContent = 'connected'
    statusDot.className = 'dot connected'
  } else {
    connStatus.textContent = 'reconnecting…'
    statusDot.className = 'dot connecting'
  }
})

// ── Message handler ─────────────────────────────────────────────
window.amandla.onMessage(function (msg) {
  switch (msg.type) {

    case 'signs':
      // Hearing → deaf: show original English + SASL gloss
      addBubble('hearing', msg.original_english || '', msg.text || '', msg.timestamp)
      break

    case 'deaf_speech':
    case 'sasl_text':
      // Deaf → hearing
      addBubble('deaf', msg.text || '', msg.sasl_original || '', msg.timestamp)
      break

    case 'turn':
      showTurn(msg.speaker)
      break

    case 'emergency':
      addBubble('emergency', 'EMERGENCY ALERT', '', msg.timestamp)
      break

    case 'translating':
      showTurn('hearing', true)
      break
  }
})

// Set initial status on load
window.addEventListener('DOMContentLoaded', function () {
  connStatus.textContent = 'waiting for session…'
  statusDot.className = 'dot connecting'
})

// ── Helpers ─────────────────────────────────────────────────────

/**
 * Add a message bubble to the transcript.
 * @param {'hearing'|'deaf'|'emergency'} side
 * @param {string} text     - Human-readable text
 * @param {string} sasl     - SASL gloss (optional)
 * @param {number} [ts]     - Timestamp (ms)
 */
function addBubble(side, text, sasl, ts) {
  if (!text && !sasl) return

  // Remove empty hint on first message
  if (emptyHint && emptyHint.parentNode) emptyHint.remove()

  const bubble = document.createElement('div')
  bubble.className = 'msg-bubble ' + side

  const meta = document.createElement('div')
  meta.className = 'msg-meta'
  const label = side === 'hearing' ? 'Hearing' : side === 'deaf' ? 'Deaf/Signer' : 'EMERGENCY'
  const time = ts ? new Date(ts).toLocaleTimeString() : new Date().toLocaleTimeString()
  meta.innerHTML = `<span>${label}</span><span>${time}</span>`
  bubble.appendChild(meta)

  if (text) {
    const textEl = document.createElement('div')
    textEl.className = 'msg-text'
    textEl.textContent = text
    bubble.appendChild(textEl)
  }

  if (sasl) {
    const saslEl = document.createElement('div')
    saslEl.className = 'msg-sasl'
    saslEl.textContent = sasl
    bubble.appendChild(saslEl)
  }

  transcriptList.appendChild(bubble)
  bubble.scrollIntoView({ behavior: 'smooth', block: 'end' })

  msgCount++
  if (msgCountEl) msgCountEl.textContent = msgCount + ' message' + (msgCount === 1 ? '' : 's')
}

/**
 * Show a turn indicator briefly.
 * @param {'hearing'|'deaf'} speaker
 * @param {boolean} [translating]
 */
function showTurn(speaker, translating) {
  if (!turnEl) return
  turnEl.classList.remove('hidden', 'hearing-turn', 'deaf-turn')
  if (speaker === 'hearing') {
    turnEl.className = 'turn-indicator hearing-turn'
    turnEl.textContent = translating ? 'Hearing — translating…' : 'Hearing is speaking'
  } else {
    turnEl.className = 'turn-indicator deaf-turn'
    turnEl.textContent = 'Signer is communicating'
  }
  clearTimeout(turnEl._hideTimer)
  turnEl._hideTimer = setTimeout(() => turnEl.classList.add('hidden'), 3000)
}

// Clean disconnect on window close
window.addEventListener('beforeunload', function () {
  window.amandla.disconnect()
})